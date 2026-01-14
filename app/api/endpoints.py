from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_current_admin_user,
)
from app.schemas.schemas import (
    AlertRead,
    AlertResolveBody,
    AlertSubscriptionCreate,
    AlertSubscriptionRead,
    AuditLogRead,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSessionSummary,
    ConcentrationResponse,
    CustomerCreate,
    CustomerHistoryItem,
    CustomerRead,
    CustomerSearchBody,
    CustomerUpdate,
    ExportRequestBody,
    ExportResponse,
    HealthResponse,
    JobStatusResponse,
    PaginatedCustomers,
    PortfolioCompareBody,
    PortfolioCompareResponse,
    PortfolioKPIResponse,
    PortfolioTrendResponse,
    RiskAnalyzeBody,
    RiskBatchBody,
    RiskBatchResult,
    RiskExplainResponse,
    RiskModelVersion,
    RiskRequest,
    RiskResponse,
    RiskSimulationBody,
    RiskSimulationResult,
    RiskDistributionResponse,
    Token,
    UploadJobResponse,
    User,
    UserCreate,
    UserRead,
)
from app.services import services

router = APIRouter()


# ---------------------------------------------------------------------------
# Health (public)
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    # db_ok ở đây demo = True; thực tế nên ping DB
    return HealthResponse(status="ok", version="v1", db_ok=True)


# ---------------------------------------------------------------------------
# Auth (JWT)
# ---------------------------------------------------------------------------


@router.post("/auth/login", response_model=Token, tags=["auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token)


# ---------------------------------------------------------------------------
# Group 1: Customers
# ---------------------------------------------------------------------------


@router.get("/customers", response_model=PaginatedCustomers, tags=["customers"])
async def list_customers_endpoint(
    page: int = 1,
    limit: int = 20,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_pd: Optional[float] = None,  # demo, chưa dùng
    current_user: User = Depends(get_current_active_user),
) -> PaginatedCustomers:
    return services.list_customers(page=page, limit=limit, search_name=search_name, risk_level=risk_level)


@router.get("/customers/{customer_id}", response_model=CustomerRead, tags=["customers"])
async def get_customer_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    customer = services.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/customers", response_model=CustomerRead, status_code=201, tags=["customers"])
async def create_customer_endpoint(
    body: CustomerCreate,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    return services.create_customer(body, created_by=current_user.email)


@router.put("/customers/{customer_id}", response_model=CustomerRead, tags=["customers"])
async def update_customer_endpoint(
    customer_id: int,
    body: CustomerUpdate,
    current_user: User = Depends(get_current_active_user),
) -> CustomerRead:
    updated = services.update_customer(customer_id, body, updated_by=current_user.email)
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


@router.get("/customers/{customer_id}/history", response_model=List[CustomerHistoryItem], tags=["customers"])
async def customer_history_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> List[CustomerHistoryItem]:
    return services.get_customer_history(customer_id)


@router.post("/customers/search", response_model=PaginatedCustomers, tags=["customers"])
async def customer_search_endpoint(
    body: CustomerSearchBody,
    current_user: User = Depends(get_current_active_user),
) -> PaginatedCustomers:
    return services.advanced_customer_search(body)


# ---------------------------------------------------------------------------
# Group 2: Risk Analysis & Scoring
# ---------------------------------------------------------------------------


@router.post("/risk/score", response_model=RiskResponse, tags=["risk"])
async def score_risk(payload: RiskRequest) -> RiskResponse:
    # Để giữ compat với demo ban đầu, endpoint này không bắt buộc JWT
    result = services.simple_credit_risk_score(payload)
    return RiskResponse(**result)


@router.get("/risk/score/{customer_id}", response_model=RiskScoreDetail, tags=["risk"])
async def score_risk_for_customer(
    customer_id: int,
    as_of_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> RiskScoreDetail:
    customer = services.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # Demo: dùng lại heuristic theo income/debt giả định
    req = RiskRequest(
        income=customer.income,
        debt=customer.income * 0.3,
        age=customer.age,
        credit_history_months=24,
    )
    base = services.simple_credit_risk_score(req)
    return services.score_to_pd_lgd_ead(base["risk_score"])


@router.post("/risk/analyze", response_model=RiskScoreDetail, tags=["risk"])
async def risk_analyze_endpoint(
    body: RiskAnalyzeBody,
    current_user: User = Depends(get_current_active_user),
) -> RiskScoreDetail:
    # Map từ dict vào RiskRequest đơn giản
    data = body.customer_data
    req = RiskRequest(
        income=data.get("income", 0.0),
        debt=data.get("debt", 0.0),
        age=data.get("age", 30),
        credit_history_months=data.get("credit_history_months", 12),
    )
    base = services.simple_credit_risk_score(req)
    return services.score_to_pd_lgd_ead(base["risk_score"])


@router.post("/risk/batch", response_model=RiskBatchResult, tags=["risk"])
async def risk_batch_endpoint(
    body: RiskBatchBody,
    current_user: User = Depends(get_current_active_user),
) -> RiskBatchResult:
    results = []
    for rec in body.records[:500]:
        req = RiskRequest(
            income=rec.get("income", 0.0),
            debt=rec.get("debt", 0.0),
            age=rec.get("age", 30),
            credit_history_months=rec.get("credit_history_months", 12),
        )
        base = services.simple_credit_risk_score(req)
        results.append(services.score_to_pd_lgd_ead(base["risk_score"]))

    summary = {"count": len(results), "avg_pd": sum(r.pd for r in results) / max(len(results), 1)}
    return RiskBatchResult(results=results, summary=summary)


@router.post("/risk/simulation", response_model=RiskSimulationResult, tags=["risk"])
async def risk_simulation_endpoint(
    body: RiskSimulationBody,
    current_user: User = Depends(get_current_active_user),
) -> RiskSimulationResult:
    # Demo: trả về base_data + từng scenario
    scenario_results = []
    for s in body.scenarios:
        scenario_results.append({"scenario": s, "delta_el": 10_000})
    return RiskSimulationResult(scenario_results=scenario_results)


@router.get("/risk/model/version", response_model=List[RiskModelVersion], tags=["risk"])
async def risk_model_versions_endpoint(
    current_user: User = Depends(get_current_active_user),
) -> List[RiskModelVersion]:
    # Demo: 1 version
    from datetime import datetime

    return [
        RiskModelVersion(version="v1", accuracy=0.85, deployed_at=datetime.utcnow()),
    ]


@router.get("/risk/explain/{customer_id}", response_model=RiskExplainResponse, tags=["risk"])
async def risk_explain_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
) -> RiskExplainResponse:
    customer = services.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return services.explain_risk(customer_id)


# ---------------------------------------------------------------------------
# Group 3: Portfolio & Aggregated Metrics
# ---------------------------------------------------------------------------


@router.get("/portfolio/kpi", response_model=PortfolioKPIResponse, tags=["portfolio"])
async def portfolio_kpi_endpoint(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    segment: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> PortfolioKPIResponse:
    return services.compute_portfolio_kpi(date_from, date_to, segment)


@router.get("/portfolio/risk-distribution", response_model=RiskDistributionResponse, tags=["portfolio"])
async def portfolio_risk_distribution_endpoint(
    group_by: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> RiskDistributionResponse:
    return services.risk_distribution(group_by)


@router.get("/portfolio/concentration", response_model=ConcentrationResponse, tags=["portfolio"])
async def portfolio_concentration_endpoint(
    top_n: int = 10,
    current_user: User = Depends(get_current_active_user),
) -> ConcentrationResponse:
    return services.concentration(top_n)


@router.get("/portfolio/trend", response_model=PortfolioTrendResponse, tags=["portfolio"])
async def portfolio_trend_endpoint(
    metric: str,
    interval: str = "month",
    current_user: User = Depends(get_current_active_user),
) -> PortfolioTrendResponse:
    return services.portfolio_trend(metric, interval)


@router.post("/portfolio/compare", response_model=PortfolioCompareResponse, tags=["portfolio"])
async def portfolio_compare_endpoint(
    body: PortfolioCompareBody,
    current_user: User = Depends(get_current_active_user),
) -> PortfolioCompareResponse:
    return services.portfolio_compare(body)


# ---------------------------------------------------------------------------
# Group 4: Chatbot & Interactive Query
# ---------------------------------------------------------------------------


@router.post("/chat/query", response_model=ChatResponse, tags=["chat"])
async def chat_query_endpoint(
    body: ChatRequest,
    current_user: User = Depends(get_current_active_user),
) -> ChatResponse:
    _, resp = services.upsert_chat_session(body)
    return resp


@router.get("/chat/sessions", response_model=List[ChatSessionSummary], tags=["chat"])
async def chat_sessions_endpoint(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
) -> List[ChatSessionSummary]:
    return services.list_chat_sessions(user_id)


@router.get("/chat/sessions/{session_id}", response_model=List[ChatMessage], tags=["chat"])
async def chat_session_detail_endpoint(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
) -> List[ChatMessage]:
    return services.get_chat_session_messages(session_id)


@router.get("/chat/suggest", response_model=List[str], tags=["chat"])
async def chat_suggest_endpoint(
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
) -> List[str]:
    return services.suggest_queries(customer_id)


# ---------------------------------------------------------------------------
# Group 5: Alerts & Notifications
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=List[AlertRead], tags=["alerts"])
async def alerts_list_endpoint(
    status: Optional[str] = None,
    type: Optional[str] = None,  # type: ignore[assignment]
    current_user: User = Depends(get_current_active_user),
) -> List[AlertRead]:
    return services.list_alerts(status=status, type_=type)


@router.post("/alerts/subscribe", response_model=AlertSubscriptionRead, tags=["alerts"])
async def alerts_subscribe_endpoint(
    body: AlertSubscriptionCreate,
    current_user: User = Depends(get_current_active_user),
) -> AlertSubscriptionRead:
    return services.subscribe_alerts(body)


@router.put("/alerts/{alert_id}/resolve", response_model=AlertRead, tags=["alerts"])
async def alerts_resolve_endpoint(
    alert_id: int,
    body: AlertResolveBody,
    current_user: User = Depends(get_current_active_user),
) -> AlertRead:
    result = services.resolve_alert(alert_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result


# ---------------------------------------------------------------------------
# Group 6: Admin & System
# ---------------------------------------------------------------------------


@router.get("/admin/users", response_model=List[UserRead], tags=["admin"])
async def admin_list_users_endpoint(
    current_user: User = Depends(get_current_admin_user),
) -> List[UserRead]:
    return services.list_users()


@router.post("/admin/users", response_model=UserRead, tags=["admin"])
async def admin_create_user_endpoint(
    body: UserCreate,
    current_user: User = Depends(get_current_admin_user),
) -> UserRead:
    return services.create_user(body)


@router.get("/admin/audit-logs", response_model=List[AuditLogRead], tags=["admin"])
async def admin_audit_logs_endpoint(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user),
) -> List[AuditLogRead]:
    return services.list_audit_logs(from_date, to_date, user_id)


@router.post("/admin/export", response_model=ExportResponse, tags=["admin"])
async def admin_export_endpoint(
    body: ExportRequestBody,
    current_user: User = Depends(get_current_admin_user),
) -> ExportResponse:
    return services.export_data(body)


# ---------------------------------------------------------------------------
# Group 7: File & Data Ingestion
# ---------------------------------------------------------------------------


@router.post("/upload/data", response_model=UploadJobResponse, tags=["ingestion"])
async def upload_data_endpoint(
    file: UploadFile = File(...),
    type: str = "customers",  # type: ignore[assignment]
    current_user: User = Depends(get_current_active_user),
) -> UploadJobResponse:
    # Demo: chưa parse file; chỉ tạo job
    return services.create_upload_job(type)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse, tags=["ingestion"])
async def job_status_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
) -> JobStatusResponse:
    return services.get_job_status(job_id)

