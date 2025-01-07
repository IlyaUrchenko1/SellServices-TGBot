from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

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
    """Обработка команды /start"""
    telegram_id = str(message.from_user.id)
    user = db.get_user(telegram_id=telegram_id)
    
    if not user:
        try:
            username = message.from_user.username
            if not username:
                import random
                adjectives = ["Epic", "Ninja", "Cool", "Super", "Mega", "Ultra", "Awesome", "Magic", "Cosmic", "Wild"]
                nouns = ["Unicorn", "Wizard", "Warrior", "Dragon", "Phoenix", "Tiger", "Panda", "Rocket", "Hero"]
                while True:
                    random_number = random.randint(100, 999)
                    username = f"{random.choice(adjectives)}{random.choice(nouns)}{random_number}"
                    if not db.get_user(username=username):
                        break
            
            db.add_user(telegram_id=telegram_id, username=username)
            user = db.get_user(telegram_id=telegram_id)
            
            await message.answer(
                "✅ Ваш профиль успешно создан!",
                reply_markup=to_home_keyboard()
            )
            
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

async def show_main_menu(message: Message, user) -> None:
    """Показывает главное меню в зависимости от роли пользователя"""
    if not user:
        keyboard = user_keyboard()
    elif db.is_seller(telegram_id=str(user[1])):  # Используем индекс 1 для получения telegram_id из кортежа
        keyboard = seller_keyboard()
    else:
        keyboard = user_keyboard()

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
    try:
        await state.clear()
        await callback.answer("🏠 Возвращаемся в главное меню")
        
        user = db.get_user(telegram_id=str(callback.from_user.id))
        if not user:
            await callback.message.edit_text(
                "❌ Ошибка получения данных пользователя. Попробуйте перезапустить бота командой /start",
                reply_markup=to_home_keyboard()
            )
            return
            
        await show_main_menu(callback.message, user)
        
        if callback.from_user.id in ADMIN_IDS:
            await callback.message.answer(
                "🌟 Панель администратора доступна:\n"
                "- Рассылка сообщений\n"
                "- Просмотр жалоб\n"
                "- Управление типами услуг",
                reply_markup=admin_keyboard()
            )
            
    except Exception as e:
        print(f"Ошибка в go_to_home: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка. Попробуйте еще раз или перезапустите бота командой /start",
            reply_markup=to_home_keyboard()
        )
