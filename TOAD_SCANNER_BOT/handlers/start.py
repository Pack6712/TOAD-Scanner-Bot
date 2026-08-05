from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
)

from config import ADMIN_ID

from keyboards.main import (
    main_menu,
    guard_menu,
    guard_commands_menu,
    back_to_guard_menu,
    sources_menu,
)

from database.functions import (
    get_pending_reports,
)

from database.sources import (
    get_pending_candidates,
)


router = Router()


# =========================================================
# /START
# =========================================================

@router.message(CommandStart())
async def start_command(
    message: Message,
):

    user = message.from_user

    if user is None:
        return

    first_name = (
        user.first_name
        or "пользователь"
    )

    text = (
        "🐸 TOAD SCANNER\n\n"
        f"Привет, {first_name}.\n\n"
        "TOAD — антискам-система Telegram.\n\n"

        "Что умеет бот:\n"
        "🔎 проверять пользователей по базе\n"
        "🚨 принимать жалобы\n"
        "🗃 хранить подтверждённые записи\n"
        "🛡 защищать Telegram-группы\n"
        "📡 собирать scam-сигналы из подключённых чатов\n\n"

        "Выберите действие в меню ниже."
    )

    await message.answer(
        text,
        reply_markup=main_menu(
            user.id
        ),
    )


# =========================================================
# TOAD GUARD
# =========================================================

@router.message(
    F.text == "🛡 TOAD Guard"
)
async def open_guard(
    message: Message,
):

    bot_info = await message.bot.get_me()

    await message.answer(
        "🛡 TOAD GUARD\n\n"

        "Система защиты Telegram-групп.\n\n"

        "Возможности:\n"
        "• проверка новых участников по scam-базе\n"
        "• предупреждения TOAD ALERT\n"
        "• WARN\n"
        "• MUTE\n"
        "• UNMUTE\n"
        "• KICK\n"
        "• BAN\n"
        "• подключение группы как TOAD Source\n\n"

        "Чтобы использовать Guard, "
        "добавьте TOAD Scanner в группу "
        "и выдайте ему права администратора.",

        reply_markup=guard_menu(
            bot_info.username
        ),
    )


# =========================================================
# GUARD COMMANDS
# =========================================================

@router.callback_query(
    F.data == "guard_commands"
)
async def guard_commands(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "📖 TOAD GUARD — КОМАНДЫ\n\n"

        "Команды используются ответом "
        "на сообщение пользователя.\n\n"

        "⚠️ /warn\n"
        "Выдать предупреждение.\n\n"

        "🔇 /mute 30\n"
        "Ограничить пользователя на 30 минут.\n\n"

        "🔊 /unmute\n"
        "Снять ограничения.\n\n"

        "👢 /kick\n"
        "Удалить пользователя из группы "
        "без постоянного бана.\n\n"

        "🚫 /ban\n"
        "Заблокировать пользователя.\n\n"

        "🐸 /guard\n"
        "Посмотреть состояние TOAD Guard.",

        reply_markup=guard_commands_menu(),
    )

    await callback.answer()


# =========================================================
# HELP WARN
# =========================================================

@router.callback_query(
    F.data == "guard_help_warn"
)
async def guard_help_warn(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "⚠️ WARN\n\n"

        "Ответьте на сообщение пользователя "
        "командой:\n\n"

        "/warn\n\n"

        "Команда доступна только "
        "администраторам группы.",

        reply_markup=back_to_guard_menu(),
    )

    await callback.answer()


# =========================================================
# HELP MUTE
# =========================================================

@router.callback_query(
    F.data == "guard_help_mute"
)
async def guard_help_mute(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "🔇 MUTE\n\n"

        "Ответьте на сообщение пользователя:\n\n"

        "/mute 30\n\n"

        "30 — количество минут.\n\n"

        "Например:\n"
        "/mute 10\n"
        "/mute 60\n"
        "/mute 1440",

        reply_markup=back_to_guard_menu(),
    )

    await callback.answer()


# =========================================================
# HELP BAN
# =========================================================

@router.callback_query(
    F.data == "guard_help_ban"
)
async def guard_help_ban(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "🚫 BAN\n\n"

        "Ответьте на сообщение пользователя:\n\n"

        "/ban\n\n"

        "TOAD Scanner заблокирует пользователя "
        "в текущей группе.\n\n"

        "Бот должен иметь право "
        "блокировать участников.",

        reply_markup=back_to_guard_menu(),
    )

    await callback.answer()


# =========================================================
# HELP KICK
# =========================================================

@router.callback_query(
    F.data == "guard_help_kick"
)
async def guard_help_kick(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "👢 KICK\n\n"

        "Ответьте на сообщение пользователя:\n\n"

        "/kick\n\n"

        "Пользователь будет удалён из группы, "
        "но сможет вступить снова.",

        reply_markup=back_to_guard_menu(),
    )

    await callback.answer()


# =========================================================
# GUARD SOURCES
# =========================================================

@router.callback_query(
    F.data == "guard_sources"
)
async def guard_sources(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "📡 TOAD SOURCES\n\n"

        "Группу можно подключить "
        "как источник scam-сигналов.\n\n"

        "После подключения TOAD анализирует "
        "новые сообщения и ищет потенциальные "
        "сообщения о мошенничестве.\n\n"

        "Найденный сигнал сначала получает "
        "статус pending и проходит модерацию.\n\n"

        "Пользователь НЕ добавляется "
        "в публичную базу автоматически.",

        reply_markup=sources_menu(),
    )

    await callback.answer()


# =========================================================
# SOURCE ON HELP
# =========================================================

@router.callback_query(
    F.data == "source_help_on"
)
async def source_help_on(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "✅ ВКЛЮЧИТЬ TOAD SOURCE\n\n"

        "Добавьте TOAD Scanner в нужную группу "
        "и отправьте там:\n\n"

        "/source_on\n\n"

        "Включить источник может "
        "администратор группы.",

        reply_markup=back_to_guard_menu(),
    )

    await callback.answer()


# =========================================================
# SOURCE OFF HELP
# =========================================================

@router.callback_query(
    F.data == "source_help_off"
)
async def source_help_off(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "❌ ВЫКЛЮЧИТЬ TOAD SOURCE\n\n"

        "В нужной группе отправьте:\n\n"

        "/source_off\n\n"

        "После отключения новые сообщения "
        "не будут анализироваться.",

        reply_markup=back_to_guard_menu(),
    )

    await callback.answer()


# =========================================================
# SOURCE STATUS HELP
# =========================================================

@router.callback_query(
    F.data == "source_help_status"
)
async def source_help_status(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "📊 STATUS TOAD SOURCE\n\n"

        "Чтобы проверить состояние источника, "
        "отправьте в группе:\n\n"

        "/source_status",

        reply_markup=back_to_guard_menu(),
    )

    await callback.answer()


# =========================================================
# BACK TO GUARD
# =========================================================

@router.callback_query(
    F.data == "guard_menu_back"
)
async def guard_menu_back(
    callback: CallbackQuery,
):

    bot_info = await callback.bot.get_me()

    await callback.message.edit_text(
        "🛡 TOAD GUARD\n\n"

        "Система защиты Telegram-групп.\n\n"

        "• проверка участников\n"
        "• TOAD ALERT\n"
        "• WARN / MUTE / BAN / KICK\n"
        "• TOAD Sources\n\n"

        "Выберите раздел:",

        reply_markup=guard_menu(
            bot_info.username
        ),
    )

    await callback.answer()


# =========================================================
# MAIN BACK
# =========================================================

@router.callback_query(
    F.data == "main_back"
)
async def main_back(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "🐸 TOAD SCANNER\n\n"
        "Используйте главное меню "
        "внизу экрана."
    )

    await callback.answer()


# =========================================================
# HELP BUTTON
# =========================================================

@router.message(
    F.text == "ℹ️ Помощь"
)
async def help_button(
    message: Message,
):

    await message.answer(
        "🐸 TOAD Scanner — помощь\n\n"

        "🔎 Проверить человека\n"
        "Поиск аккаунта в scam-базе.\n\n"

        "🚨 Подать жалобу\n"
        "Отправка информации на модерацию.\n\n"

        "🗃 База\n"
        "Подтверждённые записи TOAD.\n\n"

        "🛡 TOAD Guard\n"
        "Защита Telegram-групп.\n\n"

        "📡 TOAD Sources\n"
        "Сбор потенциальных scam-сигналов.\n\n"

        "/cancel — отменить текущее действие."
    )


# =========================================================
# ADMIN PANEL BUTTON
# =========================================================

@router.message(
    F.text == "🛠 Панель администратора"
)
async def admin_panel_button(
    message: Message,
):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ Нет доступа."
        )

        return

    reports = await get_pending_reports()

    candidates = (
        await get_pending_candidates()
    )

    await message.answer(
        "🛠 TOAD ADMIN\n\n"

        f"⏳ Жалобы на модерации: "
        f"{len(reports)}\n"

        f"🚨 Source Signals: "
        f"{len(candidates)}\n\n"

        "Команды:\n"
        "/admin — жалобы\n"
        "/candidates — Source Signals"
    )


# =========================================================
# SOURCE SIGNALS BUTTON
# =========================================================

@router.message(
    F.text == "🚨 Source Signals"
)
async def source_signals_button(
    message: Message,
):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ Нет доступа."
        )

        return

    candidates = (
        await get_pending_candidates()
    )

    if not candidates:

        await message.answer(
            "✅ Новых TOAD Source "
            "сигналов нет."
        )

        return

    await message.answer(
        "🚨 TOAD SOURCE SIGNALS\n\n"

        f"Ожидают проверки: "
        f"{len(candidates)}\n\n"

        "Откройте очередь командой:\n"
        "/candidates"
    )