from datetime import timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ChatPermissions,
)

from database.moderation import (
    add_warning,
    count_warnings,
    get_user_warnings,
    remove_last_warning,
    clear_warnings,
)

from database.modlog import (
    add_mod_log,
)


router = Router()


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


async def bot_is_admin(
    message: Message,
) -> bool:
    try:
        member = await message.bot.get_chat_member(
            chat_id=message.chat.id,
            user_id=message.bot.id,
        )

        return (
            member.status
            == "administrator"
        )

    except Exception:
        return False


def get_reply_target(
    message: Message,
):
    if not message.reply_to_message:
        return None

    return (
        message.reply_to_message.from_user
    )


def get_reason(
    message: Message,
) -> str | None:

    if not message.text:
        return None

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:
        return None

    reason = parts[1].strip()

    if not reason:
        return None

    return reason[:500]


async def check_permissions(
    message: Message,
) -> bool:

    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        await message.answer(
            "❌ Команда работает только в группе."
        )
        return False

    if message.from_user is None:
        return False

    if not await user_is_admin(
        message,
        message.from_user.id,
    ):
        await message.answer(
            "❌ Команда доступна только "
            "администраторам группы."
        )
        return False

    if not await bot_is_admin(
        message
    ):
        await message.answer(
            "❌ TOAD Scanner должен быть "
            "администратором группы."
        )
        return False

    if not message.reply_to_message:
        await message.answer(
            "⚠️ Используйте команду ответом "
            "на сообщение пользователя."
        )
        return False

    if (
        message.reply_to_message.from_user
        is None
    ):
        await message.answer(
            "❌ Не удалось определить пользователя."
        )
        return False

    return True


# =========================================================
# WARN
# =========================================================

@router.message(
    Command("warn")
)
async def warn_user(
    message: Message,
):

    if not await check_permissions(
        message
    ):
        return

    target = get_reply_target(
        message
    )

    if target is None:
        return

    if target.id == message.from_user.id:
        await message.answer(
            "❌ Нельзя выдать предупреждение самому себе."
        )
        return

    if target.id == message.bot.id:
        await message.answer(
            "❌ Нельзя выдать предупреждение TOAD Scanner."
        )
        return

    if await user_is_admin(
        message,
        target.id,
    ):
        await message.answer(
            "❌ Нельзя выдать предупреждение администратору."
        )
        return

    reason = get_reason(
        message
    )

    # -----------------------------------------
    # SAVE WARNING
    # -----------------------------------------

    await add_warning(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
        moderator_id=message.from_user.id,
        reason=reason,
    )

    # -----------------------------------------
    # MOD LOG
    # -----------------------------------------

    await add_mod_log(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
        moderator_id=message.from_user.id,
        action="WARN",
        reason=reason,
    )

    warnings = await count_warnings(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
    )

    text = (
        "⚠️ ПРЕДУПРЕЖДЕНИЕ\n\n"
        f"👤 Пользователь: {target.full_name}\n"
        f"🆔 ID: {target.id}\n"
        f"⚠️ Предупреждений: {warnings}/3"
    )

    if reason:
        text += (
            "\n\n"
            "📋 Причина:\n"
            f"{reason}"
        )

    await message.answer(
        text
    )

    # =====================================================
    # AUTO MUTE AFTER 3 WARNS
    # =====================================================

    if warnings >= 3:

        until_date = (
            message.date
            + timedelta(
                hours=1
            )
        )

        try:

            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target.id,

                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    can_manage_topics=False,
                ),

                until_date=until_date,
            )

            # ---------------------------------
            # LOG AUTO MUTE
            # ---------------------------------

            await add_mod_log(
                telegram_chat_id=message.chat.id,
                user_id=target.id,
                moderator_id=message.from_user.id,
                action="MUTE",
                reason="Автоматически после 3 WARN",
                duration_minutes=60,
            )

            # ---------------------------------
            # RESET WARNS
            # ---------------------------------

            await clear_warnings(
                telegram_chat_id=message.chat.id,
                user_id=target.id,
            )

            await message.answer(
                "🔇 АВТОМАТИЧЕСКИЙ MUTE\n\n"
                f"👤 {target.full_name}\n"
                "⚠️ Получено 3 предупреждения.\n"
                "⏱ Ограничение: 1 час.\n\n"
                "Счётчик WARN сброшен."
            )

        except Exception as error:

            print(
                "Ошибка automatic mute:",
                repr(error),
            )

            await message.answer(
                "⚠️ Пользователь получил 3 WARN, "
                "но автоматический mute не удался.\n\n"
                "Проверьте права TOAD Scanner."
            )


# =========================================================
# WARNS
# =========================================================

@router.message(
    Command("warns")
)
async def warns_user(
    message: Message,
):

    if not await check_permissions(
        message
    ):
        return

    target = get_reply_target(
        message
    )

    if target is None:
        return

    warnings = await get_user_warnings(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
    )

    if not warnings:
        await message.answer(
            "✅ У пользователя нет предупреждений."
        )
        return

    text = (
        "⚠️ ПРЕДУПРЕЖДЕНИЯ\n\n"
        f"👤 {target.full_name}\n"
        f"🆔 ID: {target.id}\n\n"
        f"Всего: {len(warnings)}\n\n"
    )

    for warning in warnings[:10]:

        created_at = (
            warning.created_at.strftime(
                "%d.%m.%Y %H:%M"
            )
            if warning.created_at
            else "Неизвестно"
        )

        reason = (
            warning.reason
            if warning.reason
            else "Без причины"
        )

        text += (
            f"• WARN #{warning.id}\n"
            f"📋 Причина: {reason}\n"
            f"🛡 Moderator ID: "
            f"{warning.moderator_id}\n"
            f"🕒 {created_at}\n\n"
        )

    await message.answer(
        text
    )


# =========================================================
# UNWARN
# =========================================================

@router.message(
    Command("unwarn")
)
async def unwarn_user(
    message: Message,
):

    if not await check_permissions(
        message
    ):
        return

    target = get_reply_target(
        message
    )

    if target is None:
        return

    success = await remove_last_warning(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
    )

    if not success:
        await message.answer(
            "ℹ️ У пользователя нет предупреждений."
        )
        return

    await add_mod_log(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
        moderator_id=message.from_user.id,
        action="UNWARN",
        reason=get_reason(message),
    )

    warnings = await count_warnings(
        telegram_chat_id=message.chat.id,
        user_id=target.id,
    )

    await message.answer(
        "✅ ПРЕДУПРЕЖДЕНИЕ СНЯТО\n\n"
        f"👤 {target.full_name}\n"
        f"⚠️ Осталось WARN: {warnings}"
    )


# =========================================================
# MUTE
# =========================================================

@router.message(
    Command("mute")
)
async def mute_user(
    message: Message,
):

    if not await check_permissions(
        message
    ):
        return

    target = get_reply_target(
        message
    )

    if target is None:
        return

    if target.id == message.from_user.id:
        await message.answer(
            "❌ Нельзя замутить самого себя."
        )
        return

    if target.id == message.bot.id:
        await message.answer(
            "❌ Нельзя замутить TOAD Scanner."
        )
        return

    if await user_is_admin(
        message,
        target.id,
    ):
        await message.answer(
            "❌ Нельзя замутить администратора."
        )
        return

    args = (
        message.text.split()
        if message.text
        else []
    )

    minutes = 30

    if len(args) >= 2:

        try:
            minutes = int(
                args[1]
            )

        except ValueError:
            await message.answer(
                "❌ Использование:\n"
                "/mute 30\n\n"
                "30 — количество минут."
            )
            return

    if minutes < 1:
        await message.answer(
            "❌ Минимум 1 минута."
        )
        return

    if minutes > 10080:
        await message.answer(
            "❌ Максимум 10080 минут "
            "(7 дней)."
        )
        return

    reason = None

    if len(args) >= 3:
        reason = " ".join(
            args[2:]
        )[:500]

    until_date = (
        message.date
        + timedelta(
            minutes=minutes
        )
    )

    try:

        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,

            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                can_manage_topics=False,
            ),

            until_date=until_date,
        )

        await add_mod_log(
            telegram_chat_id=message.chat.id,
            user_id=target.id,
            moderator_id=message.from_user.id,
            action="MUTE",
            reason=reason,
            duration_minutes=minutes,
        )

        text = (
            "🔇 ПОЛЬЗОВАТЕЛЬ ЗАМУЧЕН\n\n"
            f"👤 {target.full_name}\n"
            f"🆔 ID: {target.id}\n"
            f"⏱ Срок: {minutes} мин."
        )

        if reason:
            text += (
                "\n\n📋 Причина:\n"
                f"{reason}"
            )

        await message.answer(
            text
        )

    except Exception as error:

        print(
            "Ошибка mute:",
            repr(error),
        )

        await message.answer(
            "❌ Не удалось замутить пользователя.\n"
            "Проверьте права TOAD Scanner."
        )


# =========================================================
# UNMUTE
# =========================================================

@router.message(
    Command("unmute")
)
async def unmute_user(
    message: Message,
):

    if not await check_permissions(
        message
    ):
        return

    target = get_reply_target(
        message
    )

    if target is None:
        return

    reason = get_reason(
        message
    )

    try:

        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,

            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
                can_manage_topics=False,
            ),
        )

        await add_mod_log(
            telegram_chat_id=message.chat.id,
            user_id=target.id,
            moderator_id=message.from_user.id,
            action="UNMUTE",
            reason=reason,
        )

        await message.answer(
            "🔊 ОГРАНИЧЕНИЯ СНЯТЫ\n\n"
            f"👤 {target.full_name}\n"
            f"🆔 ID: {target.id}"
        )

    except Exception as error:

        print(
            "Ошибка unmute:",
            repr(error),
        )

        await message.answer(
            "❌ Не удалось снять ограничения."
        )


# =========================================================
# BAN
# =========================================================

@router.message(
    Command("ban")
)
async def ban_user(
    message: Message,
):

    if not await check_permissions(
        message
    ):
        return

    target = get_reply_target(
        message
    )

    if target is None:
        return

    if target.id == message.from_user.id:
        await message.answer(
            "❌ Нельзя заблокировать самого себя."
        )
        return

    if target.id == message.bot.id:
        await message.answer(
            "❌ Нельзя заблокировать TOAD Scanner."
        )
        return

    if await user_is_admin(
        message,
        target.id,
    ):
        await message.answer(
            "❌ Нельзя заблокировать администратора."
        )
        return

    reason = get_reason(
        message
    )

    try:

        await message.bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            revoke_messages=True,
        )

        await add_mod_log(
            telegram_chat_id=message.chat.id,
            user_id=target.id,
            moderator_id=message.from_user.id,
            action="BAN",
            reason=reason,
        )

        text = (
            "🚫 ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН\n\n"
            f"👤 {target.full_name}\n"
            f"🆔 ID: {target.id}"
        )

        if reason:
            text += (
                "\n\n📋 Причина:\n"
                f"{reason}"
            )

        await message.answer(
            text
        )

    except Exception as error:

        print(
            "Ошибка ban:",
            repr(error),
        )

        await message.answer(
            "❌ Не удалось заблокировать пользователя."
        )


# =========================================================
# KICK
# =========================================================

@router.message(
    Command("kick")
)
async def kick_user(
    message: Message,
):

    if not await check_permissions(
        message
    ):
        return

    target = get_reply_target(
        message
    )

    if target is None:
        return

    if target.id == message.from_user.id:
        await message.answer(
            "❌ Нельзя кикнуть самого себя."
        )
        return

    if target.id == message.bot.id:
        await message.answer(
            "❌ Нельзя кикнуть TOAD Scanner."
        )
        return

    if await user_is_admin(
        message,
        target.id,
    ):
        await message.answer(
            "❌ Нельзя кикнуть администратора."
        )
        return

    reason = get_reason(
        message
    )

    try:

        await message.bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
        )

        await message.bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            only_if_banned=True,
        )

        await add_mod_log(
            telegram_chat_id=message.chat.id,
            user_id=target.id,
            moderator_id=message.from_user.id,
            action="KICK",
            reason=reason,
        )

        text = (
            "👢 ПОЛЬЗОВАТЕЛЬ ИСКЛЮЧЁН\n\n"
            f"👤 {target.full_name}\n"
            f"🆔 ID: {target.id}"
        )

        if reason:
            text += (
                "\n\n📋 Причина:\n"
                f"{reason}"
            )

        await message.answer(
            text
        )

    except Exception as error:

        print(
            "Ошибка kick:",
            repr(error),
        )

        await message.answer(
            "❌ Не удалось исключить пользователя."
        )