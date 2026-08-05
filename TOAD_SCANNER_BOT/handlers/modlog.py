from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database.modlog import (
    get_group_logs,
    get_user_logs,
)


router = Router()


ACTION_NAMES = {
    "WARN": "⚠️ WARN",
    "UNWARN": "✅ UNWARN",
    "MUTE": "🔇 MUTE",
    "UNMUTE": "🔊 UNMUTE",
    "KICK": "👢 KICK",
    "BAN": "🚫 BAN",
}


async def is_admin(
    message: Message,
) -> bool:
    if message.from_user is None:
        return False

    try:
        member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
        )

        return member.status in {
            "creator",
            "administrator",
        }

    except Exception:
        return False


def action_name(
    action: str,
) -> str:
    return ACTION_NAMES.get(
        action,
        f"🛡 {action}",
    )


@router.message(
    Command("modlog")
)
async def show_modlog(
    message: Message,
):
    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        await message.answer(
            "❌ Журнал модерации доступен "
            "только в группе."
        )
        return

    if not await is_admin(message):
        await message.answer(
            "❌ Журнал доступен только "
            "администраторам."
        )
        return

    logs = await get_group_logs(
        telegram_chat_id=message.chat.id,
        limit=15,
    )

    if not logs:
        await message.answer(
            "📋 TOAD MOD LOG\n\n"
            "Журнал пока пуст."
        )
        return

    text = (
        "📋 TOAD MOD LOG\n\n"
        f"🏠 Группа: {message.chat.title}\n"
        f"📊 Последних действий: {len(logs)}\n\n"
    )

    for log in logs:
        created_at = (
            log.created_at.strftime(
                "%d.%m.%Y %H:%M"
            )
            if log.created_at
            else "Неизвестно"
        )

        text += (
            "━━━━━━━━━━━━━━\n"
            f"#{log.id} • {action_name(log.action)}\n"
            f"👤 User ID: {log.user_id}\n"
            f"🛡 Moderator ID: {log.moderator_id}\n"
        )

        if log.reason:
            text += (
                f"📋 Причина: {log.reason}\n"
            )

        if log.duration_minutes:
            text += (
                f"⏱ Срок: "
                f"{log.duration_minutes} мин.\n"
            )

        text += (
            f"🕒 {created_at}\n"
        )

    await message.answer(text)


@router.message(
    Command("userlog")
)
async def show_userlog(
    message: Message,
):
    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        return

    if not await is_admin(message):
        await message.answer(
            "❌ Команда доступна только "
            "администраторам."
        )
        return

    if (
        not message.reply_to_message
        or not message.reply_to_message.from_user
    ):
        await message.answer(
            "⚠️ Используйте /userlog ответом "
            "на сообщение пользователя."
        )
        return

    target = (
        message.reply_to_message.from_user
    )

    logs = await get_user_logs(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
        limit=20,
    )

    if not logs:
        await message.answer(
            "📋 История модерации\n\n"
            f"👤 {target.full_name}\n"
            f"🆔 {target.id}\n\n"
            "✅ Записей нет."
        )
        return

    text = (
        "📋 ИСТОРИЯ МОДЕРАЦИИ\n\n"
        f"👤 {target.full_name}\n"
        f"🆔 {target.id}\n"
        f"📊 Действий: {len(logs)}\n\n"
    )

    for log in logs:
        created_at = (
            log.created_at.strftime(
                "%d.%m.%Y %H:%M"
            )
            if log.created_at
            else "Неизвестно"
        )

        text += (
            "━━━━━━━━━━━━━━\n"
            f"{action_name(log.action)}\n"
            f"🛡 Moderator ID: "
            f"{log.moderator_id}\n"
        )

        if log.reason:
            text += (
                f"📋 Причина: "
                f"{log.reason}\n"
            )

        if log.duration_minutes:
            text += (
                f"⏱ Срок: "
                f"{log.duration_minutes} мин.\n"
            )

        text += (
            f"🕒 {created_at}\n"
        )

    await message.answer(text)