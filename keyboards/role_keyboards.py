from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def seller_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='📈 Выставить свою услугу'))
    keyboard.add(KeyboardButton(text='Все мои услуги 📋'))
    return keyboard.as_markup(resize_keyboard=True)

def admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text='Рассылка', callback_data='start_broadcast'))
    keyboard.row(InlineKeyboardButton(text='Просмотр жалоб', callback_data='get_all_reports'))
    keyboard.row(InlineKeyboardButton(text='Создать новый тип услуги', callback_data='create_service_type'))
    return keyboard.as_markup()

def default_user_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text='👁️ Смотреть объявления'))
    keyboard.add(KeyboardButton(text='👨‍🦰 Поддержка'))
    return keyboard.as_markup(resize_keyboard=True)

def to_home_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Вернуться домой 🏠", callback_data="go_to_home"))
    return keyboard.as_markup() 