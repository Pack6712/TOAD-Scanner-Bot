from aiogram.fsm.state import StatesGroup, State


class AddReport(StatesGroup):
    username = State()
    telegram_id = State()
    full_name = State()
    amount = State()
    description = State()

    # Новое состояние
    proofs = State()

    # Подтверждение
    confirm = State() 