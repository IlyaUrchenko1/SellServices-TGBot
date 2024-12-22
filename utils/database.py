import sqlite3
from typing import Optional, Tuple, Dict, Any, List
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
                    "city": {"type": "text", "label": "Город", "required": true, "description": "Укажите город оказания услуги"},
                    "district": {"type": "text", "label": "Район", "required": true, "description": "Укажите район города"},
                    "price": {"type": "number", "label": "Стоимость", "required": true, "description": "Укажите стоимость услуги в рублях"},
                    "title": {"type": "text", "label": "Название услуги", "required": true, "description": "Введите краткое название вашей услуги"}
                }'
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service_type_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                photo BLOB NOT NULL,
                city TEXT NOT NULL,
                district TEXT NOT NULL,
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
        Добавляет новый тип услуги с указанными полями
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
                "city": {"type": "text", "label": "Город", "required": True, "description": "Укажите город оказания услуги"},
                "district": {"type": "text", "label": "Район", "required": True, "description": "Укажите район города"},
                "price": {"type": "number", "label": "Стоимость", "required": True, "description": "Укажите стоимость в рублях"},
                "title": {"type": "text", "label": "Название", "required": True, "description": "Введите название услуги"}
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

    def add_service(self, user_id: int, service_type_id: int, title: str, photo: bytes,
                   city: str, district: str, price: float, custom_fields: Dict[str, Any]) -> Optional[int]:
        """
        Создает новую услугу
        Args:
            custom_fields: Дополнительные поля, специфичные для данного типа услуги
        Returns:
            ID созданной услуги или None в случае ошибки
        """
        try:
            self.cursor.execute("""
                INSERT INTO services (
                    user_id, service_type_id, title, photo, city, 
                    district, price, custom_fields
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, (
                user_id, service_type_id, title, photo, city,
                district, price, json.dumps(custom_fields, ensure_ascii=False)
            ))
            
            result = self.cursor.fetchone()
            self.connection.commit()
            return result[0] if result else None
            
        except Exception as e:
            print(f"Ошибка при создании услуги: {e}")
            return None

    def get_service(self, service_id: int) -> Optional[Dict]:
        """
        Получает детальную информацию об услуге
        """
        try:
            self.cursor.execute("""
                SELECT s.*, st.name as type_name, st.required_fields
                FROM services s
                JOIN service_types st ON s.service_type_id = st.id
                WHERE s.id = ? AND s.status = 'active'
            """, (service_id,))
            
            row = self.cursor.fetchone()
            if not row:
                return None
                
            return {
                "id": row[0],
                "user_id": row[1],
                "service_type": {
                    "id": row[2],
                    "name": row[12],
                    "required_fields": json.loads(row[13])
                },
                "title": row[3],
                "photo": row[4],
                "city": row[5],
                "district": row[6],
                "price": row[7],
                "custom_fields": json.loads(row[8]) if row[8] else {},
                "views": row[10],
                "created_at": row[11]
            }
            
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

    def get_services_by_user(self, user_id: int) -> List[Dict]:
        """
        Получает список всех активных услуг пользователя
        """
        try:
            self.cursor.execute("""
                SELECT s.id, s.title, s.price, s.city, s.district, s.views,
                       st.name as type_name
                FROM services s
                JOIN service_types st ON s.service_type_id = st.id
                WHERE s.user_id = ? AND s.status = 'active'
                ORDER BY s.created_at DESC
            """, (user_id,))
            
            services = []
            for row in self.cursor.fetchall():
                services.append({
                    "id": row[0],
                    "title": row[1],
                    "price": row[2],
                    "city": row[3],
                    "district": row[4],
                    "views": row[5],
                    "type_name": row[6]
                })
            return services
            
        except Exception as e:
            print(f"Ошибка при получении списка услуг пользователя: {e}")
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
            print(f"Ошибка при деактивации услуги: {e}")
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

