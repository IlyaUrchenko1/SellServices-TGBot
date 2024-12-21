from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from utils.database import Database
from utils.variables import ADMIN_IDS

router = Router()
db = Database()

class CreateServiceType(StatesGroup):
    waiting_for_name = State()
    waiting_for_field_name = State()
    waiting_for_field_type = State() 
    waiting_for_field_label = State()
    waiting_for_field_description = State()
    waiting_for_field_required = State()
    waiting_for_select_options = State()
    waiting_for_more_fields = State()

@router.callback_query(F.data == "create_service_type")
async def start_create_service_type(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.reply("❌ У вас нет прав администратора")
        return
        
    await state.set_state(CreateServiceType.waiting_for_name)
    await state.set_data({"fields": {}})
    await callback.message.answer(
        "📝 Введите название нового типа услуги\n\n"
        "Например: Репетитор, Мастер маникюра, Фотограф"
    )

@router.message(CreateServiceType.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await add_new_field(message, state)

async def add_new_field(message: Message, state: FSMContext):
    await state.set_state(CreateServiceType.waiting_for_field_name)
    await message.reply(
        "🔑 Введите техническое название поля (на английском)\n\n"
        "Примеры:\n"
        "- experience\n"
        "- education\n"
        "- skills\n\n"
        "Используйте только английские буквы, цифры или _"
    )

@router.message(CreateServiceType.waiting_for_field_name)
async def process_field_name(message: Message, state: FSMContext):
    field_name = message.text.lower().strip()
    if not field_name.replace("_", "").isalnum():
        await message.reply("❌ Некорректное название. Попробуйте еще раз")
        return
        
    await state.update_data(current_field_name=field_name)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="📝 Текст", callback_data="field_type:text"),
        InlineKeyboardButton(text="🔢 Число", callback_data="field_type:number"),
        InlineKeyboardButton(text="📋 Список", callback_data="field_type:select")
    )
    
    await state.set_state(CreateServiceType.waiting_for_field_type)
    await message.reply(
        "📊 Выберите тип данных для поля:",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(CreateServiceType.waiting_for_field_type)
async def process_field_type(callback: CallbackQuery, state: FSMContext):
    field_type = callback.data.split(":")[1]
    await state.update_data(current_field_type=field_type)
    await callback.message.delete()
    
    await state.set_state(CreateServiceType.waiting_for_field_label)
    await callback.message.answer(
        "💭 Введите название поля для пользователей\n\n"
        "Например: Опыт работы, Образование, Навыки"
    )

@router.message(CreateServiceType.waiting_for_field_label)
async def process_field_label(message: Message, state: FSMContext):
    await state.update_data(current_field_label=message.text)
    
    await state.set_state(CreateServiceType.waiting_for_field_description)
    await message.reply(
        "📝 Введите описание поля\n\n"
        "Это подсказка для пользователей о том, что нужно ввести"
    )

@router.message(CreateServiceType.waiting_for_field_description)
async def process_field_description(message: Message, state: FSMContext):
    await state.update_data(current_field_description=message.text)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="✅ Да", callback_data="required_true"),
        InlineKeyboardButton(text="❌ Нет", callback_data="required_false")
    )
    
    await state.set_state(CreateServiceType.waiting_for_field_required)
    await message.reply(
        "❓ Поле обязательно для заполнения?",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(CreateServiceType.waiting_for_field_required)
async def process_field_required(callback: CallbackQuery, state: FSMContext):
    required = callback.data.split("_")[1] == "true"
    data = await state.get_data()
    await callback.message.delete()
    
    if data["current_field_type"] == "select":
        await state.set_state(CreateServiceType.waiting_for_select_options)
        await callback.message.answer(
            "📝 Введите варианты для выбора через запятую\n\n"
            "Пример: Начинающий, Продвинутый, Эксперт"
        )
    else:
        await save_field(callback.message, state, required)

@router.message(CreateServiceType.waiting_for_select_options)
async def process_select_options(message: Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split(",") if opt.strip()]
    if len(options) < 2:
        await message.reply("❌ Укажите минимум 2 варианта")
        return
    await save_field(message, state, True, options)

async def save_field(message: Message, state: FSMContext, required: bool, options: list[str] = None):
    data = await state.get_data()
    
    field_data = {
        "type": data["current_field_type"],
        "label": data["current_field_label"],
        "description": data["current_field_description"],
        "required": required
    }
    
    if options:
        field_data["options"] = options
        
    fields = data.get("fields", {})
    fields[data["current_field_name"]] = field_data
    await state.update_data(fields=fields)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="➕ Добавить поле", callback_data="add_field"),
        InlineKeyboardButton(text="✅ Завершить", callback_data="finish")
    )
    
    await state.set_state(CreateServiceType.waiting_for_more_fields)
    await message.answer(
        "✅ Поле добавлено! Что дальше?",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(CreateServiceType.waiting_for_more_fields)
async def process_more_fields(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    
    if callback.data == "add_field":
        await add_new_field(callback.message, state)
    else:
        data = await state.get_data()
        if not data.get("fields"):
            await callback.message.answer("❌ Добавьте хотя бы одно поле!")
            await add_new_field(callback.message, state)
            return
            
        try:
            type_id = db.add_service_type(
                name=data["name"],
                created_by_id=str(callback.from_user.id),
                required_fields=data["fields"]
            )
            if type_id:
                await callback.message.answer("✅ Новый тип услуги успешно создан!")
            else:
                await callback.message.answer("❌ Не удалось создать тип услуги")
        except Exception as e:
            await callback.message.answer(f"❌ Ошибка: {str(e)}")
        finally:
            await state.clear()
