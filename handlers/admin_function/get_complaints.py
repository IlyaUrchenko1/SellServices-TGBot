from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

from utils.database import Database
from utils.variables import ADMIN_IDS
from keyboards.main_keyboards import admin_keyboard

router = Router()
db = Database()

COMPLAINTS_PER_PAGE = 1  # Changed to show 1 complaint per page

class BanStates(StatesGroup):
    waiting_for_duration = State()
    waiting_for_reason = State()

@router.callback_query(F.data == "get_all_reports")
async def show_complaints(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для выполнения этой команды")
        return
        
    complaints = db.get_complaints()
    
    if not complaints:
        await callback.message.edit_text(
            "На данный момент жалоб нет",
            reply_markup=admin_keyboard()
        )
        return

    await show_complaints_page(callback.message, complaints, 0)

async def show_complaints_page(message: Message, complaints: list, page: int):
    if not complaints:
        await message.edit_text(
            "На данный момент жалоб нет",
            reply_markup=admin_keyboard()
        )
        return

    total_pages = len(complaints)
    if page >= total_pages:
        page = 0
    elif page < 0:
        page = total_pages - 1

    complaint = complaints[page]
    complaint_id = complaint[0]
    complainant_username = complaint[1]
    accused_username = complaint[2]
    date = complaint[3]
    text = complaint[4]

    keyboard = []
    nav_row = []

    # Add navigation buttons if there are multiple complaints
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"complaints_page_{page-1}"))
        nav_row.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"complaints_page_{page+1}"))
    
    # Add action buttons
    action_row = [
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"dismiss_{complainant_username}"),
        InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_{accused_username}_{complainant_username}")
    ]
    
    # Add return button
    return_row = [InlineKeyboardButton(text="🔙 Вернуться в админ меню", callback_data="admin_menu")]
    
    keyboard_rows = [action_row]
    if nav_row:
        keyboard_rows.append(nav_row)
    keyboard_rows.append(return_row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    complaint_text = (
        f"📝 Жалоба #{complaint_id}\n"
        f"От: {complainant_username}\n"
        f"На: {accused_username}\n"
        f"Дата: {date}\n"
        f"Текст: {text}\n\n"
        f"Страница {page + 1} из {total_pages}"
    )

    try:
        await message.edit_text(complaint_text, reply_markup=keyboard)
    except:
        await message.answer(complaint_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("complaints_page_"))
async def handle_pagination(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split("_")[2])
    complaints = db.get_complaints()
    await show_complaints_page(callback.message, complaints, page)

@router.callback_query(F.data == "admin_menu")
async def return_to_admin_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Админ панель:", reply_markup=admin_keyboard())

@router.callback_query(F.data.startswith("dismiss_"))
async def dismiss_complaint(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для выполнения этой команды", show_alert=True)
        return
        
    complaint_username = callback.data.split("_")[1]
    db.delete_complaint_by_complainant_telegram_username(complaint_username)
    
    # Get updated complaints list and show next complaint
    complaints = db.get_complaints()
    current_page = 0  # Reset to first page after dismissal
    await show_complaints_page(callback.message, complaints, current_page)
    await callback.answer("Жалоба удалена")

@router.callback_query(F.data.startswith("ban_"))
async def start_ban_process(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для выполнения этой команды", show_alert=True)
        return
        
    username = callback.data.split("_")[1]
    complaint_username = callback.data.split("_")[2]
    
    await state.update_data(username=username, complaint_username=complaint_username)
    await state.set_state(BanStates.waiting_for_duration)
    await callback.message.edit_text("Введите длительность бана в часах (целое число):")

@router.message(BanStates.waiting_for_duration)
async def process_ban_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите целое число часов")
        return
        
    hours = int(message.text)
    await state.update_data(ban_hours=hours)
    await state.set_state(BanStates.waiting_for_reason)
    await message.answer("Введите причину бана:")
    
@router.message(BanStates.waiting_for_reason)
async def process_ban_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    complaint_id = data['complaint_id']
    ban_hours = data['ban_hours']
    ban_reason = message.text
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    user = db.get_user(username=username)
    if not user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return

    # Ban user and delete complaint
    db.ban_user(user[1], current_time, ban_hours, ban_reason)  # Using telegram_id from user tuple
    db.delete_complaint_bycomplainant_telegram_username(complaint_id)
    
    # Notify banned user
    await message.bot.send_message(
        user[1], 
        f"❌ Ваш аккаунт заблокирован на {ban_hours} часов\n"
        f"Причина: {ban_reason}\n"
        "Если вы заблокированы по ошибке, пожалуйста, обратитесь в поддержку"
    )

    # Get updated complaints list and show next complaint
    complaints = db.get_complaints()
    if complaints:
        await show_complaints_page(message, complaints, 0)
    else:
        await message.answer(
            f"✅ Пользователь {username} забанен на {ban_hours} часов\n"
            f"Причина: {ban_reason}\n\n"
            "Больше жалоб нет",
            reply_markup=admin_keyboard()
        )
    
    await state.clear()
