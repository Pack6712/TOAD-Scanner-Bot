from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    ChatMemberUpdated,
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database.groups import (
    get_group,
    save_or_update_group,
    disable_group,
    toggle_guard,
    toggle_auto_check_members,
    toggle_warn_mode,
    toggle_mute_mode,
    toggle_ban_mode,
)


router = Router()


# =========================================================
# HELPERS
# =========================================================

def on_off(value: bool) -> str:
    return "✅ ON" if value else "❌ OFF"


async def is_group_admin(
    bot,
    chat_id: int,
    user_id: int,
) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=chat_id,
            user_id=user_id,
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


async def bot_is_admin(
    bot,
    chat_id: int,
) -> bool:
    try:
        me = await bot.get_me()

        member = await bot.get_chat_member(
            chat_id=chat_id,
            user_id=me.id,
        )

        return member.status == "administrator"

    except Exception as error:
        print(
            "Ошибка проверки прав TOAD:",
            repr(error),
        )
        return False


# =========================================================
# GUARD KEYBOARD
# =========================================================

def guard_settings_keyboard(
    group,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        "🛡 Guard "
                        + (
                            "✅"
                            if group.guard_enabled
                            else "❌"
                        )
                    ),
                    callback_data="group_toggle_guard",
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "🔎 Проверка участников "
                        + (
                            "✅"
                            if group.auto_check_members
                            else "❌"
                        )
                    ),
                    callback_data="group_toggle_auto_check",
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "⚠️ Warn "
                        + (
                            "✅"
                            if group.warn_mode
                            else "❌"
                        )
                    ),
                    callback_data="group_toggle_warn",
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "🔇 Mute mode "
                        + (
                            "✅"
                            if group.mute_mode
                            else "❌"
                        )
                    ),
                    callback_data="group_toggle_mute",
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "🚫 Ban mode "
                        + (
                            "✅"
                            if group.ban_mode
                            else "❌"
                        )
                    ),
                    callback_data="group_toggle_ban",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="group_guard_refresh",
                )
            ],
        ]
    )


# =========================================================
# GUARD TEXT
# =========================================================

async def build_guard_text(
    bot,
    group,
) -> str:

    bot_admin = await bot_is_admin(
        bot=bot,
        chat_id=group.telegram_chat_id,
    )

    return (
        "🛡 TOAD GUARD 2.0\n\n"

        f"🏠 Группа: "
        f"{group.title or 'Без названия'}\n"

        f"🆔 Chat ID: "
        f"{group.telegram_chat_id}\n\n"

        f"🐸 Guard: "
        f"{on_off(group.guard_enabled)}\n"

        f"🔎 Проверка новых участников: "
        f"{on_off(group.auto_check_members)}\n"

        f"⚠️ Warn mode: "
        f"{on_off(group.warn_mode)}\n"

        f"🔇 Mute mode: "
        f"{on_off(group.mute_mode)}\n"

        f"🚫 Ban mode: "
        f"{on_off(group.ban_mode)}\n\n"

        f"🤖 TOAD администратор: "
        f"{'✅ Да' if bot_admin else '❌ Нет'}\n\n"

        "Нажимайте кнопки ниже, "
        "чтобы менять настройки защиты."
    )


# =========================================================
# БОТА ДОБАВИЛИ / УДАЛИЛИ
# =========================================================

@router.my_chat_member()
async def bot_chat_member_update(
    event: ChatMemberUpdated,
):

    chat = event.chat

    if chat.type not in {
        "group",
        "supergroup",
    }:
        return

    new_status = event.new_chat_member.status

    if new_status in {
        "member",
        "administrator",
    }:

        owner_id = None

        try:
            admins = await event.bot.get_chat_administrators(
                chat.id
            )

            for admin in admins:
                if admin.status == "creator":
                    owner_id = admin.user.id
                    break

        except Exception as error:
            print(
                "Ошибка получения владельца:",
                repr(error),
            )

        await save_or_update_group(
            telegram_chat_id=chat.id,
            title=chat.title,
            username=chat.username,
            owner_id=owner_id,
        )

        bot_admin = await bot_is_admin(
            bot=event.bot,
            chat_id=chat.id,
        )

        if bot_admin:

            text = (
                "🐸 TOAD Scanner подключён\n\n"
                f"🏠 Группа: {chat.title}\n\n"
                "✅ Бот добавлен\n"
                "✅ Права администратора получены\n\n"
                "Панель управления:\n"
                "/guard"
            )

        else:

            text = (
                "🐸 TOAD Scanner добавлен\n\n"
                f"🏠 Группа: {chat.title}\n\n"
                "⚠️ Для полной работы "
                "TOAD должен быть администратором.\n\n"
                "После выдачи прав используйте:\n"
                "/guard"
            )

        try:
            await event.bot.send_message(
                chat_id=chat.id,
                text=text,
            )

        except Exception as error:
            print(
                "Ошибка сообщения TOAD:",
                repr(error),
            )

    elif new_status in {
        "left",
        "kicked",
    }:

        await disable_group(
            telegram_chat_id=chat.id,
        )


# =========================================================
# /guard
# =========================================================

@router.message(
    Command("guard")
)
async def guard_panel(
    message: Message,
):

    if message.chat.type not in {
        "group",
        "supergroup",
    }:

        await message.answer(
            "❌ TOAD Guard работает "
            "только в Telegram-группах."
        )
        return

    if message.from_user is None:
        return

    admin = await is_group_admin(
        bot=message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
    )

    if not admin:

        await message.answer(
            "❌ Панель TOAD Guard доступна "
            "только администраторам группы."
        )
        return

    group = await get_group(
        message.chat.id
    )

    if group is None:

        owner_id = None

        try:
            admins = await message.bot.get_chat_administrators(
                message.chat.id
            )

            for member in admins:
                if member.status == "creator":
                    owner_id = member.user.id
                    break

        except Exception as error:
            print(
                "Ошибка получения владельца:",
                repr(error),
            )

        group = await save_or_update_group(
            telegram_chat_id=message.chat.id,
            title=message.chat.title,
            username=message.chat.username,
            owner_id=owner_id,
        )

    text = await build_guard_text(
        bot=message.bot,
        group=group,
    )

    await message.answer(
        text,
        reply_markup=guard_settings_keyboard(
            group
        ),
    )


# =========================================================
# CALLBACK ACCESS
# =========================================================

async def get_callback_group(
    callback: CallbackQuery,
):

    if callback.message is None:
        await callback.answer(
            "Ошибка сообщения.",
            show_alert=True,
        )
        return None

    if callback.message.chat.type not in {
        "group",
        "supergroup",
    }:

        await callback.answer(
            "Настройки доступны "
            "только в группе.",
            show_alert=True,
        )
        return None

    admin = await is_group_admin(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
    )

    if not admin:

        await callback.answer(
            "❌ Только администратор группы "
            "может менять настройки.",
            show_alert=True,
        )
        return None

    group = await get_group(
        callback.message.chat.id
    )

    if group is None:

        await callback.answer(
            "❌ Группа не зарегистрирована.",
            show_alert=True,
        )
        return None

    return group


# =========================================================
# UPDATE PANEL
# =========================================================

async def update_guard_panel(
    callback: CallbackQuery,
):

    if callback.message is None:
        return

    group = await get_group(
        callback.message.chat.id
    )

    if group is None:
        return

    text = await build_guard_text(
        bot=callback.bot,
        group=group,
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=guard_settings_keyboard(
                group
            ),
        )

    except Exception as error:
        print(
            "Guard panel update:",
            repr(error),
        )


# =========================================================
# TOGGLE GUARD
# =========================================================

@router.callback_query(
    F.data == "group_toggle_guard"
)
async def group_toggle_guard(
    callback: CallbackQuery,
):

    group = await get_callback_group(
        callback
    )

    if group is None:
        return

    updated = await toggle_guard(
        group.telegram_chat_id
    )

    if updated is None:
        return

    await callback.answer(
        (
            "🛡 Guard включён"
            if updated.guard_enabled
            else "🛡 Guard выключен"
        )
    )

    await update_guard_panel(
        callback
    )


# =========================================================
# TOGGLE AUTO CHECK
# =========================================================

@router.callback_query(
    F.data == "group_toggle_auto_check"
)
async def group_toggle_auto_check(
    callback: CallbackQuery,
):

    group = await get_callback_group(
        callback
    )

    if group is None:
        return

    updated = await toggle_auto_check_members(
        group.telegram_chat_id
    )

    if updated is None:
        return

    await callback.answer(
        (
            "🔎 Проверка участников включена"
            if updated.auto_check_members
            else "🔎 Проверка участников выключена"
        )
    )

    await update_guard_panel(
        callback
    )


# =========================================================
# TOGGLE WARN
# =========================================================

@router.callback_query(
    F.data == "group_toggle_warn"
)
async def group_toggle_warn(
    callback: CallbackQuery,
):

    group = await get_callback_group(
        callback
    )

    if group is None:
        return

    updated = await toggle_warn_mode(
        group.telegram_chat_id
    )

    if updated is None:
        return

    await callback.answer(
        (
            "⚠️ Warn mode включён"
            if updated.warn_mode
            else "⚠️ Warn mode выключен"
        )
    )

    await update_guard_panel(
        callback
    )


# =========================================================
# TOGGLE MUTE
# =========================================================

@router.callback_query(
    F.data == "group_toggle_mute"
)
async def group_toggle_mute(
    callback: CallbackQuery,
):

    group = await get_callback_group(
        callback
    )

    if group is None:
        return

    updated = await toggle_mute_mode(
        group.telegram_chat_id
    )

    if updated is None:
        return

    await callback.answer(
        (
            "🔇 Mute mode включён"
            if updated.mute_mode
            else "🔇 Mute mode выключен"
        )
    )

    await update_guard_panel(
        callback
    )


# =========================================================
# TOGGLE BAN
# =========================================================

@router.callback_query(
    F.data == "group_toggle_ban"
)
async def group_toggle_ban(
    callback: CallbackQuery,
):

    group = await get_callback_group(
        callback
    )

    if group is None:
        return

    updated = await toggle_ban_mode(
        group.telegram_chat_id
    )

    if updated is None:
        return

    await callback.answer(
        (
            "🚫 Ban mode включён"
            if updated.ban_mode
            else "🚫 Ban mode выключен"
        )
    )

    await update_guard_panel(
        callback
    )


# =========================================================
# REFRESH
# =========================================================

@router.callback_query(
    F.data == "group_guard_refresh"
)
async def group_guard_refresh(
    callback: CallbackQuery,
):

    group = await get_callback_group(
        callback
    )

    if group is None:
        return

    await update_guard_panel(
        callback
    )

    await callback.answer(
        "🔄 Панель обновлена"
    )