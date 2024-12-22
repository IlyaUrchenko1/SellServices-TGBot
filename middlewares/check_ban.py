from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from utils.database import Database

import datetime

db = Database()

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, (Message, CallbackQuery)):
            user = db.get_user(telegram_id=str(event.from_user.id))
            if not user:
                return await handler(event, data)
                
            username = user[2]  # Получаем username пользователя
            banned_users = db.get_banned_users()
            
            for banned_user in banned_users:
                if banned_user[1] == username:  # Проверяем по username
                    ban_date = datetime.datetime.strptime(banned_user[2], "%Y-%m-%d %H:%M:%S")
                    ban_duration = datetime.timedelta(hours=banned_user[3])
                    ban_end_date = ban_date + ban_duration
                    remaining_time = ban_end_date - datetime.datetime.now()
                    
                    if remaining_time.total_seconds() > 0:
                        remaining_hours = int(remaining_time.total_seconds() // 3600)
                        remaining_minutes = int((remaining_time.total_seconds() % 3600) // 60)
                        
                        if isinstance(event, Message):
                            await event.answer(
                                f"❌ Вы заблокированы на {remaining_hours} часов и {remaining_minutes} минут\n"
                                f"Причина: {banned_user[4]}\n"
                                "Если вы заблокированы по ошибке, пожалуйста, обратитесь в поддержку"
                            )
                        else:
                            await event.answer(
                                f"❌ Вы заблокированы на {remaining_hours}ч {remaining_minutes}мин. Причина: {banned_user[4]}", 
                                show_alert=True
                            )
                        return
                        
        return await handler(event, data)