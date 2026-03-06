import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as api_router
from app.api.routers.registration import router as registration_router
from app.api.routers.loan_products import router as loan_products_router
from app.api.routers.ai_chat import router as ai_chat_router
from app.api.routers.powerbi import router as powerbi_router
# from app.api.routers import upload, analysis  # TODO: Fix imports
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

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
