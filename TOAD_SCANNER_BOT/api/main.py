import base64
import hashlib
import hmac
import json
import secrets
import time

from collections import defaultdict, deque

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

from sqlalchemy import (
    select,
    func,
)

from config import ADMIN_SECRET

from database.database import Session

from database.models import (
    ScamEntity,
    ScamReport,
    EntityIdentifier,
)

from database.entities import (
    normalize_username,
    make_hash,
)

from database.functions import (
    get_proofs,
)


# =========================================================
# НАСТРОЙКИ
# =========================================================

SESSION_COOKIE_NAME = "toad_admin_session"

# Админская сессия действует 12 часов
SESSION_LIFETIME_SECONDS = 60 * 60 * 12


# =========================================================
# RATE LIMIT
# =========================================================

# Пока храним лимиты в памяти.
# После перезапуска API они сбрасываются.
RATE_LIMIT_STORAGE = defaultdict(deque)


def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
):
    """
    Проверяет количество запросов
    за заданный промежуток времени.
    """

    now = time.time()

    bucket = RATE_LIMIT_STORAGE[key]

    # Удаляем старые запросы
    while (
        bucket
        and bucket[0]
        <= now - window_seconds
    ):
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                "Слишком много запросов. "
                "Попробуйте позже."
            ),
        )

    bucket.append(now)


def clear_rate_limit(
    key: str,
):
    """
    Очищает счётчик.
    Например после успешного входа.
    """

    RATE_LIMIT_STORAGE.pop(
        key,
        None,
    )


def get_client_ip(
    request: Request,
) -> str:

    if request.client:
        return request.client.host

    return "unknown"


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="TOAD Scanner API",
    description="Backend API for TOAD Scanner",
    version="2.0.0",
)


# =========================================================
# STATIC FILES
# =========================================================

app.mount(
    "/web",
    StaticFiles(
        directory="web"
    ),
    name="web",
)


# =========================================================
# СТРАНИЦЫ
# =========================================================

@app.get(
    "/scanner",
    include_in_schema=False,
)
async def scanner_page():

    return FileResponse(
        "web/index.html"
    )


@app.get(
    "/admin",
    include_in_schema=False,
)
async def admin_page():

    return FileResponse(
        "web/admin.html"
    )


# =========================================================
# PYDANTIC MODELS
# =========================================================

class AdminLoginRequest(BaseModel):
    secret: str


# =========================================================
# БЕЗОПАСНОЕ СРАВНЕНИЕ СЕКРЕТОВ
# =========================================================

def secure_compare(
    value1: str,
    value2: str,
) -> bool:
    """
    Сравнение секретов через UTF-8 bytes.

    Поэтому работает даже если ADMIN_SECRET
    содержит кириллицу.
    """

    return secrets.compare_digest(
        value1.strip().encode("utf-8"),
        value2.strip().encode("utf-8"),
    )


# =========================================================
# ADMIN SESSION TOKEN
# =========================================================

def create_session_token() -> str:

    payload = {
        "admin": True,

        "exp": int(
            time.time()
            + SESSION_LIFETIME_SECONDS
        ),
    }

    payload_json = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")

    payload_encoded = (
        base64.urlsafe_b64encode(
            payload_json
        )
        .decode("utf-8")
        .rstrip("=")
    )

    signature = hmac.new(
        ADMIN_SECRET
        .strip()
        .encode("utf-8"),

        payload_encoded
        .encode("utf-8"),

        hashlib.sha256,
    ).hexdigest()

    return (
        f"{payload_encoded}.{signature}"
    )


# =========================================================
# ПРОВЕРКА ADMIN SESSION TOKEN
# =========================================================

def verify_session_token(
    token: str | None,
) -> bool:

    if not token:
        return False

    try:

        payload_encoded, signature = (
            token.split(
                ".",
                1,
            )
        )

    except ValueError:
        return False

    expected_signature = hmac.new(
        ADMIN_SECRET
        .strip()
        .encode("utf-8"),

        payload_encoded
        .encode("utf-8"),

        hashlib.sha256,
    ).hexdigest()

    if not secrets.compare_digest(
        signature,
        expected_signature,
    ):
        return False

    try:

        padding = (
            "="
            * (-len(payload_encoded) % 4)
        )

        payload_bytes = (
            base64.urlsafe_b64decode(
                payload_encoded
                + padding
            )
        )

        payload = json.loads(
            payload_bytes.decode(
                "utf-8"
            )
        )

    except Exception:
        return False

    if payload.get("admin") is not True:
        return False

    expiration = payload.get(
        "exp"
    )

    if not isinstance(
        expiration,
        int,
    ):
        return False

    if expiration <= int(
        time.time()
    ):
        return False

    return True


# =========================================================
# REQUIRE ADMIN SESSION
# =========================================================

def require_admin_session(
    request: Request,
):

    token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    if not verify_session_token(
        token
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Admin authorization required"
            ),
        )


# =========================================================
# X-ADMIN-KEY
# =========================================================

def verify_admin_key(
    x_admin_key: str | None,
):

    if not x_admin_key:

        raise HTTPException(
            status_code=401,
            detail="Admin key required",
        )

    if not secure_compare(
        x_admin_key,
        ADMIN_SECRET,
    ):

        raise HTTPException(
            status_code=403,
            detail="Invalid admin key",
        )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "service":
            "TOAD Scanner API",

        "version":
            "2.0.0",

        "status":
            "online",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get(
    "/api/health"
)
async def health():

    return {
        "status": "ok",

        "service":
            "TOAD Scanner API",
    }


# =========================================================
# PUBLIC SEARCH
# =========================================================

@app.get(
    "/api/search/{username}"
)
async def search_username(
    username: str,
    request: Request,
):

    # -----------------------------------------
    # RATE LIMIT
    # 60 поисковых запросов в минуту с одного IP
    # -----------------------------------------

    client_ip = get_client_ip(
        request
    )

    check_rate_limit(
        key=f"search:{client_ip}",
        limit=60,
        window_seconds=60,
    )

    # -----------------------------------------
    # USERNAME
    # -----------------------------------------

    normalized = normalize_username(
        username
    )

    if not normalized:

        raise HTTPException(
            status_code=400,
            detail="Username не указан",
        )

    # Telegram username максимум 32 символа
    if len(normalized) > 32:

        raise HTTPException(
            status_code=400,
            detail="Некорректный username",
        )

    username_hash = make_hash(
        normalized
    )

    # -----------------------------------------
    # DATABASE
    # -----------------------------------------

    async with Session() as session:

        result = await session.execute(
            select(
                EntityIdentifier
            ).where(

                EntityIdentifier.identifier_type
                == "telegram_username",

                EntityIdentifier.value_hash
                == username_hash,
            )
        )

        identifier = (
            result.scalar_one_or_none()
        )

        if identifier is None:

            raise HTTPException(
                status_code=404,
                detail="Досье не найдено",
            )

        entity = await session.get(
            ScamEntity,
            identifier.entity_id,
        )

        if entity is None:

            raise HTTPException(
                status_code=404,
                detail="Досье не найдено",
            )

        reports_result = await session.execute(
            select(
                func.count(
                    ScamReport.id
                )
            ).where(

                ScamReport.entity_id
                == entity.id,

                ScamReport.status
                == "approved",
            )
        )

        reports_count = (
            reports_result.scalar()
            or 0
        )

        return {
            "found": True,

            "entity_id":
                entity.id,

            "username": (
                f"@{entity.primary_username}"
                if entity.primary_username
                else None
            ),

            "display_name":
                entity.display_name,

            "risk_score":
                entity.risk_score,

            "reports_count":
                reports_count,

            "status":
                entity.status,
        }


# =========================================================
# PUBLIC ENTITY DETAILS — SAFE
# =========================================================

@app.get(
    "/api/entities/{entity_id}"
)
async def entity_details(
    entity_id: int,
    request: Request,
):

    # -----------------------------------------
    # RATE LIMIT
    # -----------------------------------------

    client_ip = get_client_ip(
        request
    )

    check_rate_limit(
        key=f"entity:{client_ip}",
        limit=60,
        window_seconds=60,
    )

    # -----------------------------------------
    # ID VALIDATION
    # -----------------------------------------

    if entity_id <= 0:

        raise HTTPException(
            status_code=400,
            detail="Некорректный ID досье",
        )

    # -----------------------------------------
    # DATABASE
    # -----------------------------------------

    async with Session() as session:

        entity = await session.get(
            ScamEntity,
            entity_id,
        )

        if entity is None:

            raise HTTPException(
                status_code=404,
                detail="Досье не найдено",
            )

        reports_result = await session.execute(
            select(
                ScamReport
            )
            .where(

                ScamReport.entity_id
                == entity.id,

                ScamReport.status
                == "approved",
            )
            .order_by(
                ScamReport.created_at.desc()
            )
        )

        reports = (
            reports_result
            .scalars()
            .all()
        )

        identifiers_result = (
            await session.execute(
                select(
                    EntityIdentifier
                ).where(

                    EntityIdentifier.entity_id
                    == entity.id
                )
            )
        )

        identifiers = (
            identifiers_result
            .scalars()
            .all()
        )

        # -----------------------------------------
        # БЕЗОПАСНЫЕ ИДЕНТИФИКАТОРЫ
        # -----------------------------------------

        safe_identifiers = []

        for identifier in identifiers:

            if (
                identifier.identifier_type
                in {
                    "telegram_username",
                    "telegram_id",
                }
            ):

                safe_identifiers.append(
                    {
                        "type":
                            identifier.identifier_type,

                        "value":
                            identifier.value_masked,

                        "label":
                            identifier.label,
                    }
                )

        # -----------------------------------------
        # БЕЗОПАСНЫЕ ЖАЛОБЫ
        # -----------------------------------------

        safe_reports = []

        for report in reports:

            description = (
                report.description
                or ""
            )

            safe_reports.append(
                {
                    "id":
                        report.id,

                    "amount":
                        report.amount,

                    # Максимум 1000 символов
                    "description":
                        description[:1000],

                    "created_at": (
                        report.created_at
                        .isoformat()

                        if report.created_at
                        else None
                    ),
                }
            )

        # -----------------------------------------
        # RESPONSE
        # -----------------------------------------

        return {
            "entity_id":
                entity.id,

            "username": (
                f"@{entity.primary_username}"
                if entity.primary_username
                else None
            ),

            "display_name":
                entity.display_name,

            "risk_score":
                entity.risk_score,

            "status":
                entity.status,

            "reports_count":
                len(reports),

            "identifiers":
                safe_identifiers,

            "reports":
                safe_reports,
        }


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.post(
    "/api/admin/login"
)
async def admin_login(
    data: AdminLoginRequest,
    response: Response,
    request: Request,
):

    # -----------------------------------------
    # IP
    # -----------------------------------------

    client_ip = get_client_ip(
        request
    )

    rate_key = (
        f"admin-login:{client_ip}"
    )

    # -----------------------------------------
    # RATE LIMIT
    #
    # Максимум 5 попыток за 5 минут
    # -----------------------------------------

    check_rate_limit(
        key=rate_key,
        limit=5,
        window_seconds=300,
    )

    # -----------------------------------------
    # SECRET LENGTH
    # -----------------------------------------

    if len(data.secret) > 512:

        raise HTTPException(
            status_code=400,
            detail="Invalid request",
        )

    # -----------------------------------------
    # SECRET CHECK
    # -----------------------------------------

    if not secure_compare(
        data.secret,
        ADMIN_SECRET,
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Неверный административный ключ"
            ),
        )

    # Успешный вход:
    # сбрасываем счётчик попыток этого IP.
    clear_rate_limit(
        rate_key
    )

    # -----------------------------------------
    # SESSION
    # -----------------------------------------

    token = create_session_token()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,

        value=token,

        # JavaScript не может читать cookie
        httponly=True,

        # localhost работает по HTTP.
        # После перехода на HTTPS:
        # secure=True
        secure=False,

        # Защита от CSRF для большинства сценариев
        samesite="strict",

        max_age=(
            SESSION_LIFETIME_SECONDS
        ),

        path="/",
    )

    return {
        "success": True,

        "message":
            "Admin session created",
    }


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.post(
    "/api/admin/logout"
)
async def admin_logout(
    response: Response,
):

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )

    return {
        "success": True,
    }


# =========================================================
# ADMIN SESSION CHECK
# =========================================================

@app.get(
    "/api/admin/session"
)
async def admin_session(
    request: Request,
):

    require_admin_session(
        request
    )

    return {
        "authenticated":
            True,

        "role":
            "admin",
    }


# =========================================================
# ADMIN PENDING REPORTS
# =========================================================

@app.get(
    "/api/admin/reports/pending"
)
async def admin_pending_reports(
    request: Request,
):

    require_admin_session(
        request
    )

    async with Session() as session:

        result = await session.execute(
            select(
                ScamReport
            )
            .where(

                ScamReport.status
                == "pending"
            )
            .order_by(
                ScamReport.created_at.desc()
            )
        )

        reports = (
            result
            .scalars()
            .all()
        )

        result_data = []

        for report in reports:

            proofs = get_proofs(
                report
            )

            result_data.append(
                {
                    "id":
                        report.id,

                    "username":
                        report.username,

                    "telegram_id":
                        report.telegram_id,

                    "full_name":
                        report.full_name,

                    "amount":
                        report.amount,

                    "description":
                        report.description,

                    "proofs_count":
                        len(proofs),

                    "status":
                        report.status,

                    "created_at": (
                        report.created_at
                        .isoformat()

                        if report.created_at
                        else None
                    ),
                }
            )

        return {
            "count":
                len(result_data),

            "reports":
                result_data,
        }


# =========================================================
# ADMIN KEY CHECK
# =========================================================

@app.get(
    "/api/admin/check"
)
async def admin_check(
    x_admin_key: str | None = Header(
        default=None,
        alias="X-Admin-Key",
    ),
):

    verify_admin_key(
        x_admin_key
    )

    return {
        "admin":
            True,

        "access":
            "granted",
    }


# =========================================================
# ADMIN MODERATION ROUTER
# =========================================================

# ВАЖНО:
# импорт оставляем в самом низу,
# потому что admin_actions использует
# require_admin_session из этого файла.

from api.admin_actions import (
    router as admin_actions_router,
)

app.include_router(
    admin_actions_router
)