import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from middlewares.antiflood import AntiFloodMiddleware
from middlewares.check_ban import BanCheckMiddleware
from handlers import main_handler
from middlewares.private_chat import PrivateChatMiddleware

load_dotenv()

# Настройки бота по умолчанию
default_setting = DefaultBotProperties(parse_mode='HTML')
bot = Bot(os.getenv("BOT_TOKEN"), default=default_setting)
dp = Dispatcher()

async def main():
    # Добавление промежуточных обработчиков
    dp.message.middleware(PrivateChatMiddleware())
    dp.message.middleware(BanCheckMiddleware())
    # dp.message.middleware(AntiFloodMiddleware(limit=1))  # Антифлуд можно включить по необходимости

    # Включение роутеров
    dp.include_routers(main_handler.router)
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        print("Бот стартовал :)")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен :(")