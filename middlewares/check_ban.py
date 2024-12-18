from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from utils.database import Database

import datetime

db = Database()

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id if isinstance(event, (Message, CallbackQuery)) else None
        if user_id:
            banned_users = db.get_banned_users()
            for banned_user in banned_users:
                if banned_user[1] == str(user_id):  # Проверяем, совпадает ли telegram_id
                    ban_date = datetime.datetime.strptime(banned_user[2], "%Y-%m-%d %H:%M:%S")
                    ban_duration = datetime.timedelta(hours=banned_user[3])
                    ban_end_date = ban_date + ban_duration
                    remaining_time = ban_end_date - datetime.datetime.now()
                    if remaining_time.total_seconds() > 0:
                        remaining_hours = remaining_time.total_seconds() // 3600
                        remaining_minutes = (remaining_time.total_seconds() % 3600) // 60
                        await event.answer(f"❌ Вы забанены на {remaining_hours} часов и {remaining_minutes} минут. Причина: {banned_user[4]}", show_alert=True)
                        return  # Прекращаем обработку, если пользователь в бане

        return await handler(event, data)  # Продолжаем обработку, если пользователь не в бане