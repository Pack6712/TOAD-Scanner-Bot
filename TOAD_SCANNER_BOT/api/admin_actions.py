from pydantic import BaseModel

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)

from database.functions import (
    get_report,
    approve_report,
    reject_report,
)

from database.entities import (
    attach_report_to_entity,
)


router = APIRouter(
    prefix="/api/admin/reports",
    tags=["Admin moderation"],
)


class RejectRequest(BaseModel):
    reason: str


def check_admin(request: Request):
    from api.main import require_admin_session

    require_admin_session(request)


@router.post("/{report_id}/approve")
async def approve_web_report(
    report_id: int,
    request: Request,
):
    check_admin(request)

    report = await get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Жалоба не найдена",
        )

    if report.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Жалоба уже обработана",
        )

    success = await approve_report(report_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Не удалось одобрить жалобу",
        )

    entity = None

    try:
        entity = await attach_report_to_entity(
            report_id
        )

    except Exception as error:
        print(
            "Ошибка создания досье:",
            repr(error)
        )

    return {
        "success": True,
        "report_id": report_id,
        "status": "approved",
        "entity_id": (
            entity.id
            if entity
            else None
        ),
        "risk_score": (
            entity.risk_score
            if entity
            else None
        ),
    }


@router.post("/{report_id}/reject")
async def reject_web_report(
    report_id: int,
    data: RejectRequest,
    request: Request,
):
    check_admin(request)

    report = await get_report(report_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Жалоба не найдена",
        )

    if report.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Жалоба уже обработана",
        )

    reason = data.reason.strip()

    if len(reason) < 3:
        raise HTTPException(
            status_code=400,
            detail="Причина слишком короткая",
        )

    if len(reason) > 500:
        raise HTTPException(
            status_code=400,
            detail="Максимум 500 символов",
        )

    success = await reject_report(
        report_id,
        reason,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Не удалось отклонить жалобу",
        )

    return {
        "success": True,
        "report_id": report_id,
        "status": "rejected",
        "reason": reason,
    }