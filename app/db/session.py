from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Ví dụ connection string cho SQL Server.
# Bạn chỉnh lại USER, PASSWORD, SERVER, DBNAME theo môi trường thực tế.
#
# Format chung (pyodbc):
#   mssql+pyodbc://USER:PASSWORD@SERVER/DBNAME?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
#
SQLALCHEMY_DATABASE_URL = (
    "mssql+pyodbc://sa:YourStrong!Passw0rd@localhost\\SQLEXPRESS/CreditRiskDB"
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

