from datetime import timedelta

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
)

from sqlalchemy import select

from database.database import Session
from database.models import (
    ScamReport,
    ScamEntity,
)

from database.groups import get_group


router = Router()


# =========================================================
# ПРОВЕРКА АДМИНИСТРАТОРА ГРУППЫ
# =========================================================

async def is_group_admin(
    callback: CallbackQuery,
) -> bool:

    try:
        member = await callback.bot.get_chat_member(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
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
# ПРОВЕРКА ПРАВ БОТА
# =========================================================

async def bot_is_group_admin(
    callback: CallbackQuery,
) -> bool:

    try:
        bot_member = await callback.bot.get_chat_member(
            chat_id=callback.message.chat.id,
            user_id=callback.bot.id,
        )

        return (
            bot_member.status
            == "administrator"
        )

    except Exception as error:

        print(
            "Ошибка проверки прав бота:",
            repr(error),
        )

        return False


# =========================================================
# ОБЩАЯ ПРОВЕРКА GUARD CALLBACK
# =========================================================

async def check_guard_access(
    callback: CallbackQuery,
) -> bool:

    if callback.message is None:
        return False

    if callback.message.chat.type not in {
        "group",
        "supergroup",
    }:

        await callback.answer(
            "Команда доступна только в группе.",
            show_alert=True,
        )

        return False

    group = await get_group(
        callback.message.chat.id
    )

    if group is None:

        await callback.answer(
            "Группа не подключена к TOAD Guard.",
            show_alert=True,
        )

        return False

    if not group.is_active:

        await callback.answer(
            "TOAD Guard отключён для этой группы.",
            show_alert=True,
        )

        return False

    if not await is_group_admin(
        callback
    ):

        await callback.answer(
            "❌ Только администратор группы "
            "может использовать эту кнопку.",
            show_alert=True,
        )

        return False

    return True


# =========================================================
# ПОИСК ПОДТВЕРЖДЁННЫХ ЖАЛОБ
# =========================================================

async def find_member_reports(
    telegram_id: int,
    username: str | None,
):

    async with Session() as session:

        result = await session.execute(
            select(
                ScamReport
            )
            .where(
                ScamReport.status
                == "approved"
            )
            .order_by(
                ScamReport.created_at.desc()
            )
        )

        reports = (
            result.scalars().all()
        )

        found = {}

        for report in reports:

            # Telegram ID
            if (
                report.telegram_id is not None
                and report.telegram_id
                == telegram_id
            ):

                found[report.id] = report
                continue

            # Username
            if (
                username
                and report.username
                and report.username.lower()
                == username.lower()
            ):

                found[report.id] = report

        return list(
            found.values()
        )


# =========================================================
# ПОЛУЧИТЬ ДОСЬЕ
# =========================================================

async def get_entity_from_reports(
    reports,
):

    for report in reports:

        if report.entity_id is None:
            continue

        async with Session() as session:

            entity = await session.get(
                ScamEntity,
                report.entity_id,
            )

            if entity is not None:
                return entity

    return None


# =========================================================
# КЛАВИАТУРА ALERT
# =========================================================

def member_alert_keyboard(
    user_id: int,
    entity_id: int | None,
):

    rows = []

    if entity_id is not None:

        rows.append(
            [
                InlineKeyboardButton(
                    text="📂 Досье",
                    callback_data=(
                        f"guard_entity_{entity_id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔇 Mute 1ч",
                callback_data=(
                    f"guard_mute_{user_id}"
                ),
            ),
            InlineKeyboardButton(
                text="🚫 Ban",
                callback_data=(
                    f"guard_ban_{user_id}"
                ),
            ),
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="✅ Игнорировать",
                callback_data=(
                    f"guard_ignore_{user_id}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================================
# НОВЫЙ УЧАСТНИК
# =========================================================

@router.message(
    F.new_chat_members
)
async def check_new_members(
    message: Message,
):

    if message.chat.type not in {
        "group",
        "supergroup",
    }:
        return

    group = await get_group(
        message.chat.id
    )

    if group is None:
        return

    if not group.is_active:
        return

    for member in message.new_chat_members:

        # Не проверяем самого бота
        if member.id == message.bot.id:
            continue

        # Пока других ботов тоже пропускаем
        if member.is_bot:
            continue

        username = (
            member.username
            if member.username
            else None
        )

        reports = await find_member_reports(
            telegram_id=member.id,
            username=username,
        )

        # Пользователя нет в scam-базе
        if not reports:
            continue

        entity = await get_entity_from_reports(
            reports
        )

        entity_id = (
            entity.id
            if entity
            else None
        )

        risk_score = (
            entity.risk_score
            if entity
            else min(
                len(reports) * 25,
                100,
            )
        )

        if username:

            account_text = (
                f"@{username}"
            )

        else:

            account_text = (
                member.full_name
            )

        text = (
            "🚨 TOAD ALERT\n\n"

            "В группу вошёл пользователь, "
            "который найден в базе "
            "TOAD Scanner.\n\n"

            f"👤 Пользователь: "
            f"{account_text}\n"

            f"🆔 Telegram ID: "
            f"{member.id}\n\n"

            f"🚨 Подтверждённых жалоб: "
            f"{len(reports)}\n"

            f"📊 Risk Score: "
            f"{risk_score}/100"
        )

        if entity_id is not None:

            text += (
                f"\n🐸 Досье: "
                f"#{entity_id}"
            )

        text += (
            "\n\n"
            "⚠️ Запись означает наличие "
            "подтверждённых модерацией жалоб.\n"
            "Решение о санкциях принимает "
            "администратор группы."
        )

        await message.answer(
            text,
            reply_markup=member_alert_keyboard(
                user_id=member.id,
                entity_id=entity_id,
            ),
        )


# =========================================================
# ОТКРЫТЬ ДОСЬЕ
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^guard_entity_\d+$"
    )
)
async def guard_entity(
    callback: CallbackQuery,
):

    if not await check_guard_access(
        callback
    ):
        return

    try:

        entity_id = int(
            callback.data.split("_")[-1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await callback.answer(
            "Ошибка ID досье.",
            show_alert=True,
        )

        return

    async with Session() as session:

        entity = await session.get(
            ScamEntity,
            entity_id,
        )

        if entity is None:

            await callback.answer(
                "Досье не найдено.",
                show_alert=True,
            )

            return

        result = await session.execute(
            select(
                ScamReport
            )
            .where(
                ScamReport.entity_id
                == entity.id,

                ScamReport.status
                == "approved",
            )
            .order_by(
                ScamReport.created_at.desc()
            )
        )

        reports = (
            result.scalars().all()
        )

    username = (
        f"@{entity.primary_username}"
        if entity.primary_username
        else "Не указан"
    )

    text = (
        f"🐸 TOAD DOSSIER #{entity.id}\n\n"

        f"👤 Username: {username}\n"

        f"📛 Имя: "
        f"{entity.display_name or 'Не указано'}\n\n"

        f"📊 Risk Score: "
        f"{entity.risk_score}/100\n"

        f"🚨 Подтверждённых жалоб: "
        f"{len(reports)}\n\n"
    )

    if reports:

        text += "Последние жалобы:\n\n"

        for report in reports[:5]:

            description = (
                report.description
                or "Без описания"
            )

            if len(description) > 180:
                description = (
                    description[:180]
                    + "..."
                )

            text += (
                f"• #{report.id}"
                f" | {report.amount or '—'}\n"
                f"{description}\n\n"
            )

    text += (
        "ℹ️ Досье основано на "
        "подтверждённых модерацией жалобах."
    )

    await callback.answer()

    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=text,
    )


# =========================================================
# MUTE
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^guard_mute_\d+$"
    )
)
async def guard_mute(
    callback: CallbackQuery,
):

    if not await check_guard_access(
        callback
    ):
        return

    if not await bot_is_group_admin(
        callback
    ):

        await callback.answer(
            "TOAD Scanner не является "
            "администратором группы.",
            show_alert=True,
        )

        return

    try:

        user_id = int(
            callback.data.split("_")[-1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await callback.answer(
            "Ошибка ID пользователя.",
            show_alert=True,
        )

        return

    # Не позволяем мутить админов
    try:

        target_member = await callback.bot.get_chat_member(
            callback.message.chat.id,
            user_id,
        )

        if target_member.status in {
            "creator",
            "administrator",
        }:

            await callback.answer(
                "❌ Нельзя ограничить администратора.",
                show_alert=True,
            )

            return

    except Exception:

        pass

    until_date = (
        callback.message.date
        + timedelta(hours=1)
    )

    try:

        await callback.bot.restrict_chat_member(
            chat_id=callback.message.chat.id,

            user_id=user_id,

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

    except Exception as error:

        print(
            "Ошибка Guard mute:",
            repr(error),
        )

        await callback.answer(
            "❌ Не удалось выдать mute. "
            "Проверьте права TOAD Scanner.",
            show_alert=True,
        )

        return

    await callback.answer(
        "🔇 Пользователь ограничен на 1 час.",
        show_alert=True,
    )

    try:

        await callback.message.edit_text(
            callback.message.text
            + (
                "\n\n"
                f"🔇 Пользователь получил mute "
                f"на 1 час.\n"
                f"👮 Действие: "
                f"{callback.from_user.full_name}"
            )
        )

    except Exception:
        pass


# =========================================================
# BAN
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^guard_ban_\d+$"
    )
)
async def guard_ban(
    callback: CallbackQuery,
):

    if not await check_guard_access(
        callback
    ):
        return

    if not await bot_is_group_admin(
        callback
    ):

        await callback.answer(
            "TOAD Scanner не является "
            "администратором группы.",
            show_alert=True,
        )

        return

    try:

        user_id = int(
            callback.data.split("_")[-1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await callback.answer(
            "Ошибка ID пользователя.",
            show_alert=True,
        )

        return

    try:

        target_member = await callback.bot.get_chat_member(
            callback.message.chat.id,
            user_id,
        )

        if target_member.status in {
            "creator",
            "administrator",
        }:

            await callback.answer(
                "❌ Нельзя заблокировать администратора.",
                show_alert=True,
            )

            return

    except Exception:
        pass

    try:

        await callback.bot.ban_chat_member(
            chat_id=callback.message.chat.id,
            user_id=user_id,
            revoke_messages=True,
        )

    except Exception as error:

        print(
            "Ошибка Guard ban:",
            repr(error),
        )

        await callback.answer(
            "❌ Не удалось заблокировать пользователя. "
            "Проверьте права TOAD Scanner.",
            show_alert=True,
        )

        return

    await callback.answer(
        "🚫 Пользователь заблокирован.",
        show_alert=True,
    )

    try:

        await callback.message.edit_text(
            callback.message.text
            + (
                "\n\n"
                "🚫 Пользователь заблокирован.\n"
                f"👮 Действие: "
                f"{callback.from_user.full_name}"
            )
        )

    except Exception:
        pass


# =========================================================
# IGNORE
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^guard_ignore_\d+$"
    )
)
async def guard_ignore(
    callback: CallbackQuery,
):

    if not await check_guard_access(
        callback
    ):
        return

    await callback.answer(
        "Предупреждение закрыто."
    )

    try:

        await callback.message.edit_text(
            callback.message.text
            + (
                "\n\n"
                "✅ Администратор решил "
                "не применять санкции.\n"
                f"👮 {callback.from_user.full_name}"
            )
        )

    except Exception:

        pass 