from datetime import datetime
from typing import Optional
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.database import Database
from aiogram.types import Message, CallbackQuery
from aiogram import F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router(name='create_complaints')
db = Database()

class ComplaintStates(StatesGroup):
    waiting_for_text = State()

@router.callback_query(F.data.startswith("create_complaint_"))
async def create_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Создает новую жалобу на пользователя или услугу
    """
    try:
        # Получаем тип жалобы и username из callback data
        data_parts = callback.data.split("_")
        if len(data_parts) < 4:
            await callback.message.answer("Некорректные данные для создания жалобы.")
            return
            
        complaint_type = data_parts[2]
        accused_username = data_parts[3]

        # Проверяем валидность типа жалобы
        if complaint_type not in ['user', 'service']:
            await callback.message.answer("Неверный тип жалобы.")
            await callback.answer()
            return

        # Проверяем, что обвиняемый пользователь существует
        accused_user = db.get_user(username=accused_username)
        if not accused_user:
            await callback.message.answer("Пользователь, на которого вы хотите пожаловаться, не найден.")
            await callback.answer()
            return

        # Проверяем, не жалуется ли пользователь сам на себя
        complainant_username = callback.from_user.username
        if not complainant_username:
            await callback.message.answer("У вас должен быть установлен username в Telegram для подачи жалобы.")
            await callback.answer()
            return
            
        if complainant_username.lower() == accused_username.lower():
            await callback.message.answer("Вы не можете подать жалобу на самого себя.")
            await callback.answer()
            return

        # Сохраняем начальные данные в состояние
        await state.update_data(
            complaint_type=complaint_type,
            accused_username=accused_username,
            complainant_username=complainant_username
        )
        
        # Создаем клавиатуру для отмены
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_complaint")]
        ])
        
        # Запрашиваем текст жалобы
        await state.set_state(ComplaintStates.waiting_for_text)
        await callback.message.answer(
            "Пожалуйста, опишите причину жалобы.\n"
            "Укажите конкретные факты и детали ситуации.",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer("Произошла ошибка при создании жалобы. Попробуйте позже.")
        print(f"Ошибка при инициализации жалобы: {e}")
        await state.clear()
        await callback.answer()

@router.message(ComplaintStates.waiting_for_text)
async def process_complaint_text(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает текст жалобы и сохраняет жалобу в базу данных
    """
    try:
        # Получаем текст жалобы
        complaint_text = message.text.strip()
        if not complaint_text or len(complaint_text) < 10:
            await message.answer(
                "Текст жалобы слишком короткий. Пожалуйста, опишите ситуацию подробнее (минимум 10 символов).",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_complaint")]
                ])
            )
            return
            
        # Получаем сохраненные данные
        data = await state.get_data()
        complaint_type = data.get('complaint_type')
        accused_username = data.get('accused_username')
        complainant_username = data.get('complainant_username')
        
        if not all([complaint_type, accused_username, complainant_username]):
            await message.answer("Произошла ошибка: не найдены данные жалобы. Попробуйте начать заново.")
            await state.clear()
            return
        
        # Создаем жалобу в базе данных
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        success = db.add_complaint(
            type=complaint_type,
            complainant_telegram_username=complainant_username,
            accused_telegram_username=accused_username,
            date=current_date,
            text=complaint_text
        )
        
        if success:
            await message.answer(
                "✅ Ваша жалоба успешно отправлена и будет рассмотрена модераторами.\n"
                "Спасибо за обращение!"
            )
        else:
            await message.answer(
                "❌ К сожалению, произошла ошибка при сохранении жалобы.\n"
                "Пожалуйста, попробуйте позже."
            )
            
        await state.clear()
        
    except Exception as e:
        await message.answer("Произошла ошибка при обработке жалобы. Попробуйте позже.")
        print(f"Ошибка при сохранении жалобы: {e}")
        await state.clear()

@router.callback_query(F.data == "cancel_complaint")
async def cancel_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменяет создание жалобы
    """
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await callback.message.edit_text("✅ Создание жалобы отменено.")
        await callback.answer()
