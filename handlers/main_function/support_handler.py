from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.main_keyboards import to_home_keyboard

router = Router(name='support_handler')

class SupportState(StatesGroup):
    waiting_for_question = State()
    waiting_for_answer_for_user = State()

@router.message(F.text == "👨‍🦰 Поддержка")
async def support_command(message: Message):
    ask_answer = InlineKeyboardBuilder().add(
        InlineKeyboardButton(text="Связаться", callback_data='ask_a_issue')
    ).as_markup()
    await message.answer(
        """
				🧑‍💻 Часто задаваемые вопросы:

				**Сюда можно вставить любой текст по вашему желанию**
        """,
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        """
        Если у вас остались вопросы, нажмите на кнопку ниже, чтобы связаться с поддержкой.
        """,
        reply_markup=ask_answer
    )

@router.callback_query(F.data == "ask_a_issue")
async def ask_to_helper(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Введите ваш вопрос, и он будет передан в службу поддержки.",
        reply_markup=to_home_keyboard()
    )
    await state.set_state(SupportState.waiting_for_question)

@router.message(SupportState.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    group_chat_id = -1002464551959  # ID группы для пересылки вопросов
    if message.photo:
        await message.answer("К сожалению, нельзя пока-что отправлять фото. Отправьте только текст, пожалуйста.")
        return
    issue_text = message.text if message.text else "None"
    await message.delete()
    try:
        await message.bot.send_message(
            chat_id=group_chat_id,
            text=f"Вопрос от пользователя {message.from_user.full_name} (@{message.from_user.username}):\n\n{issue_text}",
            reply_markup=get_button_answer(message=message)
        )
        await message.answer("Ваш вопрос был отправлен в службу поддержки. Мы ответим вам в ближайшее время.")
        await state.clear()
    except Exception as e:
        await message.reply("🤖 Упс! Произошла ошибка. Мы уже ее исправляем, спасибо за понимание! ❤️")
        print(f"Ошибка в process_question: {e}")

@router.callback_query(F.data.startswith("answer_"))
async def handle_admin_answer_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        user_id = callback.data.split("_")[1]
        await state.update_data(id_for_answer=user_id)
        await callback.message.answer("Введите ответ для пользователя")
        await state.set_state(SupportState.waiting_for_answer_for_user)
    except ValueError:
        await callback.message.reply("Ошибка: некорректный ID пользователя")
    except Exception as e:
        await callback.message.reply("🤖 Упс! Произошла ошибка. Мы уже ее исправляем, спасибо за понимание! ❤️")
        print(f"Ошибка в handle_admin_answer_callback: {e}")

@router.message(SupportState.waiting_for_answer_for_user)
async def process_answer(message: Message, state: FSMContext):
    try:
        msg = message.text
        data = await state.get_data()
        user_id = data.get("id_for_answer")

        if not user_id:
            await message.reply("❌ Не удалось получить ID пользователя для ответа.")
            return

        await message.bot.send_message(chat_id=user_id, text=f"Ответ от поддержки:\n{msg}")
        await message.answer("✅ Ответ успешно отправлен пользователю.")
        await state.clear()
    except Exception as e:
        await message.reply("🤖 Упс! Произошла ошибка при отправке ответа.")
        print(f"Ошибка в process_answer: {e}")

def get_button_answer(message: Message) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    try:
        keyboard.row(InlineKeyboardButton(text="Ответить", callback_data=f"answer_{message.from_user.id}"))
    except Exception as e:
        print(f"Ошибка при создании кнопки ответа: {e}")
    return keyboard.as_markup()
