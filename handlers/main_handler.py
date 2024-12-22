from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton

from keyboards.main_keyboards import default_start_keyboard, admin_keyboard
from utils.database import Database
from utils.variables import ADMIN_IDS

router = Router()
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
        await message.reply("По скольку вы админ, вы можете использовать функционал ниже", reply_markup=keyboard)

async def show_main_menu(message: Message, telegram_id: int, user, page: int = 0):
    keyboard = default_start_keyboard()

    if db.is_seller(telegram_id=telegram_id):
        keyboard.add(KeyboardButton(text='📈 Выставить свою услугу'))
        
        services = db.get_services_by_user(user_id=user[0])
        if services:
            keyboard.add(KeyboardButton(text='Все мои услуги 📋'))
            
            # Добавляем пагинацию для услуг
            start_idx = page * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_services = services[start_idx:end_idx]
            total_pages = (len(services) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            
            services_text = "Ваши услуги:\n\n"
            for service in page_services:
                services_text += f"• {service['name']}\n"
                
            services_text += f"\nСтраница {page + 1} из {total_pages}"
            
            # Создаем клавиатуру с кнопками навигации
            nav_keyboard = InlineKeyboardBuilder()
            
            if page > 0:
                nav_keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"services_page_{page-1}"))
            if page < total_pages - 1:
                nav_keyboard.add(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"services_page_{page+1}"))
                
            await message.answer(services_text, reply_markup=nav_keyboard.as_markup())
    else:
        keyboard.add(KeyboardButton(text="💲 Стать продавцом"))

    reply_markup = keyboard.as_markup(resize_keyboard=True)

    await message.reply(
        f"Привет, {message.from_user.first_name}!\nЭто бот для продажи товаров и услуг\n",
        reply_markup=reply_markup
    )

@router.callback_query(F.data.startswith("services_page_"))
async def handle_services_pagination(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split("_")[2])
    telegram_id = callback.from_user.id
    user = db.get_user(telegram_id=telegram_id)
    await callback.message.delete()
    await show_main_menu(callback.message, telegram_id, user, page)

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
