from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Connection string cho SQL Server CreditRiskDB
# Server: DESKTOP-7EPLMS3\SQLEXPRESS
# User: sa
# Password: 12345
# Database: CreditRiskDB
#
SQLALCHEMY_DATABASE_URL = (
    "mssql+pyodbc://sa:12345@DESKTOP-7EPLMS3\\SQLEXPRESS/CreditRiskDB"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

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

