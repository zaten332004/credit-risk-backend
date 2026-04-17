import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Connection string should be provided via .env (DATABASE_URL).
# Example:
# mysql+pymysql://root:your_password@localhost:3306/CreditRiskDB?charset=utf8mb4
#
# Railway / many hosts expose mysql:// without a driver; SQLAlchemy maps that to MySQLdb,
# which we do not install. Force PyMySQL (see requirements.txt).
def _normalize_mysql_url(url: str) -> str:
    u = url.strip()
    if u.startswith("mysql://"):
        return "mysql+pymysql://" + u[len("mysql://") :]
    return u


SQLALCHEMY_DATABASE_URL = _normalize_mysql_url(settings.DATABASE_URL or "")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured. Please set DATABASE_URL in .env")

engine_kwargs = {"pool_pre_ping": True}
if SQLALCHEMY_DATABASE_URL.startswith("mysql"):
    engine_kwargs["pool_recycle"] = 3600
    # Production-safe defaults; can be overridden via env.
    # These settings reduce QueuePool timeout spikes under concurrent AI chat traffic.
    pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "40"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    engine_kwargs.update(
        {
            "pool_size": max(5, pool_size),
            "max_overflow": max(0, max_overflow),
            "pool_timeout": max(5, pool_timeout),
            "pool_use_lifo": True,
        }
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency cho FastAPI: mỗi request dùng một DB session.
    Ví dụ sử dụng:

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.db.session import get_db

        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

