import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as api_router
from app.api.routers.registration import router as registration_router
from app.api.routers.loan_products import router as loan_products_router
from app.api.routers.ai_chat import router as ai_chat_router
from app.api.routers.powerbi import router as powerbi_router
# from app.api.routers import upload, analysis  # TODO: Fix imports
from app.core.client_safe_errors import public_message_for_exception
from app.core.config import settings

logger = logging.getLogger(__name__)


def _configure_server_logging() -> None:
    """
    Tắt access log dạng: INFO: 1.2.3.4 - "GET /api/v1/... HTTP/1.1"
    (uvicorn.access). Bật lại khi cần debug: UVICORN_ACCESS_LOG=1
    """
    if os.getenv("UVICORN_ACCESS_LOG", "").strip().lower() in ("1", "true", "yes", "on"):
        return
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.audit_service import cleanup_expired_audit_logs
    from app.services.services import cleanup_expired_upload_jobs, cleanup_invalid_upload_jobs

    _configure_server_logging()

    tasks: list[asyncio.Task[None]] = []

    try:
        n_inv = cleanup_invalid_upload_jobs()
        if n_inv:
            logger.info("Startup: removed %s invalid/orphan upload job file(s)", n_inv)
        n_exp = cleanup_expired_upload_jobs()
        if n_exp:
            logger.info("Startup: removed %s expired upload job file(s)", n_exp)
    except Exception:
        logger.exception("Upload job storage cleanup at startup failed")

    interval_min = int(getattr(settings, "UPLOAD_JOBS_CLEANUP_INTERVAL_MINUTES", 60) or 60)
    if interval_min > 0:
        interval_sec = max(1, interval_min) * 60

        async def _upload_jobs_cleanup_loop() -> None:
            while True:
                try:
                    n_exp = cleanup_expired_upload_jobs()
                    if n_exp:
                        logger.info("Removed %s expired upload job file(s)", n_exp)
                    n_inv = cleanup_invalid_upload_jobs()
                    if n_inv:
                        logger.info("Removed %s invalid/orphan upload job file(s)", n_inv)
                except Exception:
                    logger.exception("Upload job storage cleanup failed")
                await asyncio.sleep(interval_sec)

        tasks.append(asyncio.create_task(_upload_jobs_cleanup_loop()))

    audit_days = float(getattr(settings, "AUDIT_LOG_RETENTION_DAYS", 0) or 0)
    if audit_days > 0:
        audit_interval_min = max(1, int(getattr(settings, "AUDIT_LOG_CLEANUP_INTERVAL_MINUTES", 60) or 60))
        audit_interval_sec = audit_interval_min * 60

        async def _audit_log_cleanup_loop() -> None:
            while True:
                try:
                    n = cleanup_expired_audit_logs()
                    if n:
                        logger.info("Removed %s audit log row(s) past retention", n)
                except Exception:
                    logger.exception("Audit log retention cleanup failed")
                await asyncio.sleep(audit_interval_sec)

        tasks.append(asyncio.create_task(_audit_log_cleanup_loop()))

    yield

    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

_configure_server_logging()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Lỗi chưa được bắt cụ thể: log stack server, JSON detail an toàn cho client (không lộ SQL)."""
    logger.exception("Unhandled error %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": public_message_for_exception(exc)},
    )


# CORS for frontend apps (React/Vite/etc.)
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
origins_raw = (os.getenv("CORS_ALLOW_ORIGINS") or settings.cors_allow_origins or "").strip()
allow_origins = [o.strip() for o in origins_raw.split(",") if o.strip()] if origins_raw else default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(registration_router, prefix=settings.API_V1_PREFIX)
app.include_router(loan_products_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(powerbi_router, prefix=settings.API_V1_PREFIX)
# app.include_router(upload.router, prefix=settings.API_V1_PREFIX)  # TODO: Fix imports
# app.include_router(analysis.router, prefix=settings.API_V1_PREFIX)  # TODO: Fix imports

# UI đơn giản để test AI Chat (mở /static/ai-chat-test.html hoặc /test-chat)
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/test-chat", include_in_schema=False)
async def test_chat_redirect() -> RedirectResponse:
    """Chuyển tới trang test AI Chat."""
    return RedirectResponse(url="/static/ai-chat-test.html")
