from aiogram import Router, F, types
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, 
    WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, Message
)
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.database import Database
from urllib.parse import quote
import json
from typing import List, Dict, Any, Optional
from handlers.main_function.functions.create_complaints import ComplaintStates, create_complaint

router = Router(name='watch_handler')
db = Database()

ITEMS_PER_PAGE = 8

class SearchStates(StatesGroup):
    browsing = State()
    filtering = State()
    viewing_service = State()

def build_service_types_keyboard(page: int = 1) -> Optional[InlineKeyboardMarkup]:
    """Создает клавиатуру с типами услуг"""
    service_types = db.get_active_service_types()
    if not service_types:
        return
        
    keyboard = InlineKeyboardBuilder()
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    current_page_types = service_types[start_idx:start_idx + ITEMS_PER_PAGE]
    
    for i in range(0, len(current_page_types), 2):
        row_buttons = []
        for service_type in current_page_types[i:i+2]:
            row_buttons.append(InlineKeyboardButton(
                text=service_type["name"],
                callback_data=f"watch_type:{service_type['id']}"
            ))
        keyboard.row(*row_buttons)

    # Упрощенная пагинация
    if len(service_types) > ITEMS_PER_PAGE:
        pagination_row = []
        if page > 1:
            pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"watch_page_{page-1}"))
        if len(service_types) > start_idx + ITEMS_PER_PAGE:
            pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"watch_page_{page+1}"))
        if pagination_row:
            keyboard.row(*pagination_row)
    
    keyboard.row(InlineKeyboardButton(text="🏠 На главную", callback_data="go_to_home"))
    
    return keyboard.as_markup()

def create_services_keyboard(services: List[Dict], page: int = 1, type_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком услуг"""
    keyboard = InlineKeyboardBuilder()
    
    if not services:
        print("Список услуг пуст")
        keyboard.row(InlineKeyboardButton(text="🔙 К категориям", callback_data="back_to_categories"))
        return keyboard.as_markup()
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    current_page_services = services[start_idx:start_idx + ITEMS_PER_PAGE]
    
    for service in current_page_services:
        service_info = f"{service.get('city', 'Город не указан')} - {service.get('price', 0)}₽"
        if service.get('custom_fields'):
            try:
                custom_fields = service['custom_fields'] if isinstance(service['custom_fields'], dict) else json.loads(service['custom_fields'])
                for field, value in custom_fields.items():
                    if field not in ['photo', 'adress', 'number_phone', 'price']:
                        service_info += f" - {value}"
            except (json.JSONDecodeError, TypeError):
                pass
                
        keyboard.row(InlineKeyboardButton(
            text=service_info,
            callback_data=f"service:{service['id']}"
        ))

    # Упрощенная пагинация
    if len(services) > ITEMS_PER_PAGE:
        pagination_row = []
        if page > 1:
            pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"services_page_{page-1}"))
        if len(services) > start_idx + ITEMS_PER_PAGE:
            pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"services_page_{page+1}"))
        if pagination_row:
            keyboard.row(*pagination_row)

    keyboard.row(
        InlineKeyboardButton(text="🔄 Сбросить фильтры", callback_data="reset_filters"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_services"),
        InlineKeyboardButton(text="🔙 К категориям", callback_data="back_to_categories")
    )
    
    return keyboard.as_markup()

def create_service_details_keyboard(service: Dict, seller_username: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для детального просмотра услуги"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(
        InlineKeyboardButton(text="📞 Показать телефон", callback_data=f"call_{service['id']}"),
        InlineKeyboardButton(text="⚠️ Жалоба на услугу", callback_data=f"create_complaint_service_{seller_username}")
    )
    
    keyboard.row(InlineKeyboardButton(text="🔙 К списку", callback_data="back_to_services"))
    
    return keyboard.as_markup()

def create_filter_webapp_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопкой фильтров"""
    try:
        service_types = db.get_active_service_types()
        if not service_types:
            return None

        fields = {}
        excluded_fields = {'photo', 'adress', 'number_phone', 'price'}
        
        for service_type in service_types:
            if not service_type or "required_fields" not in service_type:
                continue
                
            type_fields = service_type["required_fields"]
            if isinstance(type_fields, str):
                try:
                    type_fields = json.loads(type_fields)
                except json.JSONDecodeError:
                    continue

            for field_name, field_data in type_fields.items():
                if field_name not in excluded_fields and isinstance(field_data, dict):
                    fields[field_name] = {
                        "type": field_data.get("type", "text"),
                        "placeholder": field_data.get("label", field_name),
                        "description": field_data.get("description", ""),
                        "required": field_data.get("required", False)
                    }

        field_params = []
        for name, data in fields.items():
            encoded_name = quote(name)
            encoded_placeholder = quote(data["placeholder"])
            param = f"{encoded_name}={encoded_placeholder}"
            field_params.append(param)

        base_url = "https://spontaneous-kashata-919d92.netlify.app/search"
        if field_params:
            base_url = f"{base_url}?{('&').join(field_params)}"
        
        keyboard = ReplyKeyboardBuilder()
        keyboard.row(
            KeyboardButton(
                text="🔍 Настроить фильтры",
                web_app=WebAppInfo(url=base_url)
            )
        )
        keyboard.row(KeyboardButton(text="Вернуться домой 🏠"))
        
        return keyboard.as_markup(resize_keyboard=True, one_time_keyboard=False)

    except Exception as e:
        print(f"Ошибка создания формы фильтров: {e}")
        return None

@router.message(F.text.in_(["👁️ Смотреть услуги", "/search"]))
async def start_search(message: Message, state: FSMContext):
    """Начало поиска услуг"""
    keyboard = build_service_types_keyboard()
    if not keyboard:
        await message.answer(
            "❌ В данный момент нет доступных категорий услуг"
        )
        return

    await state.set_state(SearchStates.browsing)
    await state.set_data({})
    await message.answer(
        "📋 Выберите категорию услуг для просмотра:\n"
        "Используйте кнопку «🔍 Настроить фильтры» для уточнения поиска",
        reply_markup=create_filter_webapp_keyboard()
    )
    await message.answer("Доступные категории:", reply_markup=keyboard)

@router.callback_query(SearchStates.browsing, lambda c: c.data.startswith('watch_type:'))
async def show_services_by_type(callback: CallbackQuery, state: FSMContext):
    """Показывает услуги выбранного типа"""
    try:
        service_type_id = int(callback.data.split(':')[1])
        
        services = db.filter_services(
            service_type_id=service_type_id,
            status='active'
        )

        if not services:
            await callback.message.edit_text(
                "❌ В данной категории пока нет услуг",
                reply_markup=build_service_types_keyboard()
            )
            return
            
        await state.update_data(current_type_id=service_type_id, services=services)
        keyboard = create_services_keyboard(services, type_id=service_type_id)
        
        new_text = f"📋 Найдено услуг: {len(services)}\nИспользуйте кнопку «🔍 Настроить фильтры» для уточнения поиска"
        
        try:
            await callback.message.edit_text(new_text, reply_markup=keyboard)
        except Exception as e:
            if "message is not modified" not in str(e):
                raise
            
    except Exception as e:
        print(f"Ошибка при показе услуг: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при загрузке услуг",
            reply_markup=build_service_types_keyboard()
        )
    finally:
        await callback.answer()

@router.callback_query(SearchStates.browsing, lambda c: c.data.startswith('service:'))
async def show_service_details(callback: CallbackQuery, state: FSMContext):
    """Показывает детальную информацию об услуге"""
    try:
        service_id = int(callback.data.split(':')[1])
        service = db.get_service_by_id(service_id)
        
        if not service:
            await callback.answer("❌ Услуга не найдена")
            return

        # Преобразуем кортеж в словарь для удобства
        service_dict = {
            'id': service[0],
            'user_id': service[1],
            'service_type_id': service[2],
            'title': service[3],
            'photo_id': service[4],
            'city': service[5],
            'district': service[6],
            'street': service[7],
            'house': service[8],
            'number_phone': service[9],
            'price': service[10],
            'custom_fields': service[11]
        }

        # Получаем информацию о продавце
        seller = db.get_user(telegram_id=service_dict['user_id'])
        if not seller:
            await callback.answer("❌ Информация о продавце недоступна")
            return

        seller_username = seller[2]  # username из кортежа пользователя
        
        db.increment_service_views(service_id)
        
        details = (
            f"🎯 {service_dict['title']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Стоимость: {service_dict['price']}₽\n\n"
            f"📍 Местоположение:\n"
            f"• Город: {service_dict['city']}\n"
            f"• Район: {service_dict['district']}\n" 
            f"• Улица: {service_dict['street']}\n\n"
        )

        if service_dict['custom_fields']:
            try:
                custom_fields = json.loads(service_dict['custom_fields']) if isinstance(service_dict['custom_fields'], str) else service_dict['custom_fields']
                details += "📋 Дополнительная информация:\n"
                for field, value in custom_fields.items():
                    if field not in ['photo', 'adress', 'number_phone', 'price']:
                        details += f"• {field}: {value}\n"
            except json.JSONDecodeError as e:
                print(f"Ошибка при разборе custom_fields: {e}")

        details += "\n━━━━━━━━━━━━━━━━━━━━━"

        await state.set_state(SearchStates.viewing_service)
        await callback.message.delete()
        
        if service_dict['photo_id']:
            await callback.message.answer_photo(
                photo=service_dict['photo_id'],
                caption=details,
                reply_markup=create_service_details_keyboard(service_dict, seller_username)
            )
        else:
            await callback.message.answer(
                details,
                reply_markup=create_service_details_keyboard(service_dict, seller_username)
            )

    except Exception as e:
        print(f"Ошибка при показе деталей услуги: {e}")
        await callback.answer("❌ Ошибка при загрузке информации")
    finally:
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith("create_complaint_"))
async def handle_complaint_button(callback: CallbackQuery, state: FSMContext):
    """Обработка создания жалобы"""
    await create_complaint(callback, state)

@router.callback_query(lambda c: c.data == "reset_filters")
async def reset_filters(callback: CallbackQuery, state: FSMContext):
    """Сброс всех примененных фильтров"""
    try:
        state_data = await state.get_data()
        service_type_id = state_data.get('current_type_id')
        
        if service_type_id:
            services = db.filter_services(
                service_type_id=service_type_id,
                status='active'
            )
            await state.update_data(services=services)
            keyboard = create_services_keyboard(services)
            
            await callback.message.edit_text(
                f"🔄 Фильтры сброшены\n📋 Найдено услуг: {len(services)}",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "❌ Не удалось сбросить фильтры",
                reply_markup=build_service_types_keyboard()
            )
    except Exception as e:
        print(f"Ошибка при сбросе фильтров: {e}")
        await callback.answer("❌ Произошла ошибка")
    finally:
        await callback.answer()

@router.callback_query(lambda c: c.data == "refresh_services")
async def refresh_services(callback: CallbackQuery, state: FSMContext):
    """Обновление списка услуг"""
    try:
        state_data = await state.get_data()
        service_type_id = state_data.get('current_type_id')
        last_filters = state_data.get('last_filters', {})
        
        if not service_type_id:
            await callback.answer("❌ Не удалось обновить список")
            return
            
        services = db.filter_services(
            service_type_id=service_type_id,
            city=last_filters.get('city'),
            price_min=last_filters.get('price_min'),
            price_max=last_filters.get('price_max'),
            custom_fields=last_filters.get('custom_fields'),
            sort_by=last_filters.get('sort_by', 'created_at'),
            sort_direction=last_filters.get('sort_direction', 'DESC'),
            status='active'
        )
        
        await state.update_data(services=services)
        keyboard = create_services_keyboard(services)
        
        filter_text = ["🔄 Список обновлен"]
        
        if last_filters:
            filter_text.append("Применены фильтры:")
            if last_filters.get('city'):
                filter_text.append(f"📍 Город: {last_filters['city']}")
            if last_filters.get('price_min') or last_filters.get('price_max'):
                price_text = "💰 Цена: "
                if last_filters.get('price_min') and last_filters.get('price_max'):
                    price_text += f"от {last_filters['price_min']}₽ до {last_filters['price_max']}₽"
                elif last_filters.get('price_min'):
                    price_text += f"от {last_filters['price_min']}₽"
                else:
                    price_text += f"до {last_filters['price_max']}₽"
                filter_text.append(price_text)
            if custom_fields := last_filters.get('custom_fields'):
                filter_text.append("📌 Дополнительные фильтры:")
                for field, value in custom_fields.items():
                    filter_text.append(f"   • {field}: {value}")
                    
        filter_text.append(f"📋 Найдено услуг: {len(services)}")
        
        await callback.message.edit_text(
            "\n".join(filter_text),
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка при обновлении списка: {e}")
        await callback.answer("❌ Произошла ошибка")
    finally:
        await callback.answer()

@router.message(SearchStates.browsing, lambda message: message.web_app_data and message.web_app_data.button_text == "🔍 Настроить фильтры")
async def process_filter_webapp_data(message: Message, state: FSMContext):
    """Обработка данных фильтров из веб-приложения"""
    try:
        filter_data = json.loads(message.web_app_data.data)
        state_data = await state.get_data()
        service_type_id = state_data.get('current_type_id')

        if not service_type_id:
            await message.answer(
                "❌ Не выбрана категория услуг",
                reply_markup=build_service_types_keyboard()
            )
            return

        service_type = db.get_service_type(service_type_id)
        if not service_type:
            await message.answer(
                "❌ Ошибка получения типа услуги",
                reply_markup=build_service_types_keyboard()
            )
            return

        filters = {
            'service_type_id': service_type_id,
            'status': 'active'
        }

        if city := filter_data.get('city', '').strip():
            filters['city'] = city

        try:
            if price_str := filter_data.get('price', '').strip():
                if price_str.startswith('до'):
                    filters['price_max'] = float(price_str.split()[1].replace('₽', '').replace(' ', ''))
                elif price_str.startswith('от'):
                    filters['price_min'] = float(price_str.split()[1].replace('₽', '').replace(' ', ''))
                else:
                    price_parts = price_str.split('-')
                    if len(price_parts) == 2:
                        filters['price_min'] = float(price_parts[0].replace('₽', '').replace(' ', ''))
                        filters['price_max'] = float(price_parts[1].replace('₽', '').replace(' ', ''))
        except (ValueError, IndexError):
            print("Ошибка при парсинге цены, пропускаем")

        custom_fields = {}
        if required_fields := service_type.get('required_fields'):
            for field_name, field_info in required_fields.items():
                if (field_name not in ['photo', 'adress', 'number_phone', 'price'] and 
                    (value := filter_data.get(field_name, '').strip())):
                    custom_fields[field_name] = value

        if custom_fields:
            filters['custom_fields'] = custom_fields

        sort_by = 'created_at'
        sort_direction = 'DESC'
        if filter_data.get('sortOld'):
            sort_direction = 'ASC'
        elif filter_data.get('sortPopular'):
            sort_by = 'views'
            
        filters['sort_by'] = sort_by
        filters['sort_direction'] = sort_direction

        services = db.filter_services(
            service_type_id=filters['service_type_id'],
            city=filters.get('city'),
            price_min=filters.get('price_min'),
            price_max=filters.get('price_max'),
            custom_fields=filters.get('custom_fields'),
            sort_by=sort_by,
            sort_direction=sort_direction,
            status=filters['status']
        )

        # Сохраняем примененные фильтры в состоянии
        await state.update_data(
            services=services,
            last_filters={
                'city': filters.get('city'),
                'price_min': filters.get('price_min'),
                'price_max': filters.get('price_max'),
                'custom_fields': filters.get('custom_fields'),
                'sort_by': sort_by,
                'sort_direction': sort_direction
            }
        )

        if not services:
            await message.answer(
                "🔍 По вашему запросу ничего не найдено\n"
                "Попробуйте изменить параметры поиска",
                reply_markup=create_filter_webapp_keyboard()
            )
            return

        keyboard = create_services_keyboard(services)

        filter_text = ["🔍 Результаты поиска:"]
        
        if filters.get('city'):
            filter_text.append(f"📍 Город: {filters['city']}")
        
        if filters.get('price_min') or filters.get('price_max'):
            price_text = "💰 Цена: "
            if filters.get('price_min') and filters.get('price_max'):
                price_text += f"от {filters['price_min']}₽ до {filters['price_max']}₽"
            elif filters.get('price_min'):
                price_text += f"от {filters['price_min']}₽"
            else:
                price_text += f"до {filters['price_max']}₽"
            filter_text.append(price_text)

        if custom_fields:
            filter_text.append("📌 Дополнительные фильтры:")
            for field, value in custom_fields.items():
                filter_text.append(f"   • {field}: {value}")

        filter_text.append(f"📋 Найдено услуг: {len(services)}")

        await message.answer(
            "\n".join(filter_text),
            reply_markup=keyboard
        )

    except json.JSONDecodeError as e:
        print(f"Ошибка при разборе данных фильтров: {e}")
        await message.answer(
            "❌ Ошибка обработки данных фильтров\n"
            "Пожалуйста, попробуйте еще раз",
            reply_markup=create_filter_webapp_keyboard()
        )
    except Exception as e:
        print(f"Непредвиденная ошибка при фильтрации: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске\n"
            "Попробуйте позже или измените параметры поиска",
            reply_markup=create_filter_webapp_keyboard()
        )

@router.callback_query(lambda c: c.data.startswith('call_'))
async def handle_call_button(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки показать телефон"""
    try:
        service_id = int(callback.data.split('_')[1])
        service = db.get_service_by_id(service_id)
        
        if not service:
            print(f"Услуга с ID {service_id} не найдена")
            await callback.answer("❌ Услуга не найдена")
            return
            
        number_phone = service[9]  # Индекс номера телефона в кортеже
        seller = db.get_user(telegram_id=service[1])
        
        if not seller:
            await callback.answer("❌ Информация о продавце недоступна")
            return
            
        # Проверяем, не является ли пользователь владельцем услуги
        if str(callback.from_user.id) == str(service[1]):
            await callback.answer("❌ Вы не можете забронировать свою собственную услугу")
            return
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📞 Телефон для связи", callback_data=f"phone_{service_id}"),
                InlineKeyboardButton(text="✅ Забронировать", callback_data=f"book_{service_id}")
            ],
            [InlineKeyboardButton(text="⚠️ Жалоба на услугу", callback_data=f"create_complaint_service_{seller[2]}")],
            [InlineKeyboardButton(text="🔙 К списку", callback_data="back_to_services")]
        ])
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer(f"📞 Телефон для связи: {number_phone}")
        
    except Exception as e:
        print(f"Ошибка при показе номера телефона: {e}")
        await callback.answer("❌ Произошла ошибка")

@router.callback_query(lambda c: c.data.startswith('book_'))
async def handle_book_button(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки забронировать"""
    try:
        service_id = int(callback.data.split('_')[1])
        service = db.get_service_by_id(service_id)
        
        if not service: 
            print(f"Услуга {service_id} не найдена при бронировании")
            await callback.answer("❌ Услуга не найдена")
            return
            
        # Проверяем, не является ли пользователь владельцем услуги
        if str(callback.from_user.id) == str(service[1]):
            await callback.answer("❌ Вы не можете забронировать свою собственную услугу")
            return
            
        owner = db.get_user(telegram_id=service[1])
        if not owner:
            print(f"Владелец услуги {service_id} не найден")
            await callback.answer("❌ Ошибка при бронировании - владелец не найден")
            return
            
        db.update_service_status(service_id, 'booked')
        
        owner_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить бронь", callback_data=f"cancel_book_{service_id}"),
                InlineKeyboardButton(text="⚠️ Жалоба", callback_data=f"create_complaint_user_{callback.from_user.username}")
            ]
        ])
        
        await callback.bot.send_message(
            chat_id=owner[1],  # telegram_id из кортежа пользователя
            text=(
                f"🔔 Ваша услуга была забронирована!\n\n"
                f"👤 Пользователь: @{callback.from_user.username}\n"
                f"📝 Услуга: {service[3]}\n"
                f"💰 Стоимость: {service[10]}₽\n\n"
                "ℹ️ Если вы еще не связались с клиентом, сделайте это в ближайшее время."
            ),
            reply_markup=owner_keyboard
        )
        
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(
            "✅ Услуга успешно забронирована!\n\n"
            "ℹ️ Владелец получил уведомление и свяжется с вами в ближайшее время.\n"
            "📞 Вы также можете связаться с владельцем самостоятельно по указанному номеру телефона."
        )
        
    except Exception as e:
        print(f"Ошибка при бронировании услуги: {e}")
        await callback.answer("❌ Произошла ошибка при бронировании")
    finally:
        await callback.answer()

@router.callback_query(lambda c: c.data.startswith('cancel_book_'))
async def handle_cancel_book_button(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены бронирования"""
    try:
        service_id = int(callback.data.split('_')[2])
        service = db.get_service_by_id(service_id)
        
        if not service:
            print(f"Услуга {service_id} не найдена при отмене брони")
            await callback.answer("❌ Услуга не найдена")
            return
            
        db.update_service_status(service_id, 'active')
        
        booked_user = db.get_user(user_id=service[1])
        if booked_user:
            await callback.bot.send_message(
                chat_id=booked_user[1],  # telegram_id из кортежа пользователя
                text=f"❌ Бронирование услуги «{service[3]}» было отменено владельцем."
            )
        
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("✅ Бронирование отменено")
        
    except Exception as e:
        print(f"Ошибка при отмене бронирования: {e}")
        await callback.answer("❌ Произошла ошибка")

@router.callback_query(lambda c: c.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    """Возврат к списку услуг"""
    try:
        state_data = await state.get_data()
        services = state_data.get('services', [])
        
        if services:
            await state.set_state(SearchStates.browsing)
            keyboard = create_services_keyboard(services)
            
            await callback.message.delete()
            await callback.message.answer(
                f"📋 Найдено услуг: {len(services)}\n"
                "Используйте кнопку «🔍 Настроить фильтры» для уточнения поиска",
                reply_markup=keyboard
            )
        else:
            print("Нет сохраненных услуг в состоянии")
            await callback.message.edit_text(
                "❌ Ошибка при возврате к списку услуг",
                reply_markup=build_service_types_keyboard()
            )
    except Exception as e:
        print(f"Ошибка при возврате к списку услуг: {e}")
        await callback.answer("❌ Произошла ошибка")
    finally:
        await callback.answer()

@router.callback_query(SearchStates.browsing, lambda c: c.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Возврат к списку категорий"""
    try:
        await state.set_data({})
        keyboard = build_service_types_keyboard()
        
        await callback.message.delete()
        await callback.message.answer(
            "📋 Выберите категорию услуг для просмотра:",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка при возврате к категориям: {e}")
        await callback.answer("❌ Произошла ошибка")
    finally:
        await callback.answer()

@router.callback_query(SearchStates.browsing, lambda c: c.data.startswith('watch_page_'))
async def handle_category_pagination(callback: CallbackQuery):
    """Обработка пагинации категорий"""
    try:
        page = int(callback.data.split('_')[2])
        keyboard = build_service_types_keyboard(page)
        
        if keyboard:
            try:
                await callback.message.edit_reply_markup(reply_markup=keyboard)
            except Exception as e:
                if "message is not modified" not in str(e):
                    print(f"Ошибка при обновлении клавиатуры: {e}")
                    raise
        else:
            print(f"Не удалось создать клавиатуру для страницы {page}")
            await callback.message.edit_text(
                "❌ Ошибка загрузки категорий",
                reply_markup=types.ReplyKeyboardRemove()
            )
    except Exception as e:
        print(f"Ошибка пагинации: {e}")
        await callback.answer("❌ Ошибка при переключении страницы")
    finally:
        await callback.answer()
