
import logging
import re
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.models import init_db
from app.models.base import engine
from app.rate_limiter import limiter
from app.controllers import (
    auth_router,
    budget_router,
    income_router,
    expense_router,
    report_router,
)
from app.middleware.error_handler import (
    rate_limit_exception_handler,
    validation_exception_handler,
    value_error_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    general_exception_handler,
    http_exception_handler,
)

settings = get_settings()
logger = logging.getLogger(__name__)
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _normalize_request_id(header_value: str | None) -> str:
    """Return a safe request ID value for logs/headers."""
    candidate = (header_value or "").strip()
    if _REQUEST_ID_RE.match(candidate):
        return candidate
    return str(uuid4())


def _conditional_limit(limit_value: str):
    """Apply slowapi limit only when rate limiting is enabled."""
    def _decorator(func):
        if not settings.RATE_LIMIT_ENABLED:
            return func
        return limiter.limit(limit_value)(func)

    return _decorator


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize shared resources at app startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Cross-Platform Budgeting Application API",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a request ID to each request for traceability across logs/errors."""
    request_id = _normalize_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id

    logger.info(f"[request_id={request_id}] Incoming {request.method} {request.url.path}")
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        f"[request_id={request_id}] Completed {request.method} {request.url.path} "
        f"status={response.status_code}"
    )
    return response

# ---------------------------------------------------------------------------
# Rate limiting — only enabled when RATE_LIMIT_ENABLED=true (default).
# Set RATE_LIMIT_ENABLED=false in .env.test to disable for integration tests.
# SlowAPIMiddleware MUST be omitted when disabled — it always reads
# request.state.view_rate_limit which is only set by the real limiter.
# ---------------------------------------------------------------------------
if settings.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(budget_router, prefix=settings.API_V1_PREFIX)
app.include_router(income_router, prefix=settings.API_V1_PREFIX)
app.include_router(expense_router, prefix=settings.API_V1_PREFIX)
app.include_router(report_router, prefix=settings.API_V1_PREFIX)




if settings.TEST_ENDPOINTS_ENABLED:
    # Test-only endpoint for pure rate-limit validation.
    @app.get("/ratelimit-test", tags=["Test"])
    @_conditional_limit("3/minute")
    async def ratelimit_test(request: Request):
        return {"message": "ok"}

# Health check endpoint (must be after all routers and test endpoints)
@app.get("/health", tags=["Health"])
@limiter.exempt
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/ready", tags=["Health"])
@limiter.exempt
def readiness_check(request: Request):
    """Readiness check endpoint with DB connectivity validation."""
    request_id = getattr(getattr(request, "state", None), "request_id", "unknown")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error(f"[request_id={request_id}] Readiness DB check failed: {str(exc)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "database": "unreachable",
            },
        )

    return {
        "status": "ready",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "ok",
    }

# Root endpoint (must be after all routers and test endpoints)
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Budgeting Application API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }