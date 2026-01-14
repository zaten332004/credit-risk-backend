from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class CustomerDB(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    segment = Column(String(50), nullable=True)
    industry_code = Column(String(50), nullable=True)
    region = Column(String(100), nullable=True)
    income = Column(Float, nullable=True)

    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    loans = relationship("LoanDB", back_populates="customer")
    risk_scores = relationship("RiskScoreDB", back_populates="customer")


class LoanDB(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    product_type = Column(String(50), nullable=True)
    origination_date = Column(Date, nullable=True)
    maturity_date = Column(Date, nullable=True)
    currency = Column(String(10), nullable=True)
    limit_amount = Column(Float, nullable=True)
    outstanding_amount = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)
    status = Column(String(20), default="active")

    customer = relationship("CustomerDB", back_populates="loans")


class RiskScoreDB(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    as_of_date = Column(Date, nullable=False, default=datetime.utcnow)

    model_version = Column(String(50), nullable=False)
    pd = Column(Float, nullable=False)
    lgd = Column(Float, nullable=False)
    ead = Column(Float, nullable=False)
    expected_loss = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_grade = Column(String(20), nullable=True)
    confidence = Column(Float, nullable=True)

    run_by = Column(String(100), nullable=True)

    customer = relationship("CustomerDB", back_populates="risk_scores")


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="analyst")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertDB(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)

    type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="open")

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_reason = Column(Text, nullable=True)

