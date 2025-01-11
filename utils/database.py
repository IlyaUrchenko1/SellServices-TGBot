import sqlite3
from typing import Optional, Tuple, Dict, Any, List, Union
import json
from datetime import datetime

class Database:
    def __init__(self, db_name="data/services.db"):
        try:
            self.connection = sqlite3.connect(db_name, check_same_thread=False)
            self.cursor = self.connection.cursor()
            self.create_tables()
        except sqlite3.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE,
                username TEXT,
                number_phone TEXT,
                is_seller BOOLEAN DEFAULT 0,
                full_name TEXT,
                work_time_start TEXT DEFAULT '10:00',
                work_time_end TEXT DEFAULT '22:00',
                work_days TEXT DEFAULT '1,2,3,4,5,6,7'
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                required_fields TEXT NOT NULL DEFAULT '{
                    "photo": {"type": "image", "label": "Фотография услуги", "required": true, "description": "Загрузите фото, отражающее вашу услугу"},
                    "adress": {"type": "adress", "label": "Адрес", "required": true, "description": "Укажите адрес оказания услуги"},
                    "district": {"type": "text", "label": "Район", "required": true, "description": "Укажите район оказания услуги"},
                    "number_phone": {"type": "text", "label": "Номер телефона", "required": false, "description": "Укажите номер телефона для связи"},
                    "price": {"type": "number", "label": "Стоимость", "required": true, "description": "Укажите стоимость услуги в рублях"}
                }'
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service_type_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                photo_id TEXT NOT NULL,
                city TEXT NOT NULL,
                district TEXT NOT NULL,
                street TEXT NOT NULL,
                house TEXT,
                number_phone TEXT NOT NULL,
                price INTEGER NOT NULL,
                custom_fields TEXT,
                status TEXT DEFAULT 'active',
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (service_type_id) REFERENCES service_types(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ('user', 'service')),
                complainant_telegram_id TEXT NOT NULL,
                accused_telegram_id TEXT NOT NULL,
                service_id INTEGER,
                complaint_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'resolved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by_telegram_id TEXT,
                resolution_text TEXT,
                severity_level TEXT DEFAULT 'medium' CHECK (severity_level IN ('low', 'medium', 'high')),
                FOREIGN KEY (complainant_telegram_id) REFERENCES users(telegram_id),
                FOREIGN KEY (accused_telegram_id) REFERENCES users(telegram_id), 
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (resolved_by_telegram_id) REFERENCES users(telegram_id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE,
                ban_date TEXT,
                ban_duration_hours INTEGER,
                reason TEXT
            )
        """)

        self.connection.commit()

    #region Методы для таблицы users

    def add_user(self, telegram_id: str, username: str, number_phone: Optional[str] = None, 
                 is_seller: bool = False, full_name: Optional[str] = None) -> Optional[int]:
        """Добавляет нового пользователя в базу данных
        Args:
            telegram_id: Telegram ID пользователя
            username: Username пользователя
            number_phone: Номер телефона (опционально)
            is_seller: Является ли продавцом
            full_name: Полное имя (опционально)
        Returns:
            ID созданного пользователя или None в случае ошибки
        """
        try:
            self.cursor.execute("""
                INSERT INTO users (telegram_id, username, number_phone, is_seller, full_name,
                                 work_time_start, work_time_end, work_days)
                VALUES (?, ?, ?, ?, ?, '10:00', '22:00', '1,2,3,4,5,6,7')
                RETURNING id
            """, (telegram_id, username, number_phone, int(is_seller), full_name))
            user_id = self.cursor.fetchone()[0]
            self.connection.commit()
            return user_id
        except sqlite3.IntegrityError:
            print(f"Пользователь с telegram_id {telegram_id} уже существует")
            return None
        except Exception as e:
            print(f"Ошибка при добавлении пользователя: {e}")
            return None

    def delete_user(self, user_id: int) -> bool:
        """Удаляет пользователя из базы данных
        Args:
            user_id: ID пользователя
        Returns:
            True если удаление успешно, False если произошла ошибка
        """
        try:
            self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при удалении пользователя: {e}")
            return False

    def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновляет данные пользователя
        Args:
            user_id: ID пользователя
            **kwargs: Поля для обновления (full_name, number_phone, work_time_start, 
                     work_time_end, work_days, is_seller)
        Returns:
            True если обновление успешно, False если произошла ошибка
        """
        valid_fields = {'full_name', 'number_phone', 'work_time_start', 
                       'work_time_end', 'work_days', 'is_seller'}
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in valid_fields:
                updates.append(f"{field} = ?")
                params.append(value if field != 'is_seller' else int(value))
                
        if not updates:
            return False
            
        try:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении пользователя: {e}")
            return False

    def get_user(self, user_id: Optional[int] = None, telegram_id: Optional[str] = None, 
                 username: Optional[str] = None) -> Optional[Tuple]:
        """Получает информацию о пользователе
        Args:
            user_id: ID пользователя
            telegram_id: Telegram ID пользователя  
            username: Username пользователя
        Returns:
            Кортеж с данными пользователя или None
        """
        try:
            if user_id is not None:
                self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            elif telegram_id is not None:
                self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            elif username is not None:
                self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            else:
                return None
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Ошибка при получении пользователя: {e}")
            return None

    def user_exists(self, user_id: Optional[int] = None, telegram_id: Optional[str] = None) -> bool:
        """Проверяет существование пользователя
        Args:
            user_id: ID пользователя
            telegram_id: Telegram ID пользователя
        Returns:
            True если пользователь существует, False если нет
        """
        return self.get_user(user_id, telegram_id) is not None

    def is_seller(self, user_id: Optional[int] = None, telegram_id: Optional[str] = None) -> bool:
        """Проверяет является ли пользователь продавцом
        Args:
            user_id: ID пользователя
            telegram_id: Telegram ID пользователя
        Returns:
            True если пользователь продавец, False если нет
        """
        user = self.get_user(user_id, telegram_id)
        return bool(user[4]) if user else False

    def set_is_seller(self, is_seller: bool, user_id: Optional[int] = None, 
                     telegram_id: Optional[str] = None) -> bool:
        """Устанавливает статус продавца для пользователя
        Args:
            is_seller: Новый статус
            user_id: ID пользователя
            telegram_id: Telegram ID пользователя
        Returns:
            True если обновление успешно, False если произошла ошибка
        """
        try:
            self.cursor.execute(
                "UPDATE users SET is_seller = ? WHERE id = ? OR telegram_id = ?",
                (int(is_seller), user_id, telegram_id)
            )
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении статуса продавца: {e}")
            return False

    #endregion

    #region Методы для таблицы service_types

    def add_service_type(self, name: str, created_by_id: str, required_fields: Dict[str, Dict[str, Any]]) -> Optional[int]:
        """
        Добавляет новый тип услуги с указаниями полями
        Args:
            name: Название типа услуги
            created_by_id: Telegram ID админа, создавшего тип
            required_fields: Словарь с описанием обязательных полей
        Returns:
            ID созданного типа услуги или None в случае ошибки
        """
        try:
            # Добавляем стандартные поля, если их нет
            default_fields = {
                "photo": {"type": "image", "label": "Фотография услуги", "required": True, "description": "Загрузите фото услуги"},
                "adress": {"type": "adress", "label": "Адрес", "required": True, "description": "Укажите адрес оказания услуги"},
                "district": {"type": "text", "label": "Район", "required": True, "description": "Укажите район оказания услуги"},
                "number_phone": {"type": "text", "label": "Номер телефона", "required": False, "description": "Укажите номер телефона для связи"},
                "price": {"type": "number", "label": "Стоимость", "required": True, "description": "Укажите стоимость в рублях"},
            }
            
            # Объединяем дефолтные поля с пользовательскими
            all_fields = {**default_fields, **required_fields}
            
            self.cursor.execute("""
                INSERT INTO service_types (name, created_by_id, required_fields)
                VALUES (?, ?, ?)
                RETURNING id
            """, (name, created_by_id, json.dumps(all_fields, ensure_ascii=False)))
            
            result = self.cursor.fetchone()
            self.connection.commit()
            return result[0] if result else None
            
        except sqlite3.IntegrityError:
            print(f"Тип услуги '{name}' уже существует")
            return None
        except Exception as e:
            print(f"Ошибка при создании типа услуги: {e}")
            return None

    def get_service_type(self, type_id: int) -> Optional[Dict]:
        """
        Получает информацию о типе услуги по ID
        Returns:
            Словарь с информацией о типе услуги и его полях
        """
        try:
            self.cursor.execute("""
                SELECT id, name, created_by_id, required_fields, is_active
                FROM service_types 
                WHERE id = ?
            """, (type_id,))
            
            row = self.cursor.fetchone()
            if not row:
                return None
                
            return {
                "id": row[0],
                "name": row[1],
                "created_by_id": row[2],
                "required_fields": json.loads(row[3]),
                "is_active": bool(row[4])
            }
        except Exception as e:
            print(f"Ошибка при получении типа услуги: {e}")
            return None

    def get_active_service_types(self) -> List[Dict]:
        """
        Получает список всех активных типов услуг
        Returns:
            Список словарей с информацией о типах услуг
        """
        try:
            self.cursor.execute("""
                SELECT id, name, required_fields 
                FROM service_types
                WHERE is_active = 1
                ORDER BY name
            """)
            
            types = []
            for row in self.cursor.fetchall():
                types.append({
                    "id": row[0],
                    "name": row[1],
                    "required_fields": json.loads(row[2])
                })
            return types
            
        except Exception as e:
            print(f"Ошибка при получении типов услуг: {e}")
            return []

    def deactivate_service_type(self, type_id: int) -> bool:
        """
        Деактивирует тип услуги (мягкое удаление)
        Returns:
            bool: Успешность операции
        """
        try:
            self.cursor.execute("""
                UPDATE service_types 
                SET is_active = 0
                WHERE id = ?
            """, (type_id,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при деактивации типа услуги: {e}")
            return False

    def increment_service_views(self, service_id: int) -> bool:
        """
        Увеличивает счетчик просмотров услуги
        Args:
            service_id: ID услуги
        Returns:
            bool: Успешность операции
        """
        try:
            self.cursor.execute("""
                UPDATE services
                SET views = views + 1
                WHERE id = ?
            """, (service_id,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении просмотров: {e}")
            return False

    #endregion

    #region Методы для таблицы services

    def add_service(self, user_id: int, service_type_id: int, title: str, photo_id: str,
                   city: str, district: str, street: str, house: str, number_phone: str, price: float, 
                   custom_fields: Dict[str, Any]) -> Optional[int]:
        """
        Создает новую услугу
        Args:
            user_id: ID пользователя
            service_type_id: ID типа услуги
            title: Название услуги
            photo_id: ID фотографии
            city: Город
            district: Район
            street: Улица
            house: Номер дома
            number_phone: Номер телефона
            price: Цена
            custom_fields: Дополнительные поля
        Returns:
            ID созданной услуги или None в случае ошибки
        """
        try:
            self.cursor.execute("""
                INSERT INTO services (
                    user_id, service_type_id, title, photo_id, city, 
                    district, street, house, number_phone, price, custom_fields
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, (
                user_id, service_type_id, title, photo_id, city,
                district, street, house, number_phone, price,
                json.dumps(custom_fields, ensure_ascii=False)
            ))

            result = self.cursor.fetchone()
            self.connection.commit()
            return result[0] if result else None

        except Exception as e:
            print(f"Ошибка при создании услуги: {e}")
            return None

    def get_services(self,
                    service_type_id: Optional[int] = None,
                    service_id: Optional[int] = None, 
                    user_id: Optional[int] = None,
                    status: Optional[str] = None,
                    limit: Optional[int] = None,
                    offset: Optional[int] = None,
                    order_by: str = 'created_at DESC') -> Optional[Union[Dict, List[Dict]]]:
        """
        Получает услуги с различными фильтрами
        Args:
            service_type_id: ID типа услуги
            service_id: ID конкретной услуги
            user_id: ID пользователя для получения его услуг 
            status: Статус услуг ('active', 'deactive', 'deleted', None для всех)
            limit: Ограничение количества результатов
            offset: Смещение для пагинации
            order_by: Сортировка результатов
        Returns:
            Dict с информацией об услуге или список Dict или None при ошибке
        """
        try:
            query = """
                SELECT 
                    s.*,
                    st.name as service_type_name,
                    st.required_fields as service_type_fields,
                    u.username as seller_username,
                    u.number_phone as seller_phone,
                    u.work_time_start as seller_work_time_start,
                    u.work_time_end as seller_work_time_end,
                    u.work_days as seller_work_days
                FROM services s
                LEFT JOIN service_types st ON s.service_type_id = st.id
                LEFT JOIN users u ON s.user_id = u.id
                WHERE 1=1
            """
            params = []

            if service_id is not None:
                query += " AND s.id = ?"
                params.append(service_id)
            if service_type_id is not None:
                query += " AND s.service_type_id = ?"
                params.append(service_type_id)
            if user_id is not None:
                query += " AND s.user_id = ?"
                params.append(user_id)
            if status is not None:
                query += " AND s.status = ?"
                params.append(status)

            allowed_orders = {'created_at', 'updated_at', 'price', 'views', 'id'}
            order_parts = order_by.lower().split()
            if len(order_parts) >= 1 and order_parts[0] in allowed_orders:
                direction = 'DESC' if len(order_parts) > 1 and order_parts[1].upper() == 'DESC' else 'ASC'
                query += f" ORDER BY s.{order_parts[0]} {direction}"
            else:
                query += " ORDER BY s.created_at DESC"

            if limit is not None and limit > 0:
                query += " LIMIT ?"
                params.append(min(limit, 100))  # Ограничиваем до 100 записей
            if offset is not None and offset >= 0:
                query += " OFFSET ?"
                params.append(offset)
                
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            if not rows:
                return None

            result = []
            columns = [desc[0] for desc in self.cursor.description]
            
            for row in rows:
                item = dict(zip(columns, row))
                
                for json_field in ['custom_fields', 'service_type_fields']:
                    if item.get(json_field):
                        try:
                            item[json_field] = json.loads(item[json_field])
                        except json.JSONDecodeError:
                            item[json_field] = {}
                    else:
                        item[json_field] = {}

                result.append(item)

            return result[0] if service_id else result

        except Exception as e:
            print(f"Ошибка при получении услуг: {str(e)}")
            return None

    def update_service(self, service_id: int, **kwargs) -> bool:
        """
        Обновляет информацию об услуге
        Args:
            service_id: ID услуги
            **kwargs: Поля для обновления (title, photo_id, city, etc.)
        Returns:
            bool: Успешность операции
        """
        try:
            allowed_fields = {'title', 'photo_id', 'city', 'district', 'street', 
                            'house', 'number_phone', 'price', 'custom_fields', 'status', 'views'}
            
            updates = []
            params = []
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = ?")
                    params.append(value if field != 'custom_fields' 
                                else json.dumps(value, ensure_ascii=False))
            
            if not updates:
                return False
                
            params.append(service_id)
            query = f"""
                UPDATE services 
                SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            
            self.cursor.execute(query, params)
            self.connection.commit()
            return True

        except Exception as e:
            print(f"Ошибка при обновлении услуги: {e}")
            return False

    def delete_service(self, service_id: int, hard_delete: bool = False) -> bool:
        """
        Удаляет услугу
        Args:
            service_id: ID услуги
            hard_delete: Если True - полное удаление из БД, если False - soft delete
        Returns:
            bool: Успешность операции
        """
        try:
            if hard_delete:
                self.cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
            else:
                self.cursor.execute("""
                    UPDATE services 
                    SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (service_id,))
                
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при удалении услуги: {e}")
            return False

    def filter_services(self,
                       service_type_id: Optional[int] = None,
                       city: Optional[str] = None, 
                       district: Optional[str] = None,
                       price_min: Optional[float] = None,
                       price_max: Optional[float] = None,
                       custom_fields: Optional[Dict[str, Any]] = None,
                       search_text: Optional[str] = None,
                       sort_by: str = 'created_at',
                       sort_direction: str = 'DESC',
                       limit: int = 20,
                       offset: int = 0,
                       status: str = 'active') -> List[Dict]:
        """
        Расширенный поиск и фильтрация услуг
        Args:
            service_type_id: ID типа услуги
            city: Город
            district: Район
            price_min: Минимальная цена
            price_max: Максимальная цена
            custom_fields: Фильтры по дополнительным полям в формате {"field_name": "value"}
            search_text: Текст для поиска в названии и описании
            sort_by: Поле для сортировки
            sort_direction: Направление сортировки (ASC/DESC)
            limit: Ограничение количества результатов
            offset: Смещение для пагинации
            status: Статус услуги ('active', 'deleted' и т.д.)
        Returns:
            Список услуг, соответствующих фильтрам
        """
        try:
            # Базовый запрос с основными JOIN
            query = """
                SELECT 
                    s.*,
                    st.name as service_type_name,
                    st.required_fields as service_type_fields,
                    u.username as seller_username,
                    u.number_phone as seller_phone
                FROM services s
                LEFT JOIN service_types st ON s.service_type_id = st.id
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.status = ?
            """
            params = [status]

            # Добавляем фильтры
            if service_type_id is not None:
                query += " AND s.service_type_id = ?"
                params.append(service_type_id)
            
            if city:
                query += " AND LOWER(s.city) LIKE LOWER(?)"
                params.append(f"%{city}%")
                
            if district:
                query += " AND LOWER(s.district) LIKE LOWER(?)"
                params.append(f"%{district}%")
                
            if price_min is not None:
                query += " AND s.price >= ?"
                params.append(float(price_min))
                
            if price_max is not None:
                query += " AND s.price <= ?"
                params.append(float(price_max))

            # Поиск по тексту в названии и описании
            if search_text:
                query += """ AND (
                    LOWER(s.title) LIKE LOWER(?) 
                    OR LOWER(json_extract(s.custom_fields, '$.description')) LIKE LOWER(?)
                )"""
                search_pattern = f"%{search_text}%"
                params.extend([search_pattern, search_pattern])

            # Применяем фильтры по дополнительным полям
            if custom_fields:
                for field, value in custom_fields.items():
                    if value is not None and value != '':
                        query += f" AND json_extract(s.custom_fields, '$.{field}') LIKE ?"
                        params.append(f"%{value}%")

            # Проверяем и применяем сортировку
            allowed_sort_fields = {'created_at', 'price', 'views', 'title'}
            allowed_directions = {'ASC', 'DESC'}
            
            sort_by = sort_by.lower() if sort_by else 'created_at'
            sort_direction = sort_direction.upper() if sort_direction else 'DESC'
            
            if sort_by in allowed_sort_fields and sort_direction in allowed_directions:
                query += f" ORDER BY s.{sort_by} {sort_direction}"
            else:
                query += " ORDER BY s.created_at DESC"

            # Добавляем пагинацию
            query += " LIMIT ? OFFSET ?"
            params.extend([max(1, int(limit)), max(0, int(offset))])

            # Выполняем запрос
            self.cursor.execute(query, params)
            
            # Формируем результат
            columns = [desc[0] for desc in self.cursor.description]
            result = []
            
            for row in self.cursor.fetchall():
                item = dict(zip(columns, row))
                
                # Обрабатываем JSON поля
                for json_field in ['custom_fields', 'service_type_fields']:
                    try:
                        if item.get(json_field):
                            item[json_field] = json.loads(item[json_field])
                        else:
                            item[json_field] = {}
                    except (json.JSONDecodeError, TypeError):
                        item[json_field] = {}
                
                # Приводим числовые поля к правильному типу
                if 'price' in item:
                    item['price'] = float(item['price'])
                if 'views' in item:
                    item['views'] = int(item['views'])
                        
                result.append(item)

            return result

        except Exception as e:
            print(f"Ошибка при фильтрации услуг: {e}")
            return []

    def get_cities(self) -> List[str]:
        """
        Получает список всех городов из активных услуг
        """
        try:
            self.cursor.execute("""
                SELECT DISTINCT city 
                FROM services 
                WHERE status = 'active'
                ORDER BY city
            """)
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении списка городов: {e}")
            return []

    def get_districts(self, city: str) -> List[str]:
        """
        Получает список районов для конкретного города
        """
        try:
            self.cursor.execute("""
                SELECT DISTINCT district 
                FROM services 
                WHERE status = 'active' AND LOWER(city) = LOWER(?)
                ORDER BY district
            """, (city,))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении списка районов: {e}")
            return []

    def get_price_range(self, service_type_id: Optional[int] = None, city: Optional[str] = None) -> Tuple[float, float]:
        """
        Получает минимальную и максимальную цену для заданных фильтров
        """
        try:
            query = """
                SELECT MIN(price), MAX(price)
                FROM services
                WHERE status = 'active'
            """
            params = []

            if service_type_id:
                query += " AND service_type_id = ?"
                params.append(service_type_id)
            if city:
                query += " AND LOWER(city) = LOWER(?)"
                params.append(city)

            self.cursor.execute(query, params)
            min_price, max_price = self.cursor.fetchone()
            return (min_price or 0, max_price or 0)
        except Exception as e:
            print(f"Ошибка при получении диапазона цен: {e}")
            return (0, 0)

    def get_service_by_id(self, service_id: int) -> Optional[Dict]:
        """
        Получает информацию об услуге по его ID
        """
        self.cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        return self.cursor.fetchone()   

    def update_service_status(self, service_id: int, status: str) -> None:
        """
        Обновляет статус услуги по его ID
        """
        self.cursor.execute("UPDATE services SET status = ? WHERE id = ?", (status, service_id))
        self.connection.commit()
    #endregion

    #region Методы для таблицы complaints

    def add_complaint(self, type: str, complainant_telegram_username: str, accused_telegram_username: str,
                     text: str, service_id: Optional[int] = None) -> bool:
        """
        Добавляет новую жалобу в базу данных
        Args:
            type: Тип жалобы ('user' или 'service')
            complainant_telegram_username: Username пользователя, создавшего жалобу
            accused_telegram_username: Username обвиняемого пользователя 
            text: Текст жалобы
            service_id: ID услуги (опционально, только для жалоб на услуги)
        Returns:
            bool: True если жалоба успешно добавлена, False в случае ошибки
        """
        try:
            if type not in ['user', 'service']:
                raise ValueError("Неверный тип жалобы")

            # Получаем telegram_id пользователей по username
            self.cursor.execute("SELECT telegram_id FROM users WHERE username = ?", (complainant_telegram_username,))
            complainant = self.cursor.fetchone()
            
            self.cursor.execute("SELECT telegram_id FROM users WHERE username = ?", (accused_telegram_username,))
            accused = self.cursor.fetchone()
            
            if not complainant or not accused:
                raise ValueError("Пользователь не найден")

            complainant_telegram_id = complainant[0]
            accused_telegram_id = accused[0]

            # Проверяем, существует ли сервис, если это жалоба на сервис
            if type == 'service' and service_id:
                self.cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
                service = self.cursor.fetchone()
                if not service:
                    raise ValueError("Сервис не найден")

            # Проверяем, не подает ли пользователь жалобу на самого себя
            # if complainant_telegram_id == accused_telegram_id:
            #     raise ValueError("Нельзя подать жалобу на самого себя")

            # Проверяем, не существует ли уже активная жалоба
            existing_complaint = self.cursor.execute("""
                SELECT id FROM complaints 
                WHERE complainant_telegram_id = ? AND accused_telegram_id = ? 
                AND type = ? AND status = 'pending'
                AND (service_id = ? OR (service_id IS NULL AND ? IS NULL))
            """, (complainant_telegram_id, accused_telegram_id, type, service_id, service_id)).fetchone()

            if existing_complaint:
                raise ValueError("У вас уже есть активная жалоба на этого пользователя/сервис")

            self.cursor.execute("""
                INSERT INTO complaints (
                    type, complainant_telegram_id, accused_telegram_id, service_id,
                    complaint_text, status, created_at, severity_level
                )
                VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, 'medium')
            """, (type, complainant_telegram_id, accused_telegram_id, service_id, text))
            
            self.connection.commit()
            return True
            
        except ValueError as ve:
            print(f"Ошибка валидации при добавлении жалобы: {ve}")
            return False
        except Exception as e:
            print(f"Ошибка при добавлении жалобы: {e}")
            return False

    def get_complaint_by_id(self, complaint_id: int) -> Optional[Dict]:
        """
        Получает жалобу по ID
        Args:
            complaint_id: ID жалобы
        Returns:
            Dict с данными жалобы или None
        """
        try:
            self.cursor.execute("""
                SELECT 
                    c.*,
                    u1.username as complainant_username,
                    u2.username as accused_username,
                    u3.username as resolved_by_username,
                    s.title as service_title,
                    s.id as service_id
                FROM complaints c
                LEFT JOIN users u1 ON c.complainant_telegram_id = u1.telegram_id
                LEFT JOIN users u2 ON c.accused_telegram_id = u2.telegram_id
                LEFT JOIN users u3 ON c.resolved_by_telegram_id = u3.telegram_id
                LEFT JOIN services s ON c.service_id = s.id
                WHERE c.id = ?
            """, (complaint_id,))
            
            row = self.cursor.fetchone()
            if not row:
                return None
                
            columns = [description[0] for description in self.cursor.description]
            complaint = dict(zip(columns, row))
            
            # Преобразуем timestamp в читаемый формат
            if complaint['created_at']:
                complaint['created_at'] = datetime.strptime(
                    complaint['created_at'], '%Y-%m-%d %H:%M:%S'
                ).strftime('%d.%m.%Y %H:%M')
            if complaint['resolved_at']:
                complaint['resolved_at'] = datetime.strptime(
                    complaint['resolved_at'], '%Y-%m-%d %H:%M:%S'
                ).strftime('%d.%m.%Y %H:%M')
                
            return complaint
            
        except Exception as e:
            print(f"Ошибка при получении жалобы: {e}")
            return None

    def get_complaints(self, status: Optional[str] = None, 
                      type: Optional[str] = None,
                      complainant_telegram_id: Optional[str] = None,
                      accused_telegram_id: Optional[str] = None,
                      service_id: Optional[int] = None,
                      limit: Optional[int] = None) -> List[Dict]:
        """
        Получает список жалоб с возможностью фильтрации
        Args:
            status: Статус жалобы ('pending', 'resolved', 'rejected')
            type: Тип жалобы ('user' или 'service')
            complainant_telegram_id: Telegram ID заявителя
            accused_telegram_id: Telegram ID обвиняемого
            service_id: ID услуги
            limit: Ограничение количества результатов
        Returns:
            List[Dict]: Список жалоб
        """
        try:
            query = """
                SELECT 
                    c.*,
                    u1.username as complainant_username,
                    u2.username as accused_username,
                    u3.username as resolved_by_username,
                    s.title as service_title,
                    s.id as service_id
                FROM complaints c
                LEFT JOIN users u1 ON c.complainant_telegram_id = u1.telegram_id
                LEFT JOIN users u2 ON c.accused_telegram_id = u2.telegram_id
                LEFT JOIN users u3 ON c.resolved_by_telegram_id = u3.telegram_id
                LEFT JOIN services s ON c.service_id = s.id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND c.status = ?"
                params.append(status)
            if type:
                query += " AND c.type = ?"
                params.append(type)
            if complainant_telegram_id:
                query += " AND c.complainant_telegram_id = ?"
                params.append(complainant_telegram_id)
            if accused_telegram_id:
                query += " AND c.accused_telegram_id = ?"
                params.append(accused_telegram_id)
            if service_id:
                query += " AND c.service_id = ?"
                params.append(service_id)
                
            query += " ORDER BY c.created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            self.cursor.execute(query, params)
            columns = [description[0] for description in self.cursor.description]
            complaints = []
            
            for row in self.cursor.fetchall():
                complaint = dict(zip(columns, row))
                
                # Преобразуем timestamp в читаемый формат
                if complaint['created_at']:
                    complaint['created_at'] = datetime.strptime(
                        complaint['created_at'], '%Y-%m-%d %H:%M:%S'
                    ).strftime('%d.%m.%Y %H:%M')
                if complaint['resolved_at']:
                    complaint['resolved_at'] = datetime.strptime(
                        complaint['resolved_at'], '%Y-%m-%d %H:%M:%S'
                    ).strftime('%d.%m.%Y %H:%M')
                    
                complaints.append(complaint)
                
            return complaints
            
        except Exception as e:
            print(f"Ошибка при получении жалоб: {e}")
            return []

    def update_complaint_status(self, complaint_id: int, status: str, 
                              resolved_by_telegram_id: str, resolution_text: str) -> bool:
        """
        Обновляет статус жалобы
        Args:
            complaint_id: ID жалобы
            status: Новый статус ('resolved' или 'rejected')
            resolved_by_telegram_id: Telegram ID модератора
            resolution_text: Текст решения
        Returns:
            bool: True если обновление успешно, False если произошла ошибка
        """
        try:
            if status not in ['resolved', 'rejected']:
                raise ValueError("Неверный статус жалобы")

            # Проверяем существование жалобы
            complaint = self.get_complaint_by_id(complaint_id)
            if not complaint:
                raise ValueError("Жалоба не найдена")

            # Проверяем, не обработана ли уже жалоба
            if complaint['status'] != 'pending':
                raise ValueError("Жалоба уже обработана")

            self.cursor.execute("""
                UPDATE complaints 
                SET status = ?,
                    resolved_by_telegram_id = ?,
                    resolution_text = ?,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
            """, (status, resolved_by_telegram_id, resolution_text, complaint_id))
            
            if self.cursor.rowcount == 0:
                raise ValueError("Не удалось обновить статус жалобы")
                
            self.connection.commit()
            return True
            
        except ValueError as ve:
            print(f"Ошибка валидации при обновлении статуса жалобы: {ve}")
            return False
        except Exception as e:
            print(f"Ошибка при обновлении статуса жалобы: {e}")
            return False

    def delete_complaint(self, complaint_id: int) -> bool:
        """
        Удаляет жалобу по ID
        Args:
            complaint_id: ID жалобы
        Returns:
            bool: True если удаление успешно, False если произошла ошибка
        """
        try:
            # Проверяем существование жалобы
            complaint = self.get_complaint_by_id(complaint_id)
            if not complaint:
                raise ValueError("Жалоба не найдена")

            self.cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
            
            if self.cursor.rowcount == 0:
                raise ValueError("Не удалось удалить жалобу")
                
            self.connection.commit()
            return True
            
        except ValueError as ve:
            print(f"Ошибка валидации при удалении жалобы: {ve}")
            return False
        except Exception as e:
            print(f"Ошибка при удалении жалобы: {e}")
            return False

    def get_user_complaints_stats(self, telegram_id: str) -> Dict[str, int]:
        """
        Получает статистику жалоб пользователя
        Args:
            telegram_id: Telegram ID пользователя
        Returns:
            Dict со статистикой:
            {
                'sent_total': общее количество отправленных жалоб,
                'received_total': общее количество полученных жалоб,
                'sent_pending': количество ожидающих рассмотрения отправленных жалоб,
                'received_pending': количество ожидающих рассмотрения полученных жалоб,
                'resolved_count': количество разрешенных жалоб,
                'rejected_count': количество отклоненных жалоб
            }
        """
        try:
            self.cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM complaints WHERE complainant_telegram_id = ?) as sent_total,
                    (SELECT COUNT(*) FROM complaints WHERE accused_telegram_id = ?) as received_total,
                    (SELECT COUNT(*) FROM complaints WHERE complainant_telegram_id = ? AND status = 'pending') as sent_pending,
                    (SELECT COUNT(*) FROM complaints WHERE accused_telegram_id = ? AND status = 'pending') as received_pending,
                    (SELECT COUNT(*) FROM complaints WHERE (complainant_telegram_id = ? OR accused_telegram_id = ?) AND status = 'resolved') as resolved_count,
                    (SELECT COUNT(*) FROM complaints WHERE (complainant_telegram_id = ? OR accused_telegram_id = ?) AND status = 'rejected') as rejected_count
            """, (telegram_id, telegram_id, telegram_id, telegram_id, telegram_id, telegram_id, telegram_id, telegram_id))
            
            row = self.cursor.fetchone()
            if not row:
                raise ValueError("Не удалось получить статистику")
                
            return {
                'sent_total': row[0],
                'received_total': row[1], 
                'sent_pending': row[2],
                'received_pending': row[3],
                'resolved_count': row[4],
                'rejected_count': row[5]
            }
            
        except Exception as e:
            print(f"Ошибка при получении статистики жалоб: {e}")
            return {
                'sent_total': 0,
                'received_total': 0,
                'sent_pending': 0,
                'received_pending': 0,
                'resolved_count': 0,
                'rejected_count': 0
            }

    def get_complaints_count(self, status: Optional[str] = None) -> int:
        """
        Получает количество жалоб с указанным статусом
        Args:
            status: Статус жалобы ('pending', 'resolved', 'rejected')
        Returns:
            int: Количество жалоб
        """
        try:
            query = "SELECT COUNT(*) FROM complaints"
            params = []
            
            if status:
                if status not in ['pending', 'resolved', 'rejected']:
                    raise ValueError("Неверный статус жалобы")
                query += " WHERE status = ?"
                params.append(status)
                
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            print(f"Ошибка при получении количества жалоб: {e}")
            return 0

    #endregion

    #region Методы для таблицы banned_users

    def ban_user(self, telegram_id: str, ban_date: str, ban_duration_hours: int, 
                reason: str) -> None:
        try:
            self.cursor.execute("""
                INSERT INTO banned_users (telegram_id, ban_date, ban_duration_hours, reason)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, ban_date, ban_duration_hours, reason))
            self.connection.commit()
        except sqlite3.IntegrityError:
            print("Пользователь уже заблокирован.")

    def unban_user(self, telegram_id: str) -> None:
        self.cursor.execute("DELETE FROM banned_users WHERE telegram_id = ?", (telegram_id,))
        self.connection.commit()

    def get_banned_user(self, telegram_id: str) -> Optional[Tuple]:
        self.cursor.execute("SELECT * FROM banned_users WHERE telegram_id = ?", (telegram_id,))
        return self.cursor.fetchone()

    def get_banned_users(self) -> List[Tuple]:
        self.cursor.execute("SELECT * FROM banned_users")
        return self.cursor.fetchall()

    #endregion

    def __del__(self):
        self.connection.close()

