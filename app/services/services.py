from __future__ import annotations

import csv
import json
import logging
import statistics
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import case, desc, func, literal, or_
from sqlalchemy.orm import aliased

from app.core.security import normalize_role_name, pwd_context
from app.db.models import (
    AlertDB,
    AlertSubscriptionDB,
    AuditLogDB,
    CustomerDB,
    LoanApplicationDB,
    RiskPredictionDB,
    RoleDB,
    UserDB,
)
from app.db.session import SessionLocal
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
    PortfolioRiskFactorItem,
    PortfolioRiskFactorsResponse,
    PortfolioTrendPoint,
    PortfolioTrendResponse,
    RiskExplainResponse,
    RiskRequest,
    RiskScoreDetail,
    RiskDistributionResponse,
    UploadJobResponse,
    UserCreate,
    UserRead,
)
from app.services.audit_service import log_action, to_audit_log_read
from app.services import customer_intake_service
from app.services.risk_service import compute_heuristic_state

logger = logging.getLogger(__name__)

_customers: Dict[int, Customer] = {}
_customer_histories: Dict[int, List[CustomerHistoryItem]] = {}
_risk_models: List[RiskModelInfo] = []
_chat_sessions: Dict[str, ChatSession] = {}
_alerts: Dict[int, AlertRead] = {}
_upload_jobs: Dict[str, UploadJob] = {}
_upload_job_contents: Dict[str, Dict[str, Any]] = {}
_UPLOAD_STORAGE_DIR = Path(__file__).resolve().parents[2] / ".ai_chat_uploads"
_EXPORT_STORAGE_DIR = Path(__file__).resolve().parents[2] / ".exports"
_alert_subscriptions: List[AlertSubscriptionRead] = []

_id_counters: Dict[str, int] = {"customer": 0, "alert": 0, "subscription": 0}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _next_id(key: str) -> int:
    _id_counters[key] = _id_counters.get(key, 0) + 1
    return _id_counters[key]


def _to_customer_read(customer: Customer) -> CustomerRead:
    return CustomerRead(**customer.model_dump())


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _display_score_from_credit_score(credit_score: Optional[int]) -> float:
    """Map stored credit_score to 0–100 for histograms (FICO-like → normalized, else as-is)."""
    v = float(credit_score) if credit_score is not None else 650.0
    if v <= 100.0:
        return max(0.0, min(100.0, v))
    return max(0.0, min(100.0, (v - 300.0) / 550.0 * 100.0))


def _display_score_from_prediction_row(row: RiskPredictionDB) -> float:
    """Use (1 − PD)×100 so higher = healthier, aligned with typical 'điểm' UX."""
    if row.risk_score is not None:
        pdv = max(0.0, min(1.0, _to_float(row.risk_score)))
        return max(0.0, min(100.0, (1.0 - pdv) * 100.0))
    level = str(row.risk_level or "").strip().lower()
    if level == "low":
        return 85.0
    if level == "high":
        return 35.0
    return 55.0


def _score_histogram_and_stats(display_scores: List[float]) -> tuple[List[Dict[str, Any]], Dict[str, float]]:
    bin_specs: List[tuple[str, float, float]] = [
        ("0-20", 0.0, 20.0),
        ("20-40", 20.0, 40.0),
        ("40-60", 40.0, 60.0),
        ("60-80", 60.0, 80.0),
        ("80-100", 80.0, 100.0001),
    ]
    score_buckets: List[Dict[str, Any]] = []
    for label, lo, hi in bin_specs:
        c = sum(1 for s in display_scores if lo <= s < hi)
        score_buckets.append({"range": label, "count": c})
    if not display_scores:
        return score_buckets, {"mean": 0.0, "median": 0.0, "std_dev": 0.0}
    std = statistics.pstdev(display_scores) if len(display_scores) > 1 else 0.0
    return score_buckets, {
        "mean": round(float(statistics.mean(display_scores)), 1),
        "median": round(float(statistics.median(display_scores)), 1),
        "std_dev": round(float(std), 1),
    }


def _safe_risk_credit_score(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    try:
        v = int(float(raw))
    except (TypeError, ValueError):
        return None
    return max(0, min(1000, v))


def _safe_risk_interest_rate_pct(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None
    return min(v, 100.0)


def _resolve_user_role(user: UserDB, role_name: Optional[str] = None) -> str:
    if role_name:
        return normalize_role_name(role_name)

    if user.user_type:
        return normalize_role_name(user.user_type)

    return "viewer"


def _is_user_active(status: Optional[str]) -> bool:
    normalized = (status or "").strip().lower()
    if not normalized:
        return True
    return normalized in {"approved", "verified", "active", "true"}


def _to_user_read(user: UserDB, role_name: Optional[str] = None) -> UserRead:
    resolved_role = _resolve_user_role(user, role_name)
    return UserRead(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        full_name=user.full_name,
        role=resolved_role,
        status=user.status,
        is_active=_is_user_active(user.status),
        created_at=user.created_at,
    )


def simple_credit_risk_score(payload: RiskRequest) -> dict:
    from app.services import risk_service

    return risk_service.simple_credit_risk_score(payload)


def score_to_pd_lgd_ead(risk_score: float) -> RiskScoreDetail:
    pd = min(max(risk_score, 0.01), 0.99)
    lgd = 0.4 + 0.3 * risk_score
    ead = 100_000
    el = pd * lgd * ead
    return RiskScoreDetail(pd=pd, lgd=lgd, ead=ead, el=el, risk_score=risk_score, confidence=0.8, model_version="v1")


def explain_risk(customer_id: int) -> RiskExplainResponse:
    return RiskExplainResponse(feature_importance={"income": -0.3, "debt": 0.4, "age": -0.1, "credit_history": -0.2})


def list_customers(
    page: int = 1,
    limit: int = 20,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> PaginatedCustomers:
    return customer_intake_service.list_customers(
        page=page,
        limit=limit,
        search_name=search_name,
        risk_level=risk_level,
    )


def get_customer(customer_id: int) -> Optional[CustomerRead]:
    return customer_intake_service.get_customer(customer_id)


def create_customer(payload: CustomerCreate, created_by: str) -> CustomerRead:
    return customer_intake_service.create_customer(payload, created_by=created_by, created_by_user_id=None)


def update_customer(customer_id: int, payload: CustomerUpdate, updated_by: str) -> Optional[CustomerRead]:
    return customer_intake_service.update_customer(
        customer_id,
        payload,
        updated_by=updated_by,
        updated_by_user_id=None,
    )


def get_customer_history(customer_id: int) -> List[CustomerHistoryItem]:
    return customer_intake_service.get_customer_history(customer_id)


def advanced_customer_search(body: CustomerSearchBody) -> PaginatedCustomers:
    return customer_intake_service.advanced_customer_search(body)


def compute_portfolio_kpi(date_from: Optional[str], date_to: Optional[str], segment: Optional[str]) -> PortfolioKPIResponse:
    db = SessionLocal()
    try:
        applications = db.query(LoanApplicationDB).all()
        total_exposure = sum(_to_float(item.loan_amount) for item in applications)

        predictions = db.query(RiskPredictionDB).all()
        if predictions:
            avg_pd = sum(_to_float(p.risk_score) for p in predictions) / len(predictions)
        else:
            avg_pd = 0.0

        delinquent_statuses = {"rejected", "overdue", "default", "npl", "doubtful", "loss"}
        delinquent_count = sum(1 for item in applications if str(item.loan_status or "").strip().lower() in delinquent_statuses)
        total_applications = len(applications)
        npl_ratio = (delinquent_count / total_applications) if total_applications else 0.0

        # Approximation without full LGD/EAD data: EL ~= Exposure * PD * 45%
        expected_loss = total_exposure * avg_pd * 0.45
        var_99 = expected_loss * 2.33

        return PortfolioKPIResponse(
            total_exposure=round(total_exposure, 2),
            avg_pd=round(avg_pd, 6),
            expected_loss=round(expected_loss, 2),
            npl_ratio=round(npl_ratio, 6),
            var_99=round(var_99, 2),
        )
    finally:
        db.close()


def risk_distribution(group_by: Optional[str]) -> RiskDistributionResponse:
    db = SessionLocal()
    try:
        bucket_counts = {"low": 0, "medium": 0, "high": 0}
        rows = (
            db.query(RiskPredictionDB)
            .order_by(desc(RiskPredictionDB.predicted_at), desc(RiskPredictionDB.prediction_id))
            .all()
        )

        display_scores: List[float] = []
        if rows:
            seen_customer_ids: set[int] = set()
            for row in rows:
                if row.customer_id is not None:
                    if row.customer_id in seen_customer_ids:
                        continue
                    seen_customer_ids.add(row.customer_id)
                level = str(row.risk_level or "").strip().lower()
                if level not in bucket_counts:
                    score = _to_float(row.risk_score)
                    level = "low" if score < 0.33 else "medium" if score < 0.66 else "high"
                bucket_counts[level] += 1
                display_scores.append(_display_score_from_prediction_row(row))
        else:
            customers = db.query(CustomerDB).all()
            for customer in customers:
                credit_score = customer.credit_score if customer.credit_score is not None else 650
                if credit_score >= 750:
                    bucket_counts["low"] += 1
                elif credit_score >= 650:
                    bucket_counts["medium"] += 1
                else:
                    bucket_counts["high"] += 1
                display_scores.append(_display_score_from_credit_score(customer.credit_score))

        total = max(1, sum(bucket_counts.values()))
        buckets = {k: round(v / total, 4) for k, v in bucket_counts.items()}
        chart_data = [{"bucket": k, "value": v, "count": bucket_counts[k]} for k, v in buckets.items()]
        score_buckets, score_stats = _score_histogram_and_stats(display_scores)
        return RiskDistributionResponse(
            buckets=buckets,
            chart_data=chart_data,
            score_buckets=score_buckets,
            score_stats=score_stats,
        )
    finally:
        db.close()


# Maps heuristic engine keys → UI i18n keys used on the risk analyze chart.
_ENGINE_TO_UI_FACTOR: Dict[str, str] = {
    "dti": "debt_ratio",
    "history": "credit_history",
    "employment": "employment",
    "loan_type": "loan_amount",
    "interest": "loan_amount",
    "term": "loan_amount",
    "collateral": "loan_amount",
    "age": "income",
    "credit_score": "income",
}

_UI_FACTOR_ORDER = ("debt_ratio", "credit_history", "employment", "loan_amount", "income")


def portfolio_risk_factor_impact() -> PortfolioRiskFactorsResponse:
    """
    Mean (weight × factor) contributions across customers + latest loan application,
    rolled up to the five chart categories. Same engine as POST /risk/score.
    """
    db = SessionLocal()
    try:
        subq = (
            db.query(
                LoanApplicationDB.customer_id.label("cid"),
                func.max(LoanApplicationDB.application_id).label("max_aid"),
            )
            .group_by(LoanApplicationDB.customer_id)
            .subquery()
        )
        la = aliased(LoanApplicationDB)
        rows = (
            db.query(CustomerDB, la)
            .outerjoin(subq, CustomerDB.customer_id == subq.c.cid)
            .outerjoin(la, la.application_id == subq.c.max_aid)
            .all()
        )

        ui_totals: Dict[str, float] = {k: 0.0 for k in _UI_FACTOR_ORDER}
        n = 0
        for customer, app in rows:
            try:
                income = max(_to_float(customer.monthly_income), 1.0)
                loan_amt = _to_float(app.loan_amount) if app is not None else 0.0
                term_m = int(app.loan_term) if app is not None and app.loan_term else 0
                if loan_amt > 0 and term_m > 0:
                    monthly_pay = loan_amt / float(term_m)
                elif loan_amt > 0:
                    monthly_pay = loan_amt / 12.0
                else:
                    monthly_pay = income * 0.35

                age = int(customer.age) if customer.age is not None else 35
                age = min(max(age, 18), 120)

                hist_m = term_m if term_m > 0 else 12

                ir_raw = app.interest_rate if app is not None and app.interest_rate is not None else None
                ir = _safe_risk_interest_rate_pct(ir_raw)
                lt = (app.loan_type or "").strip() if app is not None else None
                cv = _to_float(app.collateral_value) if app is not None and app.collateral_value is not None else None
                if cv <= 0:
                    cv = None

                cs = _safe_risk_credit_score(customer.credit_score)
                payload = RiskRequest(
                    income=income,
                    debt=max(monthly_pay, 0.0),
                    age=age,
                    credit_history_months=max(hist_m, 0),
                    credit_score=cs,
                    loan_type=lt or None,
                    interest_rate=ir,
                    loan_term_months=term_m if term_m > 0 else None,
                    collateral_value=cv,
                    employment_status=(customer.employment_status or "").strip() or None,
                )
                h = compute_heuristic_state(payload)
                for eng_key, val in h.contributions.items():
                    ui_key = _ENGINE_TO_UI_FACTOR.get(eng_key)
                    if ui_key:
                        ui_totals[ui_key] += float(val)
                n += 1
            except Exception as exc:
                logger.warning(
                    "portfolio_risk_factor_impact skip customer_id=%s: %s",
                    getattr(customer, "customer_id", "?"),
                    exc,
                )
                continue

        if n == 0:
            return PortfolioRiskFactorsResponse(
                items=[PortfolioRiskFactorItem(factor_key=k, impact=0.0) for k in _UI_FACTOR_ORDER],
                sample_size=0,
            )

        total_mass = sum(ui_totals.values())
        if total_mass <= 1e-12:
            eq = round(100.0 / len(_UI_FACTOR_ORDER), 1)
            return PortfolioRiskFactorsResponse(
                items=[PortfolioRiskFactorItem(factor_key=k, impact=eq) for k in _UI_FACTOR_ORDER],
                sample_size=n,
            )

        items = [
            PortfolioRiskFactorItem(
                factor_key=k,
                impact=round(100.0 * ui_totals[k] / total_mass, 1),
            )
            for k in _UI_FACTOR_ORDER
        ]
        return PortfolioRiskFactorsResponse(items=items, sample_size=n)
    finally:
        db.close()


def concentration(top_n: Optional[int] = None, group_by: Optional[str] = None) -> ConcentrationResponse:
    """
    Concentration by exposure (loan_amount sum), descending.

    group_by:
      - customer (default): one row per customer_id, label = full name.
      - occupation | sector | industry: one row per Customer.occupation (trimmed);
        empty/null occupation -> sentinel name __unspecified__ (client translates).
    """
    db = SessionLocal()
    try:
        mode = (group_by or "customer").strip().lower()
        if mode in {"occupation", "sector", "industry"}:
            occ = CustomerDB.occupation
            trimmed = func.trim(func.coalesce(occ, ""))
            sector_key = case(
                (or_(occ.is_(None), trimmed == "", occ == ""), literal("__unspecified__")),
                else_=func.trim(occ),
            ).label("sector_key")
            query = (
                db.query(sector_key, func.sum(LoanApplicationDB.loan_amount).label("exposure"))
                .select_from(LoanApplicationDB)
                .join(CustomerDB, LoanApplicationDB.customer_id == CustomerDB.customer_id)
                .group_by(sector_key)
                .order_by(desc("exposure"))
            )
            limit = top_n if top_n is not None and top_n > 0 else 25
            grouped = query.limit(limit).all()
            items = [
                ConcentrationItem(name=str(row.sector_key or "__unspecified__"), exposure=round(_to_float(row.exposure), 2))
                for row in grouped
            ]
            return ConcentrationResponse(items=items)

        query = (
            db.query(
                LoanApplicationDB.customer_id,
                func.sum(LoanApplicationDB.loan_amount).label("exposure"),
            )
            .group_by(LoanApplicationDB.customer_id)
            .order_by(desc("exposure"))
        )
        if top_n is not None and top_n > 0:
            query = query.limit(top_n)
        grouped = query.all()

        customer_ids = [row.customer_id for row in grouped if row.customer_id is not None]
        names = {
            row.customer_id: row.full_name
            for row in db.query(CustomerDB.customer_id, CustomerDB.full_name)
            .filter(CustomerDB.customer_id.in_(customer_ids))
            .all()
        } if customer_ids else {}

        items = [
            ConcentrationItem(
                name=names.get(row.customer_id) or f"Customer {row.customer_id}",
                exposure=round(_to_float(row.exposure), 2),
            )
            for row in grouped
        ]
        return ConcentrationResponse(items=items)
    finally:
        db.close()


def portfolio_trend(metric: str, interval: str) -> PortfolioTrendResponse:
    db = SessionLocal()
    try:
        metric_name = (metric or "total_exposure").strip().lower()
        rows = db.query(LoanApplicationDB).all()

        buckets: Dict[str, float] = {}
        for row in rows:
            dt = row.application_date
            if dt is None:
                created_at = row.created_at
                dt = created_at.date() if created_at else None
            if dt is None:
                continue
            key = dt.strftime("%Y-%m")
            if metric_name in {"total_exposure", "value", "portfolio_value"}:
                buckets[key] = buckets.get(key, 0.0) + _to_float(row.loan_amount)
            else:
                buckets[key] = buckets.get(key, 0.0) + 1.0

        points = [
            PortfolioTrendPoint(
                timestamp=datetime.strptime(month_key, "%Y-%m"),
                value=round(value, 4),
            )
            for month_key, value in sorted(buckets.items())
        ]
        return PortfolioTrendResponse(metric=metric_name, points=points)
    finally:
        db.close()


def portfolio_compare(body: PortfolioCompareBody) -> PortfolioCompareResponse:
    # Current implementation compares current portfolio with a simple trailing period baseline.
    db = SessionLocal()
    try:
        applications = db.query(LoanApplicationDB).all()
        if not applications:
            return PortfolioCompareResponse(diff_metrics={"expected_loss_diff": 0.0, "npl_diff": 0.0})

        total_exposure = sum(_to_float(item.loan_amount) for item in applications)
        delinquent_statuses = {"rejected", "overdue", "default", "npl", "doubtful", "loss"}
        current_npl = (
            sum(1 for item in applications if str(item.loan_status or "").strip().lower() in delinquent_statuses)
            / max(len(applications), 1)
        )

        predictions = db.query(RiskPredictionDB).all()
        avg_pd = (sum(_to_float(p.risk_score) for p in predictions) / len(predictions)) if predictions else 0.0
        current_el = total_exposure * avg_pd * 0.45

        baseline_el = current_el * 0.92
        baseline_npl = current_npl * 0.95
        return PortfolioCompareResponse(
            diff_metrics={
                "expected_loss_diff": round(current_el - baseline_el, 2),
                "npl_diff": round(current_npl - baseline_npl, 6),
            }
        )
    finally:
        db.close()


def simple_chat_reply(message: str) -> str:
    msg = message.strip().lower()
    if "risk" in msg or "rui ro" in msg:
        return (
            "Ban co the goi POST /api/v1/risk/score voi income, debt, age, credit_history_months "
            "de nhan diem rui ro (0..1) va nhan low/medium/high."
        )
    if "power bi" in msg:
        return "Backend nay cung cap API de Power BI/Flutter goi lay diem rui ro va du lieu tong hop."
    return "Minh da nhan cau hoi. Hay mo ta du lieu khach hang/bai toan de minh huong dan endpoint phu hop."


def upsert_chat_session(body: ChatRequest) -> tuple[ChatSession, ChatResponse]:
    session_id = body.session_id or str(uuid.uuid4())
    now = _now()
    session = _chat_sessions.get(
        session_id,
        ChatSession(session_id=session_id, started_at=now, last_activity_at=now, messages=[]),
    )
    session.messages.append({"role": "user", "content": body.message, "timestamp": now.isoformat()})
    answer = simple_chat_reply(body.message)
    session.messages.append({"role": "assistant", "content": answer, "timestamp": now.isoformat()})
    session.last_activity_at = now
    _chat_sessions[session_id] = session
    return session, ChatResponse(answer=answer, extracted_metrics=None, sources=None)


def list_chat_sessions(user_id: Optional[int]) -> List[ChatSessionSummary]:
    return [
        ChatSessionSummary(session_id=s.session_id, started_at=s.started_at, last_activity_at=s.last_activity_at)
        for s in _chat_sessions.values()
    ]


def get_chat_session_messages(session_id: str) -> List[ChatMessage]:
    session = _chat_sessions.get(session_id)
    if not session:
        return []
    return [ChatMessage(role=m["role"], content=m["content"], timestamp=datetime.fromisoformat(m["timestamp"])) for m in session.messages]


def suggest_queries(customer_id: Optional[int]) -> List[str]:
    return [
        "Tong du no va PD trung binh cua portfolio hien tai la bao nhieu?",
        "Liet ke top 10 khach hang co Expected Loss cao nhat.",
        "So sanh NPL ratio quy nay voi quy truoc.",
    ]


def _create_alert_if_missing(
    db,
    *,
    existing_keys: set[tuple[int, str, str]],
    next_alert_id: list[int],
    customer_id: Optional[int],
    alert_type: str,
    severity: str,
    message: str,
    facility_id: Optional[int] = None,
) -> None:
    if customer_id is None:
        return
    key = (int(customer_id), alert_type, severity)
    if key in existing_keys:
        return

    row = AlertDB(
        alert_id=next_alert_id[0],
        facility_id=facility_id,
        customer_id=int(customer_id),
        alert_type=alert_type,
        severity=severity,
        message=message,
        is_resolved=False,
        created_at=_now(),
    )
    db.add(row)
    existing_keys.add(key)
    next_alert_id[0] += 1


def _approved_customers_by_latest_application(db) -> set[int]:
    # Newest application per customer by business time, then id (not id alone — ids may not reflect timeline).
    rows = (
        db.query(LoanApplicationDB.customer_id, LoanApplicationDB.loan_status)
        .filter(LoanApplicationDB.customer_id.isnot(None))
        .order_by(desc(LoanApplicationDB.created_at), desc(LoanApplicationDB.application_id))
        .all()
    )
    approved_customers: set[int] = set()
    seen_customers: set[int] = set()
    for customer_id, loan_status in rows:
        if customer_id is None:
            continue
        cid = int(customer_id)
        if cid in seen_customers:
            continue
        seen_customers.add(cid)
        normalized_status = str(loan_status or "").strip().lower()
        if normalized_status in {"approved", "disbursed"}:
            approved_customers.add(cid)
    return approved_customers


def _sync_alerts_from_live_data(db) -> None:
    # Keep idempotency by checking all existing alerts first (open + resolved),
    # so resolving an alert does not immediately recreate another duplicate.
    existing_rows = db.query(AlertDB).all()
    existing_keys: set[tuple[int, str, str]] = set()
    next_alert_id = [int((db.query(func.max(AlertDB.alert_id)).scalar() or 0) + 1)]
    customer_name_map = {
        int(row.customer_id): str(row.full_name or "").strip()
        for row in db.query(CustomerDB.customer_id, CustomerDB.full_name).filter(CustomerDB.customer_id.isnot(None)).all()
    }
    for row in existing_rows:
        if row.customer_id is None:
            continue
        existing_keys.add((int(row.customer_id), str(row.alert_type), str(row.severity)))

    # Only keep customers whose latest loan application is approved.
    approved_customers_latest = _approved_customers_by_latest_application(db)

    # Rule 1: latest risk prediction per customer -> high_pd alert.
    prediction_rows = (
        db.query(RiskPredictionDB)
        .order_by(desc(RiskPredictionDB.predicted_at), desc(RiskPredictionDB.prediction_id))
        .limit(5000)
        .all()
    )
    seen_prediction_customers: set[int] = set()
    for row in prediction_rows:
        if row.customer_id is None:
            continue
        cid = int(row.customer_id)
        if cid not in approved_customers_latest:
            continue
        if cid in seen_prediction_customers:
            continue
        seen_prediction_customers.add(cid)

        score = _to_float(row.risk_score, default=-1.0)
        if score < 0:
            continue
        level = str(row.risk_level or "").strip().lower()
        severity: Optional[str] = None

        if level == "high":
            severity = "critical" if score >= 0.85 else "high"
        elif level == "medium":
            severity = "medium"
        elif score >= 0.85:
            severity = "critical"
        elif score >= 0.70:
            severity = "high"
        elif score >= 0.55:
            severity = "medium"
        if not severity:
            continue

        _create_alert_if_missing(
            db,
            existing_keys=existing_keys,
            next_alert_id=next_alert_id,
            customer_id=cid,
            alert_type="high_pd",
            severity=severity,
            message=(
                f"{customer_name_map.get(cid) or f'Customer {cid}'} has elevated predicted risk score ({score:.2f})."
            ),
            facility_id=None,
        )

    # Rule 1b: fallback from customer credit score when predictions are missing/outdated.
    customers = (
        db.query(CustomerDB.customer_id, CustomerDB.credit_score)
        .filter(CustomerDB.customer_id.isnot(None))
        .all()
    )
    for customer_id, credit_score in customers:
        if customer_id is None or credit_score is None:
            continue
        cid = int(customer_id)
        if cid not in approved_customers_latest:
            continue
        score = int(round(_to_float(credit_score, default=-1.0)))
        if score < 0:
            continue
        severity: Optional[str] = None
        # CIC-like grouping: <430 high, 431-569 medium, >=570 no alert.
        if score < 430:
            severity = "critical"
        elif score < 570:
            severity = "high"
        if not severity:
            continue

        _create_alert_if_missing(
            db,
            existing_keys=existing_keys,
            next_alert_id=next_alert_id,
            customer_id=cid,
            alert_type="high_pd",
            severity=severity,
            message=(
                f"{customer_name_map.get(cid) or f'Customer {cid}'} has weak credit score ({score})."
            ),
            facility_id=None,
        )

    # Rule 2: latest loan status per customer -> overdue/delinquency alert.
    application_rows = (
        db.query(LoanApplicationDB)
        .order_by(desc(LoanApplicationDB.created_at), desc(LoanApplicationDB.application_id))
        .limit(5000)
        .all()
    )
    seen_application_customers: set[int] = set()
    for row in application_rows:
        if row.customer_id is None:
            continue
        cid = int(row.customer_id)
        if cid not in approved_customers_latest:
            continue
        if cid in seen_application_customers:
            continue
        seen_application_customers.add(cid)

        status = str(row.loan_status or "").strip().lower()
        if status in {"default", "npl", "doubtful", "loss"}:
            _create_alert_if_missing(
                db,
                existing_keys=existing_keys,
                next_alert_id=next_alert_id,
                customer_id=cid,
                alert_type="delinquency",
                severity="critical",
                message=(
                    f"{customer_name_map.get(cid) or f'Customer {cid}'} has delinquent loan status: {status}."
                ),
                facility_id=None,
            )
        elif status in {"overdue", "arrears"}:
            _create_alert_if_missing(
                db,
                existing_keys=existing_keys,
                next_alert_id=next_alert_id,
                customer_id=cid,
                alert_type="overdue",
                severity="high",
                message=(
                    f"{customer_name_map.get(cid) or f'Customer {cid}'} has overdue loan status: {status}."
                ),
                facility_id=None,
            )

    db.commit()


def list_alerts(status: Optional[str], type_: Optional[str]) -> List[AlertRead]:
    db = SessionLocal()
    try:
        try:
            _sync_alerts_from_live_data(db)
        except Exception:
            # Do not break alerts API when sync hits inconsistent rows/concurrency.
            db.rollback()
        approved_customers_latest = _approved_customers_by_latest_application(db)

        query = (
            db.query(AlertDB)
            .filter(
                AlertDB.alert_type == "high_pd",
                AlertDB.severity.in_(["medium", "high", "critical"]),
            )
            .order_by(desc(AlertDB.created_at), desc(AlertDB.alert_id))
        )
        if status:
            expected = status.strip().lower()
            if expected in {"open", "active", "pending"}:
                query = query.filter(AlertDB.is_resolved.is_(False))
            elif expected == "resolved":
                query = query.filter(AlertDB.is_resolved.is_(True))
        if type_:
            query = query.filter(AlertDB.alert_type == type_)
        rows = query.limit(2000).all()
        rows = [row for row in rows if row.customer_id is not None and int(row.customer_id) in approved_customers_latest]
        return [
            AlertRead(
                alert_id=row.alert_id,
                facility_id=row.facility_id,
                customer_id=row.customer_id,
                customer_name=row.customer.full_name if row.customer else None,
                alert_type=row.alert_type,
                severity=row.severity,
                message=row.message,
                is_resolved=row.is_resolved,
                created_at=row.created_at,
                resolved_at=row.resolved_at,
            )
            for row in rows
        ]
    finally:
        db.close()


def subscribe_alerts(body: AlertSubscriptionCreate) -> AlertSubscriptionRead:
    db = SessionLocal()
    try:
        existing = (
            db.query(AlertSubscriptionDB)
            .filter(
                AlertSubscriptionDB.user_id == body.user_id,
                AlertSubscriptionDB.alert_type == body.alert_type,
                AlertSubscriptionDB.alert_severity == body.alert_severity,
            )
            .first()
        )
        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.commit()
                db.refresh(existing)
            return AlertSubscriptionRead.model_validate(existing)

        next_id = (db.query(func.max(AlertSubscriptionDB.subscription_id)).scalar() or 0) + 1
        row = AlertSubscriptionDB(
            subscription_id=next_id,
            user_id=body.user_id,
            alert_type=body.alert_type,
            alert_severity=body.alert_severity,
            is_active=True,
            created_at=_now(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return AlertSubscriptionRead.model_validate(row)
    finally:
        db.close()


def resolve_alert(alert_id: int, body: AlertResolveBody, actor_user_id: Optional[int] = None) -> Optional[AlertRead]:
    db = SessionLocal()
    try:
        row = db.query(AlertDB).filter(AlertDB.alert_id == alert_id).first()
        if not row:
            return None
        old_payload = {
            "alert_id": row.alert_id,
            "customer_id": row.customer_id,
            "alert_type": row.alert_type,
            "severity": row.severity,
            "message": row.message,
            "is_resolved": row.is_resolved,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        }
        row.is_resolved = True
        row.resolved_at = _now()
        row.message = f"{row.message or ''} (resolved: {body.reason})".strip()
        new_payload = {
            "alert_id": row.alert_id,
            "customer_id": row.customer_id,
            "alert_type": row.alert_type,
            "severity": row.severity,
            "message": row.message,
            "is_resolved": row.is_resolved,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            "reason": body.reason,
        }
        log_action(
            db,
            user_id=actor_user_id,
            action="RESOLVE_ALERT",
            entity_type="Alert",
            entity_id=row.alert_id,
            old_value=old_payload,
            new_value=new_payload,
        )
        db.commit()
        db.refresh(row)
        return AlertRead(
            alert_id=row.alert_id,
            facility_id=row.facility_id,
            customer_id=row.customer_id,
            customer_name=row.customer.full_name if row.customer else None,
            alert_type=row.alert_type,
            severity=row.severity,
            message=row.message,
            is_resolved=row.is_resolved,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
        )
    finally:
        db.close()


def list_users(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[UserRead]:
    db = SessionLocal()
    try:
        query = (
            db.query(UserDB, RoleDB.role_name)
            .outerjoin(RoleDB, RoleDB.role_id == UserDB.role_id)
            .order_by(UserDB.created_at.desc())
        )

        if user_id is not None:
            query = query.filter(UserDB.user_id == user_id)

        if username:
            query = query.filter(func.lower(UserDB.username) == username.strip().lower())

        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(UserDB.username).like(pattern),
                    func.lower(UserDB.email).like(pattern),
                    func.lower(func.coalesce(UserDB.full_name, "")).like(pattern),
                )
            )

        if status_filter:
            normalized_status = status_filter.strip().lower()
            if normalized_status == "active":
                query = query.filter(
                    or_(
                        UserDB.status.is_(None),
                        func.lower(UserDB.status).in_(["approved", "verified", "active", "true"]),
                    )
                )
            elif normalized_status == "inactive":
                query = query.filter(
                    func.lower(func.coalesce(UserDB.status, "")).in_(["disabled", "inactive", "rejected", "false", "pending"])
                )
            else:
                query = query.filter(func.lower(func.coalesce(UserDB.status, "")) == normalized_status)

        rows = query.all()
        return [
            _to_user_read(user, role_name)
            for user, role_name in rows
        ]
    finally:
        db.close()


def create_user(user: UserCreate) -> UserRead:
    db = SessionLocal()
    try:
        existing = db.query(UserDB).filter((UserDB.username == user.username) | (UserDB.email == user.email)).first()
        if existing:
            raise ValueError("Username or email already exists")

        row = UserDB(
            role_id=user.role_id,
            username=user.username,
            email=user.email,
            password_hash=pwd_context.hash(user.password),
            status="approved",
            is_email_verified=True,
            created_at=_now(),
        )
        db.add(row)
        db.flush()
        log_action(
            db,
            user_id=None,
            action="CREATE_USER",
            entity_type="User",
            entity_id=row.user_id,
            new_value={
                "username": row.username,
                "email": row.email,
                "role_id": row.role_id,
                "status": row.status,
            },
        )
        db.commit()
        db.refresh(row)
        role = db.query(RoleDB).filter(RoleDB.role_id == row.role_id).first()
        return _to_user_read(row, role.role_name if role else None)
    finally:
        db.close()


def set_user_active(user_id: int, is_active: bool) -> Optional[UserRead]:
    db = SessionLocal()
    try:
        row = db.query(UserDB).filter(UserDB.user_id == user_id).first()
        if not row:
            return None

        old_state = {"status": row.status, "updated_at": row.updated_at}
        row.status = "approved" if is_active else "disabled"
        row.updated_at = _now()
        log_action(
            db,
            user_id=None,
            action="UPDATE_USER_STATUS",
            entity_type="User",
            entity_id=row.user_id,
            old_value=old_state,
            new_value={"status": row.status, "updated_at": row.updated_at},
        )

        db.commit()
        db.refresh(row)

        role = db.query(RoleDB).filter(RoleDB.role_id == row.role_id).first()
        return _to_user_read(row, role.role_name if role else None)
    finally:
        db.close()


def set_user_role(user_id: int, role: str) -> Optional[UserRead]:
    db = SessionLocal()
    try:
        row = db.query(UserDB).filter(UserDB.user_id == user_id).first()
        if not row:
            return None

        normalized = normalize_role_name(role)
        role_aliases = {
            "admin": ["admin", "administrator", "quản trị viên"],
            "manager": ["manager", "quản lý", "quản lý rủi ro"],
            "analyst": ["analyst", "risk analyst", "credit analyst", "chuyên viên", "chuyên viên phân tích"],
            "viewer": ["viewer", "user", "guest"],
        }
        candidates = role_aliases.get(normalized, [normalized])
        role_row = (
            db.query(RoleDB)
            .filter(func.lower(RoleDB.role_name).in_([c.lower() for c in candidates]))
            .first()
        )
        if not role_row:
            return None

        old_role = db.query(RoleDB).filter(RoleDB.role_id == row.role_id).first()
        old_state = {
            "role_id": row.role_id,
            "role": normalize_role_name(old_role.role_name if old_role else None),
            "updated_at": row.updated_at,
        }
        row.role_id = role_row.role_id
        if normalized in {"manager", "analyst", "viewer"}:
            row.user_type = normalized
        row.updated_at = _now()

        log_action(
            db,
            user_id=None,
            action="UPDATE_USER_ROLE",
            entity_type="User",
            entity_id=row.user_id,
            old_value=old_state,
            new_value={
                "role_id": row.role_id,
                "role": normalize_role_name(role_row.role_name),
                "updated_at": row.updated_at,
            },
        )
        db.commit()
        db.refresh(row)
        return _to_user_read(row, role_row.role_name)
    finally:
        db.close()


def list_audit_logs(from_date: Optional[str], to_date: Optional[str], user_id: Optional[int]) -> List[AuditLogRead]:
    db = SessionLocal()
    try:
        query = (
            db.query(AuditLogDB, UserDB.full_name, UserDB.username)
            .outerjoin(UserDB, UserDB.user_id == AuditLogDB.user_id)
            .order_by(AuditLogDB.performed_at.desc(), AuditLogDB.audit_id.desc())
        )

        if user_id is not None:
            query = query.filter(AuditLogDB.user_id == user_id)

        if from_date:
            try:
                query = query.filter(AuditLogDB.performed_at >= datetime.fromisoformat(from_date))
            except ValueError:
                pass

        if to_date:
            try:
                query = query.filter(AuditLogDB.performed_at <= datetime.fromisoformat(to_date))
            except ValueError:
                pass

        rows = query.all()
        return [
            to_audit_log_read(
                row,
                actor_name=(full_name or username or (f"User #{row.user_id}" if row.user_id is not None else None)),
            )
            for row, full_name, username in rows
        ]
    finally:
        db.close()


def list_upload_history(user_id: Optional[int], limit: int = 5) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        query = (
            db.query(AuditLogDB)
            .filter(AuditLogDB.entity_type == "CustomerImport")
            .order_by(AuditLogDB.performed_at.desc(), AuditLogDB.audit_id.desc())
        )
        if user_id is not None:
            query = query.filter(AuditLogDB.user_id == user_id)
        rows = query.limit(max(1, min(limit, 200))).all()

        result: List[Dict[str, Any]] = []
        for row in rows:
            payload: Dict[str, Any] = {}
            try:
                loaded = json.loads(row.new_value) if row.new_value else {}
                if isinstance(loaded, dict):
                    payload = loaded
            except Exception:
                payload = {}

            action = str(row.action or "").upper()
            status = "completed" if action == "IMPORT_CUSTOMERS" else "failed"
            result.append(
                {
                    "audit_id": int(row.audit_id),
                    "job_id": payload.get("job_id"),
                    "file_name": payload.get("file_name"),
                    "status": status,
                    "processed_count": payload.get("processed_count"),
                    "success_count": payload.get("success_count"),
                    "error_count": payload.get("error_count"),
                    "created_at": row.performed_at,
                }
            )
        return result
    finally:
        db.close()


def _safe_export_filename(raw_name: Optional[str], default_stem: str) -> str:
    candidate = (raw_name or "").strip()
    if not candidate:
        candidate = f"{default_stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"

    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in candidate)
    if not cleaned.lower().endswith(".csv"):
        cleaned = f"{cleaned}.csv"
    return cleaned


def _write_csv_export(filename: str, headers: List[str], rows: List[Dict[str, Any]]) -> str:
    _EXPORT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:12]}-{filename}"
    file_path = _EXPORT_STORAGE_DIR / stored_name

    with file_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in headers})

    return stored_name


def _build_users_export_rows(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    users = list_users(
        user_id=filters.get("user_id"),
        username=filters.get("username"),
        search=filters.get("search"),
        status_filter=filters.get("status_filter"),
    )
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "full_name": user.full_name or "",
            "email": user.email,
            "role": user.role or "",
            "status": user.status or "",
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        }
        for user in users
    ]


def _build_audit_logs_export_rows(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    logs = list_audit_logs(
        from_date=filters.get("from_date"),
        to_date=filters.get("to_date"),
        user_id=filters.get("user_id"),
    )
    return [
        {
            "audit_id": log.audit_id,
            "actor_name": log.actor_name or "",
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id if log.entity_id is not None else "",
            "old_value": log.old_value or "",
            "new_value": log.new_value or "",
            "performed_at": log.performed_at.isoformat() if log.performed_at else "",
        }
        for log in logs
    ]


def _build_customers_export_rows(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    page = int(filters.get("page") or 1)
    search_name = filters.get("search_name")
    risk_level = filters.get("risk_level")
    result = customer_intake_service.list_customers(
        page=page,
        limit=None,
        search_name=search_name,
        risk_level=risk_level,
    )
    return [
        {
            "customer_id": row.customer_id,
            "full_name": row.full_name,
            "email": row.email or "",
            "phone_number": row.phone_number or row.phone or "",
            "loan_type": row.loan_type or "",
            "requested_loan_amount": row.requested_loan_amount if row.requested_loan_amount is not None else "",
            "requested_term_months": row.requested_term_months if row.requested_term_months is not None else "",
            "annual_interest_rate": row.annual_interest_rate if row.annual_interest_rate is not None else "",
            "risk_level": row.risk_level or "",
            "application_status": row.application_status or "",
            "created_at": row.created_at.isoformat() if row.created_at else "",
        }
        for row in result.items
    ]


def export_data(body: ExportRequestBody) -> ExportResponse:
    export_type = (body.type or "").strip().lower()
    filters = body.filters if isinstance(body.filters, dict) else {}
    requested_format = str(filters.get("format") or "csv").strip().lower()

    if requested_format != "csv":
        raise ValueError("Only CSV export is supported")

    if export_type == "users":
        headers = ["user_id", "username", "full_name", "email", "role", "status", "is_active", "created_at"]
        rows = _build_users_export_rows(filters)
        file_name = _safe_export_filename(filters.get("file_name"), "users-export")
    elif export_type == "audit-logs":
        headers = ["audit_id", "actor_name", "action", "entity_type", "entity_id", "old_value", "new_value", "performed_at"]
        rows = _build_audit_logs_export_rows(filters)
        file_name = _safe_export_filename(filters.get("file_name"), "audit-logs-export")
    elif export_type in {"customers", "customer"}:
        headers = [
            "customer_id",
            "full_name",
            "email",
            "phone_number",
            "loan_type",
            "requested_loan_amount",
            "requested_term_months",
            "annual_interest_rate",
            "risk_level",
            "application_status",
            "created_at",
        ]
        rows = _build_customers_export_rows(filters)
        file_name = _safe_export_filename(filters.get("file_name"), "customers-export")
    else:
        raise ValueError(f"Unsupported export type: {body.type}")

    stored_name = _write_csv_export(file_name, headers, rows)
    return ExportResponse(file_url=f"/api/v1/admin/export/download/{stored_name}")


def get_export_file_path(file_name: str) -> Optional[Path]:
    safe_name = Path(file_name).name
    if not safe_name or safe_name != file_name:
        return None

    file_path = _EXPORT_STORAGE_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        return None
    return file_path


def create_upload_job(job_type: str) -> UploadJobResponse:
    job_id = str(uuid.uuid4())
    job = UploadJob(job_id=job_id, status="pending", progress=0.0, result_url=None)
    _upload_jobs[job_id] = job
    return UploadJobResponse(job_id=job_id, status=job.status)


def get_job_status(job_id: str) -> JobStatusResponse:
    job = _upload_jobs.get(job_id)
    if not job:
        return JobStatusResponse(job_id=job_id, progress=0.0, status="missing", result_url=None)
    return JobStatusResponse(job_id=job.job_id, progress=job.progress, status=job.status, result_url=job.result_url)


def update_upload_job(job_id: str, *, status: Optional[str] = None, progress: Optional[float] = None, result_url: Optional[str] = None) -> None:
    job = _upload_jobs.get(job_id)
    if not job:
        return
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if result_url is not None:
        job.result_url = result_url


def set_upload_job_content(job_id: str, payload: Dict[str, Any]) -> None:
    _upload_job_contents[job_id] = payload


def _normalize_upload_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = payload.get("rows") or []
    declared_columns = payload.get("columns") or []

    columns: List[str] = [str(col).strip() for col in declared_columns if str(col).strip()]
    seen = set(columns)
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in row.keys():
                normalized_key = str(key).strip()
                if not normalized_key or normalized_key in seen:
                    continue
                seen.add(normalized_key)
                columns.append(normalized_key)

    payload["columns"] = columns
    payload["column_count"] = max(int(payload.get("column_count") or 0), len(columns))
    return payload


def persist_upload_job_file(job_id: str, filename: str, content: bytes) -> None:
    _UPLOAD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename or "uploaded_file").suffix or ".bin"
    file_path = _UPLOAD_STORAGE_DIR / f"{job_id}{ext}"
    meta_path = _UPLOAD_STORAGE_DIR / f"{job_id}.json"
    file_path.write_bytes(content)
    meta_path.write_text(json.dumps({"file_name": filename or f"{job_id}{ext}"}, ensure_ascii=False), encoding="utf-8")


def get_upload_job_content(job_id: str) -> Optional[Dict[str, Any]]:
    cached = _upload_job_contents.get(job_id)
    if cached is not None:
        normalized = _normalize_upload_payload(cached)
        _upload_job_contents[job_id] = normalized
        return normalized

    meta_path = _UPLOAD_STORAGE_DIR / f"{job_id}.json"
    if not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        file_name = str(meta.get("file_name") or "").strip()
        if not file_name:
            return None
        ext = Path(file_name).suffix or ".bin"
        file_path = _UPLOAD_STORAGE_DIR / f"{job_id}{ext}"
        if not file_path.exists():
            return None

        from app.services.ai_chat_file_context_service import AIChatFileContextService

        extracted = AIChatFileContextService.extract_context(filename=file_name, content=file_path.read_bytes())
        payload = {
            "file_name": extracted["file_name"],
            "row_count": extracted["row_count"],
            "column_count": extracted["column_count"],
            "columns": extracted["columns"],
            "rows": extracted["full_rows"],
            "context_text": extracted["context_text"],
        }
        payload = _normalize_upload_payload(payload)
        _upload_job_contents[job_id] = payload
        return payload
    except Exception:
        return None
