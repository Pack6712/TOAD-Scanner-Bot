import re
import math

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from states.report import AddReport

from database.functions import (
    add_report,
    has_pending_duplicate,
    can_submit_report,
)

from keyboards.admin import (
    report_moderation_keyboard,
)


router = Router()


# =========================================================
# LIMITS
# =========================================================

MAX_PROOFS = 10

MAX_PHOTO_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 50 * 1024 * 1024
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024


# =========================================================
# KEYBOARDS
# =========================================================

def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить жалобу",
                    callback_data="cancel_report",
                )
            ]
        ]
    )


def proofs_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Завершить",
                    callback_data="finish_proofs",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить жалобу",
                    callback_data="cancel_report",
                )
            ],
        ]
    )


# =========================================================
# CANCEL
# =========================================================

@router.callback_query(
    F.data == "cancel_report"
)
async def cancel_report(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.answer(
        "Жалоба отменена"
    )

    if callback.message:
        await callback.message.edit_text(
            "❌ Подача жалобы отменена."
        )


# =========================================================
# START REPORT
# =========================================================

@router.message(
    F.text == "🚨 Подать жалобу"
)
async def add_report_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    allowed, seconds_left = (
        await can_submit_report(
            author_id=message.from_user.id,
            cooldown_minutes=2,
        )
    )

    if not allowed:
        minutes = max(
            1,
            math.ceil(
                seconds_left / 60
            )
        )

        await message.answer(
            "⏳ Слишком частая отправка жалоб.\n\n"
            f"Попробуйте снова примерно через "
            f"{minutes} мин."
        )
        return

    await message.answer(
        "🚨 НОВАЯ ЖАЛОБА\n\n"
        "Введите Telegram username пользователя.\n\n"
        "Например:\n"
        "@username\n\n"
        "Username должен содержать только "
        "латинские буквы, цифры и _.",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(
        AddReport.username
    )


# =========================================================
# USERNAME
# =========================================================

@router.message(
    AddReport.username
)
async def report_username(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Username нужно отправить текстом.",
            reply_markup=cancel_keyboard(),
        )
        return

    username = (
        message.text
        .strip()
        .lstrip("@")
    )

    if not re.fullmatch(
        r"[A-Za-z0-9_]{5,32}",
        username,
    ):
        await message.answer(
            "❌ Некорректный username.\n\n"
            "Допустимо:\n"
            "• 5–32 символа\n"
            "• латинские буквы\n"
            "• цифры\n"
            "• символ _\n\n"
            "Пример: @test_user",
            reply_markup=cancel_keyboard(),
        )
        return

    duplicate = (
        await has_pending_duplicate(
            author_id=message.from_user.id,
            username=username,
        )
    )

    if duplicate is not None:
        await message.answer(
            "⚠️ У вас уже есть жалоба "
            f"на @{username}, которая находится "
            "на модерации.\n\n"
            f"🆔 Жалоба #{duplicate.id}"
        )

        await state.clear()
        return

    await state.update_data(
        username=username
    )

    await message.answer(
        "Введите Telegram ID пользователя.\n\n"
        "Если ID неизвестен — отправьте -",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(
        AddReport.telegram_id
    )


# =========================================================
# TELEGRAM ID
# =========================================================

@router.message(
    AddReport.telegram_id
)
async def report_telegram_id(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Telegram ID нужно отправить текстом.",
            reply_markup=cancel_keyboard(),
        )
        return

    telegram_id = (
        message.text.strip()
    )

    if telegram_id != "-":
        if not telegram_id.isdigit():
            await message.answer(
                "❌ Telegram ID должен состоять "
                "только из цифр.\n\n"
                "Если ID неизвестен — отправьте -",
                reply_markup=cancel_keyboard(),
            )
            return

        if len(telegram_id) > 20:
            await message.answer(
                "❌ Telegram ID слишком длинный.",
                reply_markup=cancel_keyboard(),
            )
            return

    await state.update_data(
        telegram_id=telegram_id
    )

    await message.answer(
        "Введите имя или ник пользователя.",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(
        AddReport.full_name
    )


# =========================================================
# FULL NAME
# =========================================================

@router.message(
    AddReport.full_name
)
async def report_full_name(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Имя нужно отправить текстом.",
            reply_markup=cancel_keyboard(),
        )
        return

    full_name = (
        message.text.strip()
    )

    if len(full_name) < 2:
        await message.answer(
            "❌ Имя или ник слишком короткий.",
            reply_markup=cancel_keyboard(),
        )
        return

    if len(full_name) > 100:
        await message.answer(
            "❌ Максимум 100 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(
        full_name=full_name
    )

    await message.answer(
        "Введите сумму ущерба.\n\n"
        "Например:\n"
        "500 USDT\n"
        "15000 UAH",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(
        AddReport.amount
    )


# =========================================================
# AMOUNT
# =========================================================

@router.message(
    AddReport.amount
)
async def report_amount(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Сумму нужно отправить текстом.",
            reply_markup=cancel_keyboard(),
        )
        return

    amount = (
        message.text.strip()
    )

    if len(amount) > 50:
        await message.answer(
            "❌ Сумма указана слишком длинно.\n"
            "Максимум 50 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(
        amount=amount
    )

    await message.answer(
        "📝 Опишите подробно ситуацию.\n\n"
        "Минимум 10 символов.",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(
        AddReport.description
    )


# =========================================================
# DESCRIPTION
# =========================================================

@router.message(
    AddReport.description
)
async def report_description(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Описание нужно отправить текстом.",
            reply_markup=cancel_keyboard(),
        )
        return

    description = (
        message.text.strip()
    )

    if len(description) < 10:
        await message.answer(
            "❌ Описание слишком короткое.\n\n"
            "Напишите хотя бы 10 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    if len(description) > 3000:
        await message.answer(
            "❌ Описание слишком длинное.\n"
            "Максимум 3000 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(
        description=description,
        proofs=[],
    )

    await state.set_state(
        AddReport.proofs
    )

    await message.answer(
        "📎 ПРИКРЕПИТЕ ДОКАЗАТЕЛЬСТВА\n\n"
        "Можно отправить:\n"
        "📸 Фото — до 10 MB\n"
        "🎥 Видео — до 50 MB\n"
        "📄 Документ — до 20 MB\n\n"
        f"Максимум файлов: {MAX_PROOFS}\n\n"
        "Когда закончите — нажмите "
        "«✅ Завершить».",
        reply_markup=proofs_keyboard(),
    )


# =========================================================
# PROOFS
# =========================================================

@router.message(
    AddReport.proofs
)
async def report_proof(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    proofs = data.get(
        "proofs",
        [],
    )

    if len(proofs) >= MAX_PROOFS:
        await message.answer(
            f"⚠️ Уже прикреплено максимум "
            f"{MAX_PROOFS} файлов.",
            reply_markup=proofs_keyboard(),
        )
        return

    proof = None
    proof_name = None

    if message.photo:
        photo = message.photo[-1]

        if (
            photo.file_size is not None
            and photo.file_size > MAX_PHOTO_SIZE
        ):
            await message.answer(
                "❌ Фото слишком большое.\n"
                "Максимальный размер: 10 MB.",
                reply_markup=proofs_keyboard(),
            )
            return

        proof = (
            f"photo:{photo.file_id}"
        )

        proof_name = "📸 Фото"

    elif message.video:
        video = message.video

        if (
            video.file_size is not None
            and video.file_size > MAX_VIDEO_SIZE
        ):
            await message.answer(
                "❌ Видео слишком большое.\n"
                "Максимальный размер: 50 MB.",
                reply_markup=proofs_keyboard(),
            )
            return

        proof = (
            f"video:{video.file_id}"
        )

        proof_name = "🎥 Видео"

    elif message.document:
        document = message.document

        if (
            document.file_size is not None
            and document.file_size > MAX_DOCUMENT_SIZE
        ):
            await message.answer(
                "❌ Документ слишком большой.\n"
                "Максимальный размер: 20 MB.",
                reply_markup=proofs_keyboard(),
            )
            return

        proof = (
            f"document:{document.file_id}"
        )

        proof_name = "📄 Документ"

    if proof is None:
        await message.answer(
            "⚠️ Поддерживаются только:\n"
            "📸 фото\n"
            "🎥 видео\n"
            "📄 документы",
            reply_markup=proofs_keyboard(),
        )
        return

    proofs.append(
        proof
    )

    await state.update_data(
        proofs=proofs
    )

    await message.answer(
        f"✅ {proof_name} добавлено.\n\n"
        f"📎 Прикреплено: "
        f"{len(proofs)}/{MAX_PROOFS}",
        reply_markup=proofs_keyboard(),
    )


# =========================================================
# FINISH REPORT
# =========================================================

@router.callback_query(
    F.data == "finish_proofs"
)
async def finish_report(
    callback: CallbackQuery,
    state: FSMContext,
):
    current_state = (
        await state.get_state()
    )

    if current_state != AddReport.proofs.state:
        await callback.answer(
            "Жалоба уже завершена "
            "или не была начата.",
            show_alert=True,
        )
        return

    data = await state.get_data()

    username = data.get(
        "username"
    )

    if not username:
        await callback.answer(
            "Не удалось получить username.",
            show_alert=True,
        )

        await state.clear()
        return

    duplicate = (
        await has_pending_duplicate(
            author_id=callback.from_user.id,
            username=username,
        )
    )

    if duplicate is not None:
        await state.clear()

        await callback.answer(
            "Такая жалоба уже есть",
            show_alert=True,
        )

        if callback.message:
            await callback.message.edit_text(
                "⚠️ Жалоба не отправлена.\n\n"
                f"У вас уже есть жалоба "
                f"#{duplicate.id} на "
                f"@{username}, которая "
                "находится на модерации."
            )

        return

    allowed, seconds_left = (
        await can_submit_report(
            author_id=callback.from_user.id,
            cooldown_minutes=2,
        )
    )

    if not allowed:
        await state.clear()

        minutes = max(
            1,
            math.ceil(
                seconds_left / 60
            )
        )

        await callback.answer(
            "Слишком частая отправка",
            show_alert=True,
        )

        if callback.message:
            await callback.message.edit_text(
                "⏳ Жалоба не отправлена.\n\n"
                f"Попробуйте снова примерно "
                f"через {minutes} мин."
            )

        return

    await callback.answer(
        "Обрабатываю жалобу..."
    )

    telegram_id_text = str(
        data.get(
            "telegram_id",
            "",
        )
    ).strip()

    telegram_id = None

    if telegram_id_text.isdigit():
        telegram_id = int(
            telegram_id_text
        )

    proofs = data.get(
        "proofs",
        [],
    )

    try:
        report = await add_report(
            username=username,
            telegram_id=telegram_id,
            full_name=data["full_name"],
            amount=data["amount"],
            description=data["description"],
            proofs=proofs,
            author_id=callback.from_user.id,
        )

    except Exception as error:
        print(
            "Ошибка сохранения жалобы:",
            repr(error),
        )

        if callback.message:
            await callback.message.answer(
                "❌ Не удалось сохранить жалобу."
            )

        return

    await state.clear()

    admin_text = (
        "🚨 НОВАЯ ЖАЛОБА\n\n"

        f"🆔 Жалоба #{report.id}\n"
        "📌 Статус: На модерации\n\n"

        f"👤 Username: @{username}\n"
        f"🆔 Telegram ID: {telegram_id_text}\n"
        f"📛 Имя: {data['full_name']}\n"
        f"💰 Сумма: {data['amount']}\n\n"

        f"📝 Описание:\n"
        f"{data['description']}\n\n"

        f"📎 Доказательств: {len(proofs)}\n"
        f"👤 Автор жалобы ID: "
        f"{callback.from_user.id}"
    )

    try:
        await callback.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=(
                report_moderation_keyboard(
                    report.id
                )
            ),
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
                        chat_id=ADMIN_ID,
                        photo=file_id,
                        caption=(
                            f"📸 Доказательство "
                            f"к жалобе #{report.id}"
                        ),
                    )

                elif proof_type == "video":
                    await callback.bot.send_video(
                        chat_id=ADMIN_ID,
                        video=file_id,
                        caption=(
                            f"🎥 Доказательство "
                            f"к жалобе #{report.id}"
                        ),
                    )

                elif proof_type == "document":
                    await callback.bot.send_document(
                        chat_id=ADMIN_ID,
                        document=file_id,
                        caption=(
                            f"📄 Доказательство "
                            f"к жалобе #{report.id}"
                        ),
                    )

            except Exception as proof_error:
                print(
                    "Ошибка отправки доказательства:",
                    repr(proof_error),
                )

    except Exception as admin_error:
        print(
            "Ошибка отправки админу:",
            repr(admin_error),
        )

    if callback.message:
        await callback.message.edit_text(
            "✅ ЖАЛОБА ОТПРАВЛЕНА\n\n"

            f"🆔 Жалоба #{report.id}\n"
            "📌 Статус: На модерации\n\n"

            f"👤 Username: @{username}\n"
            f"🆔 Telegram ID: {telegram_id_text}\n"
            f"📛 Имя: {data['full_name']}\n"
            f"💰 Сумма: {data['amount']}\n"
            f"📎 Доказательств: {len(proofs)}\n\n"

            "После проверки бот сообщит "
            "результат модерации."
        )