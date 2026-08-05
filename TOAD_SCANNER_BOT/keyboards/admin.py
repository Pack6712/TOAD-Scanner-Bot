from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def report_moderation_keyboard(report_id: int):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_{report_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{report_id}"
                ),
            ]
        ]
    ) 