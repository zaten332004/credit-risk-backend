from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Connection string should be provided via .env (DATABASE_URL).
# Example:
# mssql+pyodbc://sa:YourPassword@DESKTOP-7EPLMS3\\SQLEXPRESS/CreditRiskDB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
SQLALCHEMY_DATABASE_URL = (settings.DATABASE_URL or "").strip()
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured. Please set DATABASE_URL in .env")

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

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

