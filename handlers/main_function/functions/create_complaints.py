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

def parse_complaint_data(callback_data: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Парсит данные из callback_data
    Returns:
        Tuple[complaint_type, accused_id, service_id]
    """
    try:
        parts = callback_data.split("_")
        if len(parts) < 4:
            return None, None, None
            
        complaint_type = parts[2]
        accused_id = parts[3]
        service_id = parts[4] if len(parts) > 4 else None
        
        return complaint_type, accused_id, service_id
    except Exception:
        return None, None, None

def validate_complaint_data(
    complaint_type: str,
    complainant_id: str,
    accused_id: str,
    service_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Проверяет валидность данных жалобы
    Returns:
        Tuple[is_valid: bool, error_message: str]
    """
    if complaint_type not in ['user', 'service']:
        return False, "Неверный тип жалобы"
        
    if complainant_id == accused_id:
        return False, "Нельзя подать жалобу на самого себя"
        
    accused_user = db.get_user(telegram_id=accused_id)
    if not accused_user:
        return False, "Пользователь не найден"
        
    if complaint_type == 'service' and service_id:
        service = db.get_service_by_id(int(service_id))
        if not service:
            return False, "Услуга не найдена"
            
    return True, ""

@router.callback_query(F.data.startswith("create_complaint_"))
async def create_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        complaint_type, accused_id, service_id = parse_complaint_data(callback.data)
        if not complaint_type or not accused_id:
            await callback.message.answer("Некорректные данные для создания жалобы")
            await callback.answer()
            return

        complainant_id = str(callback.from_user.id)
        
        # Валидация данных
        is_valid, error_msg = validate_complaint_data(
            complaint_type, 
            complainant_id,
            accused_id,
            service_id
        )
        
        if not is_valid:
            await callback.message.answer(error_msg)
            await callback.answer()
            return

        # Проверка существующих жалоб
        existing_complaints = db.get_complaints(
            status='pending',
            type=complaint_type,
            complainant_telegram_id=complainant_id,
            accused_telegram_id=accused_id,
            service_id=service_id if service_id else None
        )
        
        if existing_complaints:
            await callback.message.answer("У вас уже есть активная жалоба на этого пользователя/услугу")
            await callback.answer()
            return

        # Сохраняем данные в состояние
        await state.update_data(
            complaint_type=complaint_type,
            accused_telegram_id=accused_id,
            complainant_telegram_id=complainant_id,
            service_id=service_id
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
            await message.answer(
                "Текст жалобы слишком короткий. Опишите ситуацию подробнее (минимум 10 символов).",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_complaint")]
                ])
            )
            return
            
        data = await state.get_data()
        required_fields = ['complaint_type', 'accused_telegram_id', 'complainant_telegram_id']
        if not all(data.get(field) for field in required_fields):
            await message.answer("Ошибка: не найдены необходимые данные жалобы. Начните заново")
            await state.clear()
            return

        # Получаем пользователей
        complainant = db.get_user(telegram_id=data['complainant_telegram_id'])
        accused = db.get_user(telegram_id=data['accused_telegram_id'])
        
        if not complainant or not accused:
            await message.answer("Ошибка: пользователь не найден")
            await state.clear()
            return
            
        complainant_username = complainant[2] if len(complainant) > 2 else None
        accused_username = accused[2] if len(accused) > 2 else None
        
        if not complainant_username or not accused_username:
            await message.answer("Ошибка: не найден username пользователя")
            await state.clear()
            return
            
        success = db.add_complaint(
            type=data['complaint_type'],
            complainant_telegram_username=complainant_username,
            accused_telegram_username=accused_username,
            text=complaint_text,
            service_id=data.get('service_id')
        )
        
        await message.answer(
            "✅ Жалоба успешно отправлена и будет рассмотрена модераторами" if success
            else "❌ Произошла ошибка при сохранении жалобы. Попробуйте позже"
        )
        
        # Возврат в главное меню
        user = db.get_user(telegram_id=str(message.from_user.id))
        if user:
            await show_main_menu(message, user)
        else:
            await message.answer("Ошибка при возврате в главное меню")
        
        await state.clear()
        
    except Exception as e:
        print(f"Ошибка при сохранении жалобы: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже")
        await state.clear()

@router.callback_query(F.data == "cancel_complaint")
async def cancel_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
        await callback.message.edit_text("✅ Создание жалобы отменено")
        await callback.answer()
