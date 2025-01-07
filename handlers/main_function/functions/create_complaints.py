from datetime import datetime
from typing import Optional
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.database import Database
from aiogram.types import Message

class ComplaintStates(StatesGroup):
    waiting_for_text = State()

async def create_complaint(message: Message,
                         state: FSMContext, 
                         complaint_type: str,
                         accused_username: str,
                         db: Database) -> None:
    """
    Создает новую жалобу на пользователя или услугу
    
    Args:
        message: Сообщение от пользователя
        state: Состояние FSM
        complaint_type: Тип жалобы ('user' или 'service')
        accused_username: Username пользователя/владельца услуги, на которого подается жалоба
        db: Экземпляр базы данных
    """
    try:
        # Проверяем, что обвиняемый пользователь существует
        if not db.get_user(username=accused_username):
            await message.answer("Пользователь, на которого вы хотите пожаловаться, не найден.")
            return

        # Сохраняем начальные данные в состояние
        await state.update_data(
            complaint_type=complaint_type,
            accused_username=accused_username
        )
        
        # Запрашиваем текст жалобы
        await state.set_state(ComplaintStates.waiting_for_text)
        await message.answer(
            "Пожалуйста, опишите причину жалобы.\n"
            "Укажите конкретные факты и детали ситуации."
        )
        
    except Exception as e:
        await message.answer("Произошла ошибка при создании жалобы. Попробуйте позже.")
        print(f"Ошибка при инициализации жалобы: {e}")
        await state.clear()

async def process_complaint_text(message: Message,
                               state: FSMContext,
                               db: Database) -> None:
    """
    Обрабатывает текст жалобы и сохраняет жалобу в базу данных
    
    Args:
        message: Сообщение с текстом жалобы
        state: Состояние FSM
        db: Экземпляр базы данных
    """
    try:
        # Получаем текст жалобы
        complaint_text = message.text
        if not complaint_text or len(complaint_text.strip()) < 10:
            await message.answer(
                "Текст жалобы слишком короткий. Пожалуйста, опишите ситуацию подробнее (минимум 10 символов)."
            )
            return
            
        # Получаем сохраненные данные
        data = await state.get_data()
        complaint_type = data.get('complaint_type')
        accused_username = data.get('accused_username')
        
        if not complaint_type or not accused_username:
            await message.answer("Произошла ошибка: не найдены данные жалобы. Попробуйте начать заново.")
            await state.clear()
            return
        
        # Создаем жалобу в базе данных
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        complainant_username = message.from_user.username or str(message.from_user.id)
        
        # Проверяем, не жалуется ли пользователь сам на себя
        if complainant_username == accused_username:
            await message.answer("Вы не можете подать жалобу на самого себя.")
            await state.clear()
            return
        
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

async def cancel_complaint(message: Message, state: FSMContext) -> None:
    """
    Отменяет создание жалобы
    
    Args:
        message: Сообщение от пользователя
        state: Состояние FSM
    """
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("✅ Создание жалобы отменено.")
