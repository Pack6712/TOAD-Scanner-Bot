from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    BigInteger,
    Text,
    DateTime,
    ForeignKey,
)

from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


# =========================================================
# ДОСЬЕ
# =========================================================

class ScamEntity(Base):
    __tablename__ = "scam_entities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Основной Telegram username
    primary_username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # Имя / псевдоним
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # active / hidden / archived
    status: Mapped[str] = mapped_column(
        String(30),
        default="active"
    )

    # Внутренний рейтинг риска
    risk_score: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =========================================================
# ИДЕНТИФИКАТОРЫ ДОСЬЕ
# =========================================================

class EntityIdentifier(Base):
    __tablename__ = "entity_identifiers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("scam_entities.id"),
        nullable=False,
        index=True
    )

    # telegram_username
    # telegram_id
    # phone
    # bank_card
    # crypto_wallet
    identifier_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    # Значение, безопасное для отображения.
    # Например:
    # @username
    # +380******123
    # 5375 **** **** 1234
    value_masked: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # SHA-256 нормализованного значения.
    # Нужен для поиска совпадений без публикации полного значения.
    value_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True
    )

    label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


# =========================================================
# ЖАЛОБЫ
# =========================================================

class ScamReport(Base):
    __tablename__ = "scam_reports"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Досье, к которому относится жалоба.
    # Nullable, чтобы старые записи продолжали работать.
    entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("scam_entities.id"),
        nullable=True,
        index=True
    )

    # Кто отправил жалобу
    author_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True
    )

    # Telegram username объекта жалобы
    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # Telegram ID объекта жалобы
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    amount: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    proofs: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # pending / approved / rejected
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending"
    )

    reject_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    ) 