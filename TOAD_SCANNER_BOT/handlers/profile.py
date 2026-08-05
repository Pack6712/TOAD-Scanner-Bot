from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database.functions import (
    get_user_report_stats,
    get_user_reports,
    get_report,
    get_proofs,
)


router = Router()


# =========================================================
# KEYBOARDS
# =========================================================

def profile_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📂 Мои жалобы",
                    callback_data="profile_reports",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить профиль",
                    callback_data="profile_refresh",
                )
            ],
        ]
    )


def back_to_profile_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в профиль",
                    callback_data="profile_back",
                )
            ]
        ]
    )


# =========================================================
# STATUS
# =========================================================

def status_text(
    status: str,
) -> str:

    if status == "approved":
        return "✅ Одобрена"

    if status == "pending":
        return "⏳ На модерации"

    if status == "rejected":
        return "❌ Отклонена"

    return status


# =========================================================
# SEND PROFILE
# =========================================================

async def send_profile(
    message: Message,
    user_id: int,
    username: str | None,
):

    stats = await get_user_report_stats(
        user_id
    )

    username_text = (
        f"@{username}"
        if username
        else "Не установлен"
    )

    await message.answer(
        "👤 МОЙ ПРОФИЛЬ\n\n"

        f"🆔 Telegram ID: "
        f"{user_id}\n"

        f"👤 Username: "
        f"{username_text}\n\n"

        "📨 МОИ ЖАЛОБЫ\n\n"

        f"📊 Всего подано: "
        f"{stats['total']}\n"

        f"✅ Одобрено: "
        f"{stats['approved']}\n"

        f"⏳ На модерации: "
        f"{stats['pending']}\n"

        f"❌ Отклонено: "
        f"{stats['rejected']}",

        reply_markup=profile_keyboard(),
    )


# =========================================================
# PROFILE BUTTON
# =========================================================

@router.message(
    F.text == "👤 Мой профиль"
)
async def profile_handler(
    message: Message,
):

    await send_profile(
        message=message,
        user_id=message.from_user.id,
        username=message.from_user.username,
    )


# =========================================================
# MY REPORTS
# =========================================================

@router.callback_query(
    F.data == "profile_reports"
)
async def profile_reports(
    callback: CallbackQuery,
):

    reports = await get_user_reports(
        callback.from_user.id
    )

    if not reports:

        await callback.message.edit_text(
            "📂 МОИ ЖАЛОБЫ\n\n"
            "У вас пока нет отправленных жалоб.",

            reply_markup=(
                back_to_profile_keyboard()
            ),
        )

        await callback.answer()
        return

    rows = []

    for report in reports[:20]:

        username = (
            f"@{report.username}"
            if report.username
            else "без username"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"#{report.id} • "
                        f"{status_text(report.status)} • "
                        f"{username}"
                    ),
                    callback_data=(
                        f"profile_report_"
                        f"{report.id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад в профиль",
                callback_data="profile_back",
            )
        ]
    )

    await callback.message.edit_text(
        "📂 МОИ ЖАЛОБЫ\n\n"
        f"Всего: {len(reports)}\n\n"
        "Выберите жалобу:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()


# =========================================================
# OPEN REPORT
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^profile_report_\d+$"
    )
)
async def profile_report_open(
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

    if report is None:

        await callback.answer(
            "Жалоба не найдена",
            show_alert=True,
        )

        return

    # Пользователь может открыть
    # только свою жалобу.
    if (
        report.author_id
        != callback.from_user.id
    ):

        await callback.answer(
            "Нет доступа к этой жалобе",
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
        str(report.telegram_id)
        if report.telegram_id is not None
        else "Не указан"
    )

    created_at = (
        report.created_at.strftime(
            "%d.%m.%Y %H:%M"
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

    reject_reason_text = ""

    if report.status == "rejected":

        reject_reason = (
            report.reject_reason
            if report.reject_reason
            else "Причина не указана."
        )

        reject_reason_text = (
            "\n\n"
            "📋 Причина отклонения:\n"
            f"{reject_reason}"
        )

    await callback.message.edit_text(
        "📄 МОЯ ЖАЛОБА\n\n"

        f"🆔 Жалоба #{report.id}\n"

        f"📌 Статус: "
        f"{status_text(report.status)}\n\n"

        f"👤 Username: "
        f"{username}\n"

        f"🆔 Telegram ID: "
        f"{telegram_id}\n"

        f"📛 Имя: "
        f"{report.full_name or 'Не указано'}\n"

        f"💰 Сумма: "
        f"{report.amount or 'Не указана'}\n\n"

        "📝 Описание:\n"
        f"{description}"

        f"{reject_reason_text}\n\n"

        f"📎 Доказательств: "
        f"{len(proofs)}\n"

        f"📅 Отправлено: "
        f"{created_at}",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=(
                            "📎 Показать "
                            f"доказательства "
                            f"({len(proofs)})"
                        ),
                        callback_data=(
                            f"profile_proofs_"
                            f"{report.id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ К моим жалобам",
                        callback_data="profile_reports",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


# =========================================================
# SHOW PROOFS
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^profile_proofs_\d+$"
    )
)
async def profile_show_proofs(
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

    if report is None:

        await callback.answer(
            "Жалоба не найдена",
            show_alert=True,
        )

        return

    if (
        report.author_id
        != callback.from_user.id
    ):

        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )

        return

    proofs = get_proofs(
        report
    )

    if not proofs:

        await callback.answer(
            "У жалобы нет доказательств",
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
                        f"к жалобе "
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
                        f"к жалобе "
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
                        f"к жалобе "
                        f"#{report.id}"
                    ),
                )

        except Exception as error:

            print(
                "Ошибка доказательства "
                f"жалобы #{report.id}:",
                repr(error),
            )


# =========================================================
# BACK / REFRESH
# =========================================================

@router.callback_query(
    F.data.in_({
        "profile_back",
        "profile_refresh",
    })
)
async def profile_back(
    callback: CallbackQuery,
):

    stats = await get_user_report_stats(
        callback.from_user.id
    )

    username = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else "Не установлен"
    )

    await callback.message.edit_text(
        "👤 МОЙ ПРОФИЛЬ\n\n"

        f"🆔 Telegram ID: "
        f"{callback.from_user.id}\n"

        f"👤 Username: "
        f"{username}\n\n"

        "📨 МОИ ЖАЛОБЫ\n\n"

        f"📊 Всего подано: "
        f"{stats['total']}\n"

        f"✅ Одобрено: "
        f"{stats['approved']}\n"

        f"⏳ На модерации: "
        f"{stats['pending']}\n"

        f"❌ Отклонено: "
        f"{stats['rejected']}",

        reply_markup=profile_keyboard(),
    )

    await callback.answer()