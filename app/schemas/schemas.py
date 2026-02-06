from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


# ============================================================================
# Common / Auth
# ============================================================================


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str | None = None
    db_ok: bool | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str | None = None
    role: str  # admin, manager, analyst, viewer


class TokenData(BaseModel):
    sub: str | None = None
    role: str | None = None


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


# ============================================================================
# Role
# ============================================================================


class RoleRead(BaseModel):
    role_id: int
    role_name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# User
# ============================================================================


class User(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool = True
    is_admin: bool = False
    role: str | None = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role_id: int


class UserRead(BaseModel):
    user_id: int
    username: str
    email: str
    role_id: int | None = None
    full_name: str | None = None
    user_type: str | None = None
    status: str | None = None
    is_email_verified: bool | None = None
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# ============================================================================
# User Registration
# ============================================================================
class UserRegistrationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    registration_type: str = Field(..., description="'analyst' or 'manager'")


class UserRegistrationResponse(BaseModel):
    registration_id: int
    username: str
    email: str
    registration_type: str
    status: str  # pending, approved, rejected, verified
    is_email_verified: bool
    verification_token: str | None = None  # Token for email verification
    verification_link: str | None = None  # Full URL for verification
    created_at: datetime
    message: str = "Registration successful. Please check your email to verify."

    class Config:
        from_attributes = True


class UserRegistrationApprovalRequest(BaseModel):
    registration_id: int
    action: str = Field(..., description="'approve' or 'reject'")
    rejection_reason: str | None = Field(None, description="Required if action is 'reject'")


class UserRegistrationRead(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str | None = None
    phone: str | None = None
    user_type: str | None = None  # 'analyst' or 'manager'
    status: str  # pending, approved, rejected
    is_email_verified: bool
    created_at: datetime
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    class Config:
        from_attributes = True

# ============================================================================
# Customer & Employment
# ============================================================================


class CustomerEmploymentRead(BaseModel):
    employment_id: int
    customer_id: int
    company_name: Optional[str] = None
    position: Optional[str] = None
    years_of_experience: Optional[int] = None
    monthly_income: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerCreate(BaseModel):
    full_name: str
    age: int
    monthly_income: float
    credit_score: Optional[int] = None
    employment_status: Optional[str] = None

    @validator('age')
    def age_valid(cls, v):
        if v < 18 or v > 150:
            raise ValueError('Age must be between 18 and 150')
        return v

    @validator('monthly_income')
    def income_valid(cls, v):
        if v <= 0:
            raise ValueError('Monthly income must be positive')
        return v


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    monthly_income: Optional[float] = None
    credit_score: Optional[int] = None
    employment_status: Optional[str] = None


class CustomerRead(BaseModel):
    customer_id: int
    full_name: str
    age: Optional[int] = None
    monthly_income: Optional[float] = None
    credit_score: Optional[int] = None
    employment_status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    employments: List[CustomerEmploymentRead] = []

    class Config:
        from_attributes = True


class PaginatedCustomers(BaseModel):
    items: List[CustomerRead]
    total: int
    page: int
    limit: int


class CustomerSearchBody(BaseModel):
    filters: Dict[str, Any]
    page: int = 1
    limit: int = 20


class CustomerHistoryItem(BaseModel):
    timestamp: datetime
    changed_by: str
    changes: Dict[str, Any]

    class Config:
        from_attributes = True


# ============================================================================
# Loan Application
# ============================================================================


class LoanApplicationCreate(BaseModel):
    customer_id: int
    loan_amount: float
    loan_term: int  # months
    interest_rate: Optional[float] = None
    loan_purpose: Optional[str] = None

    @validator('loan_amount')
    def loan_amount_valid(cls, v):
        if v <= 0:
            raise ValueError('Loan amount must be positive')
        return v

    @validator('loan_term')
    def loan_term_valid(cls, v):
        if v <= 0 or v > 360:
            raise ValueError('Loan term must be between 1 and 360 months')
        return v


class LoanApplicationRead(BaseModel):
    application_id: int
    customer_id: int
    loan_amount: float
    loan_term: int
    interest_rate: Optional[float] = None
    loan_status: str
    loan_purpose: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Loan Facility
# ============================================================================


class LoanFacilityCreate(BaseModel):
    application_id: int
    customer_id: int
    facility_type: Optional[str] = None
    approved_amount: float
    interest_rate: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class LoanFacilityRead(BaseModel):
    facility_id: int
    application_id: Optional[int] = None
    customer_id: int
    facility_type: Optional[str] = None
    approved_amount: float
    interest_rate: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Loan Payment & Repayment
# ============================================================================


class LoanRepaymentScheduleRead(BaseModel):
    schedule_id: int
    facility_id: int
    installment_no: int
    due_date: datetime
    principal_amount: float
    interest_amount: float
    total_due: float
    remaining_balance: float
    created_at: datetime

    class Config:
        from_attributes = True


class LoanPaymentCreate(BaseModel):
    facility_id: int
    schedule_id: Optional[int] = None
    payment_date: datetime
    amount_paid: float
    payment_method: Optional[str] = None


class LoanPaymentRead(BaseModel):
    payment_id: int
    facility_id: int
    schedule_id: Optional[int] = None
    payment_date: datetime
    amount_paid: float
    principal_paid: Optional[float] = None
    interest_paid: Optional[float] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Loan Delinquency
# ============================================================================


class LoanDelinquencyRead(BaseModel):
    delinquency_id: int
    facility_id: int
    as_of_date: datetime
    days_past_due: int
    overdue_amount: Optional[float] = None
    risk_bucket: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Risk Scoring
# ============================================================================


class RiskRequest(BaseModel):
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


class RiskPredictionRead(BaseModel):
    prediction_id: int
    application_id: Optional[int] = None
    customer_id: Optional[int] = None
    model_id: Optional[int] = None
    risk_score: float
    risk_level: Optional[str] = None
    predicted_at: datetime

    class Config:
        from_attributes = True


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


# ============================================================================
# Portfolio
# ============================================================================


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


# ============================================================================
# Chat
# ============================================================================


class ChatSessionCreate(BaseModel):
    user_id: int


class ChatSessionRead(BaseModel):
    session_id: UUID
    user_id: int
    created_at: datetime
    last_interaction: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    session_id: UUID
    user_id: int
    message: str


class ChatMessageRead(BaseModel):
    chat_id: int
    user_id: int
    session_id: Optional[UUID] = None
    message: str
    bot_response: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    answer: str
    extracted_metrics: Optional[Dict[str, Any]] = None
    sources: Optional[List[str]] = None


class ChatSessionSummary(BaseModel):
    session_id: UUID
    started_at: datetime
    last_activity_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime


# ============================================================================
# Alert
# ============================================================================


class AlertRead(BaseModel):
    alert_id: int
    facility_id: Optional[int] = None
    customer_id: Optional[int] = None
    alert_type: str
    severity: str
    message: Optional[str] = None
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertSubscriptionCreate(BaseModel):
    user_id: int
    alert_type: str
    alert_severity: str


class AlertSubscriptionRead(BaseModel):
    subscription_id: int
    user_id: int
    alert_type: str
    alert_severity: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResolveBody(BaseModel):
    reason: str


# ============================================================================
# Admin / System
# ============================================================================


class AuditLogRead(BaseModel):
    audit_id: int
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    performed_at: datetime

    class Config:
        from_attributes = True


class ExportRequestBody(BaseModel):
    type: str
    filters: Dict[str, Any]


class ExportResponse(BaseModel):
    file_url: str


# ============================================================================
# File / Ingestion
# ============================================================================


class UploadJobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    progress: float
    result_url: Optional[str] = None
