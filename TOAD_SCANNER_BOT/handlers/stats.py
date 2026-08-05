from aiogram import Router, F
from aiogram.types import Message

from database.functions import get_global_stats


router = Router()


@router.message(F.text == "📊 Статистика")
async def stats_handler(message: Message):

    stats = await get_global_stats()

    await message.answer(
        "📊 Статистика TOAD Scanner\n\n"
        f"📨 Всего жалоб: {stats['total']}\n\n"
        f"✅ Подтверждено: {stats['approved']}\n"
        f"⏳ На модерации: {stats['pending']}\n"
        f"❌ Отклонено: {stats['rejected']}\n\n"
        "🐸 База обновляется после проверки жалоб модератором."
    ) 