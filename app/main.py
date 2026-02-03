from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.endpoints import router as api_router
from app.api.routers.registration import router as registration_router
from app.api.routers.loan_products import router as loan_products_router
from app.api.routers.ai_chat import router as ai_chat_router
from app.api.routers.powerbi import router as powerbi_router
# from app.api.routers import upload, analysis  # TODO: Fix imports
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(registration_router, prefix=settings.API_V1_PREFIX)
app.include_router(loan_products_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(powerbi_router, prefix=settings.API_V1_PREFIX)
# app.include_router(upload.router, prefix=settings.API_V1_PREFIX)  # TODO: Fix imports
# app.include_router(analysis.router, prefix=settings.API_V1_PREFIX)  # TODO: Fix imports


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:

    return RedirectResponse(url="/docs")