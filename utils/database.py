import sqlite3
from typing import Optional, Tuple


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
                telegram_id TEXT,
                full_name TEXT,
                number_phone TEXT,
                is_seller BOOLEAN DEFAULT 0
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_name TEXT,
                service_description TEXT,
                price REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complainant_telegram_id TEXT,
                accused_telegram_id TEXT,
                date TEXT,
                text TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT,
                ban_date TEXT,
                ban_duration_hours INTEGER,
                reason TEXT
            )
        """)

        self.connection.commit()

    #region Методы для таблицы users

    def add_user(self, telegram_id: str, full_name: Optional[str] = None, number_phone: Optional[str] = None, is_seller: bool = False) -> None:
        try:
            self.cursor.execute("""
                INSERT INTO users (telegram_id, full_name, number_phone, is_seller)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, full_name, number_phone, int(is_seller)))
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

    def get_user(self, user_id: Optional[int] = None, telegram_id: Optional[str] = None) -> Optional[Tuple]:
        if user_id is not None:
            self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        elif telegram_id is not None:
            self.cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
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

    #region Методы для таблицы services

    def add_service(self, user_id: int, service_name: str, service_description: str, price: float) -> None:
        self.cursor.execute("""
            INSERT INTO services (user_id, service_name, service_description, price)
            VALUES (?, ?, ?, ?)
        """, (user_id, service_name, service_description, price))
        self.connection.commit()

    def delete_service(self, service_id: int) -> None:
        self.cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
        self.connection.commit()

    def update_service(self, service_id: int, service_name: Optional[str] = None,
                       service_description: Optional[str] = None, price: Optional[float] = None) -> None:
        updates = []
        params = []
        if service_name is not None:
            updates.append("service_name = ?")
            params.append(service_name)
        if service_description is not None:
            updates.append("service_description = ?")
            params.append(service_description)
        if price is not None:
            updates.append("price = ?")
            params.append(price)
        params.append(service_id)
        if updates:
            self.cursor.execute(f"UPDATE services SET {', '.join(updates)} WHERE id = ?", params)
            self.connection.commit()

    def get_services_by_user(self, user_id: int) -> list:
        self.cursor.execute("SELECT * FROM services WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    #endregion

    #region Методы для таблицы complaints

    def add_complaint(self, complainant_telegram_id: str, accused_telegram_id: str, date: str, text: str) -> None:
        self.cursor.execute("""
            INSERT INTO complaints (complainant_telegram_id, accused_telegram_id, date, text)
            VALUES (?, ?, ?, ?)
        """, (complainant_telegram_id, accused_telegram_id, date, text))
        self.connection.commit()

    def delete_complaint(self, complaint_id: int) -> None:
        self.cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        self.connection.commit()

    def update_complaint(self, complaint_id: int, text: Optional[str] = None) -> None:
        if text is not None:
            self.cursor.execute("UPDATE complaints SET text = ? WHERE id = ?", (text, complaint_id))
            self.connection.commit()

    def get_complaints(self) -> list:
        self.cursor.execute("SELECT * FROM complaints")
        return self.cursor.fetchall()

    #endregion

    #region Методы для таблицы banned_users

    def ban_user(self, telegram_id: str, ban_date: str, ban_duration_hours: int, reason: str) -> None:
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

    def get_banned_users(self) -> list:
        self.cursor.execute("SELECT * FROM banned_users")
        return self.cursor.fetchall()

    #endregion

    def __del__(self):
        self.connection.close()

