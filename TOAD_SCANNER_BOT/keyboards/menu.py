from aiogram.types import ReplyKeyboardMarkup, KeyboardButton # type: ignore

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔍 Проверить пользователя")
        ],
        [
            KeyboardButton(text="➕ Подать жалобу")
        ],
        [
            KeyboardButton(text="📂 База мошенников"),
            KeyboardButton(text="👤 Профиль")
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="ℹ️ О проекте")
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
) 