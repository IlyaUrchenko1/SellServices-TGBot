import sqlite3
from typing import Optional, Tuple, Dict, Any, List, Union
import json


class Database:
    def __init__(self, db_name="services.db"):
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
                is_seller BOOLEAN DEFAULT 0
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
                    "number_phone": {"type": "text", "label": "Номер телефона", "required": true, "description": "Укажите номер телефона для связи"},
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
                complainant_telegram_username TEXT,
                accused_telegram_username TEXT,
                date TEXT,
                text TEXT
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

    def add_user(self, telegram_id: str, username: str, number_phone: Optional[str] = None, is_seller: bool = False) -> None:
        try:
            self.cursor.execute("""
                INSERT INTO users (telegram_id, username, number_phone, is_seller)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, username, number_phone, int(is_seller)))
            self.connection.commit()
        except sqlite3.IntegrityError:
            print("Пользователь с таким telegram_id уже существует.")

    def delete_user(self, user_id: int) -> None:
        self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.connection.commit()

    def update_user(self, user_id: int, full_name: Optional[str] = None, number_phone: Optional[str] = None) -> None:
        updates = []
        params = []
        if full_name is not None:
            updates.append("full_name = ?")
            params.append(full_name)
        if number_phone is not None:
            updates.append("number_phone = ?")
            params.append(number_phone)
        params.append(user_id)
        if updates:
            self.cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            self.connection.commit()

    def get_user(self, user_id: Optional[int] = None, telegram_id: Optional[str] = None, username: Optional[str] = None) -> Optional[Tuple]:
        if user_id is not None:
            self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        elif telegram_id is not None:
            self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        elif username is not None:
            self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        else:
            return None
        return self.cursor.fetchone()

    def user_exists(self, user_id: Optional[int] = None, telegram_id: Optional[str] = None) -> bool:
        return self.get_user(user_id, telegram_id) is not None

    def is_seller(self, user_id: Optional[int] = None, telegram_id: Optional[str] = None) -> bool:
        user = self.get_user(user_id, telegram_id)
        if user:
            return bool(user[4])
        return False

    def set_is_seller(self, is_seller: bool, user_id: Optional[int] = None, telegram_id: Optional[str] = None) -> None:
        self.cursor.execute("UPDATE users SET is_seller = ? WHERE id = ? OR telegram_id = ?",
                            (int(is_seller), user_id, telegram_id))
        self.connection.commit()

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
                "number_phone": {"type": "text", "label": "Номер телефона", "required": True, "description": "Укажите номер телефона для связи"},
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

    def get_service(self, service_id: Optional[int] = None, user_id: Optional[int] = None) -> Optional[Union[Dict, List[Dict]]]:
        """
        Получает детальную информацию об услуге по ID услуги ��ли ID пользователя
        Args:
            service_id: ID услуги (опционально)
            user_id: ID пользователя (опционально)
        Returns:
            Dict с информацией об услуге или список Dict для user_id или None при ошибке
        """
        try:
            query = """
                SELECT 
                    s.id, s.user_id, s.service_type_id, s.title, s.photo_id,
                    s.city, s.district, s.street, s.house, s.number_phone, 
                    s.price, s.custom_fields, s.views, s.created_at,
                    st.name as type_name, st.required_fields
                FROM services s
                JOIN service_types st ON s.service_type_id = st.id
                WHERE s.status = 'active'
            """
            params = []

            if service_id is not None:
                query += " AND s.id = ?"
                params.append(service_id)
            elif user_id is not None:
                query += " AND s.user_id = ?"
                params.append(user_id)
            else:
                raise ValueError("Необходимо указать service_id или user_id")

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            if not rows:
                return None

            def safe_json_loads(json_str: Optional[str]) -> dict:
                """Безопасная загрузка JSON строки"""
                if not json_str:
                    return {}
                try:
                    return json.loads(str(json_str))
                except (json.JSONDecodeError, TypeError):
                    return {}

            def row_to_dict(row: Tuple) -> Dict:
                """Преобразование строки результата в словарь"""
                return {
                    "id": row[0],
                    "user_id": row[1], 
                    "service_type_id": row[2],
                    "title": row[3],
                    "photo_id": row[4],
                    "city": row[5],
                    "district": row[6],
                    "street": row[7],
                    "house": row[8],
                    "number_phone": row[9],
                    "price": float(row[10]),
                    "custom_fields": safe_json_loads(row[11]),
                    "views": row[12],
                    "created_at": row[13],
                    "type_name": row[14],
                    "required_fields": safe_json_loads(row[15])
                }

            if service_id is not None:
                return row_to_dict(rows[0])
            else:
                return [row_to_dict(row) for row in rows]

        except Exception as e:
            print(f"Ошибка при получении услуги: {e}")
            return None

    def get_services_by_type(self, type_id: int, limit: int = 20, offset: int = 0) -> List[Dict]:
        """
        Получает список услуг определенного типа с пагинацией
        """
        try:
            self.cursor.execute("""
                SELECT s.id, s.title, s.price, s.city, s.district, s.views, 
                       u.full_name as seller_name
                FROM services s
                JOIN users u ON s.user_id = u.id
                WHERE s.service_type_id = ? AND s.status = 'active'
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            """, (type_id, limit, offset))
            
            services = []
            for row in self.cursor.fetchall():
                services.append({
                    "id": row[0],
                    "title": row[1],
                    "price": row[2],
                    "city": row[3],
                    "district": row[4],
                    "views": row[5],
                    "seller_name": row[6]
                })
            return services
            
        except Exception as e:
            print(f"Ошибка при получении списка услуг: {e}")
            return []

    def update_service_views(self, service_id: int) -> None:
        """
        Увеличивает счетчик просмотров услуги
        """
        try:
            self.cursor.execute("""
                UPDATE services 
                SET views = views + 1
                WHERE id = ?
            """, (service_id,))
            self.connection.commit()
        except Exception as e:
            print(f"Ошибка при обновлении просмотров: {e}")

    def deactivate_service(self, service_id: int, user_id: int) -> bool:
        """
        Деактивирует услугу (только владелец может деактивировать)
        """
        try:
            self.cursor.execute("""
                UPDATE services 
                SET status = 'inactive'
                WHERE id = ? AND user_id = ?
            """, (service_id, user_id))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при ��еактивации услуги: {e}")
            return False

    #endregion

    #region Методы для таблицы complaints

    def add_complaint(self, complainant_telegram_username: str, accused_telegram_username: str, 
                     date: str, text: str) -> None:
        self.cursor.execute("""
            INSERT INTO complaints (complainant_telegram_username, accused_telegram_username, date, text)
            VALUES (?, ?, ?, ?)
        """, (complainant_telegram_username, accused_telegram_username, date, text))
        self.connection.commit()


    def get_complaints(self) -> List[Tuple]:
        self.cursor.execute("SELECT * FROM complaints")
        return self.cursor.fetchall()


    def delete_complaint_by_complainant_telegram_username(self, complainant_telegram_username: int) -> None:
        self.cursor.execute("DELETE FROM complaints WHERE complainant_telegram_username = ?", (complainant_telegram_username,))
        self.connection.commit()

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

