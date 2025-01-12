from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
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

COMPLAINTS_PER_PAGE = 5

class BanStates(StatesGroup):
    waiting_for_duration = State()
    waiting_for_reason = State()

def format_complaint_text(complaint: dict) -> str:
    """Форматирует текст жалобы для отображения"""
    creator = db.get_user(telegram_id=complaint['creator_telegram_id'])
    creator_username = creator[2] if creator else 'Неизвестно'
    
    base_text = (
        f"📝 Жалоба #{complaint['id']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 От: @{creator_username}\n"
        f"📅 Дата: {complaint['created_at']}\n"
        f"🔍 Тип: {'На сервис 🛍' if complaint['type'] == 'service' else 'На пользователя 👤'}\n"
        f"━━━━━━━━━━━━━━━\n"
    )
    
    if complaint['type'] == 'service':
        service = db.get_service_by_id(complaint['accused_service_id'])
        if service:
            base_text += f"🛍 Услуга: {service[3]}\n"  # title is at index 3
            seller = db.get_user(user_id=service[1])  # user_id is at index 1
            if seller:
                base_text += f"👤 Владелец: @{seller[2]}\n"  # username is at index 2
    else:
        accused = db.get_user(telegram_id=complaint['accused_telegram_id'])
        accused_username = accused[2] if accused else 'Неизвестно'  # username is at index 2
        base_text += f"👤 На пользователя: @{accused_username}\n"
        
    base_text += f"\n📄 Текст жалобы:\n{complaint['text']}"
    return base_text

def get_complaint_keyboard(complaint: dict, page: int, total_pages: int) -> InlineKeyboardBuilder:
    """Создает клавиатуру для жалобы"""
    kb = InlineKeyboardBuilder()
    
    # Кнопки действий
    kb.row(
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"dismiss_{complaint['id']}"),
        InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{complaint['id']}")
    )
    
    # Кнопки просмотра
    kb.row(InlineKeyboardButton(
        text="👤 Профиль отправителя", 
        url=f"tg://user?id={complaint['creator_telegram_id']}"
    ))
    
    if complaint['type'] == 'service':
        kb.row(InlineKeyboardButton(
            text="🛍 Просмотр услуги",
            callback_data=f"view_service_{complaint['accused_service_id']}"
        ))
    else:
        kb.row(InlineKeyboardButton(
            text="👤 Профиль обвиняемого",
            url=f"tg://user?id={complaint['accused_telegram_id']}"
        ))

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"complaints_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"complaints_page_{page+1}"))
    kb.row(*nav_buttons)

    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu"))
    return kb

@router.callback_query(F.data == "get_all_reports")
async def show_complaints(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
        
    complaints = db.get_complaints()
    if not complaints:
        await callback.message.edit_text(
            "📝 Активных жалоб нет",
            reply_markup=admin_keyboard()
        )
        return

    await show_complaints_page(callback.message, complaints, 0)
    await callback.answer()

async def show_complaints_page(message: Message, complaints: list, page: int):
    total_pages = (len(complaints) + COMPLAINTS_PER_PAGE - 1) // COMPLAINTS_PER_PAGE
    page = min(max(0, page), total_pages - 1)
    start_idx = page * COMPLAINTS_PER_PAGE
    complaint = complaints[start_idx]

    text = format_complaint_text(complaint)
    keyboard = get_complaint_keyboard(complaint, page, total_pages)

    try:
        # Проверяем тип сообщения перед редактированием
        if message.photo:
            # Если сообщение содержит фото, отправляем новое сообщение
            await message.answer(text, reply_markup=keyboard.as_markup())
            await message.delete()
        else:
            # Если сообщение текстовое, редактируем его
            await message.edit_text(text, reply_markup=keyboard.as_markup())
    except Exception as e:
        print(f"Error showing complaints: {e}")
        await message.answer(text, reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("complaints_page_"))
async def handle_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    complaints = db.get_complaints()
    await show_complaints_page(callback.message, complaints, page)
    await callback.answer()

@router.callback_query(F.data == "admin_menu")
async def return_to_admin_menu(callback: CallbackQuery):
    try:
        # Проверяем тип сообщения перед редактированием
        if callback.message.photo:
            # Если сообщение содержит фото, отправляем новое сообщение
            await callback.message.answer(
                "🔰 Админ-панель",
                reply_markup=admin_keyboard()
            )
            await callback.message.delete()
        else:
            # Если сообщение текстовое, редактируем его
            await callback.message.edit_text(
                "🔰 Админ-панель",
                reply_markup=admin_keyboard()
            )
    except Exception as e:
        print(f"Error returning to admin menu: {e}")
        await callback.message.answer(
            "🔰 Админ-панель",
            reply_markup=admin_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data.startswith("dismiss_"))
async def dismiss_complaint(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
        
    complaint_id = int(callback.data.split("_")[1])
    if db.delete_complaint(complaint_id):
        complaints = db.get_complaints()
        if complaints:
            await show_complaints_page(callback.message, complaints, 0)
        else:
            try:
                if callback.message.photo:
                    await callback.message.answer(
                        "📝 Активных жалоб больше нет",
                        reply_markup=admin_keyboard()
                    )
                    await callback.message.delete()
                else:
                    await callback.message.edit_text(
                        "📝 Активных жалоб больше нет",
                        reply_markup=admin_keyboard()
                    )
            except Exception as e:
                print(f"Error dismissing complaint: {e}")
                await callback.message.answer(
                    "📝 Активных жалоб больше нет",
                    reply_markup=admin_keyboard()
                )
        await callback.answer("✅ Жалоба отклонена")
    else:
        await callback.answer("❌ Ошибка при отклонении жалобы", show_alert=True)

class ComplaintAction(StatesGroup):
    waiting_for_action = State()
    waiting_for_duration = State()
    waiting_for_reason = State()

@router.callback_query(F.data.startswith("accept_"))
async def accept_complaint(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    complaint_id = int(callback.data.split("_")[1])
    complaint = db.get_complaints(complaint_id=complaint_id)[0]
    
    await state.update_data(complaint_id=complaint_id, complaint=complaint)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Предупреждение", callback_data="action_warning")],
        [InlineKeyboardButton(text="🕒 Временный бан", callback_data="action_temp_ban")],
        [InlineKeyboardButton(text="🚫 Перманентный бан", callback_data="action_perm_ban")],
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="action_cancel")]
    ])
    
    action_text = "пользователя" if complaint['type'] == 'user' else "услугу"
    await callback.message.edit_text(
        f"Выберите действие для жалобы на {action_text}:",
        reply_markup=keyboard
    )
    await state.set_state(ComplaintAction.waiting_for_action)

@router.callback_query(ComplaintAction.waiting_for_action)
async def process_action(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    action = callback.data.split("_")[1]
    data = await state.get_data()
    complaint = data['complaint']
    
    if action == "cancel":
        await state.clear()
        complaints = db.get_complaints()
        if complaints:
            await show_complaints_page(callback.message, complaints, 0)
        else:
            await callback.message.edit_text(
                "📝 Активных жалоб больше нет",
                reply_markup=admin_keyboard()
            )
        return

    if action == "warning":
        if complaint['type'] == 'user':
            await callback.message.answer(
                f"⚠️ Пользователю {complaint['accused_username']} отправлено предупреждение",
                reply_markup=admin_keyboard()
            )
            await callback.bot.send_message(
                complaint['accused_telegram_id'],
                "⚠️ Вам вынесено предупреждение от администрации. При повторном нарушении вы будете заблокированы."
            )
        else:
            await callback.message.answer(
                f"⚠️ Владельцу услуги отправлено предупреждение",
                reply_markup=admin_keyboard() 
            )
            await callback.bot.send_message(
                complaint['accused_telegram_id'],
                "⚠️ На вашу услугу поступила жалоба. При повторном нарушении услуга будет заблокирована."
            )
        db.delete_complaint(data['complaint_id'])
        await state.clear()
        return

    await state.update_data(action=action)
    
    if action == "temp_ban":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 час", callback_data="duration_1")],
            [InlineKeyboardButton(text="24 часа", callback_data="duration_24")],
            [InlineKeyboardButton(text="72 часа", callback_data="duration_72")],
            [InlineKeyboardButton(text="↩️ Отмена", callback_data="action_cancel")]
        ])
        await callback.message.edit_text(
            "Выберите длительность бана:",
            reply_markup=keyboard
        )
        await state.set_state(ComplaintAction.waiting_for_duration)
    else:  # permanent ban
        await callback.message.edit_text("Введите причину бана:")
        await state.set_state(ComplaintAction.waiting_for_reason)

@router.callback_query(ComplaintAction.waiting_for_duration)
async def process_duration(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == "action_cancel":
        await state.clear()
        complaints = db.get_complaints()
        await show_complaints_page(callback.message, complaints, 0)
        return

    duration = int(callback.data.split("_")[1])
    await state.update_data(duration=duration)
    await callback.message.edit_text("Введите причину бана:")
    await state.set_state(ComplaintAction.waiting_for_reason)

@router.message(ComplaintAction.waiting_for_reason)
async def process_reason(message: Message, state: FSMContext):
    await message.answer()
    data = await state.get_data()
    complaint = data['complaint']
    action = data['action']
    reason = message.text
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if complaint['type'] == 'user':
        duration = None if action == "perm_ban" else data.get('duration')
        db.ban_user(
            complaint['accused_telegram_id'],
            current_time,
            duration,
            reason
        )
        ban_text = "навсегда" if action == "perm_ban" else f"на {duration} час(ов)"
        await message.bot.send_message(
            complaint['accused_telegram_id'],
            f"🚫 Вы были заблокированы {ban_text}\nПричина: {reason}"
        )
    else:
        if action == "perm_ban":
            db.delete_service(complaint['accused_service_id'], hard_delete=True)
        else:
            db.update_service_status(complaint['accused_service_id'], 'blocked')
        await message.bot.send_message(
            complaint['accused_telegram_id'],
            f"🚫 Ваша услуга была заблокирована\nПричина: {reason}"
        )

    db.delete_complaint(data['complaint_id'])
    await state.clear()
    
    complaints = db.get_complaints()
    if complaints:
        await show_complaints_page(message, complaints, 0)
    else:
        await message.answer(
            "📝 Активных жалоб больше нет",
            reply_markup=admin_keyboard()
        )
