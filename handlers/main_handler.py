from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from typing import Optional
from keyboards.main_keyboards import to_home_keyboard
from keyboards.role_keyboards import seller_keyboard, user_keyboard, admin_keyboard

from utils.database import Database
from utils.variables import ADMIN_IDS

router = Router(name='main')
db = Database()

ITEMS_PER_PAGE = 5  

class FilterStates(StatesGroup):
    waiting_for_filter = State()
    waiting_for_field_input = State()

@router.message(CommandStart())
async def start_command(message: Message):
    telegram_id = str(message.from_user.id)
    user = db.get_user(telegram_id=telegram_id)
    
    if not user:
        try:
            db.add_user(telegram_id=telegram_id, username=message.from_user.username)
            user = db.get_user(telegram_id=telegram_id)
            
        except Exception as e:
            await message.answer(
                "❌ Произошла ошибка при создании вашего профиля. Попробуйте позже.",
                reply_markup=to_home_keyboard()
            )
            print(f"Ошибка в start_command: {e}")
            return

    await show_main_menu(message, user)
    
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "🌟 Панель администратора доступна:\n"
            "- Рассылка сообщений\n"
            "- Просмотр жалоб\n"
            "- Управление типами услуг",
            reply_markup=admin_keyboard()
        )

async def show_main_menu(message: Message, user, name: Optional[str] = None) -> None:
    """Показывает главное меню в зависимости от роли пользователя"""
    if not user:
        keyboard = user_keyboard()
    elif db.is_seller(telegram_id=str(user[1])):  # Используем индекс 1 для получения telegram_id из кортежа
        keyboard = seller_keyboard()
    else:
        keyboard = user_keyboard()

    if name:
        welcome_text = f"👋 Здравствуйте, {name}!\n\n"
    else:
        welcome_text = f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
    
    try:
        await message.answer(welcome_text, reply_markup=keyboard)
    except Exception as e:
        print(f"Ошибка отображения меню: {e}")
        await message.answer(
            "❌ Произошла ошибка при отображении меню. Попробуйте еще раз.",
            reply_markup=to_home_keyboard()
        )

@router.callback_query(F.data == "go_to_home")
async def go_to_home(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата в главное меню"""
    await open_home(callback.message, state)
    
@router.message(F.text.in_(["Вернуться домой 🏠"]))
async def go_to_home_reply(message: Message, state: FSMContext):
    await open_home(message, state)


async def open_home(message: Message, state: FSMContext):
    try:
        await state.clear()
        
        user = db.get_user(telegram_id=str(message.from_user.id))
        if not user:
            try:
                await message.edit_text(
                    "❌ Ошибка получения данных пользователя. Попробуйте перезапустить бота командой /start",
                    reply_markup=to_home_keyboard()
                )
            except Exception as e:
                await message.answer(
                    "❌ Произошла ошибка при отображении меню. Попробуйте еще раз.",
                    reply_markup=to_home_keyboard()
                )
            return
            
        await show_main_menu(message, user, name=message.from_user.first_name)
        
        if message.from_user.id in ADMIN_IDS:
            await message.answer(
                "🌟 Панель администратора доступна:\n"
                "- Рассылка сообщений\n"
                "- Просмотр жалоб\n"
                "- Управление типами услуг",
                reply_markup=admin_keyboard()
            )
            
    except Exception as e:
        print(f"Ошибка в go_to_home: {e}")
        await message.edit_text(
            "❌ Произошла ошибка. Попробуйте еще раз или перезапустите бота командой /start",
            reply_markup=to_home_keyboard()
        )

@router.message(F.text == "/get_id")
async def get_id(message: Message):
    """Получение ID чата и пользователя"""
    await message.answer(
        f"🆔 ID чата: {message.chat.id}\n"
        f"👤 ID пользователя: {message.from_user.id}"
    )

