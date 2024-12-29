import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramBadRequest

from utils.database import Database
from utils.variables import ADMIN_IDS
from keyboards.main_keyboards import admin_keyboard

router = Router(name='admin')
db = Database()

USERS_PER_PAGE = 50  # Количество пользователей для рассылки на одной странице

class NewsletterStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()
    confirm = State()
    sending = State()

@router.callback_query(F.data == "start_broadcast")
async def start_newsletter(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer("❌ У вас нет прав администратора для выполнения этой команды")
        return

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔙 Отменить рассылку", callback_data="cancel_newsletter"))
    keyboard.row(InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu"))
    
    try:
        await callback.message.edit_text(
            "📝 Введите текст для массовой рассылки:\n\n"
            "Вы можете использовать базовое форматирование:\n"
            "- *текст* для жирного\n"
            "- _текст_ для курсива\n"
            "- `текст` для моноширинного",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "📝 Введите текст для массовой рассылки:\n\n"
            "Вы можете использовать базовое форматирование:\n"
            "- *текст* для жирного\n"
            "- _текст_ для курсива\n"
            "- `текст` для моноширинного",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    
    await state.set_state(NewsletterStates.waiting_for_text)

@router.message(NewsletterStates.waiting_for_text)
async def process_text(message: Message, state: FSMContext):
    # Сохраняем текст
    await state.update_data(text=message.text)
    
    # Удаляем предыдущие сообщения
    await message.delete()
    try:
        await message.answer_message.delete()
    except:
        pass
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="➡️ Пропустить фото", callback_data="skip_photo"))
    keyboard.row(InlineKeyboardButton(text="🔙 Назад к вводу текста", callback_data="back_to_text"))
    keyboard.row(InlineKeyboardButton(text="🔙 Отменить рассылку", callback_data="cancel_newsletter"))
    keyboard.row(InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu"))
    
    await message.answer(
        "📸 Отправьте фотографию для рассылки или нажмите 'Пропустить фото':\n\n"
        "Рекомендуемый размер: 1280x720 пикселей",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(NewsletterStates.waiting_for_photo)

@router.callback_query(F.data == "back_to_text")
async def back_to_text(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔙 Отменить рассылку", callback_data="cancel_newsletter"))
    keyboard.row(InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu"))
    
    await callback.message.edit_text(
        "📝 Введите текст для массовой рассылки:\n\n"
        "Вы можете использовать базовое форматирование:\n"
        "- *текст* для жирного\n"
        "- _текст_ для курсива\n"
        "- `текст` для моноширинного",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    
    await state.set_state(NewsletterStates.waiting_for_text)

@router.message(NewsletterStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("text", "")
    
    await state.update_data(photo=message.photo[-1].file_id)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="✅ Подтвердить и начать", callback_data="confirm_newsletter"))
    keyboard.row(InlineKeyboardButton(text="🔄 Начать заново", callback_data="start_broadcast"))
    keyboard.row(InlineKeyboardButton(text="🔙 Отменить", callback_data="cancel_newsletter"))
    keyboard.row(InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu"))
    
    await message.answer("📢 Предпросмотр рассылки")
    await message.answer_photo(
        photo=message.photo[-1].file_id,
        caption=f"{text}",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(NewsletterStates.confirm)

@router.callback_query(F.data == "skip_photo")
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    text = data.get("text", "")
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="✅ Подтвердить и начать", callback_data="confirm_newsletter"))
    keyboard.row(InlineKeyboardButton(text="🔄 Начать заново", callback_data="start_broadcast"))
    keyboard.row(InlineKeyboardButton(text="🔙 Отменить", callback_data="cancel_newsletter"))
    keyboard.row(InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu"))
    
    await callback.message.answer("📢 Предпросмотр рассылки")
    await callback.message.answer(
        f"{text}",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(NewsletterStates.confirm)

@router.callback_query(F.data == "confirm_newsletter")
async def confirm_newsletter(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    text = data.get("text", "")
    photo = data.get("photo")
    
    users = db.cursor.execute("SELECT telegram_id FROM users").fetchall()
    total_users = len(users)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    
    sent_count = 0
    failed_count = 0
    
    status_message = await callback.message.answer(
        "📤 Начинаю рассылку...\n"
        f"Всего получателей: {total_users}"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu"))

    batch_size = 10  # Отправляем по 10 сообщений за раз
    for i in range(0, total_users, batch_size):
        batch_users = users[i:i + batch_size]
        
        for user in batch_users:
            try:
                if photo:
                    await callback.bot.send_photo(
                        chat_id=user[0],
                        photo=photo,
                        caption=text,
                        parse_mode="Markdown"
                    )
                else:
                    await callback.bot.send_message(
                        chat_id=user[0],
                        text=text,
                        parse_mode="Markdown"
                    )
                sent_count += 1
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user[0]}: {e}")
                failed_count += 1

            current_count = sent_count + failed_count
            if current_count % 5 == 0 or current_count == total_users:
                progress = (current_count / total_users) * 100
                current_page = (current_count // USERS_PER_PAGE) + 1
                try:
                    await status_message.edit_text(
                        f"📤 Рассылка в процессе...\n\n"
                        f"✅ Отправлено: {sent_count}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"📊 Прогресс: {progress:.1f}%\n"
                        f"📑 Страница {current_page} из {total_pages}",
                        reply_markup=keyboard.as_markup()
                    )
                except TelegramBadRequest:
                    continue

        # Небольшая задержка между батчами чтобы избежать флуда
        await asyncio.sleep(0.1)

    try:
        await status_message.edit_text(
            f"✅ Рассылка успешно завершена\n\n"
            f"📊 Статистика:\n"
            f"📨 Успешно отправлено: {sent_count}\n"
            f"❌ Ошибок доставки: {failed_count}\n"
            f"👥 Всего получателей: {total_users}",
            reply_markup=admin_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            f"✅ Рассылка успешно завершена\n\n"
            f"📊 Статистика:\n"
            f"📨 Успешно отправлено: {sent_count}\n"
            f"❌ Ошибок доставки: {failed_count}\n"
            f"👥 Всего получателей: {total_users}",
            reply_markup=admin_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "cancel_newsletter")
async def cancel_newsletter(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(
            "❌ Рассылка отменена\n"
            "Вы можете начать новую рассылку в любое время",
            reply_markup=admin_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "❌ Рассылка отменена\n"
            "Вы можете начать новую рассылку в любое время",
            reply_markup=admin_keyboard()
        )

@router.callback_query(F.data == "admin_menu")
async def return_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(
            "Админ панель:",
            reply_markup=admin_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "Админ панель:",
            reply_markup=admin_keyboard()
        )
