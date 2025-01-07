from aiogram import Router, F
from aiogram.fsm.context import FSMContext 
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.database import Database
from utils.variables import ADMIN_IDS
import math
from keyboards.role_keyboards import admin_keyboard
router = Router(name='admin')
db = Database()

ITEMS_PER_PAGE = 5
RESERVED_FIELDS = {"title", "photo", "adress", "price"}

class CreateServiceType(StatesGroup):
    waiting_for_name = State()
    waiting_for_field_name = State()
    waiting_for_field_type = State()
    waiting_for_field_label = State() 
    waiting_for_field_description = State()
    waiting_for_field_required = State()
    waiting_for_select_options = State()
    waiting_for_more_fields = State()

def get_pagination_keyboard(total_items, current_page):
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    keyboard = InlineKeyboardBuilder()
    
    start_idx = (current_page - 1) * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
    
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{current_page-1}"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{current_page+1}"))
        
    if nav_buttons:
        keyboard.row(*nav_buttons)
        
    keyboard.row(InlineKeyboardButton(text=f"📄 {current_page}/{total_pages}", callback_data="current_page"))
    return keyboard.as_markup()

def get_back_admin_keyboard(back_callback: str = None):
    keyboard = InlineKeyboardBuilder()
    if back_callback:
        keyboard.row(InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback))
    keyboard.row(InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu"))
    return keyboard.as_markup()

@router.callback_query(F.data == "create_service_type")
async def start_create_service_type(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return

    await state.set_state(CreateServiceType.waiting_for_name)
    await state.set_data({
        "fields": {
            "photo": {
                "type": "image", 
                "label": "Фотография услуги",
                "description": "Загрузите фото, отражающее вашу услугу",
                "required": True
            },
            "adress": {
                "type": "adress",
                "label": "Адрес",
                "description": "Укажите адрес оказания услуги",
                "required": True
            },
            "number_phone": {
                "type": "text",
                "label": "Номер телефона", 
                "description": "Укажите номер телефона для связи",
                "required": True
            },
            "price": {
                "type": "number",
                "label": "Стоимость",
                "description": "Укажите стоимость услуги в рублях",
                "required": True
            }
        },
        "current_page": 1
    })
    
    keyboard = get_back_admin_keyboard()
    
    await callback.message.edit_text(
        "📝 Добро пожаловать в создание нового типа услуги!\n\n"
        "Пожалуйста, введите название для нового типа услуги.\n"
        "Это название будут видеть все пользователи при выборе категории.\n\n"
        "🎯 Примеры хороших названий:\n"
        "- Репетитор английского языка\n" 
        "- Мастер маникюра\n"
        "- Фотограф на мероприятия\n\n"
        "❗️ Важно: Название должно быть понятным и точно описывать тип услуги",
        reply_markup=keyboard
    )

@router.message(CreateServiceType.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Название слишком короткое. Пожалуйста, введите более подробное название.")
        return
        
    await state.update_data(name=name)
    await add_new_field(message, state)

async def add_new_field(message: Message, state: FSMContext):
    await state.set_state(CreateServiceType.waiting_for_field_name)
    
    data = await state.get_data()
    fields = data.get("fields", {})
    
    field_list = "\n".join([f"- {field['label']} ({field['type']})" for field in fields.values()])
    
    keyboard = get_back_admin_keyboard(back_callback="back_to_name")
    
    await message.answer(
        "🔑 Текущие поля:\n"
        f"{field_list}\n\n"
        "Введите техническое название нового поля (используйте английские буквы, цифры или знак подчеркивания (_)):\n\n"
        "✨ Примеры хороших названий:\n"
        "- experience\n"
        "- education\n"
        "- skills\n"
        "- work_hours\n\n"
        "❗️ Важно: Название должно быть уникальным и не зарезервированным системой.",
        reply_markup=keyboard
    )

@router.message(CreateServiceType.waiting_for_field_name)
async def process_field_name(message: Message, state: FSMContext):
    field_name = message.text.lower().strip()
    
    if field_name in RESERVED_FIELDS:
        await message.answer(
            "❌ Это имя зарезервировано системой!\n"
            "Пожалуйста, выберите другое название для поля."
        )
        return
        
    if not field_name.replace("_", "").isalnum():
        await message.answer(
            "❌ Некорректное название поля!\n\n"
            "Используйте только:\n"
            "- Английские буквы (a-z)\n"
            "- Цифры (0-9)\n"
            "- Знак подчеркивания (_)\n\n"
            "Попробуйте еще раз!"
        )
        return
        
    data = await state.get_data()
    if field_name in data.get("fields", {}):
        await message.answer(
            "❌ Поле с таким названием уже существует!\n"
            "Пожалуйста, выберите другое название."
        )
        return
        
    await state.update_data(current_field_name=field_name)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="📝 Текст", callback_data="field_type:text"),
        InlineKeyboardButton(text="🔢 Число", callback_data="field_type:number"),
        InlineKeyboardButton(text="📋 Список", callback_data="field_type:select")
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_field_name"),
        InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu")
    )
    
    await state.set_state(CreateServiceType.waiting_for_field_type)
    await message.answer(
        "📊 Выберите тип данных для поля:\n\n"
        "📝 Текст - для ввода текста (описание, адрес)\n"
        "🔢 Число - для цифр (стаж, цена, возраст)\n" 
        "📋 Список - для выбора из вариантов (уровень, категория)",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(CreateServiceType.waiting_for_field_type)
async def process_field_type(callback: CallbackQuery, state: FSMContext):
    field_type = callback.data.split(":")[1]
    await state.update_data(current_field_type=field_type)
    
    keyboard = get_back_admin_keyboard(back_callback="back_to_field_type")
    
    await state.set_state(CreateServiceType.waiting_for_field_label)
    await callback.message.edit_text(
        "💭 Введите понятное название поля для пользователей:\n\n"
        "✨ Примеры:\n"
        "- Опыт работы\n"
        "- Стоимость услуги\n"
        "- Район города\n"
        "- График работы\n\n"
        "❗️ Важно: Название должно быть понятным для всех пользователей",
        reply_markup=keyboard
    )

@router.message(CreateServiceType.waiting_for_field_label)
async def process_field_label(message: Message, state: FSMContext):
    label = message.text.strip()
    if len(label) < 3:
        await message.answer("❌ Название слишком короткое. Введите более понятное название.")
        return
        
    await state.update_data(current_field_label=label)
    
    keyboard = get_back_admin_keyboard(back_callback="back_to_field_label")
    
    await state.set_state(CreateServiceType.waiting_for_field_description)
    await message.answer(
        "📝 Введите подсказку для пользователей:\n\n"
        "✨ Примеры хороших подсказок:\n"
        "- Укажите ваш опыт работы в годах\n"
        "- Опишите ваши основные навыки и умения\n"
        "- Укажите район, где вы оказываете услуги\n\n"
        "❗️ Подсказка должна помочь пользователю правильно заполнить поле",
        reply_markup=keyboard
    )

@router.message(CreateServiceType.waiting_for_field_description)
async def process_field_description(message: Message, state: FSMContext):
    description = message.text.strip()
    if len(description) < 10:
        await message.answer("❌ Подсказка слишком короткая. Опишите подробнее, что нужно ввести.")
        return
        
    await state.update_data(current_field_description=description)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Да", callback_data="required_true"),
        InlineKeyboardButton(text="❌ Нет", callback_data="required_false")
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_field_description"),
        InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu")
    )
    
    await state.set_state(CreateServiceType.waiting_for_field_required)
    await message.answer(
        "❓ Должен ли пользователь обязательно заполнить это поле?\n\n"
        "✅ Да - поле обязательно для заполнения\n"
        "❌ Нет - поле можно оставить пустым",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(CreateServiceType.waiting_for_field_required)
async def process_field_required(callback: CallbackQuery, state: FSMContext):
    required = callback.data.split("_")[1] == "true"
    
    if required and (await state.get_data())["current_field_type"] == "select":
        keyboard = get_back_admin_keyboard(back_callback="back_to_field_required")
        
        await state.set_state(CreateServiceType.waiting_for_select_options)
        await callback.message.edit_text(
            "📝 Введите варианты для выбора через запятую:\n\n"
            "✨ Примеры:\n"
            "- Начинающий, Продвинутый, Эксперт\n"
            "- Утро, День, Вечер\n"
            "- Онлайн, Офлайн\n\n"
            "❗️ Важно: Укажите минимум 2 варианта",
            reply_markup=keyboard
        )
    else:
        await save_field(callback.message, state, required)

@router.message(CreateServiceType.waiting_for_select_options)
async def process_select_options(message: Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split(",") if opt.strip()]
    if len(options) < 2:
        await message.answer(
            "❌ Ошибка! Нужно указать минимум 2 варианта.\n"
            "Введите варианты через запятую."
        )
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
    
    field_count = len(fields)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="➕ Добавить поле", callback_data="add_field"),
        InlineKeyboardButton(text="✅ Завершить", callback_data="finish")
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_save_field"),
        InlineKeyboardButton(text="🏠 В админ меню", callback_data="admin_menu")
    )
    
    await state.set_state(CreateServiceType.waiting_for_more_fields)
    
    if isinstance(message, Message):
        await message.answer(
            f"✅ Поле успешно добавлено!\n\n"
            f"📊 Текущее количество полей: {field_count}\n\n"
            "Что делаем дальше?",
            reply_markup=keyboard.as_markup()
        )
    else:
        await message.edit_text(
            f"✅ Поле успешно добавлено!\n\n"
            f"📊 Текущее количество полей: {field_count}\n\n"
            "Что делаем дальше?",
            reply_markup=keyboard.as_markup()
        )

@router.callback_query(F.data.startswith("back_to_"))
async def handle_back(callback: CallbackQuery, state: FSMContext):
    step = callback.data.replace("back_to_", "")
    
    step_handlers = {
        "name": start_create_service_type,
        "field_name": add_new_field,
        "field_type": lambda msg, st: process_field_name(msg, st),
        "field_label": lambda msg, st: process_field_type(callback, st),
        "field_description": lambda msg, st: process_field_label(msg, st),
        "field_required": lambda msg, st: process_field_description(msg, st),
        "select_options": lambda msg, st: process_field_required(callback, st),
        "save_field": lambda msg, st: process_more_fields(callback, st)
    }
    
    handler = step_handlers.get(step)
    if handler:
        if callable(handler):
            await handler(callback, state) if isinstance(handler, type(lambda: None)) else await handler(callback.message, state)
    else:
        await callback.answer("❌ Неизвестный шаг для возврата", show_alert=True)

@router.callback_query(F.data == "admin_menu")
async def return_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 Админ-панель\n\n"
        "Выберите нужное действие из меню ниже:",
        reply_markup=admin_keyboard()
    )

@router.callback_query(CreateServiceType.waiting_for_more_fields)
async def process_more_fields(callback: CallbackQuery, state: FSMContext):
    if callback.data == "add_field":
        await add_new_field(callback.message, state)
    elif callback.data == "finish":
        data = await state.get_data()
        if not data.get("fields"):
            await callback.message.edit_text(
                "❌ Ошибка: Нужно добавить хотя бы одно поле!\n"
                "Давайте создадим первое поле."
            )
            await add_new_field(callback.message, state)
            return
            
        try:
            type_id = db.add_service_type(
                name=data["name"],
                created_by_id=str(callback.from_user.id),
                required_fields=data["fields"]
            )
            if type_id:
                await callback.message.edit_text(
                    "✅ Поздравляем!\n\n"
                    f"Новый тип услуги \"{data['name']}\" успешно создан!\n"
                    f"Количество настроенных полей: {len(data['fields'])}\n\n"
                    "Теперь пользователи смогут создавать объявления этого типа.",
                    reply_markup=admin_keyboard()
                )
            else:
                await callback.message.edit_text(
                    "❌ Ошибка при создании типа услуги\n\n"
                    "Возможно, тип услуги с таким названием уже существует.\n"
                    "Попробуйте создать тип услуги с другим названием.",
                    reply_markup=admin_keyboard()
                )
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Произошла ошибка:\n{str(e)}\n\n"
                "Пожалуйста, попробуйте еще раз или обратитесь к разработчику.",
                reply_markup=admin_keyboard()
            )
        finally:
            await state.clear()
    else:
        await callback.answer("❌ Неизвестная команда", show_alert=True)