from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from utils.database import Database

router = Router(name='create_complaints')
db = Database()

class ComplaintStates(StatesGroup):
    waiting_for_text = State()

@router.callback_query(F.data.startswith("create_complaint_"))
async def create_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        data_parts = callback.data.split("_")
        if len(data_parts) < 4:
            await callback.message.answer("Некорректные данные для создания жалобы.")
            return
            
        complaint_type = data_parts[2]
        accused_username = data_parts[3]

        if complaint_type not in ['user', 'service']:
            await callback.message.answer("Неверный тип жалобы.")
            await callback.answer()
            return

        accused_user = db.get_user(username=accused_username)
        if not accused_user:
            await callback.message.answer("Пользователь не найден.")
            await callback.answer()
            return

        complainant_username = callback.from_user.username
        if not complainant_username:
            await callback.message.answer("Установите username в Telegram для подачи жалобы.")
            await callback.answer()
            return
            
        if complainant_username.lower() == accused_username.lower():
            await callback.message.answer("Нельзя подать жалобу на самого себя.")
            await callback.answer()
            return

        await state.update_data(
            complaint_type=complaint_type,
            accused_username=accused_username,
            complainant_username=complainant_username
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
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
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
        if not all([data.get(field) for field in ['complaint_type', 'accused_username', 'complainant_username']]):
            await message.answer("Ошибка: не найдены данные жалобы. Начните заново.")
            await state.clear()
            return
        
        success = db.add_complaint(
            type=data['complaint_type'],
            complainant_telegram_username=data['complainant_username'],
            accused_telegram_username=data['accused_username'],
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            text=complaint_text
        )
        
        await message.answer(
            "✅ Жалоба успешно отправлена и будет рассмотрена модераторами." if success
            else "❌ Произошла ошибка при сохранении жалобы. Попробуйте позже."
        )
        await state.clear()
        
    except Exception as e:
        print(f"Ошибка при сохранении жалобы: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()

@router.callback_query(F.data == "cancel_complaint")
async def cancel_complaint(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
        await callback.message.edit_text("✅ Создание жалобы отменено.")
        await callback.answer()
