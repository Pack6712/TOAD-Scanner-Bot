import hashlib

from sqlalchemy import select, func

from database.database import Session
from database.models import (
    ScamEntity,
    ScamReport,
    EntityIdentifier,
)


def normalize_username(username: str) -> str:
    return username.strip().lower().lstrip("@")


def make_hash(value: str) -> str:
    normalized = value.strip().lower()

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


async def find_entity_by_username(
    username: str
):
    normalized = normalize_username(
        username
    )

    username_hash = make_hash(
        normalized
    )

    async with Session() as session:

        result = await session.execute(
            select(EntityIdentifier).where(
                EntityIdentifier.identifier_type
                == "telegram_username",

                EntityIdentifier.value_hash
                == username_hash
            )
        )

        identifier = result.scalar_one_or_none()

        if identifier is None:
            return None

        entity = await session.get(
            ScamEntity,
            identifier.entity_id
        )

        return entity


async def create_entity_from_report(
    report_id: int
):
    async with Session() as session:

        report = await session.get(
            ScamReport,
            report_id
        )

        if report is None:
            return None

        if report.entity_id is not None:

            entity = await session.get(
                ScamEntity,
                report.entity_id
            )

            return entity

        username = None

        if report.username:
            username = normalize_username(
                report.username
            )

        # =========================
        # ИЩЕМ СУЩЕСТВУЮЩЕЕ ДОСЬЕ
        # =========================

        entity = None

        if username:

            username_hash = make_hash(
                username
            )

            result = await session.execute(
                select(EntityIdentifier).where(
                    EntityIdentifier.identifier_type
                    == "telegram_username",

                    EntityIdentifier.value_hash
                    == username_hash
                )
            )

            identifier = (
                result.scalar_one_or_none()
            )

            if identifier is not None:

                entity = await session.get(
                    ScamEntity,
                    identifier.entity_id
                )

        # =========================
        # СОЗДАЁМ НОВОЕ ДОСЬЕ
        # =========================

        if entity is None:

            entity = ScamEntity(
                primary_username=username,
                display_name=report.full_name,
                status="active",
                risk_score=0,
            )

            session.add(entity)

            await session.flush()

            # Telegram username
            if username:

                username_identifier = (
                    EntityIdentifier(
                        entity_id=entity.id,

                        identifier_type=(
                            "telegram_username"
                        ),

                        value_masked=(
                            f"@{username}"
                        ),

                        value_hash=make_hash(
                            username
                        ),

                        label="Telegram Username",
                    )
                )

                session.add(
                    username_identifier
                )

            # Telegram ID
            if report.telegram_id is not None:

                telegram_id_string = str(
                    report.telegram_id
                )

                telegram_id_identifier = (
                    EntityIdentifier(
                        entity_id=entity.id,

                        identifier_type=(
                            "telegram_id"
                        ),

                        value_masked=(
                            telegram_id_string
                        ),

                        value_hash=make_hash(
                            telegram_id_string
                        ),

                        label="Telegram ID",
                    )
                )

                session.add(
                    telegram_id_identifier
                )

        # =========================
        # ПРИВЯЗЫВАЕМ ЖАЛОБУ
        # =========================

        report.entity_id = entity.id

        await session.commit()
        await session.refresh(entity)

        return entity


async def recalculate_entity_risk(
    entity_id: int
):
    async with Session() as session:

        entity = await session.get(
            ScamEntity,
            entity_id
        )

        if entity is None:
            return None

        result = await session.execute(
            select(
                func.count(ScamReport.id)
            ).where(
                ScamReport.entity_id
                == entity_id,

                ScamReport.status
                == "approved"
            )
        )

        approved_count = (
            result.scalar() or 0
        )

        # =========================
        # РЕЙТИНГ
        # =========================

        if approved_count == 0:
            risk_score = 0

        elif approved_count == 1:
            risk_score = 25

        elif approved_count <= 4:
            risk_score = 60

        else:
            risk_score = 90

        entity.risk_score = (
            risk_score
        )

        await session.commit()

        return risk_score


async def attach_report_to_entity(
    report_id: int
):
    entity = await create_entity_from_report(
        report_id
    )

    if entity is None:
        return None

    await recalculate_entity_risk(
        entity.id
    )

    return entity


async def get_entity(
    entity_id: int
):
    async with Session() as session:

        return await session.get(
            ScamEntity,
            entity_id
        )


async def get_entity_reports(
    entity_id: int
):
    async with Session() as session:

        result = await session.execute(
            select(ScamReport)
            .where(
                ScamReport.entity_id
                == entity_id,

                ScamReport.status
                == "approved"
            )
            .order_by(
                ScamReport.created_at.desc()
            )
        )

        return result.scalars().all()


async def get_entity_identifiers(
    entity_id: int
):
    async with Session() as session:

        result = await session.execute(
            select(EntityIdentifier).where(
                EntityIdentifier.entity_id
                == entity_id
            )
        )

        return result.scalars().all() 
