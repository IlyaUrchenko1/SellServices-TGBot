from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def start_keyboard_if_not_seller() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()

    keyboard.add(KeyboardButton(text='👁️ Смотреть объявления')) 
    keyboard.add(KeyboardButton(text="💲 Стать продавцом"))
    keyboard.row(KeyboardButton(text='👨‍🦰 Поддержка'))

    return keyboard.as_markup(resize_keyboard=True)


def start_keyboard_if_seller() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()

    keyboard.add(KeyboardButton(text='👁️ Смотреть объявления')) 
    keyboard.add(KeyboardButton(text='📈 Выставить свою услугу')) 
    keyboard.row(KeyboardButton(text='👨‍🦰 Поддержка')) 

    return keyboard.as_markup(resize_keyboard=True)


def admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text='Рассылка', callback_data='start_broadcast'))
    keyboard.row(InlineKeyboardButton(text='Просмотр жалоб', callback_data='get_all_reports'))

    return keyboard.as_markup()

def to_home_keyboard():
    keyboard = InlineKeyboardBuilder()
    
    keyboard.add(InlineKeyboardButton(text="Вернуться домой 🏠", callback_data="go_to_home"))
    
    return keyboard.as_markup()

