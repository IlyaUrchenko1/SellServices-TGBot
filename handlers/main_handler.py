from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.main_keyboards import start_keyboard_if_not_seller, start_keyboard_if_seller
from utils.database import Database

router = Router()
db = Database()


@router.message(CommandStart())
async def start_command(message: Message):
    telegram_id = message.from_user.id

    if not db.user_exists(telegram_id=telegram_id):
        try:
            db.add_user(telegram_id)
        except Exception as e:
            await message.reply("❌ Произошла ошибка при создании вашего профиля. Попробуйте позже.")
            print(f"Ошибка в start_command: {e}")
            
    is_seller = db.is_seller(telegram_id=telegram_id)
    keyboard = start_keyboard_if_seller() if is_seller else start_keyboard_if_not_seller()
    await message.reply(
        f"Привет, {message.from_user.first_name}!\nЭто бот для продажи товаров и услуг\n",
        reply_markup=keyboard
    )
        
    
    
# Обработчик кнопки "Вернуться домой 🏠"
@router.callback_query(F.data == "go_home")
async def go_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=start_keyboard_if_not_seller())

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
            
        

