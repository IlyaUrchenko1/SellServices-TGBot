from aiogram import Router, F
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
from utils.database import Database
from keyboards.role_keyboards import seller_keyboard
from keyboards.main_keyboards import to_home_keyboard
from urllib.parse import quote, unquote
from typing import Dict, Any, Optional

router = Router(name='post_handler')
db = Database()

ITEMS_PER_PAGE = 8

class ServiceStates(StatesGroup):
    selecting_type = State()
    filling_form = State()
    waiting_for_photo = State()

def create_pagination_keyboard(total_items: int, current_page: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру пагинации"""
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    keyboard = InlineKeyboardBuilder()
    
    row_buttons = []
    
    if current_page > 1:
        row_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{current_page-1}"))
    
    row_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="current_page"))
    
    if current_page < total_pages:
        row_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{current_page+1}"))
    
    keyboard.row(*row_buttons)
    keyboard.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="go_to_home"))
    
    return keyboard.as_markup()

def build_service_types_keyboard(page: int = 1) -> Optional[InlineKeyboardMarkup]:
    """Создает клавиатуру типов услуг с пагинацией"""
    service_types = db.get_active_service_types()
    if not service_types:
        return None
        
    keyboard = InlineKeyboardBuilder()
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    current_page_types = service_types[start_idx:start_idx + ITEMS_PER_PAGE]
    
    for i in range(0, len(current_page_types), 2):
        row_buttons = []
        for service_type in current_page_types[i:i+2]:
            row_buttons.append(InlineKeyboardButton(
                text=service_type["name"],
                callback_data=f"service_type:{service_type['id']}"
            ))
        keyboard.row(*row_buttons)
    
    keyboard.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"))
    pagination = create_pagination_keyboard(len(service_types), page)
    keyboard.attach(InlineKeyboardBuilder.from_markup(pagination))
    
    return keyboard.as_markup()

def create_webapp_form(service_type_id: int, user_phone: Optional[str] = None) -> Optional[ReplyKeyboardMarkup]:
    """Создает форму веб-приложения для услуги"""
    try:
        service_type = db.get_service_type(service_type_id)
        if not service_type or "required_fields" not in service_type:
            return None
            
        fields = {}
        for name, data in service_type["required_fields"].items():
            if name != "photo" and isinstance(data, dict):
                # Пропускаем поле number_phone если у пользователя есть номер телефона
                if name == "number_phone" and user_phone:
                    continue
                fields[name] = {
                    "type": data.get("type", "text"),
                    "placeholder": data.get("label", name),
                    "description": data.get("description", ""),
                    "required": data.get("required", True)
                }

        field_params = []
        for name, data in fields.items():
            encoded_name = quote(name)
            encoded_placeholder = quote(data["placeholder"])
            param = f"{encoded_name}={encoded_placeholder}"
            field_params.append(param)

        # Если есть номер телефона, добавляем его как параметр
        if user_phone:
            field_params.append(f"number_phone={quote(user_phone)}")

        base_url = "https://spontaneous-kashata-919d92.netlify.app/create"
        full_url = f"{base_url}?{('&').join(field_params)}"
        
        keyboard = ReplyKeyboardBuilder()
        keyboard.row(
            KeyboardButton(
                text="📝 Заполнить форму", 
                web_app=WebAppInfo(url=full_url)
            )
        )
        keyboard.row(KeyboardButton(text="🔙 Назад"))
        
        return keyboard.as_markup(resize_keyboard=True)
        
    except Exception as e:
        print(f"Ошибка создания формы: {e}")
        return None

def validate_form_data(data: Dict[str, Any], required_fields: Dict[str, Any]) -> Optional[str]:
    """Валидация данных формы"""
    try:
        for field, field_data in required_fields.items():
            if field == "photo":
                continue
                
            if field_data.get("required", True):
                if field not in data or not data[field]:
                    return f"Поле {field_data.get('label', field)} обязательно для заполнения"
                
                if field_data["type"] == "number":
                    try:
                        float(data[field])
                    except ValueError:
                        return f"Поле {field_data.get('label', field)} должно быть числом"
                        
        return None
    except Exception as e:
        return f"Ошибка валидации: {str(e)}"

@router.message(lambda m: m.text == '📈 Выставить свою услугу' or m.text == '/add_service')
async def start_post_service(message: Message, state: FSMContext):
    """Начало публикации услуги"""
    keyboard = build_service_types_keyboard()
    if not keyboard:
        await message.answer(
            "❌ В данный момент нет доступных категорий услуг",
            reply_markup=to_home_keyboard()
        )
        return
        
    await state.set_state(ServiceStates.selecting_type)
    await message.answer(
        "📋 Выберите категорию услуги:\n"
        "❗️ Выбор категории влияет на видимость вашей услуги для клиентов",
        reply_markup=keyboard
    )

@router.callback_query(ServiceStates.selecting_type, lambda c: c.data.startswith('service_type:'))
async def handle_service_type_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа услуги"""
    try:
        service_type_id = int(callback.data.split(':')[1])
        await state.update_data(service_type_id=service_type_id)
        
        # Получаем номер телефона пользователя из профиля
        user = db.get_user(telegram_id=str(callback.from_user.id))
        user_phone = user[3] if user else None  # Индекс 3 соответствует полю number_phone
        
        keyboard = create_webapp_form(service_type_id, user_phone)
        if keyboard:
            await callback.message.delete()
            await callback.message.answer(
                "🖥 Нажмите «Заполнить форму» для создания объявления",
                reply_markup=keyboard
            )
            await state.set_state(ServiceStates.filling_form)
        else:
            await callback.message.edit_text(
                "❌ Ошибка получения формы",
                reply_markup=build_service_types_keyboard()
            )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка выбора категории",
            reply_markup=build_service_types_keyboard()
        )
    finally:
        await callback.answer()

@router.callback_query(ServiceStates.selecting_type, F.data.startswith('page_'))
async def handle_pagination(callback: CallbackQuery):
    """Обработка пагинации"""
    try:
        page = int(callback.data.split('_')[1])
        keyboard = build_service_types_keyboard(page)
        if keyboard:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        else:
            await callback.message.edit_text(
                "❌ Ошибка загрузки категорий",
                reply_markup=build_service_types_keyboard()
            )
    except Exception as e:
        print(f"Ошибка пагинации: {e}")
        await callback.answer("❌ Ошибка пагинации")
    await callback.answer()

@router.message(ServiceStates.filling_form, lambda message: message.web_app_data and message.web_app_data.button_text == "📝 Заполнить форму")
async def process_create_webapp_data(message: Message, state: FSMContext):
    """Обработка данных формы для создания услуги"""
    try:
        data = json.loads(message.web_app_data.data)
        state_data = await state.get_data()
        service_type_id = state_data.get('service_type_id')
        
        if not service_type_id:
            raise ValueError("Не выбран тип услуги")
            
        service_type = db.get_service_type(service_type_id)
        if not service_type:
            raise ValueError("Неверный тип услуги")
            
        validation_error = validate_form_data(data, service_type["required_fields"])
        if validation_error:
            raise ValueError(validation_error)
            
        await state.update_data(form_data=data)
        await state.set_state(ServiceStates.waiting_for_photo)
        
        keyboard = ReplyKeyboardBuilder()
        keyboard.row(KeyboardButton(text="🔙 Отмена"))
        
        await message.answer(
            "📸 Отправьте фото услуги\n"
            "- Фото должно быть качественным\n"
            "- Наглядно показывать услугу",
            reply_markup=keyboard.as_markup(resize_keyboard=True)
        )
        
    except json.JSONDecodeError:
        await message.answer(
            "❌ Ошибка обработки данных формы",
            reply_markup=to_home_keyboard()
        )
        await state.clear()
    except ValueError as e:
        await message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=to_home_keyboard()
        )
        await state.clear()
    except Exception as e:
        print(f"Ошибка обработки формы: {e}")
        await message.answer(
            "❌ Произошла неизвестная ошибка",
            reply_markup=to_home_keyboard()
        )
        await state.clear()

@router.message(ServiceStates.waiting_for_photo, F.photo)
async def process_service_photo(message: Message, state: FSMContext):
    """Обработка фото услуги"""
    try:
        data = await state.get_data()
        form_data = data.get('form_data')
        service_type_id = data.get('service_type_id')

        if not all([form_data, service_type_id]):
            raise ValueError("Отсутствуют необходимые данные формы")

        service_type = db.get_service_type(service_type_id)
        if not service_type:
            raise ValueError("Неверный тип услуги")

        user = db.get_user(telegram_id=str(message.from_user.id))
        if not user:
            raise ValueError("Пользователь не найден")

        # Если у пользователя есть номер телефона в профиле, используем его
        user_phone = user[3]  # Индекс 3 соответствует полю number_phone
        if user_phone and 'number_phone' not in form_data:
            form_data['number_phone'] = user_phone

        address_parts = form_data.get('adress', '').split(',')
        city = address_parts[0].strip().replace('г ', '') if len(address_parts) > 0 else ''
        street = address_parts[1].strip().replace('ул ', '') if len(address_parts) > 1 else ''
        house = address_parts[2].strip().replace('д ', '') if len(address_parts) > 2 else ''

        service_data = {
            "user_id": user[1],
            "service_type_id": service_type_id,
            "title": form_data.get('title', service_type["name"]),
            "photo_id": message.photo[-1].file_id,
            "city": city,
            "district": form_data.get('district', '').strip(),
            "street": street,
            "house": house,
            "number_phone": form_data.get('number_phone', '').strip(),
            "price": float(form_data.get('price', 0)),
            "custom_fields": {
                k: v.strip() if isinstance(v, str) else v
                for k, v in form_data.items() 
                if k not in ['title', 'city', 'district', 'street', 'price', 'number_phone', 'adress']
            }
        }
    
        service_id = db.add_service(**service_data)
        if not service_id:
            raise Exception("Ошибка при создании услуги")

        await state.clear()
        await message.answer(
            "✅ Услуга успешно создана!\n"
            "Теперь она будет доступна для поиска и просмотра", 
            reply_markup=seller_keyboard()
        )

    except ValueError as e:
        await message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=to_home_keyboard()
        )
        await state.clear()
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        await message.answer(
            "❌ Ошибка публикации услуги\n"
            "Попробуйте позже или обратитесь в поддержку",
            reply_markup=to_home_keyboard()
        )
        await state.clear()
