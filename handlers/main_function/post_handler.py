from aiogram import Router, F
from aiogram.types import Message, WebAppInfo
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

router = Router()

@router.message(F.text == '📈 Выставить свою услугу')
async def start_post_service(message: Message):
    # Создаем клавиатуру с кнопкой для открытия веб-приложения
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="Опубликовать услугу",
        web_app=WebAppInfo(url="https://ya.ru")  # Replace with your actual web app URL
    ))
    
    await message.answer(
        "Нажмите кнопку ниже, чтобы открыть форму публикации услуги:",
        reply_markup=keyboard.as_markup()
    )
