from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def seller_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='👁️ Смотреть услуги'))
    keyboard.row(KeyboardButton(text='📈 Выставить свою услугу'))
    keyboard.add(KeyboardButton(text='📋 Все мои услуги'))
    keyboard.row(KeyboardButton(text='👤 Профиль'))
    keyboard.row(KeyboardButton(text='👨‍🦰 Поддержка'))

    return keyboard.as_markup(resize_keyboard=True, one_time_keyboard=False)

def admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Рассылка 📩', callback_data='start_broadcast'))
    keyboard.row(InlineKeyboardButton(text='Просмотр жалоб 📝', callback_data='get_all_reports'))
    keyboard.row(InlineKeyboardButton(text='Создать новый тип услуги 📈', callback_data='create_service_type'))
    return keyboard.as_markup()

def user_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='👁️ Смотреть услуги'))
    # keyboard.row(KeyboardButton(text='💲Стать продавцом')) - не нужно т.к будет платная подписка
    keyboard.row(KeyboardButton(text='👤 Профиль'))
    keyboard.row(KeyboardButton(text='👨‍🦰 Поддержка'))
    
    return keyboard.as_markup(resize_keyboard=True, one_time_keyboard=False)