import json
from datetime import datetime, timedelta

from sqlalchemy import select, func

from database.database import Session
from database.models import ScamReport


async def add_report(
    username: str,
    telegram_id: int | None,
    full_name: str,
    amount: str,
    description: str,
    proofs: list[str] | None = None,
    author_id: int | None = None,
):
    async with Session() as session:
        proofs_json = None

        if proofs:
            proofs_json = json.dumps(
                proofs,
                ensure_ascii=False
            )

        report = ScamReport(
            author_id=author_id,
            username=username,
            telegram_id=telegram_id,
            full_name=full_name,
            amount=amount,
            description=description,
            proofs=proofs_json,
            status="pending",
            reject_reason=None,
        )

        session.add(report)

        await session.commit()
        await session.refresh(report)

        return report


async def search_by_username(username: str):
    async with Session() as session:
        result = await session.execute(
            select(ScamReport).where(
                ScamReport.username.ilike(f"%{username}%"),
                ScamReport.status == "approved"
            )
        )

        return result.scalars().all()


async def search_by_telegram_id(telegram_id: int):
    async with Session() as session:
        result = await session.execute(
            select(ScamReport).where(
                ScamReport.telegram_id == telegram_id,
                ScamReport.status == "approved"
            )
        )

        return result.scalars().all()


async def get_report(report_id: int):
    async with Session() as session:
        result = await session.execute(
            select(ScamReport).where(
                ScamReport.id == report_id
            )
        )

        return result.scalar_one_or_none()


async def get_pending_reports():
    async with Session() as session:
        result = await session.execute(
            select(ScamReport)
            .where(
                ScamReport.status == "pending"
            )
            .order_by(
                ScamReport.created_at.desc()
            )
        )

        return result.scalars().all()


async def get_user_reports(author_id: int):
    async with Session() as session:
        result = await session.execute(
            select(ScamReport)
            .where(
                ScamReport.author_id == author_id
            )
            .order_by(
                ScamReport.created_at.desc()
            )
        )

        return result.scalars().all()


async def get_approved_reports(limit: int = 20):
    async with Session() as session:
        result = await session.execute(
            select(ScamReport)
            .where(
                ScamReport.status == "approved"
            )
            .order_by(
                ScamReport.created_at.desc()
            )
            .limit(limit)
        )

        return result.scalars().all()


async def approve_report(report_id: int):
    async with Session() as session:
        report = await session.get(
            ScamReport,
            report_id
        )

        if report is None:
            return False

        report.status = "approved"
        report.reject_reason = None

        await session.commit()

        return True


async def reject_report(
    report_id: int,
    reason: str | None = None,
):
    async with Session() as session:
        report = await session.get(
            ScamReport,
            report_id
        )

        if report is None:
            return False

        report.status = "rejected"
        report.reject_reason = reason

        await session.commit()

        return True


def get_proofs(report: ScamReport) -> list[str]:
    if not report.proofs:
        return []

    try:
        return json.loads(report.proofs)

    except (json.JSONDecodeError, TypeError):
        return []


async def get_user_report_stats(author_id: int):
    async with Session() as session:
        total_result = await session.execute(
            select(func.count(ScamReport.id)).where(
                ScamReport.author_id == author_id
            )
        )

        approved_result = await session.execute(
            select(func.count(ScamReport.id)).where(
                ScamReport.author_id == author_id,
                ScamReport.status == "approved"
            )
        )

        pending_result = await session.execute(
            select(func.count(ScamReport.id)).where(
                ScamReport.author_id == author_id,
                ScamReport.status == "pending"
            )
        )

        rejected_result = await session.execute(
            select(func.count(ScamReport.id)).where(
                ScamReport.author_id == author_id,
                ScamReport.status == "rejected"
            )
        )

        return {
            "total": total_result.scalar() or 0,
            "approved": approved_result.scalar() or 0,
            "pending": pending_result.scalar() or 0,
            "rejected": rejected_result.scalar() or 0,
        }


async def get_global_stats():
    async with Session() as session:
        total_result = await session.execute(
            select(func.count(ScamReport.id))
        )

        approved_result = await session.execute(
            select(func.count(ScamReport.id)).where(
                ScamReport.status == "approved"
            )
        )

        pending_result = await session.execute(
            select(func.count(ScamReport.id)).where(
                ScamReport.status == "pending"
            )
        )

        rejected_result = await session.execute(
            select(func.count(ScamReport.id)).where(
                ScamReport.status == "rejected"
            )
        )

        return {
            "total": total_result.scalar() or 0,
            "approved": approved_result.scalar() or 0,
            "pending": pending_result.scalar() or 0,
            "rejected": rejected_result.scalar() or 0,
        }


async def has_pending_duplicate(
    author_id: int,
    username: str,
):
    async with Session() as session:
        result = await session.execute(
            select(ScamReport).where(
                ScamReport.author_id == author_id,
                ScamReport.username.ilike(username),
                ScamReport.status == "pending"
            )
        )

        return result.scalar_one_or_none()


async def can_submit_report(
    author_id: int,
    cooldown_minutes: int = 2,
):
    async with Session() as session:
        result = await session.execute(
            select(ScamReport)
            .where(
                ScamReport.author_id == author_id
            )
            .order_by(
                ScamReport.created_at.desc()
            )
            .limit(1)
        )

        last_report = result.scalar_one_or_none()

        if last_report is None:
            return True, 0

        if last_report.created_at is None:
            return True, 0

        now = datetime.utcnow()

        available_at = (
            last_report.created_at
            + timedelta(minutes=cooldown_minutes)
        )

        if now >= available_at:
            return True, 0

        seconds_left = int(
            (available_at - now).total_seconds()
        )

        return False, max(seconds_left, 1)