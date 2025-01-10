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
import asyncio

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
    
    if current_page < total_pages:
        row_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{current_page+1}"))
    
    if row_buttons:
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
    
    pagination = create_pagination_keyboard(len(service_types), page)
    keyboard.attach(InlineKeyboardBuilder.from_markup(pagination))
    
    return keyboard.as_markup()

def create_webapp_form(service_type_id: int, need_enter_phone: Optional[bool] = True) -> Optional[ReplyKeyboardMarkup]:
    """Создает форму веб-приложения для услуги"""
    try:
        # Проверяем входные данные
        if not isinstance(service_type_id, int) or service_type_id <= 0:
            raise ValueError("Некорректный ID типа услуги")

        # Получаем тип услуги из БД
        service_type = db.get_service_type(service_type_id)
        if not service_type:
            raise ValueError("Тип услуги не найден")
            
        required_fields = service_type.get("required_fields")
        if not required_fields or not isinstance(required_fields, dict):
            raise ValueError("Некорректная структура полей формы")

        # Формируем поля формы с учетом need_enter_phone
        fields = {}
        for name, data in required_fields.items():
            if not isinstance(data, dict) or name == "photo":
                continue
                
            if name == "number_phone" and not need_enter_phone:
                continue
                
            fields[name] = data.get("label", name)

        # Формируем параметры URL безопасным способом
        field_params = []
        for name, placeholder in fields.items():
            try:
                if name and placeholder:
                    encoded_name = quote(str(name).strip())
                    encoded_placeholder = quote(str(placeholder).strip())
                    if encoded_name and encoded_placeholder:
                        field_params.append(f"{encoded_name}={encoded_placeholder}")
            except (TypeError, ValueError) as e:
                print(f"Ошибка кодирования параметра {name}: {e}")
                continue

        # Формируем URL
        base_url = "https://spontaneous-kashata-919d92.netlify.app/create"
        full_url = f"{base_url}?{('&').join(field_params)}" if field_params else base_url

        # Создаем клавиатуру с обновленными параметрами WebAppInfo
        keyboard = ReplyKeyboardBuilder()
        keyboard.row(
            KeyboardButton(
                text="📝 Заполнить форму",
                web_app=WebAppInfo(
                    url=full_url
                )
            )
        )
        keyboard.row(KeyboardButton(text="Вернуться домой 🏠"))

        return keyboard.as_markup(
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True,
            input_field_placeholder="Нажмите кнопку для заполнения формы"
        )

    except Exception as e:
        print(f"Ошибка создания формы: {str(e)}")
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

                if field == "adress" and not data[field].count(',') == 2:
                    return "Адрес должен содержать город, улицу и дом через запятую"

                if field == "district" and not data[field].count(',') == 1:
                    return "Район должен содержать город и район через запятую"
                        
        return None
    except Exception as e:
        return f"Ошибка валидации: {str(e)}"

@router.message(F.text.in_(["📈 Выставить свою услугу", "/add_service"]))
async def start_post_service(message: Message, state: FSMContext):
    """Начало публикации услуги"""
    # Проверяем является ли пользователь продавцом
    user = db.get_user(telegram_id=str(message.from_user.id))
    if not user or not user[4]:  # user[4] - поле is_seller
        await message.answer(
            "❌ Для публикации услуг необходимо быть продавцом",
            reply_markup=to_home_keyboard()
        )
        return

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
        
        user = db.get_user(telegram_id=str(callback.from_user.id))
        if user[3]:
            keyboard = create_webapp_form(service_type_id, need_enter_phone=False)
        else:
            keyboard = create_webapp_form(service_type_id)
        
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
            "- Можно отправить одно фото или альбом до 10 фото\n"
            "- Фото должны быть качественными\n"
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

@router.message(ServiceStates.waiting_for_photo, F.media_group_id)
async def process_service_photo_album(message: Message, state: FSMContext):
    """Обработка альбома фотографий услуги"""
    try:
        # Сохраняем ID первого фото из альбома во временное хранилище
        media_group_id = message.media_group_id
        current_data = await state.get_data()
        photo_ids = current_data.get('photo_ids', [])
        
        if message.photo:
            photo_ids.append(message.photo[-1].file_id)
            await state.update_data(photo_ids=photo_ids, media_group_id=media_group_id)
            
        # Ждем небольшую паузу, чтобы собрать все фото из альбома
        await asyncio.sleep(1)
        
        # Проверяем, все ли фото собраны
        updated_data = await state.get_data()
        if len(updated_data.get('photo_ids', [])) >= 1:
            await process_service_data(message, state)

    except Exception as e:
        print(f"Ошибка обработки альбома: {e}")
        await message.answer(
            "❌ Ошибка при обработке фотографий\n"
            "Попробуйте загрузить фото по одному",
            reply_markup=to_home_keyboard()
        )
        await state.clear()

@router.message(ServiceStates.waiting_for_photo, F.photo)
async def process_service_photo(message: Message, state: FSMContext):
    """Обработка одиночного фото услуги"""
    try:
        if not message.media_group_id:
            # Если это одиночное фото
            await state.update_data(photo_ids=[message.photo[-1].file_id])
            await process_service_data(message, state)
            
    except Exception as e:
        print(f"Ошибка обработки фото: {e}")
        await message.answer(
            "❌ Ошибка при обработке фотографии",
            reply_markup=to_home_keyboard()
        )
        await state.clear()

async def process_service_data(message: Message, state: FSMContext):
    """Обработка данных услуги и сохранение в БД"""
    try:
        data = await state.get_data()
        form_data = data.get('form_data')
        service_type_id = data.get('service_type_id')
        photo_ids = data.get('photo_ids', [])

        if not all([form_data, service_type_id, photo_ids]):
            raise ValueError("Отсутствуют необходимые данные формы")

        service_type = db.get_service_type(service_type_id)
        if not service_type:
            raise ValueError("Неверный тип услуги")

        user = db.get_user(telegram_id=str(message.from_user.id))
        if not user:
            raise ValueError("Пользователь не найден")

        user_phone = user[3]
        if user_phone and 'number_phone' not in form_data:
            form_data['number_phone'] = user_phone

        address_parts = form_data.get('adress', '').split(',')
        city = address_parts[0].strip() if len(address_parts) > 0 else ''
        street = address_parts[1].strip() if len(address_parts) > 1 else ''
        house = address_parts[2].strip() if len(address_parts) > 2 else ''

        district_parts = form_data.get('district', '').split(',')
        district = district_parts[1].strip() if len(district_parts) > 1 else ''

        service_data = {
            "user_id": user[1],
            "service_type_id": service_type_id,
            "title": form_data.get('title', service_type["name"]),
            "photo_id": ','.join(photo_ids),  # Сохраняем все ID фото через запятую
            "city": city,
            "district": district,
            "street": street,
            "house": house,
            "number_phone": form_data.get('number_phone', ''),
            "price": float(form_data.get('price', 0)),
            "custom_fields": {
                k: v for k, v in form_data.items() 
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
