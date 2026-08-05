from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    Text,
    select,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from database.database import (
    Base,
    Session,
)


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

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
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


async def add_mod_log(
    telegram_chat_id: int,
    user_id: int,
    moderator_id: int,
    action: str,
    reason: str | None = None,
    duration_minutes: int | None = None,
):
    async with Session() as session:

        log = ModerationLog(
            telegram_chat_id=telegram_chat_id,
            user_id=user_id,
            moderator_id=moderator_id,
            action=action.upper(),
            reason=reason,
            duration_minutes=duration_minutes,
        )

        session.add(log)

        await session.commit()
        await session.refresh(log)

        return log


async def get_group_logs(
    telegram_chat_id: int,
    limit: int = 20,
):
    async with Session() as session:

        result = await session.execute(
            select(ModerationLog)
            .where(
                ModerationLog.telegram_chat_id
                == telegram_chat_id
            )
            .order_by(
                ModerationLog.created_at.desc()
            )
            .limit(limit)
        )

        return result.scalars().all()


async def get_user_logs(
    telegram_chat_id: int,
    user_id: int,
    limit: int = 20,
):
    async with Session() as session:

        result = await session.execute(
            select(ModerationLog)
            .where(
                ModerationLog.telegram_chat_id
                == telegram_chat_id,
                ModerationLog.user_id
                == user_id,
            )
            .order_by(
                ModerationLog.created_at.desc()
            )
            .limit(limit)
        )

        return result.scalars().all()