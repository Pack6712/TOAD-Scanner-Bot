from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext


router = Router()


# =========================================================
# /cancel
# =========================================================

@router.message(Command("cancel"))
async def cancel_action(
    message: Message,
    state: FSMContext,
):
    """
    Безопасно отменяет текущее действие пользователя
    и очищает его FSM-состояние.
    """

    current_state = await state.get_state()

    # Пользователь сейчас ничего не заполняет
    if current_state is None:
        await message.answer(
            "ℹ️ Сейчас нет активного действия для отмены."
        )
        return

    # Полностью очищаем FSM:
    # состояние + временно сохранённые данные.
    await state.clear()

    await message.answer(
        "❌ Текущее действие отменено.\n\n"
        "Все временные данные очищены.\n"
        "Используйте /start для возврата "
        "в главное меню."
    )


# =========================================================
# /help
# =========================================================

@router.message(Command("help"))
async def help_command(
    message: Message,
):
    await message.answer(
        "🐸 TOAD Scanner — помощь\n\n"

        "Основные команды:\n\n"

        "/start — главное меню\n"
        "/help — помощь\n"
        "/cancel — отменить текущее действие\n\n"

        "Основные разделы:\n\n"

        "🔍 Проверить пользователя — поиск по базе\n"
        "➕ Подать жалобу — создать новую жалобу\n"
        "📂 База мошенников — подтверждённые записи\n"
        "👤 Профиль — ваши жалобы и статистика\n"
        "📊 Статистика — общая статистика базы\n\n"

        "Если вы начали заполнять жалобу "
        "и хотите выйти — отправьте /cancel."
    )