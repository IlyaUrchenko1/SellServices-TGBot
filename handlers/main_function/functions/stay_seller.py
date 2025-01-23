from aiogram import Router, F
from aiogram.types import Message

router = Router(name='stay_seller')


@router.message(F.text == "💲 Стать продавцом")
async def become_seller(message: Message):
    await message.answer(
        "🌟 Хотите стать продавцом? Отлично!\n\n"
        "📱 Для этого напишите администратору бота:\n"
        "👉 @Ilya\n\n"
        "✨ После подтверждения вы сможете:\n"
        "• Публиковать свои услуги\n" 
        "• Управлять объявлениями\n"
        "• Получать заказы от клиентов\n\n"
        "💫 Присоединяйтесь к нашему сообществу продавцов!"
    )
    