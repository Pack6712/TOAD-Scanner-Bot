from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_ID

from database.functions import (
    get_pending_reports,
    get_report,
    get_proofs,
    approve_report,
    reject_report,
)

from database.entities import (
    attach_report_to_entity,
)


router = Router()


# =========================================================
# FSM ДЛЯ СВОЕЙ ПРИЧИНЫ ОТКЛОНЕНИЯ
# =========================================================

class AdminRejectState(StatesGroup):
    reason = State()


# =========================================================
# ПРОВЕРКА АДМИНА
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def admin_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ Жалобы на модерации",
                    callback_data="admin_pending"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="admin_refresh"
                )
            ]
        ]
    )


def back_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_back"
                )
            ]
        ]
    )


def reject_reason_keyboard(report_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📎 Недостаточно доказательств",
                    callback_data=f"reject_reason_proofs_{report_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Недостаточно информации",
                    callback_data=f"reject_reason_info_{report_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="♻️ Дубликат жалобы",
                    callback_data=f"reject_reason_duplicate_{report_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Данные не подтверждаются",
                    callback_data=f"reject_reason_unconfirmed_{report_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Другая причина",
                    callback_data=f"reject_reason_custom_{report_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к жалобе",
                    callback_data=f"admin_report_{report_id}"
                )
            ]
        ]
    )


# =========================================================
# /admin
# =========================================================

@router.message(Command("admin"))
async def admin_panel(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        await message.answer(
            "❌ У вас нет доступа к админ-панели."
        )
        return

    await state.clear()

    reports = await get_pending_reports()

    await message.answer(
        "🛡 Админ-панель TOAD Scanner\n\n"
        f"⏳ Жалоб на модерации: {len(reports)}\n\n"
        "Выберите действие:",
        reply_markup=admin_menu_keyboard()
    )


# =========================================================
# СПИСОК ЖАЛОБ НА МОДЕРАЦИИ
# =========================================================

@router.callback_query(F.data == "admin_pending")
async def admin_pending(
    callback: CallbackQuery
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    reports = await get_pending_reports()

    if not reports:
        await callback.message.edit_text(
            "✅ Жалоб на модерации сейчас нет.",
            reply_markup=back_admin_keyboard()
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
                    text=f"#{report.id} — {username}",
                    callback_data=f"admin_report_{report.id}"
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="admin_back"
            )
        ]
    )

    await callback.message.edit_text(
        "⏳ Жалобы на модерации\n\n"
        f"Всего: {len(reports)}\n\n"
        "Выберите жалобу:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        )
    )

    await callback.answer()


# =========================================================
# ОТКРЫТЬ ЖАЛОБУ
# =========================================================

@router.callback_query(
    F.data.startswith("admin_report_")
)
async def admin_open_report(
    callback: CallbackQuery
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    try:
        report_id = int(
            callback.data.split("_")[-1]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "Ошибка ID",
            show_alert=True
        )
        return

    report = await get_report(report_id)

    if report is None:
        await callback.answer(
            "Жалоба не найдена",
            show_alert=True
        )
        return

    proofs = get_proofs(report)

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

    author_id = (
        str(report.author_id)
        if report.author_id is not None
        else "Неизвестен"
    )

    reject_reason = (
        report.reject_reason
        if report.reject_reason
        else "Нет"
    )

    entity_id = (
        str(report.entity_id)
        if report.entity_id is not None
        else "Не создано"
    )

    text = (
        "🚨 Жалоба\n\n"
        f"🆔 Жалоба #{report.id}\n"
        f"📌 Статус: {report.status}\n"
        f"🐸 Досье: {entity_id}\n\n"

        f"👤 Username: {username}\n"
        f"🆔 Telegram ID: {telegram_id}\n"
        f"📛 Имя: {report.full_name or 'Не указано'}\n"
        f"💰 Сумма: {report.amount or 'Не указана'}\n\n"

        f"📝 Описание:\n"
        f"{report.description}\n\n"

        f"📎 Доказательств: {len(proofs)}\n"
        f"👤 Автор жалобы ID: {author_id}\n\n"

        f"📋 Причина отклонения:\n"
        f"{reject_reason}"
    )

    rows = []

    if report.status == "pending":
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_{report.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{report.id}"
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="📎 Показать доказательства",
                callback_data=f"admin_proofs_{report.id}"
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="admin_pending"
            )
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        )
    )

    await callback.answer()


# =========================================================
# ПОКАЗАТЬ ДОКАЗАТЕЛЬСТВА
# =========================================================

@router.callback_query(
    F.data.startswith("admin_proofs_")
)
async def admin_show_proofs(
    callback: CallbackQuery
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    try:
        report_id = int(
            callback.data.split("_")[-1]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "Ошибка ID",
            show_alert=True
        )
        return

    report = await get_report(report_id)

    if report is None:
        await callback.answer(
            "Жалоба не найдена",
            show_alert=True
        )
        return

    proofs = get_proofs(report)

    if not proofs:
        await callback.answer(
            "Доказательств нет",
            show_alert=True
        )
        return

    await callback.answer(
        f"Доказательств: {len(proofs)}"
    )

    for proof in proofs:
        try:
            proof_type, file_id = proof.split(
                ":",
                1
            )

            if proof_type == "photo":
                await callback.bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=file_id,
                    caption=(
                        f"📸 Доказательство "
                        f"к жалобе #{report.id}"
                    )
                )

            elif proof_type == "video":
                await callback.bot.send_video(
                    chat_id=callback.from_user.id,
                    video=file_id,
                    caption=(
                        f"🎥 Доказательство "
                        f"к жалобе #{report.id}"
                    )
                )

            elif proof_type == "document":
                await callback.bot.send_document(
                    chat_id=callback.from_user.id,
                    document=file_id,
                    caption=(
                        f"📄 Доказательство "
                        f"к жалобе #{report.id}"
                    )
                )

        except Exception as error:
            print(
                f"Ошибка доказательства "
                f"жалобы #{report.id}:",
                repr(error)
            )


# =========================================================
# ОДОБРЕНИЕ ЖАЛОБЫ
# =========================================================

@router.callback_query(
    F.data.regexp(r"^approve_\d+$")
)
async def approve(
    callback: CallbackQuery
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    try:
        report_id = int(
            callback.data.split("_")[1]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "Ошибка ID",
            show_alert=True
        )
        return

    report = await get_report(report_id)

    if report is None:
        await callback.answer(
            "Жалоба не найдена",
            show_alert=True
        )
        return

    if report.status != "pending":
        await callback.answer(
            "Жалоба уже обработана.",
            show_alert=True
        )
        return

    success = await approve_report(
        report_id
    )

    if not success:
        await callback.answer(
            "Не удалось одобрить жалобу",
            show_alert=True
        )
        return

    entity = None

    try:
        entity = await attach_report_to_entity(
            report_id
        )
    except Exception as error:
        print(
            "Ошибка создания/обновления досье:",
            repr(error)
        )

    if report.author_id is not None:
        try:
            username = (
                f"@{report.username}"
                if report.username
                else "не указан"
            )

            entity_text = ""

            if entity is not None:
                entity_text = (
                    f"\n\n🐸 Досье TOAD: #{entity.id}\n"
                    f"📊 Risk Score: {entity.risk_score}/100"
                )

            await callback.bot.send_message(
                chat_id=report.author_id,
                text=(
                    f"✅ Ваша жалоба #{report.id} одобрена.\n\n"
                    f"👤 Пользователь: {username}\n\n"
                    "Жалоба прошла модерацию "
                    "и теперь доступна в базе "
                    "TOAD Scanner."
                    f"{entity_text}"
                )
            )

        except Exception as error:
            print(
                "Ошибка уведомления автора:",
                repr(error)
            )

    if entity is not None:
        await callback.message.edit_text(
            f"✅ Жалоба #{report.id} одобрена.\n\n"
            f"🐸 Досье #{entity.id}\n"
            f"📊 Risk Score: {entity.risk_score}/100\n\n"
            "Жалоба привязана к досье "
            "и доступна в публичном поиске."
        )
    else:
        await callback.message.edit_text(
            f"✅ Жалоба #{report.id} одобрена.\n\n"
            "Жалоба доступна в поиске.\n\n"
            "⚠️ Досье автоматически создать "
            "не удалось.\n"
            "Проверь PowerShell."
        )

    await callback.answer(
        "Жалоба одобрена"
    )


# =========================================================
# ОТКЛОНЕНИЕ — МЕНЮ
# =========================================================

@router.callback_query(
    F.data.regexp(r"^reject_\d+$")
)
async def reject_menu(
    callback: CallbackQuery
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    try:
        report_id = int(
            callback.data.split("_")[1]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "Ошибка ID",
            show_alert=True
        )
        return

    report = await get_report(report_id)

    if report is None:
        await callback.answer(
            "Жалоба не найдена",
            show_alert=True
        )
        return

    if report.status != "pending":
        await callback.answer(
            "Жалоба уже обработана.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        f"❌ Отклонение жалобы #{report_id}\n\n"
        "Выберите причину:",
        reply_markup=reject_reason_keyboard(
            report_id
        )
    )

    await callback.answer()


# =========================================================
# ВЫБОР ПРИЧИНЫ
# =========================================================

@router.callback_query(
    F.data.startswith("reject_reason_")
)
async def reject_with_reason(
    callback: CallbackQuery,
    state: FSMContext
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    parts = callback.data.split("_")

    if len(parts) < 4:
        await callback.answer(
            "Ошибка callback",
            show_alert=True
        )
        return

    reason_code = parts[2]

    try:
        report_id = int(
            parts[3]
        )
    except ValueError:
        await callback.answer(
            "Ошибка ID",
            show_alert=True
        )
        return

    if reason_code == "custom":
        await state.update_data(
            reject_report_id=report_id
        )

        await state.set_state(
            AdminRejectState.reason
        )

        await callback.message.edit_text(
            f"✏️ Жалоба #{report_id}\n\n"
            "Напишите причину отклонения "
            "одним сообщением.\n\n"
            "Максимум 500 символов."
        )

        await callback.answer()
        return

    reasons = {
        "proofs":
            "Недостаточно доказательств.",

        "info":
            "Недостаточно информации.",

        "duplicate":
            "Дубликат уже существующей жалобы.",

        "unconfirmed":
            "Предоставленные данные не подтверждаются.",
    }

    reason = reasons.get(
        reason_code
    )

    if reason is None:
        await callback.answer(
            "Неизвестная причина",
            show_alert=True
        )
        return

    await process_rejection(
        callback=callback,
        report_id=report_id,
        reason=reason
    )


# =========================================================
# ОБРАБОТКА ОТКЛОНЕНИЯ
# =========================================================

async def process_rejection(
    callback: CallbackQuery,
    report_id: int,
    reason: str
):
    # Дополнительная защита
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    reason = reason.strip()

    if len(reason) < 3:
        await callback.answer(
            "Причина слишком короткая",
            show_alert=True
        )
        return

    if len(reason) > 500:
        await callback.answer(
            "Причина слишком длинная",
            show_alert=True
        )
        return

    report = await get_report(
        report_id
    )

    if report is None:
        await callback.answer(
            "Жалоба не найдена",
            show_alert=True
        )
        return

    if report.status != "pending":
        await callback.answer(
            "Жалоба уже обработана.",
            show_alert=True
        )
        return

    success = await reject_report(
        report_id,
        reason
    )

    if not success:
        await callback.answer(
            "Не удалось отклонить жалобу",
            show_alert=True
        )
        return

    if report.author_id is not None:
        try:
            username = (
                f"@{report.username}"
                if report.username
                else "не указан"
            )

            await callback.bot.send_message(
                chat_id=report.author_id,
                text=(
                    f"❌ Ваша жалоба #{report.id} отклонена.\n\n"
                    f"👤 Пользователь: {username}\n\n"
                    f"📋 Причина:\n"
                    f"{reason}\n\n"
                    "Жалоба не была добавлена "
                    "в публичную базу "
                    "TOAD Scanner."
                )
            )

        except Exception as error:
            print(
                "Ошибка уведомления автора:",
                repr(error)
            )

    await callback.message.edit_text(
        f"❌ Жалоба #{report.id} отклонена.\n\n"
        f"📋 Причина:\n{reason}"
    )

    await callback.answer(
        "Жалоба отклонена"
    )


# =========================================================
# СВОЯ ПРИЧИНА
# =========================================================

@router.message(
    AdminRejectState.reason
)
async def custom_reject_reason(
    message: Message,
    state: FSMContext
):
    if not is_admin(
        message.from_user.id
    ):
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "❌ Причину нужно отправить текстом."
        )
        return

    reason = (
        message.text.strip()
    )

    if len(reason) < 3:
        await message.answer(
            "❌ Причина слишком короткая."
        )
        return

    if len(reason) > 500:
        await message.answer(
            "❌ Максимум 500 символов."
        )
        return

    data = await state.get_data()

    report_id = data.get(
        "reject_report_id"
    )

    if report_id is None:
        await state.clear()

        await message.answer(
            "❌ Не удалось определить жалобу."
        )
        return

    report = await get_report(
        report_id
    )

    if report is None:
        await state.clear()

        await message.answer(
            "❌ Жалоба не найдена."
        )
        return

    if report.status != "pending":
        await state.clear()

        await message.answer(
            "⚠️ Жалоба уже обработана."
        )
        return

    success = await reject_report(
        report_id,
        reason
    )

    if not success:
        await state.clear()

        await message.answer(
            "❌ Не удалось отклонить жалобу."
        )
        return

    if report.author_id is not None:
        try:
            username = (
                f"@{report.username}"
                if report.username
                else "не указан"
            )

            await message.bot.send_message(
                chat_id=report.author_id,
                text=(
                    f"❌ Ваша жалоба #{report.id} отклонена.\n\n"
                    f"👤 Пользователь: {username}\n\n"
                    f"📋 Причина:\n"
                    f"{reason}\n\n"
                    "Жалоба не была добавлена "
                    "в публичную базу "
                    "TOAD Scanner."
                )
            )

        except Exception as error:
            print(
                "Ошибка уведомления автора:",
                repr(error)
            )

    await state.clear()

    await message.answer(
        f"❌ Жалоба #{report.id} отклонена.\n\n"
        f"📋 Причина:\n{reason}"
    )


# =========================================================
# НАЗАД / ОБНОВИТЬ
# =========================================================

@router.callback_query(
    F.data.in_({
        "admin_back",
        "admin_refresh"
    })
)
async def admin_back(
    callback: CallbackQuery
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа",
            show_alert=True
        )
        return

    reports = await get_pending_reports()

    await callback.message.edit_text(
        "🛡 Админ-панель TOAD Scanner\n\n"
        f"⏳ Жалоб на модерации: {len(reports)}\n\n"
        "Выберите действие:",
        reply_markup=admin_menu_keyboard()
    )

    await callback.answer()