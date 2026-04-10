"""
ASGI entry shim at repo root.

Railpack / Railway expect FastAPI at `main:app` (uvicorn main:app).
The real application factory and routes live in `app.main`.
"""

from app.main import app

__all__ = ["app"]
