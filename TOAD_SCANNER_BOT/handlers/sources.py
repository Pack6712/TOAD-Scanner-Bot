import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID

from database.sources import (
    get_source_group,
    save_source_group,
    disable_source_group,
    create_candidate,
)


router = Router()


# =========================================================
# НАСТРОЙКИ
# =========================================================

SCAM_KEYWORDS = {
    "скам",
    "скамер",
    "scam",
    "мошенник",
    "мошенничество",
    "обман",
    "обманул",
    "кинул",
    "кинул на",
    "украл",
    "не вернул",
    "не выплатил",
    "не заплатил",
}


USERNAME_PATTERN = re.compile(
    r"@([A-Za-z0-9_]{5,32})"
)


# =========================================================
# ПРОВЕРКА АДМИНА ГРУППЫ
# =========================================================

async def is_group_admin(
    message: Message,
) -> bool:

    try:
        member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
        )

        return member.status in {
            "creator",
            "administrator",
        }

    except Exception as error:
        print(
            "Ошибка проверки администратора:",
            repr(error),
        )

        return False


# =========================================================
# /source_on
# =========================================================

@router.message(
    Command("source_on")
)
async def source_on(
    message: Message,
):

    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        await message.answer(
            "❌ Команда работает только в группе."
        )
        return

    if not await is_group_admin(
        message
    ):
        await message.answer(
            "❌ Включить источник может "
            "только администратор группы."
        )
        return

    source = await save_source_group(
        telegram_chat_id=message.chat.id,
        title=message.chat.title,
        username=message.chat.username,
        added_by=message.from_user.id,
    )

    await message.answer(
        "🐸 TOAD Source включён\n\n"
        f"Источник: {source.title}\n"
        f"Chat ID: {source.telegram_chat_id}\n\n"
        "Теперь бот будет искать в новых "
        "сообщениях потенциальные scam-сигналы.\n\n"
        "⚠️ Найденные сообщения не попадают "
        "в публичную базу автоматически — "
        "они создаются как кандидаты на модерацию."
    )


# =========================================================
# /source_off
# =========================================================

@router.message(
    Command("source_off")
)
async def source_off(
    message: Message,
):

    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        await message.answer(
            "❌ Команда работает только в группе."
        )
        return

    if not await is_group_admin(
        message
    ):
        await message.answer(
            "❌ Отключить источник может "
            "только администратор группы."
        )
        return

    success = await disable_source_group(
        telegram_chat_id=message.chat.id,
    )

    if not success:
        await message.answer(
            "ℹ️ Эта группа не была подключена "
            "как TOAD Source."
        )
        return

    await message.answer(
        "❌ TOAD Source отключён.\n\n"
        "Новые сообщения из этой группы "
        "больше не будут анализироваться."
    )


# =========================================================
# /source_status
# =========================================================

@router.message(
    Command("source_status")
)
async def source_status(
    message: Message,
):

    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        return

    source = await get_source_group(
        telegram_chat_id=message.chat.id,
    )

    if source is None:
        await message.answer(
            "🐸 TOAD Source\n\n"
            "Статус: ❌ не подключён"
        )
        return

    await message.answer(
        "🐸 TOAD Source\n\n"
        f"Группа: {source.title}\n"
        f"Статус: "
        f"{'✅ включён' if source.is_active else '❌ выключен'}"
    )


# =========================================================
# ПОИСК USERNAME В ТЕКСТЕ
# =========================================================

def extract_usernames(
    text: str,
) -> list[str]:

    found = USERNAME_PATTERN.findall(
        text
    )

    result = []

    for username in found:

        normalized = username.lower()

        if normalized not in result:
            result.append(
                normalized
            )

    return result


# =========================================================
# ПРОВЕРКА SCAM-КЛЮЧЕВЫХ СЛОВ
# =========================================================

def contains_scam_keyword(
    text: str,
) -> bool:

    lowered = text.lower()

    for keyword in SCAM_KEYWORDS:

        if keyword in lowered:
            return True

    return False


# =========================================================
# АВТОМАТИЧЕСКИЙ СБОР СИГНАЛОВ
# =========================================================

@router.message(
    F.chat.type.in_({
        "group",
        "supergroup",
    })
)
async def collect_source_signal(
    message: Message,
):

    # -----------------------------------------
    # ИГНОРИРУЕМ СООБЩЕНИЯ БОТОВ
    # -----------------------------------------

    if (
        message.from_user
        and message.from_user.is_bot
    ):
        return

    # -----------------------------------------
    # ПРОВЕРЯЕМ SOURCE
    # -----------------------------------------

    source = await get_source_group(
        telegram_chat_id=message.chat.id,
    )

    if source is None:
        return

    if not source.is_active:
        return

    # -----------------------------------------
    # НУЖЕН ТЕКСТ
    # -----------------------------------------

    text = (
        message.text
        or message.caption
    )

    if not text:
        return

    if len(text) < 5:
        return

    # -----------------------------------------
    # НУЖНО КЛЮЧЕВОЕ СЛОВО
    # -----------------------------------------

    if not contains_scam_keyword(
        text
    ):
        return

    # -----------------------------------------
    # ИЩЕМ @USERNAME
    # -----------------------------------------

    usernames = extract_usernames(
        text
    )

    if not usernames:
        return

    # -----------------------------------------
    # АВТОР СООБЩЕНИЯ
    # -----------------------------------------

    source_author_id = None
    source_author_username = None

    if message.from_user:

        source_author_id = (
            message.from_user.id
        )

        source_author_username = (
            message.from_user.username
        )

    # -----------------------------------------
    # СОЗДАЁМ КАНДИДАТОВ
    # -----------------------------------------

    created = []

    for username in usernames[:5]:

        candidate = await create_candidate(
            source_chat_id=message.chat.id,
            source_message_id=message.message_id,
            source_author_id=source_author_id,
            source_author_username=source_author_username,
            suspect_username=username,
            suspect_telegram_id=None,
            text=text,
        )

        created.append(
            candidate
        )

    # -----------------------------------------
    # УВЕДОМЛЯЕМ ГЛАВНОГО ADMIN_ID
    # -----------------------------------------

    if not created:
        return

    try:

        usernames_text = ", ".join(
            f"@{candidate.suspect_username}"
            for candidate in created
            if candidate.suspect_username
        )

        await message.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🚨 TOAD Source — новый сигнал\n\n"

                f"📡 Источник: "
                f"{message.chat.title}\n"

                f"🆔 Chat ID: "
                f"{message.chat.id}\n\n"

                f"👤 Упомянуты:\n"
                f"{usernames_text}\n\n"

                f"📝 Сообщение:\n"
                f"{text[:1500]}\n\n"

                "📌 Статус: pending\n\n"

                "⚠️ Это только сигнал. "
                "Он ещё не добавлен "
                "в публичную scam-базу."
            )
        )

    except Exception as error:

        print(
            "Ошибка уведомления "
            "о TOAD Source:",
            repr(error),
        )