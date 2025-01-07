from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from utils.database import Database
from utils.variables import ADMIN_IDS
from keyboards.role_keyboards import admin_keyboard
router = Router(name='admin')
db = Database()

COMPLAINTS_PER_PAGE = 1

class BanStates(StatesGroup):
    waiting_for_duration = State()
    waiting_for_reason = State()

def get_complaints_keyboard(complaints: list, page: int, total_pages: int, complaint_data: dict) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    
    # Action buttons
    keyboard.row(
        keyboard.button(text="❌ Отклонить", callback_data=f"dismiss_{complaint_data['complainant_username']}"),
        keyboard.button(text="🚫 Забанить", callback_data=f"ban_{complaint_data['accused_username']}_{complaint_data['complainant_username']}")
    )

    # Navigation buttons if multiple pages
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(keyboard.button(text="⬅️ Назад", callback_data=f"complaints_page_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(keyboard.button(text="Вперед ➡️", callback_data=f"complaints_page_{page+1}"))
        if nav_buttons:
            keyboard.row(*nav_buttons)
        keyboard.row(keyboard.button(text=f"📄 {page + 1}/{total_pages}", callback_data="current_page"))

    # Return buttons
    keyboard.row(keyboard.button(text="🔙 В админ меню", callback_data="admin_menu"))
    keyboard.row(keyboard.button(text="🏠 На главную", callback_data="go_to_home"))

    return keyboard

@router.callback_query(F.data == "get_all_reports")
async def show_complaints(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
        
    complaints = db.get_complaints()
    
    if not complaints:
        await callback.message.edit_text(
            "📝 На данный момент жалоб нет",
            reply_markup=admin_keyboard()
        )
        return

    await show_complaints_page(callback.message, complaints, 0)
    await callback.answer()

async def show_complaints_page(message: Message, complaints: list, page: int):
    if not complaints:
        await message.edit_text(
            "📝 На данный момент жалоб нет",
            reply_markup=admin_keyboard()
        )
        return

    total_pages = len(complaints)
    if page >= total_pages:
        page = 0
    elif page < 0:
        page = total_pages - 1

    complaint = complaints[page]
    complaint_data = {
        'complaint_id': complaint[0],
        'complainant_username': complaint[1],
        'accused_username': complaint[2],
        'date': complaint[3],
        'text': complaint[4]
    }

    complaint_text = (
        f"📝 Жалоба #{complaint_data['complaint_id']}\n\n"
        f"От: @{complaint_data['complainant_username']}\n"
        f"На: @{complaint_data['accused_username']}\n"
        f"Дата: {complaint_data['date']}\n"
        f"Текст: {complaint_data['text']}"
    )

    keyboard = get_complaints_keyboard(complaints, page, total_pages, complaint_data)

    try:
        await message.edit_text(complaint_text, reply_markup=keyboard.as_markup())
    except Exception as e:
        print(f"Error in show_complaints_page: {e}")
        await message.answer(complaint_text, reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("complaints_page_"))
async def handle_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    complaints = db.get_complaints()
    await show_complaints_page(callback.message, complaints, page)
    await callback.answer()

@router.callback_query(F.data == "admin_menu")
async def return_to_admin_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔰 Админ-панель\nВыберите действие:",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("dismiss_"))
async def dismiss_complaint(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
        
    complainant_username = callback.data.split("_")[1]
    try:
        db.delete_complaint_by_complainant_telegram_username(complainant_username)
        complaints = db.get_complaints()
        
        if complaints:
            await show_complaints_page(callback.message, complaints, 0)
            await callback.answer("✅ Жалоба отклонена")
        else:
            await callback.message.edit_text(
                "📝 Больше жалоб нет",
                reply_markup=admin_keyboard()
            )
            await callback.answer()
    except Exception as e:
        print(f"Error in dismiss_complaint: {e}")
        await callback.answer("❌ Произошла ошибка при отклонении жалобы", show_alert=True)

@router.callback_query(F.data.startswith("ban_"))
async def start_ban_process(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
        
    _, username, complaint_username = callback.data.split("_")
    
    await state.update_data(username=username, complaint_username=complaint_username)
    await state.set_state(BanStates.waiting_for_duration)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(keyboard.button(text="🔙 Отмена", callback_data="cancel_ban"))
    
    await callback.message.edit_text(
        "⏰ Введите длительность бана в часах (целое число):",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_ban")
async def cancel_ban(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    complaints = db.get_complaints()
    await show_complaints_page(callback.message, complaints, 0)
    await callback.answer("❌ Процесс бана отменен")

@router.message(BanStates.waiting_for_duration)
async def process_ban_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(
            "❌ Пожалуйста, введите целое число часов\n"
            "Или нажмите кнопку отмены ниже"
        )
        return
        
    hours = int(message.text)
    await state.update_data(ban_hours=hours)
    await state.set_state(BanStates.waiting_for_reason)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(keyboard.button(text="🔙 Отмена", callback_data="cancel_ban"))
    
    await message.answer(
        "📝 Введите причину бана:",
        reply_markup=keyboard.as_markup()
    )

@router.message(BanStates.waiting_for_reason)
async def process_ban_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    complaint_username = data['complaint_username']
    ban_hours = data['ban_hours']
    ban_reason = message.text
    
    user = db.get_user(username=username)
    if not user:
        await message.answer(
            "❌ Пользователь не найден",
            reply_markup=admin_keyboard()
        )
        await state.clear()
        return

    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.ban_user(user[1], current_time, ban_hours, ban_reason)
        db.delete_complaint_by_complainant_telegram_username(complaint_username)
        
        # Notify banned user
        try:
            await message.bot.send_message(
                user[1],
                f"⛔️ Ваш аккаунт заблокирован на {ban_hours} часов\n"
                f"📝 Причина: {ban_reason}\n\n"
                "❗️ Если вы считаете, что произошла ошибка - обратитесь в поддержку"
            )
        except Exception as e:
            print(f"Failed to notify banned user: {e}")

        complaints = db.get_complaints()
        if complaints:
            await show_complaints_page(message, complaints, 0)
        else:
            await message.answer(
                f"✅ Пользователь @{username} забанен на {ban_hours} часов\n"
                f"📝 Причина: {ban_reason}\n\n"
                "Больше жалоб нет",
                reply_markup=admin_keyboard()
            )
    except Exception as e:
        print(f"Error in process_ban_reason: {e}")
        await message.answer(
            "❌ Произошла ошибка при бане пользователя",
            reply_markup=admin_keyboard()
        )
    finally:
        await state.clear()
