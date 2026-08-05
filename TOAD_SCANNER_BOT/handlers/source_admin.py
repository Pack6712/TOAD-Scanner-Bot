from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import ADMIN_ID

from database.sources import (
    get_pending_candidates,
    get_candidate,
    set_candidate_status,
)

from database.functions import (
    add_report,
)


router = Router()


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(
    user_id: int,
) -> bool:

    return (
        user_id == ADMIN_ID
    )


# =========================================================
# КЛАВИАТУРА СПИСКА
# =========================================================

def candidates_keyboard(
    candidates,
):

    rows = []

    for candidate in candidates[:20]:

        username = (
            f"@{candidate.suspect_username}"
            if candidate.suspect_username
            else "без username"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"#{candidate.id} — "
                        f"{username}"
                    ),
                    callback_data=(
                        f"source_candidate_"
                        f"{candidate.id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=(
                    "source_candidates_refresh"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================================
# КЛАВИАТУРА КАНДИДАТА
# =========================================================

def candidate_actions_keyboard(
    candidate_id: int,
):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Создать жалобу",
                    callback_data=(
                        f"source_create_report_"
                        f"{candidate_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить сигнал",
                    callback_data=(
                        f"source_reject_"
                        f"{candidate_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=(
                        "source_candidates_refresh"
                    ),
                )
            ],
        ]
    )


# =========================================================
# /candidates
# =========================================================

@router.message(
    Command("candidates")
)
async def candidates_command(
    message: Message,
):

    if not is_admin(
        message.from_user.id
    ):

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
        "🚨 TOAD SOURCES\n\n"
        f"Сигналов на проверке: "
        f"{len(candidates)}\n\n"
        "Выберите сигнал:",
        reply_markup=(
            candidates_keyboard(
                candidates
            )
        ),
    )


# =========================================================
# REFRESH
# =========================================================

@router.callback_query(
    F.data
    == "source_candidates_refresh"
)
async def candidates_refresh(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )

        return

    candidates = (
        await get_pending_candidates()
    )

    if not candidates:

        await callback.message.edit_text(
            "✅ Новых TOAD Source "
            "сигналов нет."
        )

        await callback.answer()

        return

    await callback.message.edit_text(
        "🚨 TOAD SOURCES\n\n"
        f"Сигналов на проверке: "
        f"{len(candidates)}\n\n"
        "Выберите сигнал:",
        reply_markup=(
            candidates_keyboard(
                candidates
            )
        ),
    )

    await callback.answer()


# =========================================================
# OPEN CANDIDATE
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^source_candidate_\d+$"
    )
)
async def open_candidate(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )

        return

    try:

        candidate_id = int(
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

    candidate = await get_candidate(
        candidate_id
    )

    if candidate is None:

        await callback.answer(
            "Сигнал не найден",
            show_alert=True,
        )

        return

    username = (
        f"@{candidate.suspect_username}"
        if candidate.suspect_username
        else "Не указан"
    )

    telegram_id = (
        str(
            candidate.suspect_telegram_id
        )
        if candidate.suspect_telegram_id
        is not None
        else "Не указан"
    )

    source_author = (
        f"@{candidate.source_author_username}"
        if candidate.source_author_username
        else (
            str(
                candidate.source_author_id
            )
            if candidate.source_author_id
            is not None
            else "Неизвестен"
        )
    )

    text = (
        "🚨 TOAD SOURCE SIGNAL\n\n"

        f"🆔 Signal #{candidate.id}\n"
        f"📌 Status: "
        f"{candidate.status}\n\n"

        f"👤 Подозреваемый:\n"
        f"{username}\n"

        f"🆔 Telegram ID:\n"
        f"{telegram_id}\n\n"

        f"📡 Source Chat ID:\n"
        f"{candidate.source_chat_id}\n"

        f"💬 Message ID:\n"
        f"{candidate.source_message_id}\n"

        f"👤 Автор сигнала:\n"
        f"{source_author}\n\n"

        "📝 Исходное сообщение:\n"
        f"{candidate.text[:3000]}\n\n"

        "⚠️ Пока это только сигнал.\n"
        "Он не находится "
        "в публичной scam-базе."
    )

    await callback.message.edit_text(
        text,
        reply_markup=(
            candidate_actions_keyboard(
                candidate.id
            )
        ),
    )

    await callback.answer()


# =========================================================
# CREATE REPORT FROM CANDIDATE
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^source_create_report_\d+$"
    )
)
async def create_report_from_candidate(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )

        return

    try:

        candidate_id = int(
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

    candidate = await get_candidate(
        candidate_id
    )

    if candidate is None:

        await callback.answer(
            "Сигнал не найден",
            show_alert=True,
        )

        return

    if candidate.status != "pending":

        await callback.answer(
            "Сигнал уже обработан.",
            show_alert=True,
        )

        return

    if not candidate.suspect_username:

        await callback.answer(
            "❌ Нельзя создать жалобу: "
            "не найден username.",
            show_alert=True,
        )

        return

    # =====================================================
    # DESCRIPTION
    # =====================================================

    description = (
        "TOAD Source signal\n\n"

        f"Источник Chat ID: "
        f"{candidate.source_chat_id}\n"

        f"Source Message ID: "
        f"{candidate.source_message_id}\n\n"

        "Исходное сообщение:\n"
        f"{candidate.text[:2500]}"
    )

    # =====================================================
    # CREATE NORMAL PENDING REPORT
    # =====================================================

    try:

        report = await add_report(
            username=(
                candidate.suspect_username
            ),

            telegram_id=(
                candidate.suspect_telegram_id
            ),

            full_name=(
                candidate.suspect_username
            ),

            amount="Не указана",

            description=description,

            proofs=[],

            author_id=(
                candidate.source_author_id
                or ADMIN_ID
            ),
        )

    except Exception as error:

        print(
            "Ошибка создания жалобы "
            "из TOAD Source:",
            repr(error),
        )

        await callback.answer(
            "❌ Не удалось создать жалобу.",
            show_alert=True,
        )

        return

    # =====================================================
    # MARK CANDIDATE REVIEWED
    # =====================================================

    await set_candidate_status(
        candidate_id,
        "reviewed",
    )

    await callback.message.edit_text(
        "✅ Сигнал обработан\n\n"

        f"🚨 TOAD Signal "
        f"#{candidate.id}\n"

        "преобразован в обычную "
        "жалобу:\n\n"

        f"🆔 Жалоба #{report.id}\n"

        f"👤 @{candidate.suspect_username}\n"

        "📌 Статус жалобы: pending\n\n"

        "Теперь открой /admin "
        "и проведи обычную модерацию.\n\n"

        "⚠️ Пользователь ещё "
        "не добавлен в публичную базу."
    )

    await callback.answer(
        "Жалоба создана"
    )


# =========================================================
# REJECT CANDIDATE
# =========================================================

@router.callback_query(
    F.data.regexp(
        r"^source_reject_\d+$"
    )
)
async def reject_candidate(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Нет доступа",
            show_alert=True,
        )

        return

    try:

        candidate_id = int(
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

    candidate = await get_candidate(
        candidate_id
    )

    if candidate is None:

        await callback.answer(
            "Сигнал не найден",
            show_alert=True,
        )

        return

    if candidate.status != "pending":

        await callback.answer(
            "Сигнал уже обработан.",
            show_alert=True,
        )

        return

    success = await set_candidate_status(
        candidate_id,
        "rejected",
    )

    if not success:

        await callback.answer(
            "Не удалось отклонить сигнал.",
            show_alert=True,
        )

        return

    await callback.message.edit_text(
        "❌ TOAD Source Signal "
        f"#{candidate_id} отклонён.\n\n"

        "Он не был добавлен "
        "в очередь жалоб "
        "и не попадёт "
        "в публичную базу."
    )

    await callback.answer(
        "Сигнал отклонён"
    )