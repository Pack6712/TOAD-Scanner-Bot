import time

from collections import defaultdict, deque

from aiogram import Router
from aiogram.types import Message

from database.moderation import (
    add_warning,
    count_warnings,
)

from database.modlog import (
    add_mod_log,
)


router = Router()


# =========================================================
# НАСТРОЙКИ АНТИСПАМА
# =========================================================

MESSAGE_LIMIT = 6
TIME_WINDOW = 8

VIOLATION_COOLDOWN = 20


# =========================================================
# ПАМЯТЬ
# =========================================================

user_messages = defaultdict(
    lambda: deque()
)

last_violation = {}


# =========================================================
# HELPERS
# =========================================================

async def user_is_admin(
    message: Message,
    user_id: int,
) -> bool:
    try:
        member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
        )

        return member.status in {
            "creator",
            "administrator",
        }

    except Exception:
        return False


# =========================================================
# ANTISPAM
# =========================================================

@router.message()
async def antispam_handler(
    message: Message,
):

    # -----------------------------------------
    # ТОЛЬКО ГРУППЫ
    # -----------------------------------------

    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        return

    # -----------------------------------------
    # НУЖЕН ПОЛЬЗОВАТЕЛЬ
    # -----------------------------------------

    if message.from_user is None:
        return

    user = message.from_user

    # -----------------------------------------
    # БОТОВ НЕ ПРОВЕРЯЕМ
    # -----------------------------------------

    if user.is_bot:
        return

    # -----------------------------------------
    # АДМИНОВ НЕ ПРОВЕРЯЕМ
    # -----------------------------------------

    if await user_is_admin(
        message,
        user.id,
    ):
        return

    now = time.monotonic()

    key = (
        message.chat.id,
        user.id,
    )

    messages = user_messages[key]

    # -----------------------------------------
    # УДАЛЯЕМ СТАРЫЕ ЗАПИСИ
    # -----------------------------------------

    while (
        messages
        and now - messages[0]
        > TIME_WINDOW
    ):
        messages.popleft()

    messages.append(
        now
    )

    # -----------------------------------------
    # ЛИМИТ НЕ ПРЕВЫШЕН
    # -----------------------------------------

    if len(messages) <= MESSAGE_LIMIT:
        return

    # -----------------------------------------
    # COOLDOWN
    # -----------------------------------------

    last = last_violation.get(
        key,
        0,
    )

    if (
        now - last
        < VIOLATION_COOLDOWN
    ):
        return

    last_violation[key] = now

    # -----------------------------------------
    # ОЧИЩАЕМ СЧЁТЧИК
    # -----------------------------------------

    messages.clear()

    # -----------------------------------------
    # WARN
    # -----------------------------------------

    reason = (
        "Антиспам: слишком много "
        "сообщений за короткое время"
    )

    await add_warning(
        telegram_chat_id=message.chat.id,
        user_id=user.id,
        moderator_id=message.bot.id,
        reason=reason,
    )

    await add_mod_log(
        telegram_chat_id=message.chat.id,
        user_id=user.id,
        moderator_id=message.bot.id,
        action="WARN",
        reason=reason,
    )

    warnings = await count_warnings(
        telegram_chat_id=message.chat.id,
        user_id=user.id,
    )

    try:
        await message.answer(
            "⚠️ TOAD ANTISPAM\n\n"
            f"👤 {user.full_name}\n"
            "Обнаружен слишком быстрый флуд.\n\n"
            f"⚠️ WARN: {warnings}/3"
        )

    except Exception as error:
        print(
            "Ошибка antispam warning:",
            repr(error),
        )