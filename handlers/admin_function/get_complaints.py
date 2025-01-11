from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import json

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
    base_text = (
        f"📝 Жалоба #{complaint['id']}\n"
        f"От: @{complaint['complainant_username']}\n"
        f"На: @{complaint['accused_username']}\n"
        f"Дата: {complaint['created_at']}\n"
        f"Статус: {complaint['status']}\n\n"
    )

    if complaint['type'] == 'service':
        service_info = (
            f"🔍 Информация о сервисе:\n"
            f"ID сервиса: {complaint['service_id']}\n"
            f"Название: {complaint['service_title']}\n\n"
        )
        base_text += service_info

    base_text += f"📄 Текст жалобы:\n{complaint['complaint_text']}"
    
    return base_text

def get_complaint_keyboard(complaint: dict, page: int, total_pages: int) -> InlineKeyboardBuilder:
    """Создает клавиатуру для жалобы"""
    keyboard = InlineKeyboardBuilder()
    
    # Кнопки действий для жалобы на сервис
    if complaint['type'] == 'service':
        keyboard.row(
            InlineKeyboardButton(
                text="👁 Просмотр сервиса", 
                callback_data=f"view_service_{complaint['service_id']}"
            ),
            InlineKeyboardButton(
                text="👤 Профиль продавца", 
                callback_data=f"view_user_{complaint['accused_username']}"
            )
        )
    # Кнопки действий для жалобы на пользователя
    else:
        keyboard.row(
            InlineKeyboardButton(
                text="👤 Профиль пользователя", 
                callback_data=f"view_user_{complaint['accused_username']}"
            )
        )

    # Кнопки модерации
    keyboard.row(
        InlineKeyboardButton(
            text="❌ Отклонить", 
            callback_data=f"dismiss_{complaint['id']}"
        ),
        InlineKeyboardButton(
            text="🚫 Забанить", 
            callback_data=f"ban_{complaint['accused_telegram_id']}_{complaint['id']}"
        )
    )

    # Навигация
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад", 
                callback_data=f"complaints_page_{page-1}"
            ))
        nav_buttons.append(InlineKeyboardButton(
            text=f"📄 {page + 1}/{total_pages}", 
            callback_data="current_page"
        ))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️", 
                callback_data=f"complaints_page_{page+1}"
            ))
        keyboard.row(*nav_buttons)

    keyboard.row(InlineKeyboardButton(text="🔙 В админ меню", callback_data="admin_menu"))
    
    return keyboard

@router.callback_query(F.data == "get_all_reports")
async def show_complaints(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
        
    complaints = db.get_complaints(status='pending')
    
    if not complaints:
        await callback.message.edit_text(
            "📝 На данный момент активных жалоб нет",
            reply_markup=admin_keyboard()
        )
        return

    await show_complaints_page(callback.message, complaints, 0)
    await callback.answer()

async def show_complaints_page(message: Message, complaints: list, page: int):
    total_pages = (len(complaints) + COMPLAINTS_PER_PAGE - 1) // COMPLAINTS_PER_PAGE
    
    if not complaints:
        await message.edit_text(
            "📝 Жалоб больше нет",
            reply_markup=admin_keyboard()
        )
        return

    page = min(max(0, page), total_pages - 1)
    start_idx = page * COMPLAINTS_PER_PAGE
    complaint = complaints[start_idx]

    text = format_complaint_text(complaint)
    keyboard = get_complaint_keyboard(complaint, page, total_pages)

    try:
        await message.edit_text(text, reply_markup=keyboard.as_markup())
    except Exception as e:
        print(f"Error in show_complaints_page: {e}")
        await message.answer(text, reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("view_service_"))
async def view_service(callback: CallbackQuery):
    service_id = int(callback.data.split("_")[2])
    service = db.get_service_by_id(service_id)
    
    if not service:
        await callback.answer("❌ Сервис не найден или удален", show_alert=True)
        return
        
    # Преобразуем результат в словарь
    service_dict = dict(service)
    
    # Загружаем JSON поля
    try:
        custom_fields = json.loads(service_dict.get('custom_fields', '{}'))
    except:
        custom_fields = {}
        
    text = (
        f"🔍 Сервис #{service_id}\n"
        f"Название: {service_dict['title']}\n"
        f"Описание: {custom_fields.get('description', 'Нет описания')}\n"
        f"Город: {service_dict['city']}\n"
        f"Район: {service_dict['district']}\n"
        f"Цена: {service_dict['price']}₽\n"
        f"Статус: {service_dict['status']}"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔙 Назад к жалобе", callback_data="get_all_reports"))
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("view_user_"))
async def view_user(callback: CallbackQuery):
    username = callback.data.split("_")[2]
    user = db.get_user(username=username)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
        
    # Преобразуем результат в словарь
    user_dict = dict(user)
    
    text = (
        f"👤 Профиль @{username}\n"
        f"Telegram ID: {user_dict['telegram_id']}\n"
        f"Телефон: {user_dict.get('number_phone', 'Не указан')}\n"
        f"Роль: {'Продавец' if user_dict.get('is_seller') else 'Покупатель'}\n"
        f"Дата регистрации: {user_dict.get('created_at', 'Не указана')}"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔙 Назад к жалобе", callback_data="get_all_reports"))
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("complaints_page_"))
async def handle_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    complaints = db.get_complaints(status='pending')
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
        
    complaint_id = int(callback.data.split("_")[1])
    
    try:
        db.update_complaint_status(
            complaint_id=complaint_id,
            status='rejected',
            resolved_by_id=callback.from_user.id
        )
        
        complaints = db.get_complaints(status='pending')
        if complaints:
            await show_complaints_page(callback.message, complaints, 0)
        else:
            await callback.message.edit_text(
                "📝 Активных жалоб больше нет",
                reply_markup=admin_keyboard()
            )
        await callback.answer("✅ Жалоба отклонена")
        
    except Exception as e:
        print(f"Error in dismiss_complaint: {e}")
        await callback.answer("❌ Ошибка при отклонении жалобы", show_alert=True)

@router.callback_query(F.data.startswith("ban_"))
async def start_ban_process(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
        
    telegram_id, complaint_id = callback.data.split("_")[1:]
    await state.update_data(telegram_id=telegram_id, complaint_id=complaint_id)
    await state.set_state(BanStates.waiting_for_duration)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_ban"))
    
    await callback.message.edit_text(
        "⏰ Введите длительность бана в часах (целое число):",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_ban")
async def cancel_ban(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    complaints = db.get_complaints(status='pending')
    await show_complaints_page(callback.message, complaints, 0)
    await callback.answer("❌ Процесс бана отменен")

@router.message(BanStates.waiting_for_duration)
async def process_ban_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_ban"))
        await message.answer(
            "❌ Пожалуйста, введите целое число часов\n"
            "Или нажмите кнопку отмены ниже",
            reply_markup=keyboard.as_markup()
        )
        return
        
    hours = int(message.text)
    await state.update_data(ban_hours=hours)
    await state.set_state(BanStates.waiting_for_reason)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_ban"))
    
    await message.answer(
        "📝 Введите причину бана:",
        reply_markup=keyboard.as_markup()
    )

@router.message(BanStates.waiting_for_reason)
async def process_ban_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = data['telegram_id']
    complaint_id = data['complaint_id']
    ban_hours = data['ban_hours']
    ban_reason = message.text
    
    user = db.get_user(telegram_id=telegram_id)
    if not user:
        await message.answer(
            "❌ Пользователь не найден",
            reply_markup=admin_keyboard()
        )
        await state.clear()
        return

    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Баним пользователя
        db.ban_user(telegram_id, current_time, ban_hours, ban_reason)
        
        # Обновляем статус жалобы
        db.update_complaint_status(
            complaint_id=int(complaint_id),
            status='resolved',
            resolved_by_id=message.from_user.id,
            resolution_text=f"Пользователь забанен на {ban_hours} часов. Причина: {ban_reason}"
        )
        
        # Деактивируем все услуги пользователя
        user_services = db.get_services(user_id=user['id'])
        if user_services:
            for service in user_services:
                db.update_service(service['id'], status='deactive')
        
        # Уведомляем забаненного пользователя
        try:
            await message.bot.send_message(
                telegram_id,
                f"⛔️ Ваш аккаунт заблокирован на {ban_hours} часов\n"
                f"📝 Причина: {ban_reason}\n\n"
                "❗️ Если вы считаете, что произошла ошибка - обратитесь в поддержку"
            )
        except Exception as e:
            print(f"Failed to notify banned user: {e}")

        complaints = db.get_complaints(status='pending')
        if complaints:
            await show_complaints_page(message, complaints, 0)
        else:
            await message.answer(
                f"✅ Пользователь с ID {telegram_id} забанен на {ban_hours} часов\n"
                f"📝 Причина: {ban_reason}\n\n"
                "Активных жалоб больше нет",
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
