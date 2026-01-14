from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# Trong demo này, models đóng vai trò domain models (có thể map sang ORM sau này).


class Customer(BaseModel):
    id: int
    name: str
    age: int
    income: float
    credit_score: Optional[float] = None
    risk_level: Optional[str] = None
    last_updated: datetime


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
