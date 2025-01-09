from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
from datetime import datetime, time
from typing import Optional
from utils.database import Database
from keyboards.role_keyboards import seller_keyboard, user_keyboard

router = Router()
db = Database()

class ProfileStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_name = State()
    waiting_for_work_time = State()
    waiting_for_work_days = State()

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message, telegram_id: Optional[int] = None):
    """Показывает профиль пользователя"""
    if telegram_id is None:
        user = db.get_user(telegram_id=str(message.from_user.id))
    else:
        user = db.get_user(telegram_id=str(telegram_id))
    
    if user is None:
        await message.answer("Ошибка: пользователь не найден")
        return
        
    # Распаковываем данные пользователя согласно структуре БД
    user_id, telegram_id, username, phone, is_seller, full_name, work_time_start, work_time_end, work_days = user
    
    # Получаем статистику жалоб
    complaints_stats = db.get_user_complaints_count(username)
    
    # Если пользователь продавец, получаем его активные услуги
    active_services_count = 0
    if is_seller:
        services = db.get_services(user_id=user_id, status='active')
        active_services_count = len(services) if services else 0
    
    # Форматируем рабочие дни
    days_map = {
        '1': 'Пн', '2': 'Вт', '3': 'Ср', '4': 'Чт',
        '5': 'Пт', '6': 'Сб', '7': 'Вс'
    }
    work_days_formatted = ', '.join(days_map[d] for d in work_days.split(',')) if work_days else 'Не указаны'
    
    # Формируем текст профиля
    profile_text = f"👤 <b>Ваш профиль</b>\n\n"
    profile_text += f"🆔 ID: {user_id}\n"
    profile_text += f"🆔 Telegram ID: {telegram_id}\n"
    profile_text += f"👤 Username: @{username}\n"
    profile_text += f"👨‍💼 Имя: {full_name or 'Не указано'}\n"
    profile_text += f"📱 Телефон: {phone or 'Не указан'}\n"
    profile_text += f"📊 Статус: {'Продавец' if is_seller else 'Покупатель'}\n"
    
    if is_seller:
        profile_text += f"\n⏰ Время работы: {work_time_start} - {work_time_end}\n"
        profile_text += f"📅 Рабочие дни: {work_days_formatted}\n"
        profile_text += f"📦 Активных услуг: {active_services_count}\n"
    
    profile_text += f"\n📝 Жалоб получено: {complaints_stats['received']}\n"
    profile_text += f"📝 Жалоб отправлено: {complaints_stats['sent']}\n"

    # Создаем клавиатуру с действиями профиля
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем кнопки в зависимости от заполненности полей
    if not phone:
        keyboard.button(text="📱 Указать телефон", callback_data="add_phone")
    else:
        keyboard.button(text="📱 Изменить телефон", callback_data="change_phone")
        
    if not full_name:
        keyboard.button(text="👤 Указать имя", callback_data="add_name")
    else:
        keyboard.button(text="👤 Изменить имя", callback_data="change_name")

    if is_seller:
        keyboard.button(text="⏰ Изменить время работы", callback_data="change_work_time")
        keyboard.button(text="📅 Изменить рабочие дни", callback_data="change_work_days")
    
    keyboard.adjust(2)  # Размещаем кнопки в два столбца
    
    await message.answer(profile_text, parse_mode="HTML", reply_markup=keyboard.as_markup())

@router.callback_query(F.data == "change_work_time")
async def work_time_request(callback: CallbackQuery, state: FSMContext):
    """Запрос на изменение времени работы"""
    keyboard = InlineKeyboardBuilder()
    
    # Создаем кнопки для выбора времени начала работы
    hours = ['09', '10', '11', '12', '13', '14', '15', '16', '17', '18']
    for hour in hours:
        keyboard.button(text=f"{hour}:00", callback_data=f"start_time_{hour}")
    
    keyboard.button(text="🔙 Отмена", callback_data="cancel_input")
    keyboard.adjust(5)  # 5 кнопок в ряд
    
    await state.set_state(ProfileStates.waiting_for_work_time)
    await callback.message.edit_text(
        "⏰ Выберите время начала работы:",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(lambda c: c.data.startswith("start_time_"))
async def process_start_time(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени начала работы"""
    start_time = callback.data.split('_')[2]
    await state.update_data(start_time=start_time)
    
    keyboard = InlineKeyboardBuilder()
    hours = ['17', '18', '19', '20', '21', '22', '23', '00']
    for hour in hours:
        keyboard.button(text=f"{hour}:00", callback_data=f"end_time_{hour}")
    
    keyboard.button(text="🔙 Отмена", callback_data="cancel_input")
    keyboard.adjust(4)
    
    await callback.message.edit_text(
        f"⏰ Начало работы: {start_time}:00\nВыберите время окончания работы:",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(lambda c: c.data.startswith("end_time_"))
async def process_end_time(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени окончания работы"""
    end_time = callback.data.split('_')[2]
    data = await state.get_data()
    start_time = data['start_time']
    
    try:
        user = db.get_user(telegram_id=str(callback.from_user.id))
        if not user:
            raise Exception("Пользователь не найден")
            
        # Обновляем время работы в БД
        db.update_user(
            user_id=user[0],
            work_time_start=f"{start_time}:00",
            work_time_end=f"{end_time}:00"
        )
        
        await state.clear()
        await callback.message.edit_text(
            f"✅ Время работы успешно обновлено!\n"
            f"⏰ {start_time}:00 - {end_time}:00"
        )
        
        # Отправляем новое сообщение с обновленным профилем
        await show_profile(callback.message, callback.from_user.id)
        
    except Exception as e:
        print(f"Ошибка при обновлении времени работы: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при обновлении времени работы")
        await state.clear()

@router.callback_query(F.data == "change_work_days")
async def work_days_request(callback: CallbackQuery, state: FSMContext):
    """Запрос на изменение рабочих дней"""
    user = db.get_user(telegram_id=str(callback.from_user.id))
    current_days = set(user[8].split(',')) if user[8] else set()
    
    keyboard = InlineKeyboardBuilder()
    days = {
        '1': 'Пн', '2': 'Вт', '3': 'Ср', '4': 'Чт',
        '5': 'Пт', '6': 'Сб', '7': 'Вс'
    }
    
    for day_num, day_name in days.items():
        status = '✅' if day_num in current_days else '⬜️'
        keyboard.button(
            text=f"{status} {day_name}",
            callback_data=f"toggle_day_{day_num}"
        )
    
    keyboard.button(text="✅ Готово", callback_data="save_work_days")
    keyboard.button(text="🔙 Отмена", callback_data="cancel_input")
    
    keyboard.adjust(4, 3, 2)  # 4 кнопки в первом ряду, 3 во втором, 2 в третьем
    
    await state.set_state(ProfileStates.waiting_for_work_days)
    await state.update_data(selected_days=list(current_days))
    
    await callback.message.edit_text(
        "📅 Выберите рабочие дни:\n"
        "Нажмите на день для выбора/отмены",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(lambda c: c.data.startswith("toggle_day_"))
async def toggle_work_day(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора/отмены рабочего дня"""
    day = callback.data.split('_')[2]
    data = await state.get_data()
    selected_days = set(data.get('selected_days', []))
    
    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.add(day)
    
    await state.update_data(selected_days=list(selected_days))
    
    # Обновляем клавиатуру
    keyboard = InlineKeyboardBuilder()
    days = {
        '1': 'Пн', '2': 'Вт', '3': 'Ср', '4': 'Чт',
        '5': 'Пт', '6': 'Сб', '7': 'Вс'
    }
    
    for day_num, day_name in days.items():
        status = '✅' if day_num in selected_days else '⬜️'
        keyboard.button(
            text=f"{status} {day_name}",
            callback_data=f"toggle_day_{day_num}"
        )
    
    keyboard.button(text="✅ Готово", callback_data="save_work_days")
    keyboard.button(text="🔙 Отмена", callback_data="cancel_input")
    
    keyboard.adjust(4, 3, 2)
    
    await callback.message.edit_text(
        "📅 Выберите рабочие дни:\n"
        "Нажмите на день для выбора/отмены",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(F.data == "save_work_days")
async def save_work_days(callback: CallbackQuery, state: FSMContext):
    """Сохранение выбранных рабочих дней"""
    try:
        data = await state.get_data()
        selected_days = data.get('selected_days', [])
        
        if not selected_days:
            await callback.message.edit_text(
                "❌ Необходимо выбрать хотя бы один рабочий день"
            )
            return
            
        user = db.get_user(telegram_id=str(callback.from_user.id))
        if not user:
            raise Exception("Пользователь не найден")
            
        # Сортируем дни и преобразуем в строку
        work_days = ','.join(sorted(selected_days))
        
        # Обновляем рабочие дни в БД
        db.update_user(
            user_id=user[0],
            work_days=work_days
        )
        
        await state.clear()
        await callback.message.edit_text("✅ Рабочие дни успешно обновлены!")
        
        # Отправляем новое сообщение с обновленным профилем
        await show_profile(callback.message, callback.from_user.id)
        
    except Exception as e:
        print(f"Ошибка при обновлении рабочих дней: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при обновлении рабочих дней")
        await state.clear()

# Оставляем существующие обработчики для телефона и имени без изменений