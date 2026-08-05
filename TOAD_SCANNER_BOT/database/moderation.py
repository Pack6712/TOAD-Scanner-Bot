from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    Text,
    select,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from database.database import (
    Base,
    Session,
)


# =========================================================
# GROUP WARNING
# =========================================================

class GroupWarning(Base):
    __tablename__ = "group_warnings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    moderator_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# ADD WARNING
# =========================================================

async def add_warning(
    telegram_chat_id: int,
    user_id: int,
    moderator_id: int,
    reason: str | None = None,
):
    async with Session() as session:

        warning = GroupWarning(
            telegram_chat_id=telegram_chat_id,
            user_id=user_id,
            moderator_id=moderator_id,
            reason=reason,
        )

        session.add(
            warning
        )

        await session.commit()
        await session.refresh(
            warning
        )

        return warning


# =========================================================
# COUNT WARNINGS
# =========================================================

async def count_warnings(
    telegram_chat_id: int,
    user_id: int,
) -> int:
    async with Session() as session:

        result = await session.execute(
            select(
                func.count(
                    GroupWarning.id
                )
            ).where(
                GroupWarning.telegram_chat_id
                == telegram_chat_id,

                GroupWarning.user_id
                == user_id,
            )
        )

        return (
            result.scalar()
            or 0
        )


# =========================================================
# GET USER WARNINGS
# =========================================================

async def get_user_warnings(
    telegram_chat_id: int,
    user_id: int,
):
    async with Session() as session:

        result = await session.execute(
            select(
                GroupWarning
            )
            .where(
                GroupWarning.telegram_chat_id
                == telegram_chat_id,

                GroupWarning.user_id
                == user_id,
            )
            .order_by(
                GroupWarning.created_at.desc()
            )
        )

        return (
            result.scalars().all()
        )


# =========================================================
# REMOVE LAST WARNING
# =========================================================

async def remove_last_warning(
    telegram_chat_id: int,
    user_id: int,
):
    async with Session() as session:

        result = await session.execute(
            select(
                GroupWarning
            )
            .where(
                GroupWarning.telegram_chat_id
                == telegram_chat_id,

                GroupWarning.user_id
                == user_id,
            )
            .order_by(
                GroupWarning.created_at.desc()
            )
        )

        warning = (
            result.scalars().first()
        )

        if warning is None:
            return False

        await session.delete(
            warning
        )

        await session.commit()

        return True


# =========================================================
# CLEAR ALL WARNINGS
# =========================================================

async def clear_warnings(
    telegram_chat_id: int,
    user_id: int,
):
    async with Session() as session:

        result = await session.execute(
            select(
                GroupWarning
            ).where(
                GroupWarning.telegram_chat_id
                == telegram_chat_id,

                GroupWarning.user_id
                == user_id,
            )
        )

        warnings = (
            result.scalars().all()
        )

        if not warnings:
            return 0

        removed = 0

        for warning in warnings:
            await session.delete(
                warning
            )

            removed += 1

        await session.commit()

        return removed