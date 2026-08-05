from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from states.search import SearchState

from database.functions import (
    search_by_username,
    search_by_telegram_id,
    get_proofs,
)


router = Router()


# =========================================================
# RISK LEVEL
# =========================================================

def get_risk_level(
    reports_count: int,
) -> str:

    if reports_count <= 0:
        return "🟢 Риск не выявлен"

    if reports_count == 1:
        return "🟢 Низкий риск"

    if 2 <= reports_count <= 4:
        return "🟡 Средний риск"

    return "🔴 Высокий риск"


# =========================================================
# START SEARCH
# =========================================================

@router.message(
    F.text == "🔎 Проверить человека"
)
async def search_start(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await message.answer(
        "🔎 ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ\n\n"
        "Введите:\n"
        "• Telegram Username\n"
        "• или Telegram ID\n\n"
        "Примеры:\n"
        "@username\n"
        "username\n"
        "123456789"
    )

    await state.set_state(
        SearchState.query
    )


# =========================================================
# SEARCH USER
# =========================================================

@router.message(
    SearchState.query
)
async def search_user(
    message: Message,
    state: FSMContext,
):

    if not message.text:

        await message.answer(
            "❌ Отправьте Username "
            "или Telegram ID текстом."
        )

        return

    query = (
        message.text
        .strip()
    )

    # -----------------------------------------
    # REMOVE @
    # -----------------------------------------

    if query.startswith("@"):

        query = query[1:]

    # -----------------------------------------
    # BASIC VALIDATION
    # -----------------------------------------

    if not query:

        await message.answer(
            "❌ Пустой запрос."
        )

        return

    if len(query) > 64:

        await message.answer(
            "❌ Запрос слишком длинный."
        )

        return

    # -----------------------------------------
    # SEARCH
    # -----------------------------------------

    if query.isdigit():

        reports = (
            await search_by_telegram_id(
                int(query)
            )
        )

    else:

        reports = (
            await search_by_username(
                query
            )
        )

    # -----------------------------------------
    # NOTHING FOUND
    # -----------------------------------------

    if not reports:

        await message.answer(
            "✅ ПОДТВЕРЖДЁННЫХ ЗАПИСЕЙ "
            "НЕ НАЙДЕНО\n\n"

            "В базе TOAD Scanner "
            "нет подтверждённых жалоб "
            "по этому пользователю.\n\n"

            "⚠️ Это не является гарантией "
            "безопасности аккаунта."
        )

        await state.clear()

        return

    # -----------------------------------------
    # STATS
    # -----------------------------------------

    reports_count = len(
        reports
    )

    risk = get_risk_level(
        reports_count
    )

    total_proofs = 0

    for report in reports:

        total_proofs += len(
            get_proofs(
                report
            )
        )

    # -----------------------------------------
    # MAIN USER DATA
    # -----------------------------------------

    first_report = reports[0]

    username = (
        f"@{first_report.username}"
        if first_report.username
        else "Не указан"
    )

    telegram_id = (
        str(
            first_report.telegram_id
        )
        if first_report.telegram_id
        is not None
        else "Не указан"
    )

    # -----------------------------------------
    # RESULT
    # -----------------------------------------

    await message.answer(
        "🐸 TOAD SCANNER\n\n"
        "🚨 НАЙДЕНЫ ПОДТВЕРЖДЁННЫЕ ЖАЛОБЫ\n\n"

        f"👤 Username: {username}\n"
        f"🆔 Telegram ID: {telegram_id}\n\n"

        f"🚨 Жалоб: {reports_count}\n"
        f"📎 Доказательств: {total_proofs}\n"
        f"📊 Уровень риска: {risk}\n\n"

        "Ниже показаны "
        "подтверждённые записи."
    )

    # -----------------------------------------
    # REPORTS
    # -----------------------------------------

    for report in reports:

        proofs = get_proofs(
            report
        )

        report_username = (
            f"@{report.username}"
            if report.username
            else "Не указан"
        )

        report_telegram_id = (
            str(
                report.telegram_id
            )
            if report.telegram_id
            is not None
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

        # Telegram не любит слишком
        # длинные сообщения.
        if len(description) > 3000:

            description = (
                description[:3000]
                + "..."
            )

        text = (
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"🆔 Жалоба #{report.id}\n"
            "✅ Статус: Подтверждена\n\n"

            f"👤 Username: "
            f"{report_username}\n"

            f"🆔 Telegram ID: "
            f"{report_telegram_id}\n"

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

            "━━━━━━━━━━━━━━━━━━"
        )

        await message.answer(
            text
        )

        # -----------------------------------------
        # PROOFS
        # -----------------------------------------

        for proof in proofs:

            try:

                proof_type, file_id = (
                    proof.split(
                        ":",
                        1,
                    )
                )

                if proof_type == "photo":

                    await message.answer_photo(
                        photo=file_id,
                        caption=(
                            "📸 Доказательство "
                            f"к жалобе "
                            f"#{report.id}"
                        ),
                    )

                elif proof_type == "video":

                    await message.answer_video(
                        video=file_id,
                        caption=(
                            "🎥 Доказательство "
                            f"к жалобе "
                            f"#{report.id}"
                        ),
                    )

                elif proof_type == "document":

                    await message.answer_document(
                        document=file_id,
                        caption=(
                            "📄 Доказательство "
                            f"к жалобе "
                            f"#{report.id}"
                        ),
                    )

            except Exception as error:

                print(
                    "Ошибка показа "
                    f"доказательства жалобы "
                    f"#{report.id}:",
                    repr(error),
                )

    # -----------------------------------------
    # FINISH
    # -----------------------------------------

    await state.clear()