from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import ADMIN_ID


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

def main_menu(
    user_id: int,
) -> ReplyKeyboardMarkup:

    rows = [
        [
            KeyboardButton(
                text="🔎 Проверить человека"
            ),
            KeyboardButton(
                text="🚨 Подать жалобу"
            ),
        ],
        [
            KeyboardButton(
                text="🗃 База"
            ),
            KeyboardButton(
                text="👤 Мой профиль"
            ),
        ],
        [
            KeyboardButton(
                text="🛡 TOAD Guard"
            ),
            KeyboardButton(
                text="ℹ️ Помощь"
            ),
        ],
    ]

    # Админ получает дополнительные кнопки
    if user_id == ADMIN_ID:
        rows.append(
            [
                KeyboardButton(
                    text="🛠 Панель администратора"
                )
            ]
        )

        rows.append(
            [
                KeyboardButton(
                    text="🚨 Source Signals"
                )
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=(
            "Выберите действие..."
        ),
    )


# =========================================================
# TOAD GUARD MENU
# =========================================================

def guard_menu(
    bot_username: str,
) -> InlineKeyboardMarkup:

    add_to_group_url = (
        f"https://t.me/{bot_username}"
        "?startgroup=true"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить TOAD в группу",
                    url=add_to_group_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="📖 Команды Guard",
                    callback_data="guard_commands",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📡 TOAD Sources",
                    callback_data="guard_sources",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="main_back",
                )
            ],
        ]
    )


# =========================================================
# GUARD COMMANDS MENU
# =========================================================

def guard_commands_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔇 Mute",
                    callback_data="guard_help_mute",
                ),
                InlineKeyboardButton(
                    text="🚫 Ban",
                    callback_data="guard_help_ban",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Warn",
                    callback_data="guard_help_warn",
                ),
                InlineKeyboardButton(
                    text="👢 Kick",
                    callback_data="guard_help_kick",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="guard_menu_back",
                )
            ],
        ]
    )


# =========================================================
# BACK BUTTON
# =========================================================

def back_to_guard_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="guard_menu_back",
                )
            ]
        ]
    )


# =========================================================
# SOURCES MENU
# =========================================================

def sources_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Включить источник",
                    callback_data="source_help_on",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Выключить источник",
                    callback_data="source_help_off",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Проверить статус",
                    callback_data="source_help_status",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="guard_menu_back",
                )
            ],
        ]
    )