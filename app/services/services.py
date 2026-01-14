from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models.models import Alert, ChatSession, Customer, RiskModelInfo, UploadJob
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
    ConcentrationItem,
    ConcentrationResponse,
    CustomerCreate,
    CustomerHistoryItem,
    CustomerRead,
    CustomerSearchBody,
    CustomerUpdate,
    ExportRequestBody,
    ExportResponse,
    JobStatusResponse,
    PaginatedCustomers,
    PortfolioCompareBody,
    PortfolioCompareResponse,
    PortfolioKPIResponse,
    PortfolioTrendPoint,
    PortfolioTrendResponse,
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
    UploadJobResponse,
)


# In-memory "repositories" cho demo, thay bằng DB trong production
_customers: Dict[int, Customer] = {}
_customer_histories: Dict[int, List[CustomerHistoryItem]] = {}
_risk_models: List[RiskModelInfo] = []
_chat_sessions: Dict[str, ChatSession] = {}
_alerts: Dict[int, Alert] = {}
_upload_jobs: Dict[str, UploadJob] = {}
_audit_logs: List[AuditLogRead] = []
_alert_subscriptions: List[AlertSubscriptionRead] = []

_id_counters: Dict[str, int] = {"customer": 0, "alert": 0, "subscription": 0}


def _next_id(key: str) -> int:
    _id_counters[key] = _id_counters.get(key, 0) + 1
    return _id_counters[key]


# ---------------------------------------------------------------------------
# Risk / scoring helpers
# ---------------------------------------------------------------------------


def simple_credit_risk_score(payload: RiskRequest) -> dict:
    """
    Baseline heuristic scoring to keep the backend functional.
    Replace with a trained model (sklearn, SageMaker endpoint, etc.) later.
    """
    dti = (payload.debt / payload.income) if payload.income > 0 else 1.0  # debt-to-income
    # Normalize rough factors into [0,1]
    dti_factor = min(max(dti, 0.0), 2.0) / 2.0
    age_factor = 1.0 - min(max((payload.age - 18) / (70 - 18), 0.0), 1.0)
    history_factor = 1.0 - min(max(payload.credit_history_months / 120.0, 0.0), 1.0)

    risk_score = 0.6 * dti_factor + 0.2 * age_factor + 0.2 * history_factor
    if risk_score < 0.33:
        label = "low"
    elif risk_score < 0.66:
        label = "medium"
    else:
        label = "high"

    explanation = (
        f"DTI={dti:.2f}, age={payload.age}, history_months={payload.credit_history_months}. "
        f"Higher DTI / younger age / shorter history increases risk."
    )
    return {"risk_score": float(round(risk_score, 4)), "risk_label": label, "explanation": explanation}


def score_to_pd_lgd_ead(risk_score: float) -> RiskScoreDetail:
    pd = min(max(risk_score, 0.01), 0.99)
    lgd = 0.4 + 0.3 * risk_score
    ead = 100_000  # demo
    el = pd * lgd * ead
    return RiskScoreDetail(pd=pd, lgd=lgd, ead=ead, el=el, risk_score=risk_score, confidence=0.8, model_version="v1")


def explain_risk(customer_id: int) -> RiskExplainResponse:
    # Demo SHAP-like output
    return RiskExplainResponse(feature_importance={"income": -0.3, "debt": 0.4, "age": -0.1, "credit_history": -0.2})


# ---------------------------------------------------------------------------
# Customer services
# ---------------------------------------------------------------------------


def list_customers(
    page: int = 1,
    limit: int = 20,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> PaginatedCustomers:
    items = list(_customers.values())
    if search_name:
        items = [c for c in items if search_name.lower() in c.name.lower()]
    if risk_level:
        items = [c for c in items if c.risk_level == risk_level]

    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    page_items = [CustomerRead(**c.model_dump()) for c in items[start:end]]
    return PaginatedCustomers(items=page_items, total=total, page=page, limit=limit)


def get_customer(customer_id: int) -> Optional[CustomerRead]:
    c = _customers.get(customer_id)
    return CustomerRead(**c.model_dump()) if c else None


def create_customer(payload: CustomerCreate, created_by: str) -> CustomerRead:
    now = datetime.utcnow()
    cid = _next_id("customer")
    customer = Customer(
        id=cid,
        name=payload.name,
        age=payload.age,
        income=payload.income,
        credit_score=payload.credit_score,
        risk_level="medium",
        last_updated=now,
    )
    _customers[cid] = customer
    _customer_histories.setdefault(cid, []).append(
        CustomerHistoryItem(timestamp=now, changed_by=created_by, changes=payload.model_dump())
    )
    return CustomerRead(**customer.model_dump())


def update_customer(customer_id: int, payload: CustomerUpdate, updated_by: str) -> Optional[CustomerRead]:
    if customer_id not in _customers:
        return None
    current = _customers[customer_id]
    data = current.model_dump()
    changes: Dict[str, Any] = {}
    for field, value in payload.model_dump(exclude_unset=True).items():
        data[field] = value
        changes[field] = value
    data["last_updated"] = datetime.utcnow()
    updated = Customer(**data)
    _customers[customer_id] = updated
    _customer_histories.setdefault(customer_id, []).append(
        CustomerHistoryItem(timestamp=data["last_updated"], changed_by=updated_by, changes=changes)
    )
    return CustomerRead(**updated.model_dump())


def get_customer_history(customer_id: int) -> List[CustomerHistoryItem]:
    return _customer_histories.get(customer_id, [])


def advanced_customer_search(body: CustomerSearchBody) -> PaginatedCustomers:
    # Demo: chỉ dùng list_customers, thực tế sẽ parse filters phức tạp
    return list_customers(page=body.page, limit=body.limit)


# ---------------------------------------------------------------------------
# Portfolio / aggregation
# ---------------------------------------------------------------------------


def compute_portfolio_kpi(date_from: Optional[str], date_to: Optional[str], segment: Optional[str]) -> PortfolioKPIResponse:
    # Demo dùng dữ liệu giả
    return PortfolioKPIResponse(
        total_exposure=10_000_000,
        avg_pd=0.03,
        expected_loss=250_000,
        npl_ratio=0.05,
        var_99=500_000,
    )


def risk_distribution(group_by: Optional[str]) -> RiskDistributionResponse:
    buckets = {"low": 0.5, "medium": 0.3, "high": 0.2}
    chart_data = [{"bucket": k, "value": v} for k, v in buckets.items()]
    return RiskDistributionResponse(buckets=buckets, chart_data=chart_data)


def concentration(top_n: int = 10) -> ConcentrationResponse:
    items = [
        ConcentrationItem(name=f"Customer {i}", exposure=1_000_000 / i) for i in range(1, top_n + 1)
    ]
    return ConcentrationResponse(items=items)


def portfolio_trend(metric: str, interval: str) -> PortfolioTrendResponse:
    now = datetime.utcnow()
    points = [
        PortfolioTrendPoint(timestamp=now - timedelta(days=i), value=0.01 * (i + 1)) for i in range(10)
    ]
    return PortfolioTrendResponse(metric=metric, points=list(reversed(points)))


def portfolio_compare(body: PortfolioCompareBody) -> PortfolioCompareResponse:
    # Demo diff
    return PortfolioCompareResponse(diff_metrics={"expected_loss_diff": 10_000, "npl_diff": 0.01})


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------


def simple_chat_reply(message: str) -> str:
    """
    Placeholder chatbot behavior.
    Later: integrate Langflow/LangChain + AWS (Bedrock/Lambda) or your chosen LLM stack.
    """
    msg = message.strip().lower()
    if "risk" in msg or "rủi ro" in msg:
        return (
            "Bạn có thể gọi POST /api/v1/risk/score với income, debt, age, credit_history_months "
            "để nhận điểm rủi ro (0..1) và nhãn low/medium/high."
        )
    if "power bi" in msg:
        return "Backend này cung cấp API để Power BI/Flutter gọi lấy điểm rủi ro và dữ liệu tổng hợp."
    return "Mình đã nhận câu hỏi. Hãy mô tả dữ liệu khách hàng/bài toán để mình hướng dẫn endpoint phù hợp."


def upsert_chat_session(body: ChatRequest) -> tuple[ChatSession, ChatResponse]:
    session_id = body.session_id or str(uuid.uuid4())
    now = datetime.utcnow()
    session = _chat_sessions.get(
        session_id,
        ChatSession(session_id=session_id, started_at=now, last_activity_at=now, messages=[]),
    )
    # Append user message
    session.messages.append({"role": "user", "content": body.message, "timestamp": now.isoformat()})
    answer = simple_chat_reply(body.message)
    session.messages.append({"role": "assistant", "content": answer, "timestamp": now.isoformat()})
    session.last_activity_at = now
    _chat_sessions[session_id] = session

    response = ChatResponse(answer=answer, extracted_metrics=None, sources=None)
    return session, response


def list_chat_sessions(user_id: Optional[int]) -> List[ChatSessionSummary]:
    return [
        ChatSessionSummary(
            session_id=s.session_id,
            started_at=s.started_at,
            last_activity_at=s.last_activity_at,
        )
        for s in _chat_sessions.values()
    ]


def get_chat_session_messages(session_id: str) -> List[ChatMessage]:
    session = _chat_sessions.get(session_id)
    if not session:
        return []
    return [
        ChatMessage(role=m["role"], content=m["content"], timestamp=datetime.fromisoformat(m["timestamp"]))
        for m in session.messages
    ]


def suggest_queries(customer_id: Optional[int]) -> List[str]:
    return [
        "Tổng dư nợ và PD trung bình của portfolio hiện tại là bao nhiêu?",
        "Liệt kê top 10 khách hàng có Expected Loss cao nhất.",
        "So sánh NPL ratio quý này với quý trước.",
    ]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


def list_alerts(status: Optional[str], type_: Optional[str]) -> List[AlertRead]:
    alerts = list(_alerts.values())
    if status:
        alerts = [a for a in alerts if a.status == status]
    if type_:
        alerts = [a for a in alerts if a.type == type_]
    return [
        AlertRead(
            id=a.id,
            type=a.type,
            status=a.status,
            message=a.message,
            created_at=a.created_at,
        )
        for a in alerts
    ]


def subscribe_alerts(body: AlertSubscriptionCreate) -> AlertSubscriptionRead:
    sid = _next_id("subscription")
    sub = AlertSubscriptionRead(subscription_id=sid)
    _alert_subscriptions.append(sub)
    return sub


def resolve_alert(alert_id: int, body: AlertResolveBody) -> Optional[AlertRead]:
    alert = _alerts.get(alert_id)
    if not alert:
        return None
    alert.status = "resolved"
    return AlertRead(
        id=alert.id,
        type=alert.type,
        status=alert.status,
        message=f"{alert.message} (resolved: {body.reason})",
        created_at=alert.created_at,
    )


# ---------------------------------------------------------------------------
# Admin / system
# ---------------------------------------------------------------------------


def list_users() -> List[UserRead]:
    # Thực tế sẽ dùng DB; ở đây demo trống để bạn tự nối
    return []


def create_user(user: UserCreate) -> UserRead:
    # Demo trả giả; thực tế hash password và lưu DB
    return UserRead(id=1, email=user.email, full_name=user.full_name, is_active=True, is_admin=user.is_admin)


def list_audit_logs(from_date: Optional[str], to_date: Optional[str], user_id: Optional[int]) -> List[AuditLogRead]:
    return _audit_logs


def export_data(body: ExportRequestBody) -> ExportResponse:
    # Demo presigned URL giả
    return ExportResponse(file_url="https://example-bucket.s3.amazonaws.com/export/demo.csv")


# ---------------------------------------------------------------------------
# File / ingestion
# ---------------------------------------------------------------------------


def create_upload_job(job_type: str) -> UploadJobResponse:
    job_id = str(uuid.uuid4())
    job = UploadJob(job_id=job_id, status="pending", progress=0.0, result_url=None)
    _upload_jobs[job_id] = job
    return UploadJobResponse(job_id=job_id, status=job.status)


def get_job_status(job_id: str) -> JobStatusResponse:
    job = _upload_jobs.get(job_id)
    if not job:
        return JobStatusResponse(job_id=job_id, progress=0.0, result_url=None)
    return JobStatusResponse(job_id=job.job_id, progress=job.progress, result_url=job.result_url)
