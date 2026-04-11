from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_REGEX = re.compile(r"^0\d{9}$")
PIN_REGEX = re.compile(r"^\d{6}$")


def _validate_email_format(value: str) -> str:
    candidate = (value or "").strip()
    if not EMAIL_REGEX.match(candidate):
        raise ValueError("Invalid email format")
    return candidate


def _validate_phone_format(value: str) -> str:
    candidate = (value or "").strip()
    if not PHONE_REGEX.match(candidate):
        raise ValueError("Phone number must start with 0 and contain exactly 10 digits")
    return candidate


def _validate_password_strength(value: str) -> str:
    candidate = value or ""
    if len(candidate) < 6:
        raise ValueError("Password must be at least 6 characters")
    if not re.search(r"[A-Z]", candidate):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", candidate):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", candidate):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[^A-Za-z0-9]", candidate):
        raise ValueError("Password must contain at least one special character")
    return candidate


def _validate_pin_digits(value: str) -> str:
    candidate = (value or "").strip()
    if not PIN_REGEX.match(candidate):
        raise ValueError("PIN must contain exactly 6 digits")
    return candidate


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
    role: str  # admin, manager, risk analyst, viewer
    status: str | None = None
    has_pin: bool = False


class TokenData(BaseModel):
    sub: str | None = None
    role: str | None = None


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class PasswordResetRequestBody(BaseModel):
    email: str = Field(..., description="Email address")

    @validator("email")
    def validate_email(cls, v: str) -> str:
        return _validate_email_format(v)


class PasswordResetConfirmBody(BaseModel):
    email: str = Field(..., description="Email address")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit PIN")
    new_password: str = Field(..., min_length=6, description="New password")

    @validator("email")
    def validate_email(cls, v: str) -> str:
        return _validate_email_format(v)

    @validator("code")
    def validate_code(cls, v: str) -> str:
        return _validate_pin_digits(v)

    @validator("new_password")
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class AccountPinSetBody(BaseModel):
    pin: str = Field(..., pattern=r"^\d{6}$", description="6-digit PIN")

    @validator("pin")
    def validate_pin(cls, v: str) -> str:
        return _validate_pin_digits(v)


class AccountPinChangeBody(BaseModel):
    old_pin: str = Field(..., pattern=r"^\d{6}$", description="Current 6-digit PIN")
    new_pin: str = Field(..., pattern=r"^\d{6}$", description="New 6-digit PIN")

    @validator("old_pin", "new_pin")
    def validate_pin(cls, v: str) -> str:
        return _validate_pin_digits(v)


class AccountPinEmailChangeBody(BaseModel):
    new_email: str = Field(..., description="New email address")
    pin: str = Field(..., pattern=r"^\d{6}$", description="Current 6-digit PIN")

    @validator("new_email")
    def validate_new_email(cls, v: str) -> str:
        return _validate_email_format(v)

    @validator("pin")
    def validate_pin(cls, v: str) -> str:
        return _validate_pin_digits(v)


class PendingAccountStatusResponse(BaseModel):
    user_id: int
    email: str
    role: str
    status: str
    has_pin: bool


class MessageResponse(BaseModel):
    message: str


class OAuthLoginRequest(BaseModel):
    token: str = Field(..., description="Google ID token or GitHub access token")


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
    role: str = "viewer"  # admin, manager, risk analyst, viewer
    is_admin: bool = False
    status: str | None = None
    has_pin: bool = False


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role_id: int

    @validator("email")
    def validate_email(cls, v: str) -> str:
        return _validate_email_format(v)

    @validator("password")
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserRead(BaseModel):
    user_id: int
    username: str
    email: str
    role_id: int | None = None
    full_name: str | None = None
    role: str = "viewer"
    status: str | None = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserRoleUpdateBody(BaseModel):
    role: str = Field(..., description="admin|manager|analyst|viewer")


class ProfileRead(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    role: str = "viewer"
    status: str | None = None
    is_email_verified: bool = False
    created_at: datetime


class ProfileUpdateBody(BaseModel):
    full_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)

    @validator("phone", pre=True)
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        candidate = str(v).strip()
        if candidate == "":
            return None
        return _validate_phone_format(candidate)


class PasswordChangeBody(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)

    @validator("new_password")
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class EmailChangeRequestBody(BaseModel):
    new_email: str = Field(..., description="New email address")

    @validator("new_email")
    def validate_new_email(cls, v: str) -> str:
        return _validate_email_format(v)


class EmailChangeRequestResponse(BaseModel):
    message: str
    pending_email: str
    expires_in_seconds: int


class EmailChangeConfirmBody(BaseModel):
    code: str = Field(..., min_length=4, max_length=10)


class EmailChangeConfirmResponse(BaseModel):
    message: str
    email: str
    access_token: str
    role: str


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

    @validator("email")
    def validate_email(cls, v: str) -> str:
        return _validate_email_format(v)

    @validator("password")
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)

    @validator("phone", pre=True)
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        candidate = str(v).strip()
        if candidate == "":
            return None
        return _validate_phone_format(candidate)


class UserRegistrationResponse(BaseModel):
    registration_id: int
    username: str
    email: str
    registration_type: str
    role: str | None = None
    status: str  # pending, approved, rejected, verified
    access_token: str | None = None
    token_type: str = "bearer"
    has_pin: bool = False
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


class UserRegistrationResendRequest(BaseModel):
    email: str = Field(..., description="Registered email address")

    @validator("email")
    def validate_email(cls, v: str) -> str:
        return _validate_email_format(v)


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
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    class Config:
        from_attributes = True


class ManagerUpgradeRequestCreate(BaseModel):
    purpose: str = Field(..., min_length=10, max_length=1000)


class ManagerUpgradeNominationCreate(BaseModel):
    analyst_user_id: int
    purpose: str = Field(..., min_length=10, max_length=1000)


class ManagerUpgradeVoteRequest(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    note: str | None = Field(None, max_length=1000)


class ManagerUpgradeRequestRead(BaseModel):
    request_id: int
    target_user_id: int
    target_username: str
    target_email: str
    purpose: str
    status: str
    requested_by_role: str
    nominated_by: int | None = None
    nominated_by_username: str | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    approve_votes: int = 0
    reject_votes: int = 0
    total_managers: int = 0
    approval_ratio: float = 0.0
    created_at: datetime
    updated_at: datetime | None = None

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
    age: Optional[int] = None
    monthly_income: float
    external_customer_ref: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    national_id: Optional[str] = None
    id_issue_date: Optional[date] = None
    id_issue_place: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    permanent_address: Optional[str] = None
    current_address: Optional[str] = None
    occupation: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    credit_score: Optional[int] = None
    employment_status: Optional[str] = None
    loan_type: Optional[str] = None
    requested_loan_amount: Optional[float] = None
    requested_term_months: Optional[int] = None
    annual_interest_rate: Optional[float] = None
    risk_level: Optional[str] = None
    application_status: Optional[str] = None
    application_ref_no: Optional[str] = None
    source_department_code: Optional[str] = None
    source_branch_code: Optional[str] = None
    application_date: Optional[date] = None
    loan_purpose: Optional[str] = None
    collateral_id: Optional[str] = None
    collateral_value: Optional[float] = None
    template_version: Optional[str] = None
    upload_batch_id: Optional[str] = None
    notes: Optional[str] = None

    @validator('age')
    def age_valid(cls, v):
        if v is None:
            return v
        if v < 18 or v > 150:
            raise ValueError('Age must be between 18 and 150')
        return v

    @validator('monthly_income')
    def income_valid(cls, v):
        if v <= 0:
            raise ValueError('Monthly income must be positive')
        return v

    @validator('requested_loan_amount')
    def requested_loan_amount_valid(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Requested loan amount must be positive')
        return v

    @validator('requested_term_months')
    def requested_term_valid(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Requested term must be positive')
        return v

    @validator('annual_interest_rate')
    def annual_interest_rate_valid(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Annual interest rate must be between 0 and 100')
        return v


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    monthly_income: Optional[float] = None
    external_customer_ref: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    national_id: Optional[str] = None
    id_issue_date: Optional[date] = None
    id_issue_place: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    permanent_address: Optional[str] = None
    current_address: Optional[str] = None
    occupation: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    credit_score: Optional[int] = None
    employment_status: Optional[str] = None
    loan_type: Optional[str] = None
    requested_loan_amount: Optional[float] = None
    requested_term_months: Optional[int] = None
    annual_interest_rate: Optional[float] = None
    risk_level: Optional[str] = None
    application_status: Optional[str] = None
    application_ref_no: Optional[str] = None
    source_department_code: Optional[str] = None
    source_branch_code: Optional[str] = None
    application_date: Optional[date] = None
    loan_purpose: Optional[str] = None
    collateral_id: Optional[str] = None
    collateral_value: Optional[float] = None
    template_version: Optional[str] = None
    upload_batch_id: Optional[str] = None
    notes: Optional[str] = None


class CustomerStatusUpdateBody(BaseModel):
    application_status: str

    @validator("application_status")
    def application_status_valid(cls, v):
        normalized = str(v or "").strip().lower()
        if normalized not in {"pending", "approved", "rejected", "disbursed"}:
            raise ValueError("application_status must be one of: pending, approved, rejected, disbursed")
        return normalized


class CustomerRead(BaseModel):
    customer_id: int
    full_name: str
    age: Optional[int] = None
    monthly_income: Optional[float] = None
    external_customer_ref: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    national_id: Optional[str] = None
    id_issue_date: Optional[date] = None
    id_issue_place: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    permanent_address: Optional[str] = None
    current_address: Optional[str] = None
    occupation: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    credit_score: Optional[int] = None
    employment_status: Optional[str] = None
    loan_type: Optional[str] = None
    requested_loan_amount: Optional[float] = None
    requested_term_months: Optional[int] = None
    annual_interest_rate: Optional[float] = None
    risk_level: Optional[str] = None
    application_status: Optional[str] = None
    application_ref_no: Optional[str] = None
    source_department_code: Optional[str] = None
    source_branch_code: Optional[str] = None
    application_date: Optional[date] = None
    loan_purpose: Optional[str] = None
    collateral_id: Optional[str] = None
    collateral_value: Optional[float] = None
    template_version: Optional[str] = None
    upload_batch_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
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
    application_ref_no: Optional[str] = None
    source_department_code: Optional[str] = None
    source_branch_code: Optional[str] = None
    application_date: Optional[date] = None
    loan_amount: float
    loan_term: int  # months
    interest_rate: Optional[float] = None
    loan_purpose: Optional[str] = None
    loan_type: Optional[str] = None
    collateral_id: Optional[str] = None
    collateral_value: Optional[float] = None
    template_version: Optional[str] = None
    upload_batch_id: Optional[str] = None

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
    application_ref_no: Optional[str] = None
    source_department_code: Optional[str] = None
    source_branch_code: Optional[str] = None
    application_date: Optional[date] = None
    loan_amount: float
    loan_term: int
    interest_rate: Optional[float] = None
    loan_status: str
    loan_purpose: Optional[str] = None
    loan_type: Optional[str] = None
    collateral_id: Optional[str] = None
    collateral_value: Optional[float] = None
    template_version: Optional[str] = None
    upload_batch_id: Optional[str] = None
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
    credit_score: Optional[int] = Field(None, ge=0, le=1000)
    loan_type: Optional[str] = None
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    loan_term_months: Optional[int] = Field(None, ge=0)
    collateral_value: Optional[float] = Field(None, ge=0)
    employment_status: Optional[str] = None


class RiskResponse(BaseModel):
    risk_score: float = Field(..., ge=0, le=1, description="0 (low risk) .. 1 (high risk)")
    risk_label: str = Field(..., description="low|medium|high")
    cic_score: int = Field(..., ge=150, le=850, description="CIC-like score scale for Vietnam market")
    cic_group: str = Field(..., description="very_good|good|average|high_risk")
    cic_rating: str = Field(..., description="excellent|good|watchlist|substandard|loss")
    explanation: str
    explanation_en: Optional[str] = Field(
        default=None,
        description="Detailed model walkthrough in English (optional, for bilingual clients)",
    )
    explanation_detail: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured breakdown for rich UI (factors, weights, money amounts)",
    )


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
    results: List[RiskScoreDetail] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    processed_count: int = 0
    success_count: int = 0
    error_count: int = 0
    average_score: Optional[float] = None
    max_score: Optional[float] = None
    min_score: Optional[float] = None
    errors: Optional[List[Dict[str, Any]]] = None


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
    # Histogram on a unified 0–100 "display score" scale (see risk_distribution service).
    score_buckets: List[Dict[str, Any]] = Field(default_factory=list)
    score_stats: Dict[str, float] = Field(
        default_factory=lambda: {"mean": 0.0, "median": 0.0, "std_dev": 0.0}
    )


class PortfolioRiskFactorItem(BaseModel):
    """One bar on the risk factor chart: impact is share of mean weighted contributions (0–100)."""

    factor_key: str
    impact: float


class PortfolioRiskFactorsResponse(BaseModel):
    items: List[PortfolioRiskFactorItem]
    sample_size: int


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
    customer_name: Optional[str] = None
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
    actor_name: Optional[str] = None
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
    file_name: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[List[str]] = None
    preview_rows: Optional[List[Dict[str, Any]]] = None
    context_text: Optional[str] = None
    processed_count: Optional[int] = None
    success_count: Optional[int] = None
    error_count: Optional[int] = None
    imported_customers: Optional[int] = None
    imported_applications: Optional[int] = None
    import_errors: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class UploadJobContentResponse(BaseModel):
    job_id: str
    file_name: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None
    context_text: Optional[str] = None
    total_rows: Optional[int] = None
    offset: int = 0
    limit: int = 0
    has_more: bool = False


class UploadJobErrorsResponse(BaseModel):
    job_id: str
    errors: List[Dict[str, Any]]
    total_errors: int
    offset: int = 0
    limit: int = 0
    has_more: bool = False


class JobStatusResponse(BaseModel):
    job_id: str
    progress: float
    status: Optional[str] = None
    result_url: Optional[str] = None


class UploadHistoryItemRead(BaseModel):
    audit_id: int
    job_id: Optional[str] = None
    file_name: Optional[str] = None
    status: str
    processed_count: Optional[int] = None
    success_count: Optional[int] = None
    error_count: Optional[int] = None
    created_at: datetime
