from aiogram import BaseMiddleware
from aiogram.types import Message

class PrivateChatMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        # Разрешаем команду get_id везде
        if event.text and event.text == '/get_id':
            return await handler(event, data)
            
        # Остальные команды только в приватных чатах
        if event.chat.type != 'private':
            await event.answer("Эта команда доступна только в личных сообщениях.")
            return
            
        return await handler(event, data)