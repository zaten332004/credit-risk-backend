from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# Trong demo này, models đóng vai trò domain models (có thể map sang ORM sau này).


class Customer(BaseModel):
    customer_id: int
    full_name: str
    age: int
    monthly_income: float
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    credit_score: Optional[float] = None
    employment_status: Optional[str] = None
    loan_type: Optional[str] = None
    requested_loan_amount: Optional[float] = None
    requested_term_months: Optional[int] = None
    annual_interest_rate: Optional[float] = None
    risk_level: Optional[str] = None
    application_status: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    employments: List[Dict[str, Any]] = []


class RiskModelInfo(BaseModel):
    version: str
    accuracy: float
    deployed_at: datetime


class ChatSession(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    started_at: datetime
    last_activity_at: datetime
    messages: List[Dict[str, Any]] = []


class Alert(BaseModel):
    id: int
    type: str
    status: str
    message: str
    created_at: datetime


class UploadJob(BaseModel):
    job_id: str
    status: str
    progress: float
    result_url: Optional[str] = None
