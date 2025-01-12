from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from utils.database import Database
from handlers.main_handler import show_main_menu
from typing import Optional, Dict, Tuple

router = Router(name='create_complaints')
db = Database()

class ComplaintStates(StatesGroup):
    waiting_for_text = State()

def parse_complaint_data(callback_data: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Парсит данные из callback_data
    Returns:
        Tuple[complaint_type, accused_telegram_id, accused_service_id]
    """
    try:
        parts = callback_data.split("_")
        if len(parts) < 4:
            return None, None, None
            
        complaint_type = parts[2]  # user или service
        accused_telegram_id = parts[3]
        accused_service_id = int(parts[4]) if len(parts) > 4 else None
        
        return complaint_type, accused_telegram_id, accused_service_id
    except Exception:
        return None, None, None

def validate_complaint_data(
    complaint_type: str,
    creator_telegram_id: str,
    accused_telegram_id: Optional[str] = None,
    accused_service_id: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Проверяет валидность данных жалобы
    Returns:
        Tuple[is_valid: bool, error_message: str]
    """
    if complaint_type not in ['user', 'service']:
        return False, "Неверный тип жалобы"
        
    if complaint_type == 'user':
        if not accused_telegram_id:
            return False, "Не указан ID пользователя"
            
        if creator_telegram_id == accused_telegram_id:
            return False, "Нельзя подать жалобу на самого себя"
            
        if not db.get_user(telegram_id=accused_telegram_id):
            return False, "Пользователь не найден"
            
    elif complaint_type == 'service':
        if not accused_service_id:
            return False, "Не указан ID услуги"
            
        service = db.get_services(service_id=accused_service_id)
        if not service:
            return False, "Услуга не найдена"
            
    return True, ""

@router.callback_query(F.data.startswith("create_complaint_"))
async def create_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        complaint_type, accused_telegram_id, accused_service_id = parse_complaint_data(callback.data)
        if not complaint_type:
            await callback.message.answer("Некорректные данные для создания жалобы")
            await callback.answer()
            return

        creator_telegram_id = str(callback.from_user.id)
        
        # Валидация данных
        is_valid, error_msg = validate_complaint_data(
            complaint_type, 
            creator_telegram_id,
            accused_telegram_id,
            accused_service_id
        )
        
        if not is_valid:
            await callback.message.answer(error_msg)
            await callback.answer()
            return

        # Сохраняем данные в состояние
        await state.update_data(
            complaint_type=complaint_type,
            creator_telegram_id=creator_telegram_id,
            accused_telegram_id=accused_telegram_id,
            accused_service_id=accused_service_id
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_complaint")]
        ])
        
        await state.set_state(ComplaintStates.waiting_for_text)
        await callback.message.answer(
            "Опишите причину жалобы.\nУкажите конкретные факты и детали ситуации.",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка при создании жалобы: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже")
        await state.clear()
        await callback.answer()

@router.message(ComplaintStates.waiting_for_text)
async def process_complaint_text(message: Message, state: FSMContext) -> None:
    try:
        complaint_text = message.text.strip()
        if len(complaint_text) < 10:
            await message.edit_text(
                "Текст жалобы слишком короткий. Опишите ситуацию подробнее (минимум 10 символов).",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_complaint")]
                ])
            )
            return
            
        data = await state.get_data()
        
        success = db.add_complaint(
            type=data['complaint_type'],
            creator_telegram_id=data['creator_telegram_id'],
            text=complaint_text,
            accused_telegram_id=data.get('accused_telegram_id'),
            accused_service_id=data.get('accused_service_id')
        )
        
        await message.edit_text(
            "✅ Жалоба успешно отправлена и будет рассмотрена модераторами" if success
            else "❌ Произошла ошибка при сохранении жалобы. Попробуйте позже"
        )

        # Возврат в главное меню
        user = db.get_user(telegram_id=str(message.from_user.id))
        if user:
            await show_main_menu(message, user)
        else:
            await message.edit_text("Ошибка при возврате в главное меню")
        
        await state.clear()
        
    except Exception as e:
        print(f"Ошибка при сохранении жалобы: {e}")
        await message.edit_text("Произошла ошибка. Попробуйте позже")
        await state.clear()

@router.callback_query(F.data == "cancel_complaint")
async def cancel_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
        await callback.message.edit_text("✅ Создание жалобы отменено")
        await callback.answer()
