from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.endpoints import router as api_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    # Khi mở backend trên bất kỳ browser nào tại đường dẫn gốc,
    # tự động chuyển sang trang tài liệu API (Swagger UI).
    return RedirectResponse(url="/docs")