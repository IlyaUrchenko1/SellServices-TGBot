from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import KeyboardButton

from keyboards.main_keyboards import default_start_keyboard, admin_keyboard
from utils.database import Database
from utils.variables import ADMIN_IDS

router = Router()
db = Database()


@router.message(CommandStart())
async def start_command(message: Message):
    telegram_id = message.from_user.id
    user = db.get_user(telegram_id=telegram_id)
    if not user:
        try:
            db.add_user(telegram_id)
            user = db.get_user(telegram_id=telegram_id)
        except Exception as e:
            await message.reply("❌ Произошла ошибка при создании вашего профиля. Попробуйте позже.")
            print(f"Ошибка в start_command: {e}")
            return

    keyboard = default_start_keyboard()

    if 1 == 1: #db.is_seller(telegram_id=telegram_id)
        keyboard.add(KeyboardButton(text='📈 Выставить свою услугу'))
        
        services = db.get_services_by_user(user_id=user[0])
        if services:
            keyboard.add(KeyboardButton(text='Все мои услуги 📋'))
    else:
        keyboard.add(KeyboardButton(text="💲 Стать продавцом"))

    reply_markup = keyboard.as_markup(resize_keyboard=True)

    await message.reply(
        f"Привет, {message.from_user.first_name}!\nЭто бот для продажи товаров и услуг\n",
        reply_markup=reply_markup
    )

    if message.from_user.id in ADMIN_IDS:
        keyboard = admin_keyboard()
        await message.reply("По скольку вы админ, вы можете использовать функционал ниже", reply_markup=keyboard)

# Обработчик кнопки "Вернуться домой 🏠"
@router.callback_query(F.data == "go_to_home")
async def go_to_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    
    telegram_id = callback.message.from_user.id
    user = db.get_user(telegram_id=telegram_id)
        
    keyboard = default_start_keyboard()

    if db.is_seller(telegram_id=telegram_id):
        keyboard.add(KeyboardButton(text='📈 Выставить свою услугу'))
        
        services = db.get_active_service_types(user_id=user[0])
        if services:
            keyboard.add(KeyboardButton(text='Все мои услуги 📋'))
    else:
        keyboard.add(KeyboardButton(text="💲 Стать продавцом"))

    reply_markup = keyboard.as_markup(resize_keyboard=True)
    
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=reply_markup)

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
            
        

