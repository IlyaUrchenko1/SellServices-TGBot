from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def default_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='👁️ Смотреть объявления'))
    keyboard.add(KeyboardButton(text='👨‍🦰 Поддержка'))
    return keyboard #Это дефолтная клавиатура, она дополняется кнопками из вне

def admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text='Рассылка', callback_data='start_broadcast'))
    keyboard.row(InlineKeyboardButton(text='Просмотр жалоб', callback_data='get_all_reports'))

    return keyboard.as_markup()

def to_home_keyboard():
    keyboard = InlineKeyboardBuilder()
    
    keyboard.add(InlineKeyboardButton(text="Вернуться домой 🏠", callback_data="go_to_home"))
    
    return keyboard.as_markup()

