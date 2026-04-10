import csv
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import (
    authenticate_user,
    authenticate_user_by_username_or_email,
    create_access_token,
    get_current_active_user,
    get_current_admin_user,
    get_current_manager_or_admin_user,
    get_current_manager_user,
    get_current_analyst_user,
)
from app.db.session import get_db
from app.schemas.schemas import (
    AlertRead,
    AlertResolveBody,
    AlertSubscriptionCreate,
    AlertSubscriptionRead,
    AuditLogRead,
    EmailChangeConfirmBody,
    EmailChangeConfirmResponse,
    EmailChangeRequestBody,
    EmailChangeRequestResponse,
    ConcentrationResponse,
    CustomerCreate,
    CustomerHistoryItem,
    CustomerRead,
    CustomerSearchBody,
    CustomerUpdate,
    ExportRequestBody,
    ExportResponse,
    HealthResponse,
    LoginRequest,
    JobStatusResponse,
    ManagerUpgradeNominationCreate,
    ManagerUpgradeRequestCreate,
    ManagerUpgradeRequestRead,
    ManagerUpgradeVoteRequest,
    OAuthLoginRequest,
    PasswordResetConfirmBody,
    PasswordResetRequestBody,
    PaginatedCustomers,
    PortfolioCompareBody,
    PortfolioCompareResponse,
    PortfolioKPIResponse,
    PortfolioTrendResponse,
    PortfolioRiskFactorsResponse,
    PasswordChangeBody,
    ProfileRead,
    ProfileUpdateBody,
    RiskAnalyzeBody,
    RiskBatchBody,
    RiskBatchResult,
    RiskExplainResponse,
    RiskModelVersion,
    RiskRequest,
    RiskResponse,
    RiskScoreDetail,
    RiskSimulationBody,
    RiskSimulationResult,
    RiskDistributionResponse,
    Token,
    UploadJobContentResponse,
    UploadJobErrorsResponse,
    UploadHistoryItemRead,
    UploadJobResponse,
    User,
    UserCreate,
    UserRoleUpdateBody,
    UserRead,
    MessageResponse,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.manager_upgrade_service import ManagerUpgradeService
from app.services.oauth_service import OAuthService
from app.services.ai_chat_file_context_service import AIChatFileContextService
from app.services.audit_service import log_action
from app.services import customer_intake_service
from app.services import password_reset_service
from app.services import profile_service
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
async def login_for_access_token_endpoint(body: LoginRequest) -> Token:
    """
    Login endpoint - accepts username or email + password
    Returns JWT token with user info and role
    """
    try:
        user_dict = authenticate_user_by_username_or_email(body.username_or_email, body.password)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login failed because the database query could not be completed. Verify the MySQL schema and connection settings.",
        )
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )
    
    access_token = create_access_token(
        data={
            "sub": user_dict.get("email"),
            "role": user_dict.get("role", "viewer")
        }
    )
    
    return Token(
        access_token=access_token,
        user_id=user_dict.get("id"),
        email=user_dict.get("email"),
        full_name=user_dict.get("full_name"),
        role=user_dict.get("role", "viewer")
    )


@router.post("/auth/login/google", response_model=Token, tags=["auth"])
async def login_with_google(
    body: OAuthLoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    try:
        return OAuthService.login_with_google(db, body.token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/auth/login/github", response_model=Token, tags=["auth"])
async def login_with_github(
    body: OAuthLoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    try:
        return OAuthService.login_with_github(db, body.token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/auth/forgot-password/request", response_model=MessageResponse, tags=["auth"])
async def request_password_reset_endpoint(
    body: PasswordResetRequestBody,
    db: Session = Depends(get_db),
) -> MessageResponse:
    success, message = password_reset_service.request_password_reset(db, body.email)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message)


@router.post("/auth/forgot-password/confirm", response_model=MessageResponse, tags=["auth"])
async def confirm_password_reset_endpoint(
    body: PasswordResetConfirmBody,
    db: Session = Depends(get_db),
) -> MessageResponse:
    success, message = password_reset_service.confirm_password_reset(
        db,
        body.email,
        body.code,
        body.new_password,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message)


@router.get("/profile/me", response_model=ProfileRead, tags=["profile"])
async def get_my_profile(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProfileRead:
    # Giảm bớt burst từ client gọi song song (layout + sidebar + activity): CDN/browser có thể tái sử dụng ngắn.
    response.headers["Cache-Control"] = "private, max-age=10, stale-while-revalidate=30"
    profile = profile_service.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/profile/me", response_model=ProfileRead, tags=["profile"])
async def update_my_profile(
    body: ProfileUpdateBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProfileRead:
    profile = profile_service.update_profile(db, current_user.id, body)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/profile/change-password", tags=["profile"])
async def change_my_password(
    body: PasswordChangeBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    success, message = profile_service.change_password(db, current_user.id, body.current_password, body.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/profile/change-email/request", response_model=EmailChangeRequestResponse, tags=["profile"])
async def request_my_email_change(
    body: EmailChangeRequestBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EmailChangeRequestResponse:
    success, message, pending_email, expires_in_seconds = profile_service.request_email_change(
        db,
        current_user.id,
        body.new_email,
    )
    if not success or not pending_email or not expires_in_seconds:
        raise HTTPException(status_code=400, detail=message)
    return EmailChangeRequestResponse(
        message=message,
        pending_email=pending_email,
        expires_in_seconds=expires_in_seconds,
    )


@router.post("/profile/change-email/confirm", response_model=EmailChangeConfirmResponse, tags=["profile"])
async def confirm_my_email_change(
    body: EmailChangeConfirmBody,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EmailChangeConfirmResponse:
    success, message, profile = profile_service.confirm_email_change(db, current_user.id, body.code)
    if not success or not profile:
        raise HTTPException(status_code=400, detail=message)

    access_token = create_access_token(
        data={
            "sub": profile.email,
            "role": profile.role,
        }
    )
    return EmailChangeConfirmResponse(
        message=message,
        email=profile.email,
        access_token=access_token,
        role=profile.role,
    )


@router.post("/profile/avatar", response_model=ProfileRead, tags=["profile"])
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProfileRead:
    success, message, profile = profile_service.update_avatar(db, current_user.id, file)
    if not success or not profile:
        raise HTTPException(status_code=400, detail=message)
    return profile


@router.get("/profile/avatar/me", tags=["profile"])
async def get_my_avatar(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    file_path = profile_service.get_avatar_file_path(db, current_user.id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(path=file_path)


# ---------------------------------------------------------------------------
# Group 1: Customers
# ---------------------------------------------------------------------------


@router.get("/customers", response_model=PaginatedCustomers, tags=["customers"])
async def list_customers_endpoint(
    page: int = 1,
    limit: Optional[int] = None,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_pd: Optional[float] = None,  # demo, chưa dùng
    current_user: User = Depends(get_current_analyst_user),  # Analyst, Manager, Admin
) -> PaginatedCustomers:
    return customer_intake_service.list_customers(page=page, limit=limit, search_name=search_name, risk_level=risk_level)


@router.get("/customers/{customer_id}", response_model=CustomerRead, tags=["customers"])
async def get_customer_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_analyst_user),  # Analyst, Manager, Admin
) -> CustomerRead:
    customer = customer_intake_service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/customers", response_model=CustomerRead, status_code=201, tags=["customers"])
async def create_customer_endpoint(
    body: CustomerCreate,
    current_user: User = Depends(get_current_analyst_user),  # Analyst có thể thêm, Manager/Admin approve
) -> CustomerRead:
    try:
        return customer_intake_service.create_customer(
            body,
            created_by=current_user.email,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.put("/customers/{customer_id}", response_model=CustomerRead, tags=["customers"])
async def update_customer_endpoint(
    customer_id: int,
    body: CustomerUpdate,
    current_user: User = Depends(get_current_manager_or_admin_user),  # Chỉ Manager/Admin
) -> CustomerRead:
    updated = customer_intake_service.update_customer(
        customer_id,
        body,
        updated_by=current_user.email,
        updated_by_user_id=current_user.id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


@router.delete("/customers/{customer_id}", response_model=MessageResponse, tags=["customers"])
async def delete_customer_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_manager_or_admin_user),  # Chỉ Manager/Admin
) -> MessageResponse:
    deleted = customer_intake_service.delete_customer(customer_id, deleted_by_user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return MessageResponse(message="Đã xóa hồ sơ khách hàng.")


@router.get("/customers/{customer_id}/history", response_model=List[CustomerHistoryItem], tags=["customers"])
async def customer_history_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_analyst_user),  # Analyst, Manager, Admin
) -> List[CustomerHistoryItem]:
    return customer_intake_service.get_customer_history(customer_id)


@router.post("/customers/search", response_model=PaginatedCustomers, tags=["customers"])
async def customer_search_endpoint(
    body: CustomerSearchBody,
    current_user: User = Depends(get_current_analyst_user),  # Analyst, Manager, Admin
) -> PaginatedCustomers:
    return customer_intake_service.advanced_customer_search(body)


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
    current_user: User = Depends(get_current_analyst_user),  # Analyst+
) -> RiskScoreDetail:
    customer = customer_intake_service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # Demo: dùng lại heuristic theo income/debt giả định
    req = RiskRequest(
        income=float(customer.monthly_income or 0),
        debt=float(customer.monthly_income or 0) * 0.3,
        age=customer.age or 30,
        credit_history_months=24,
    )
    base = services.simple_credit_risk_score(req)
    return services.score_to_pd_lgd_ead(base["risk_score"])


@router.post("/risk/analyze", response_model=RiskScoreDetail, tags=["risk"])
async def risk_analyze_endpoint(
    body: RiskAnalyzeBody,
    current_user: User = Depends(get_current_analyst_user),  # Analyst+
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
    body: Optional[RiskBatchBody] = None,
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_manager_or_admin_user),  # Manager+
) -> RiskBatchResult:
    records: List[dict] = []

    if file is not None:
        raw = await file.read()
        decoded = None
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                decoded = raw.decode(encoding)
                break
            except Exception:
                continue
        if decoded is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot decode CSV file.")
        reader = csv.DictReader(StringIO(decoded))
        records = [dict(row) for row in reader]
    elif body is not None:
        records = body.records
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either JSON records or CSV file.",
        )

    results = []
    errors: List[dict] = []
    ui_scores: List[float] = []

    for index, rec in enumerate(records):
        try:
            income = float(rec.get("income", rec.get("monthly_income", 0.0)) or 0.0)
            debt = float(rec.get("debt", rec.get("loan_amount", 0.0)) or 0.0)
            age = int(float(rec.get("age", 30) or 30))
            history = int(float(rec.get("credit_history_months", rec.get("credit_history", 12)) or 12))

            req = RiskRequest(
                income=income,
                debt=debt,
                age=age,
                credit_history_months=history,
            )
            base = services.simple_credit_risk_score(req)
            results.append(services.score_to_pd_lgd_ead(base["risk_score"]))
            ui_scores.append((1 - float(base["risk_score"])) * 100)
        except Exception as exc:
            errors.append(
                {
                    "row": index + 2,
                    "message": str(exc),
                }
            )

    summary = {
        "count": len(results),
        "avg_pd": sum(r.pd for r in results) / max(len(results), 1),
    }
    return RiskBatchResult(
        results=results,
        summary=summary,
        processed_count=len(records),
        success_count=len(results),
        error_count=len(errors),
        average_score=round(sum(ui_scores) / max(len(ui_scores), 1), 2) if ui_scores else None,
        max_score=round(max(ui_scores), 2) if ui_scores else None,
        min_score=round(min(ui_scores), 2) if ui_scores else None,
        errors=errors or None,
    )


@router.post("/risk/simulation", response_model=RiskSimulationResult, tags=["risk"])
async def risk_simulation_endpoint(
    body: RiskSimulationBody,
    current_user: User = Depends(get_current_manager_or_admin_user),  # Manager+
) -> RiskSimulationResult:
    base_data = body.base_data if isinstance(body.base_data, dict) else {}
    base_req = RiskRequest(
        income=float(base_data.get("income", 0.0)),
        debt=float(base_data.get("debt", 0.0)),
        age=int(base_data.get("age", 30)),
        credit_history_months=int(base_data.get("credit_history_months", 12)),
        credit_score=int(base_data["credit_score"]) if base_data.get("credit_score") is not None else None,
        loan_type=base_data.get("loan_type"),
        interest_rate=float(base_data["interest_rate"]) if base_data.get("interest_rate") is not None else None,
        loan_term_months=int(base_data["loan_term_months"]) if base_data.get("loan_term_months") is not None else None,
        collateral_value=float(base_data["collateral_value"]) if base_data.get("collateral_value") is not None else None,
        employment_status=base_data.get("employment_status"),
    )
    base_score_data = services.simple_credit_risk_score(base_req)
    base_score = float(base_score_data.get("risk_score", 0.0))

    scenario_results = []
    for scenario in body.scenarios:
        if not isinstance(scenario, dict):
            continue
        merged = dict(base_data)
        merged.update(scenario)
        req = RiskRequest(
            income=float(merged.get("income", 0.0)),
            debt=float(merged.get("debt", 0.0)),
            age=int(merged.get("age", 30)),
            credit_history_months=int(merged.get("credit_history_months", 12)),
            credit_score=int(merged["credit_score"]) if merged.get("credit_score") is not None else None,
            loan_type=merged.get("loan_type"),
            interest_rate=float(merged["interest_rate"]) if merged.get("interest_rate") is not None else None,
            loan_term_months=int(merged["loan_term_months"]) if merged.get("loan_term_months") is not None else None,
            collateral_value=float(merged["collateral_value"]) if merged.get("collateral_value") is not None else None,
            employment_status=merged.get("employment_status"),
        )
        sim = services.simple_credit_risk_score(req)
        sim_score = float(sim.get("risk_score", 0.0))
        scenario_results.append(
            {
                "scenario": scenario,
                "risk_score": sim_score,
                "risk_label": sim.get("risk_label"),
                "cic_score": sim.get("cic_score"),
                "delta_risk_score": sim_score - base_score,
            }
        )
    return RiskSimulationResult(scenario_results=scenario_results)


@router.get("/risk/model/version", response_model=List[RiskModelVersion], tags=["risk"])
async def risk_model_versions_endpoint(
    current_user: User = Depends(get_current_analyst_user),  # Analyst+
) -> List[RiskModelVersion]:
    # Demo: 1 version
    from datetime import datetime

    return [
        RiskModelVersion(version="v1", accuracy=0.85, deployed_at=datetime.utcnow()),
    ]


@router.get("/risk/explain/{customer_id}", response_model=RiskExplainResponse, tags=["risk"])
async def risk_explain_endpoint(
    customer_id: int,
    current_user: User = Depends(get_current_analyst_user),  # Analyst+
) -> RiskExplainResponse:
    customer = customer_intake_service.get_customer(customer_id)
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
    current_user: User = Depends(get_current_manager_or_admin_user),  # Manager+
) -> PortfolioKPIResponse:
    return services.compute_portfolio_kpi(date_from, date_to, segment)


@router.get("/portfolio/risk-distribution", response_model=RiskDistributionResponse, tags=["portfolio"])
async def portfolio_risk_distribution_endpoint(
    group_by: Optional[str] = None,
    current_user: User = Depends(get_current_manager_or_admin_user),  # Manager+
) -> RiskDistributionResponse:
    return services.risk_distribution(group_by)


@router.get("/portfolio/risk-factor-impact", response_model=PortfolioRiskFactorsResponse, tags=["portfolio"])
async def portfolio_risk_factor_impact_endpoint(
    current_user: User = Depends(get_current_analyst_user),
) -> PortfolioRiskFactorsResponse:
    """Portfolio mean heuristic factor contributions (same model as /risk/score), from DB."""
    return services.portfolio_risk_factor_impact()


@router.get("/portfolio/concentration", response_model=ConcentrationResponse, tags=["portfolio"])
async def portfolio_concentration_endpoint(
    top_n: Optional[int] = None,
    group_by: Optional[str] = None,
    current_user: User = Depends(get_current_manager_or_admin_user),  # Manager+
) -> ConcentrationResponse:
    """group_by=customer (default) | occupation — occupation aggregates exposure by Customer.occupation."""
    return services.concentration(top_n, group_by)


@router.get("/portfolio/trend", response_model=PortfolioTrendResponse, tags=["portfolio"])
async def portfolio_trend_endpoint(
    metric: str,
    interval: str = "month",
    current_user: User = Depends(get_current_manager_or_admin_user),  # Manager+
) -> PortfolioTrendResponse:
    return services.portfolio_trend(metric, interval)


@router.post("/portfolio/compare", response_model=PortfolioCompareResponse, tags=["portfolio"])
async def portfolio_compare_endpoint(
    body: PortfolioCompareBody,
    current_user: User = Depends(get_current_manager_or_admin_user),  # Manager+
) -> PortfolioCompareResponse:
    return services.portfolio_compare(body)


# ---------------------------------------------------------------------------
# Group 4: Alerts & Notifications
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
    result = services.resolve_alert(alert_id, body, actor_user_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result


# ---------------------------------------------------------------------------
# Group 6: Admin & System
# ---------------------------------------------------------------------------


@router.get("/admin/users", response_model=List[UserRead], tags=["admin"])
async def admin_list_users_endpoint(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
) -> List[UserRead]:
    return services.list_users(
        user_id=user_id,
        username=username,
        search=search,
        status_filter=status_filter,
    )


@router.get("/admin/users/search", response_model=List[UserRead], tags=["admin"])
async def admin_search_users_endpoint(
    search: Optional[str] = None,
    name_contains: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
) -> List[UserRead]:
    return services.list_users(
        search=search or name_contains,
        status_filter=status_filter,
    )


@router.post("/admin/users", response_model=UserRead, tags=["admin"])
async def admin_create_user_endpoint(
    body: UserCreate,
    current_user: User = Depends(get_current_admin_user),
) -> UserRead:
    return services.create_user(body)


@router.patch("/admin/users/{user_id}/status", tags=["admin"])
async def admin_update_user_status_endpoint(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    updated = services.set_user_active(user_id, is_active=is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "message": "User status updated successfully",
        "user_id": user_id,
        "is_active": is_active,
        "status": updated.status,
    }


@router.patch("/admin/users/{user_id}/role", tags=["admin"])
async def admin_update_user_role_endpoint(
    user_id: int,
    body: UserRoleUpdateBody,
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    updated = services.set_user_role(user_id, role=body.role)
    if not updated:
        raise HTTPException(status_code=404, detail="User or role not found")
    return {
        "message": "User role updated successfully",
        "user_id": user_id,
        "role": updated.role,
        "role_id": updated.role_id,
    }


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
    try:
        return services.export_data(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/admin/export/download/{file_name}", tags=["admin"])
async def admin_export_download_endpoint(
    file_name: str,
    current_user: User = Depends(get_current_admin_user),
):
    file_path = services.get_export_file_path(file_name)
    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not found")

    download_name = file_path.name.split("-", 1)[1] if "-" in file_path.name else file_path.name
    return FileResponse(path=file_path, filename=download_name, media_type="text/csv; charset=utf-8")


@router.post("/manager-upgrade/request", response_model=ManagerUpgradeRequestRead, tags=["registration"])
async def create_manager_upgrade_request(
    body: ManagerUpgradeRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ManagerUpgradeRequestRead:
    try:
        req = ManagerUpgradeService.create_self_request(db, current_user.id, body.purpose)
        return ManagerUpgradeService.get_request_by_id(db, req.request_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/manager-upgrade/nominate", response_model=ManagerUpgradeRequestRead, tags=["registration"])
async def nominate_analyst_for_manager(
    body: ManagerUpgradeNominationCreate,
    current_user: User = Depends(get_current_manager_or_admin_user),
    db: Session = Depends(get_db),
) -> ManagerUpgradeRequestRead:
    if current_user.role != "manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manager can nominate analyst")
    try:
        req = ManagerUpgradeService.create_manager_nomination(
            db=db,
            manager_user_id=current_user.id,
            analyst_user_id=body.analyst_user_id,
            purpose=body.purpose,
        )
        return ManagerUpgradeService.get_request_by_id(db, req.request_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/manager-upgrade/requests", response_model=List[ManagerUpgradeRequestRead], tags=["registration"])
async def list_manager_upgrade_requests(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_manager_or_admin_user),
    db: Session = Depends(get_db),
) -> List[ManagerUpgradeRequestRead]:
    return ManagerUpgradeService.list_requests(db, status_filter=status_filter)


@router.get("/manager-upgrade/my-requests", response_model=List[ManagerUpgradeRequestRead], tags=["registration"])
async def list_my_manager_upgrade_requests(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[ManagerUpgradeRequestRead]:
    return ManagerUpgradeService.list_requests(db, target_user_id=current_user.id)


@router.post("/manager-upgrade/requests/{request_id}/vote", response_model=ManagerUpgradeRequestRead, tags=["registration"])
async def vote_manager_upgrade_request(
    request_id: int,
    body: ManagerUpgradeVoteRequest,
    current_user: User = Depends(get_current_manager_or_admin_user),
    db: Session = Depends(get_db),
) -> ManagerUpgradeRequestRead:
    try:
        return ManagerUpgradeService.vote_or_decide(
            db=db,
            request_id=request_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            action=body.action,
            note=body.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# Group 7: File & Data Ingestion
# ---------------------------------------------------------------------------


@router.post("/upload/data", response_model=UploadJobResponse, tags=["ingestion"])
async def upload_data_endpoint(
    file: UploadFile = File(...),
    type: str = "customers",  # type: ignore[assignment]
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UploadJobResponse:
    # Demo: chưa parse file; chỉ tạo job
    job = services.create_upload_job(type)
    services.update_upload_job(job.job_id, status="processing", progress=5)
    contents = await file.read()

    try:
        services.persist_upload_job_file(job.job_id, file.filename or "", contents)
        extracted = AIChatFileContextService.extract_context(filename=file.filename or "", content=contents)
        import_summary = None
        if (type or "customers").strip().lower() == "customers":
            import_summary = customer_intake_service.import_customer_file(
                filename=file.filename or "",
                content=contents,
                created_by=current_user.email,
                created_by_user_id=current_user.id,
                upload_batch_id=job.job_id,
            )
            try:
                log_action(
                    db,
                    user_id=current_user.id,
                    action="IMPORT_CUSTOMERS",
                    entity_type="CustomerImport",
                    entity_id=None,
                    new_value={
                        "job_id": job.job_id,
                        "file_name": file.filename,
                        "processed_count": import_summary.get("processed_count") if import_summary else None,
                        "success_count": import_summary.get("success_count") if import_summary else None,
                        "error_count": import_summary.get("error_count") if import_summary else None,
                    },
                )
                db.commit()
            except Exception:
                db.rollback()
        services.update_upload_job(
            job.job_id,
            status="completed",
            progress=100,
            result_url=f"/api/v1/jobs/{job.job_id}/content",
        )
        services.set_upload_job_content(
            job.job_id,
            {
                "file_name": extracted["file_name"],
                "row_count": extracted["row_count"],
                "column_count": extracted["column_count"],
                "columns": extracted["columns"],
                "rows": extracted["full_rows"],
                "context_text": extracted["context_text"],
                "import_summary": import_summary,
            },
        )
        return UploadJobResponse(
            job_id=job.job_id,
            status="completed",
            file_name=extracted["file_name"],
            row_count=extracted["row_count"],
            column_count=extracted["column_count"],
            columns=extracted["columns"],
            preview_rows=extracted["preview_rows"],
            context_text=(
                f"Đã xử lý {import_summary['success_count']}/{import_summary['processed_count']} dòng."
                if import_summary
                else extracted["context_text"]
            ),
            processed_count=import_summary["processed_count"] if import_summary else None,
            success_count=import_summary["success_count"] if import_summary else None,
            error_count=import_summary["error_count"] if import_summary else None,
            imported_customers=import_summary["imported_customers"] if import_summary else None,
            imported_applications=import_summary["imported_applications"] if import_summary else None,
            import_errors=import_summary.get("import_errors") if import_summary else None,
            error_reason_counts=import_summary.get("error_reason_counts") if import_summary else None,
            error=None,
        )
    except Exception as exc:
        try:
            log_action(
                db,
                user_id=current_user.id,
                action="IMPORT_CUSTOMERS_FAILED" if (type or "customers").strip().lower() == "customers" else "UPLOAD_FAILED",
                entity_type="CustomerImport",
                entity_id=None,
                new_value={
                    "job_id": job.job_id,
                    "file_name": file.filename,
                    "error": str(exc),
                },
            )
            db.commit()
        except Exception:
            db.rollback()
        services.update_upload_job(job.job_id, status="failed", progress=100)
        return UploadJobResponse(
            job_id=job.job_id,
            status="failed",
            file_name=file.filename,
            row_count=None,
            column_count=None,
            columns=None,
            preview_rows=None,
            context_text=None,
            error=str(exc),
        )


@router.get("/jobs/{job_id}/content", response_model=UploadJobContentResponse, tags=["ingestion"])
async def job_content_endpoint(
    job_id: str,
    offset: int = 0,
    limit: int = 200,
    current_user: User = Depends(get_current_active_user),
) -> UploadJobContentResponse:
    payload = services.get_upload_job_content(job_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload content not found")
    safe_offset = max(0, offset)
    safe_limit = max(1, min(limit, 500))
    rows = payload.get("rows") or []
    total_rows = len(rows)
    page_rows = rows[safe_offset:safe_offset + safe_limit]
    return UploadJobContentResponse(
        job_id=job_id,
        file_name=payload.get("file_name"),
        row_count=payload.get("row_count"),
        column_count=payload.get("column_count"),
        columns=payload.get("columns"),
        rows=page_rows,
        context_text=payload.get("context_text"),
        total_rows=total_rows,
        offset=safe_offset,
        limit=safe_limit,
        has_more=safe_offset + safe_limit < total_rows,
    )


@router.get("/jobs/{job_id}/errors", response_model=UploadJobErrorsResponse, tags=["ingestion"])
async def job_errors_endpoint(
    job_id: str,
    offset: int = 0,
    limit: int = 200,
    current_user: User = Depends(get_current_active_user),
) -> UploadJobErrorsResponse:
    payload = services.get_upload_job_content(job_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload content not found")

    import_summary = payload.get("import_summary") or {}
    errors = import_summary.get("import_errors") or []

    safe_offset = max(0, offset)
    safe_limit = max(1, min(limit, 1000))
    page_errors = errors[safe_offset:safe_offset + safe_limit]

    return UploadJobErrorsResponse(
        job_id=job_id,
        errors=page_errors,
        total_errors=len(errors),
        offset=safe_offset,
        limit=safe_limit,
        has_more=safe_offset + safe_limit < len(errors),
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse, tags=["ingestion"])
async def job_status_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
) -> JobStatusResponse:
    return services.get_job_status(job_id)


@router.get("/upload/history", response_model=List[UploadHistoryItemRead], tags=["ingestion"])
async def upload_history_endpoint(
    limit: int = 5,
    current_user: User = Depends(get_current_active_user),
) -> List[UploadHistoryItemRead]:
    user_filter = None if current_user.role in {"admin", "manager"} else current_user.id
    rows = services.list_upload_history(user_id=user_filter, limit=limit)
    return [UploadHistoryItemRead(**row) for row in rows]

