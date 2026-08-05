from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database.functions import (
    get_approved_reports,
    get_report,
    get_proofs,
)


router = Router()


# =========================================================
# KEYBOARDS
# =========================================================

def back_to_base_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в базу",
                    callback_data="base_list",
                )
            ]
        ]
    )


def build_base_keyboard(
    reports,
):

    rows = []

    for report in reports[:50]:

        username = (
            f"@{report.username}"
            if report.username
            else "без username"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"⚠️ #{report.id} • "
                        f"{username}"
                    ),
                    callback_data=(
                        f"base_report_"
                        f"{report.id}"
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================================
# BASE BUTTON
# =========================================================

@router.message(
    F.text == "🗃 База"
)
async def base_handler(
    message: Message,
):

    reports = (
        await get_approved_reports()
    )

    if not reports:

        await message.answer(
            "🗃 БАЗА TOAD SCANNER\n\n"
            "✅ Подтверждённых записей "
            "пока нет."
        )

        return

    await message.answer(
        "🗃 БАЗА TOAD SCANNER\n\n"
        f"🚨 Подтверждённых записей: "
        f"{len(reports)}\n\n"
        "Выберите запись:",

        reply_markup=(
            build_base_keyboard(
                reports
            )
        ),
    )


# =========================================================
# BASE LIST
# =========================================================

@router.callback_query(
    F.data == "base_list"
)
async def base_list(
    callback: CallbackQuery,
):

    reports = (
        await get_approved_reports()
    )

    if not reports:

        await callback.message.edit_text(
            "🗃 БАЗА TOAD SCANNER\n\n"
            "✅ Подтверждённых записей "
            "пока нет."
        )

        await callback.answer()
        return

    await callback.message.edit_text(
        "🗃 БАЗА TOAD SCANNER\n\n"
        f"🚨 Подтверждённых записей: "
        f"{len(reports)}\n\n"
        "Выберите запись:",

        reply_markup=(
            build_base_keyboard(
                reports
            )
        ),
    )

    await callback.answer()


# =========================================================
# OPEN REPORT
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^base_report_\d+$"
    )
)
async def base_open_report(
    callback: CallbackQuery,
):

    try:

        report_id = int(
            callback.data
            .split("_")[-1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await callback.answer(
            "Ошибка ID",
            show_alert=True,
        )

        return

    report = await get_report(
        report_id
    )

    if (
        report is None
        or report.status
        != "approved"
    ):

        await callback.answer(
            "Запись не найдена",
            show_alert=True,
        )

        return

    proofs = get_proofs(
        report
    )

    username = (
        f"@{report.username}"
        if report.username
        else "Не указан"
    )

    telegram_id = (
        str(
            report.telegram_id
        )
        if report.telegram_id
        is not None
        else "Не указан"
    )

    created_at = (
        report.created_at.strftime(
            "%d.%m.%Y"
        )
        if report.created_at
        else "Неизвестно"
    )

    description = (
        report.description
        or "Описание отсутствует"
    )

    if len(description) > 2500:

        description = (
            description[:2500]
            + "..."
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        "📎 Доказательства "
                        f"({len(proofs)})"
                    ),
                    callback_data=(
                        f"base_proofs_"
                        f"{report.id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в базу",
                    callback_data="base_list",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "🐸 TOAD SCANNER\n\n"
        "🚨 ПОДТВЕРЖДЁННАЯ ЗАПИСЬ\n\n"

        f"🆔 Запись #{report.id}\n"
        "✅ Статус: Подтверждена\n\n"

        f"👤 Username: {username}\n"
        f"🆔 Telegram ID: {telegram_id}\n"
        f"📛 Имя: "
        f"{report.full_name or 'Не указано'}\n"

        f"💰 Сумма ущерба: "
        f"{report.amount or 'Не указана'}\n\n"

        "📝 Описание:\n"
        f"{description}\n\n"

        f"📎 Доказательств: "
        f"{len(proofs)}\n"

        f"📅 Добавлено: "
        f"{created_at}\n\n"

        "⚠️ Запись добавлена после "
        "модерации TOAD Scanner.",

        reply_markup=keyboard,
    )

    await callback.answer()


# =========================================================
# SHOW PROOFS
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^base_proofs_\d+$"
    )
)
async def base_show_proofs(
    callback: CallbackQuery,
):

    try:

        report_id = int(
            callback.data
            .split("_")[-1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await callback.answer(
            "Ошибка ID",
            show_alert=True,
        )

        return

    report = await get_report(
        report_id
    )

    if (
        report is None
        or report.status
        != "approved"
    ):

        await callback.answer(
            "Запись не найдена",
            show_alert=True,
        )

        return

    proofs = get_proofs(
        report
    )

    if not proofs:

        await callback.answer(
            "Доказательств нет",
            show_alert=True,
        )

        return

    await callback.answer(
        f"Доказательств: "
        f"{len(proofs)}"
    )

    for proof in proofs:

        try:

            proof_type, file_id = (
                proof.split(
                    ":",
                    1,
                )
            )

            if proof_type == "photo":

                await callback.bot.send_photo(
                    chat_id=(
                        callback.from_user.id
                    ),

                    photo=file_id,

                    caption=(
                        "📸 Доказательство "
                        f"к записи "
                        f"#{report.id}"
                    ),
                )

            elif proof_type == "video":

                await callback.bot.send_video(
                    chat_id=(
                        callback.from_user.id
                    ),

                    video=file_id,

                    caption=(
                        "🎥 Доказательство "
                        f"к записи "
                        f"#{report.id}"
                    ),
                )

            elif proof_type == "document":

                await callback.bot.send_document(
                    chat_id=(
                        callback.from_user.id
                    ),

                    document=file_id,

                    caption=(
                        "📄 Доказательство "
                        f"к записи "
                        f"#{report.id}"
                    ),
                )

        except Exception as error:

            print(
                "Ошибка показа "
                f"доказательства "
                f"#{report.id}:",
                repr(error),
            )