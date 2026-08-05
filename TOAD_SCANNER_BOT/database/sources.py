from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
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


# =========================================================
# SOURCE GROUP
# =========================================================

class SourceGroup(Base):
    __tablename__ = "source_groups"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    added_by: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# SCAM CANDIDATE
# =========================================================

class ScamCandidate(Base):
    __tablename__ = "scam_candidates"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    source_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    source_message_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    source_author_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    source_author_username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    suspect_username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    suspect_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# GET SOURCE
# =========================================================

async def get_source_group(
    telegram_chat_id: int,
):
    async with Session() as session:

        result = await session.execute(
            select(
                SourceGroup
            ).where(
                SourceGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        return result.scalar_one_or_none()


# =========================================================
# ADD / UPDATE SOURCE
# =========================================================

async def save_source_group(
    telegram_chat_id: int,
    title: str | None,
    username: str | None,
    added_by: int,
):
    async with Session() as session:

        result = await session.execute(
            select(
                SourceGroup
            ).where(
                SourceGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        source = (
            result.scalar_one_or_none()
        )

        if source is None:

            source = SourceGroup(
                telegram_chat_id=telegram_chat_id,
                title=title,
                username=username,
                added_by=added_by,
                is_active=True,
            )

            session.add(
                source
            )

        else:

            source.title = title
            source.username = username
            source.added_by = added_by
            source.is_active = True

        await session.commit()
        await session.refresh(
            source
        )

        return source


# =========================================================
# DISABLE SOURCE
# =========================================================

async def disable_source_group(
    telegram_chat_id: int,
):
    async with Session() as session:

        source = await session.scalar(
            select(
                SourceGroup
            ).where(
                SourceGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        if source is None:
            return False

        source.is_active = False

        await session.commit()

        return True


# =========================================================
# CREATE CANDIDATE
# =========================================================

async def create_candidate(
    source_chat_id: int,
    source_message_id: int,
    source_author_id: int | None,
    source_author_username: str | None,
    suspect_username: str | None,
    suspect_telegram_id: int | None,
    text: str,
):

    async with Session() as session:

        # Защита от повторной обработки
        existing = await session.scalar(
            select(
                ScamCandidate
            ).where(
                ScamCandidate.source_chat_id
                == source_chat_id,

                ScamCandidate.source_message_id
                == source_message_id,
            )
        )

        if existing is not None:
            return existing

        candidate = ScamCandidate(
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            source_author_id=source_author_id,
            source_author_username=source_author_username,
            suspect_username=suspect_username,
            suspect_telegram_id=suspect_telegram_id,
            text=text[:5000],
            status="pending",
        )

        session.add(
            candidate
        )

        await session.commit()
        await session.refresh(
            candidate
        )

        return candidate


# =========================================================
# PENDING CANDIDATES
# =========================================================

async def get_pending_candidates():

    async with Session() as session:

        result = await session.execute(
            select(
                ScamCandidate
            )
            .where(
                ScamCandidate.status
                == "pending"
            )
            .order_by(
                ScamCandidate.created_at.desc()
            )
        )

        return (
            result.scalars().all()
        )


# =========================================================
# GET CANDIDATE
# =========================================================

async def get_candidate(
    candidate_id: int,
):

    async with Session() as session:

        return await session.get(
            ScamCandidate,
            candidate_id,
        )


# =========================================================
# UPDATE CANDIDATE STATUS
# =========================================================

async def set_candidate_status(
    candidate_id: int,
    status: str,
):

    if status not in {
        "pending",
        "reviewed",
        "rejected",
    }:
        return False

    async with Session() as session:

        candidate = await session.get(
            ScamCandidate,
            candidate_id,
        )

        if candidate is None:
            return False

        candidate.status = status

        await session.commit()

        return True