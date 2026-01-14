from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class RiskRequest(BaseModel):
    # Minimal fields for a baseline credit-risk scoring demo
    income: float = Field(..., ge=0, description="Monthly income")
    debt: float = Field(..., ge=0, description="Total monthly debt payments")
    age: int = Field(..., ge=18, le=120)
    credit_history_months: int = Field(..., ge=0)


class RiskResponse(BaseModel):
    risk_score: float = Field(..., ge=0, le=1, description="0 (low risk) .. 1 (high risk)")
    risk_label: str = Field(..., description="low|medium|high")
    explanation: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str
