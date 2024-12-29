from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from keyboards.role_keyboards import seller_keyboard, admin_keyboard, default_user_keyboard, to_home_keyboard
from utils.database import Database
from utils.variables import ADMIN_IDS

router = Router(name='main')
db = Database()

ITEMS_PER_PAGE = 5

@router.message(CommandStart())
async def start_command(message: Message):
    telegram_id = message.from_user.id
    user = db.get_user(telegram_id=telegram_id)
    
    if not user:
        try:
            username = message.from_user.username
            if not username:
                # Генерируем уникальный username если его нет
                import random
                adjectives = ["Epic", "Ninja", "Cool", "Super", "Mega", "Ultra", "Awesome", "Magic", "Cosmic", "Wild"]
                nouns = ["Unicorn", "Wizard", "Warrior", "Dragon", "Phoenix", "Tiger", "Panda", "Rocket", "Hero"]
                while True:
                    random_number = random.randint(100, 999)
                    username = f"{random.choice(adjectives)}{random.choice(nouns)}{random_number}"
                    # Проверяем что такой username еще не существует
                    if not db.get_user(username=username):
                        break
            
            db.add_user(telegram_id=telegram_id, username=username)
        except Exception as e:
            await message.reply("❌ Произошла ошибка при создании вашего профиля. Попробуйте позже.")
            print(f"Ошибка в start_command: {e}")
            return

    await show_main_menu(message, telegram_id, user)

    if message.from_user.id in ADMIN_IDS:
        keyboard = admin_keyboard()
        await message.reply("🌟 Поскольку вы являетесь администратором, вы можете использовать следующий функционал: 👇✨", reply_markup=keyboard)

async def show_main_menu(message: Message, telegram_id: int, user, page: int = 0):
    if db.is_seller(telegram_id=telegram_id):
        keyboard = seller_keyboard()
        services = db.get_services(user_id=user[1])
        if services:
            # Логика для отображения услуг и пагинации
            pass
    else:
        keyboard = default_user_keyboard()

    await message.reply(
        f"Привет, {message.from_user.first_name}! 👋\nДобро пожаловать в наш бот!",
        reply_markup=keyboard
    )

# Обработчик кнопки "Вернуться домой 🏠"
@router.callback_query(F.data == "go_to_home")
async def go_to_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    
    telegram_id = callback.from_user.id
    user = db.get_user(telegram_id=telegram_id)
    await show_main_menu(callback.message, telegram_id, user)

@router.message(F.text == "/get_id")
async def get_chat_id(message: Message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        await message.answer(
            f"Chat id: *{chat_id}*\nYour id: *{user_id}*",
            parse_mode='Markdown'
        )
    except Exception as e:
        cid = message.chat.id
        await message.answer("Ошибка при получении ID.")

@router.message(CommandStart())
async def start_command(message: Message):
    user = db.get_user(telegram_id=message.from_user.id)
    
    if user:
        if user['role'] == 'admin':
            await message.answer("Добро пожаловать в админ панель!", reply_markup=admin_keyboard())
        elif user['role'] == 'seller':
            await message.answer("Добро пожаловать, продавец!", reply_markup=seller_keyboard())
        else:
            await message.answer("Добро пожаловать!", reply_markup=default_user_keyboard())
    else:
        await message.answer("Вы не зарегистрированы в системе.")
