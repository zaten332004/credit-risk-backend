from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Common / Auth
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str | None = None
    db_ok: bool | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: str | None = None


class User(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool = True
    is_admin: bool = False


class UserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    password: str
    is_admin: bool = False


class UserRead(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


class CustomerBase(BaseModel):
    name: str
    age: int
    income: float
    credit_score: Optional[float] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[float] = None
    credit_score: Optional[float] = None


class CustomerRead(CustomerBase):
    id: int
    risk_level: Optional[str] = None
    last_updated: datetime


class CustomerHistoryItem(BaseModel):
    timestamp: datetime
    changed_by: str
    changes: Dict[str, Any]


class CustomerSearchBody(BaseModel):
    filters: Dict[str, Any]
    page: int = 1
    limit: int = 20


class PaginatedCustomers(BaseModel):
    items: List[CustomerRead]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Risk / Scoring
# ---------------------------------------------------------------------------


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


class RiskScoreDetail(BaseModel):
    pd: float
    lgd: float
    ead: float
    el: float
    risk_score: float
    confidence: float
    model_version: str


class RiskAnalyzeBody(BaseModel):
    customer_data: Dict[str, Any]


class RiskBatchBody(BaseModel):
    records: List[Dict[str, Any]]


class RiskBatchResult(BaseModel):
    results: List[RiskScoreDetail]
    summary: Dict[str, Any]


class RiskSimulationBody(BaseModel):
    base_data: Dict[str, Any]
    scenarios: List[Dict[str, Any]]


class RiskSimulationResult(BaseModel):
    scenario_results: List[Dict[str, Any]]


class RiskModelVersion(BaseModel):
    version: str
    accuracy: float
    deployed_at: datetime


class RiskExplainResponse(BaseModel):
    feature_importance: Dict[str, float]


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


class PortfolioKPIResponse(BaseModel):
    total_exposure: float
    avg_pd: float
    expected_loss: float
    npl_ratio: float
    var_99: float


class RiskDistributionResponse(BaseModel):
    buckets: Dict[str, float]
    chart_data: List[Dict[str, Any]]


class ConcentrationItem(BaseModel):
    name: str
    exposure: float


class ConcentrationResponse(BaseModel):
    items: List[ConcentrationItem]


class PortfolioTrendPoint(BaseModel):
    timestamp: datetime
    value: float


class PortfolioTrendResponse(BaseModel):
    metric: str
    points: List[PortfolioTrendPoint]


class PortfolioCompareBody(BaseModel):
    portfolio_a: Dict[str, Any]
    portfolio_b: Dict[str, Any]


class PortfolioCompareResponse(BaseModel):
    diff_metrics: Dict[str, Any]


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    answer: str
    extracted_metrics: Optional[Dict[str, Any]] = None
    sources: Optional[List[str]] = None


class ChatSessionSummary(BaseModel):
    session_id: str
    started_at: datetime
    last_activity_at: datetime


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class AlertRead(BaseModel):
    id: int
    type: str
    status: str
    message: str
    created_at: datetime


class AlertSubscriptionCreate(BaseModel):
    user_id: int
    types: List[str]
    threshold: float


class AlertSubscriptionRead(BaseModel):
    subscription_id: int


class AlertResolveBody(BaseModel):
    reason: str


# ---------------------------------------------------------------------------
# Admin / System
# ---------------------------------------------------------------------------


class AuditLogRead(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    timestamp: datetime
    metadata: Dict[str, Any]


class ExportRequestBody(BaseModel):
    type: str
    filters: Dict[str, Any]


class ExportResponse(BaseModel):
    file_url: str


# ---------------------------------------------------------------------------
# File / Ingestion
# ---------------------------------------------------------------------------


class UploadJobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    progress: float
    result_url: Optional[str] = None