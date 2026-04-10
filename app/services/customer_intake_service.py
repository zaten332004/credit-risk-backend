from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
import json
from typing import Any, Dict, List, Optional
import unicodedata

import pandas as pd
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import selectinload

from app.db.models import (
    AlertDB,
    AuditLogDB,
    CustomerDB,
    CustomerEmploymentDB,
    FinancialIndicatorDB,
    LoanApplicationDB,
    LoanDelinquencyDB,
    LoanFacilityDB,
    LoanPaymentDB,
    LoanRepaymentScheduleDB,
    RiskPredictionDB,
    SHAPExplanationDB,
    UserDB,
)
from app.db.session import SessionLocal
from app.schemas.schemas import (
    CustomerCreate,
    CustomerHistoryItem,
    CustomerRead,
    RiskRequest,
    CustomerSearchBody,
    CustomerUpdate,
    PaginatedCustomers,
)
from app.services.audit_service import log_action


IMPORT_COLUMN_ALIASES: Dict[str, List[str]] = {
    "external_customer_ref": ["external_customer_ref", "customer_id", "customer_ref", "cif", "cif_no"],
    "full_name": ["full_name", "customer_name", "name"],
    "date_of_birth": ["date_of_birth", "dob", "birth_date"],
    "gender": ["gender", "gender_code"],
    "national_id": ["national_id", "id_number", "citizen_id", "cccd"],
    "id_issue_date": ["id_issue_date"],
    "id_issue_place": ["id_issue_place"],
    "nationality": ["nationality"],
    "marital_status": ["marital_status"],
    "phone_number": ["phone_number", "phone", "mobile", "phone_no"],
    "email": ["email"],
    "permanent_address": ["permanent_address"],
    "current_address": ["current_address", "address"],
    "occupation": ["occupation", "job_title", "profession"],
    "monthly_income": [
        "monthly_income",
        "income",
        "salary",
        "thu_nhap",
        "thu nhập",
        "thu nhap",
        "thunhap",
    ],
    "credit_score": ["credit_score"],
    "application_ref_no": ["application_ref_no", "application_no", "loan_application_no"],
    "source_department_code": ["source_department_code", "department_code"],
    "source_branch_code": ["source_branch_code", "branch_code"],
    "application_date": ["application_date", "submitted_date"],
    "loan_amount": [
        "loan_amount",
        "requested_loan_amount",
        "amount",
        "so_tien_vay",
        "số tiền vay",
        "so tien vay",
        "khoan_vay",
        "khoản vay",
    ],
    "loan_term": [
        "loan_term",
        "loan_term_months",
        "term_months",
        "requested_term_months",
        "ky_han",
        "kỳ hạn",
        "ky han",
        "so_thang_vay",
        "số tháng vay",
    ],
    "interest_rate": ["interest_rate", "annual_interest_rate", "rate"],
    "loan_purpose": ["loan_purpose", "purpose"],
    "loan_type": ["loan_type"],
    "collateral_id": ["collateral_id", "asset_id"],
    "collateral_value": ["collateral_value", "asset_value"],
    "template_version": ["template_version"],
}


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _parse_float(value: Any) -> Optional[float]:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = text.replace(",", "").replace("_", "")
    try:
        return float(normalized)
    except ValueError:
        return None


def _parse_int(value: Any) -> Optional[int]:
    parsed = _parse_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()

    text = _clean_text(value)
    if text is None:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _calculate_age(date_of_birth: Optional[date]) -> Optional[int]:
    if not date_of_birth:
        return None
    today = date.today()
    age = today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )
    return age if age >= 0 else None


def _normalize_gender(value: Optional[str]) -> Optional[str]:
    text = (_clean_text(value) or "").lower()
    if not text:
        return None
    mapping = {
        "m": "male",
        "male": "male",
        "nam": "male",
        "f": "female",
        "female": "female",
        "nu": "female",
        "nữ": "female",
    }
    return mapping.get(text, text)


def _slug_text(value: Optional[str]) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_marks.replace("_", " ").lower().split())


def _normalize_loan_type(value: Optional[str]) -> Optional[str]:
    text = _slug_text(value)
    if not text:
        return None
    mapping = {
        "secured": "secured",
        "thế chấp": "secured",
        "the chap": "secured",
        "mortgage": "secured",
        "unsecured": "unsecured",
        "tín chấp": "unsecured",
        "tin chap": "unsecured",
        "business": "business",
        "vay kinh doanh": "business",
        "kinh doanh": "business",
        "working capital": "business",
        "von luu dong": "business",
        "sme": "business",
    }
    return mapping.get(text, text.replace(" ", "_"))


def _normalize_application_status(value: Optional[str]) -> Optional[str]:
    text = (_clean_text(value) or "").lower()
    if not text:
        return None
    mapping = {
        "pending": "pending",
        "approved": "approved",
        "rejected": "rejected",
        "disbursed": "disbursed",
    }
    return mapping.get(text, "pending")


def _infer_risk_level(credit_score: Optional[int]) -> Optional[str]:
    if credit_score is None:
        return "medium"
    if credit_score >= 750:
        return "low"
    if credit_score >= 650:
        return "medium"
    return "high"


def _compute_model_risk(customer: CustomerDB, application: Optional[LoanApplicationDB]) -> tuple[Optional[float], Optional[str]]:
    """Compute model-based risk using the same scorer as /risk/score."""
    # Import locally to avoid module import cycles.
    from app.services import services as scoring_services

    monthly_income = float(customer.monthly_income) if customer.monthly_income is not None else 0.0
    loan_amount = float(application.loan_amount) if application and application.loan_amount is not None else 0.0
    age = customer.age or _calculate_age(customer.date_of_birth) or 30
    loan_term = application.loan_term if application and application.loan_term is not None else None
    interest_rate = float(application.interest_rate) if application and application.interest_rate is not None else None
    collateral_value = float(application.collateral_value) if application and application.collateral_value is not None else None

    req = RiskRequest(
        income=max(monthly_income, 0.0),
        debt=max(loan_amount, 0.0),
        age=int(age),
        credit_history_months=max(int(loan_term or 12), 1),
        credit_score=customer.credit_score if customer.credit_score is not None else None,
        loan_type=application.loan_type if application else None,
        interest_rate=interest_rate,
        loan_term_months=loan_term,
        collateral_value=collateral_value,
        employment_status=customer.employment_status,
    )
    result = scoring_services.simple_credit_risk_score(req)
    score = result.get("risk_score")
    level = result.get("risk_label")
    try:
        score_value = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_value = None
    level_value = str(level).strip().lower() if level is not None else None
    if level_value not in {"low", "medium", "high"}:
        level_value = None
    return score_value, level_value


def _create_risk_prediction(
    db: Any,
    *,
    customer: CustomerDB,
    application: Optional[LoanApplicationDB],
) -> Optional[str]:
    score, level = _compute_model_risk(customer, application)
    if score is None or level is None:
        return None
    db.add(
        RiskPredictionDB(
            customer_id=customer.customer_id,
            application_id=application.application_id if application else None,
            risk_score=score,
            risk_level=level,
            predicted_at=datetime.utcnow(),
        )
    )
    db.flush()
    return level


def _latest_prediction_level_map(db: Any, customer_ids: List[int]) -> Dict[int, str]:
    if not customer_ids:
        return {}
    rows = (
        db.query(RiskPredictionDB)
        .filter(RiskPredictionDB.customer_id.in_(customer_ids))
        .order_by(desc(RiskPredictionDB.predicted_at), desc(RiskPredictionDB.prediction_id))
        .all()
    )
    mapping: Dict[int, str] = {}
    for row in rows:
        if row.customer_id is None:
            continue
        cid = int(row.customer_id)
        if cid in mapping:
            continue
        level = str(row.risk_level or "").strip().lower()
        if level in {"low", "medium", "high"}:
            mapping[cid] = level
        else:
            try:
                score = float(row.risk_score)
            except (TypeError, ValueError):
                continue
            mapping[cid] = "low" if score < 0.33 else "medium" if score < 0.66 else "high"
    return mapping


def _infer_rate_category(loan_type: Optional[str], loan_purpose: Optional[str]) -> Optional[str]:
    normalized_type = _normalize_loan_type(loan_type)
    purpose_text = _slug_text(loan_purpose)
    business_keywords = (
        "kinh doanh",
        "working capital",
        "von luu dong",
        "business",
        "sme",
        "ho kinh doanh",
    )

    if normalized_type == "business" or any(keyword in purpose_text for keyword in business_keywords):
        return "business"
    if normalized_type == "secured":
        return "secured"
    if normalized_type == "unsecured":
        return "unsecured"
    return normalized_type


def _recommended_interest_rate(
    *,
    loan_type: Optional[str],
    loan_purpose: Optional[str],
    loan_amount: Optional[float],
    loan_term: Optional[int],
    monthly_income: Optional[float],
    collateral_value: Optional[float],
) -> Optional[float]:
    category = _infer_rate_category(loan_type, loan_purpose)
    if not category:
        return None

    amount = float(loan_amount or 0)
    term = int(loan_term or 0)
    income = float(monthly_income or 0)
    collateral = float(collateral_value or 0)

    if category == "secured":
        rate = 6.5
        if amount >= 3_000_000_000:
            rate += 0.8
        elif amount >= 1_000_000_000:
            rate += 0.5
        if term >= 180:
            rate += 1.1
        elif term >= 60:
            rate += 0.6
        if collateral > 0 and amount > 0:
            ltv = amount / collateral
            if ltv >= 0.9:
                rate += 1.0
            elif ltv >= 0.8:
                rate += 0.6
        return round(min(max(rate, 6.0), 12.0), 1)

    if category == "business":
        rate = 7.5
        if amount >= 5_000_000_000:
            rate += 1.8
        elif amount >= 1_000_000_000:
            rate += 1.1
        elif amount >= 300_000_000:
            rate += 0.6
        if term >= 60:
            rate += 1.2
        elif term >= 12:
            rate += 0.5
        if collateral > 0 and amount > 0:
            ltv = amount / collateral
            if ltv <= 0.7:
                rate -= 0.4
            elif ltv >= 0.85:
                rate += 0.5
        return round(min(max(rate, 7.0), 15.0), 1)

    rate = 12.5
    if amount >= 700_000_000:
        rate += 2.5
    elif amount >= 300_000_000:
        rate += 1.5
    if term >= 60:
        rate += 2.0
    elif term >= 36:
        rate += 1.0
    if income > 0 and amount > income * 15:
        rate += 1.5
    elif income > 0 and amount > income * 10:
        rate += 0.8
    return round(min(max(rate, 12.0), 24.0), 1)


def _has_application_payload(payload: CustomerCreate | CustomerUpdate) -> bool:
    return any(
        getattr(payload, field, None) is not None
        for field in (
            "requested_loan_amount",
            "requested_term_months",
            "annual_interest_rate",
            "application_status",
            "loan_type",
            "loan_purpose",
            "application_ref_no",
            "source_department_code",
            "source_branch_code",
            "application_date",
            "collateral_id",
            "collateral_value",
        )
    )


def _build_application_ref(customer_id: int) -> str:
    return f"APP-{datetime.utcnow():%Y%m%d%H%M%S}-{customer_id}"


def _latest_application(customer: CustomerDB) -> Optional[LoanApplicationDB]:
    if not customer.loan_applications:
        return None
    return sorted(
        customer.loan_applications,
        key=lambda item: (
            item.application_date or date.min,
            item.created_at or datetime.min,
            item.application_id or 0,
        ),
        reverse=True,
    )[0]


def _to_customer_read(
    customer: CustomerDB,
    application: Optional[LoanApplicationDB] = None,
    risk_level_override: Optional[str] = None,
) -> CustomerRead:
    application = application or _latest_application(customer)
    interest_rate = None
    if application:
        interest_rate = (
            float(application.interest_rate)
            if application.interest_rate is not None
            else _recommended_interest_rate(
                loan_type=application.loan_type,
                loan_purpose=application.loan_purpose,
                loan_amount=float(application.loan_amount) if application.loan_amount is not None else None,
                loan_term=application.loan_term,
                monthly_income=float(customer.monthly_income) if customer.monthly_income is not None else None,
                collateral_value=float(application.collateral_value) if application.collateral_value is not None else None,
            )
        )
    return CustomerRead(
        customer_id=customer.customer_id,
        full_name=customer.full_name,
        age=customer.age,
        monthly_income=float(customer.monthly_income) if customer.monthly_income is not None else None,
        external_customer_ref=customer.external_customer_ref,
        date_of_birth=customer.date_of_birth,
        gender=customer.gender,
        national_id=customer.national_id,
        id_issue_date=customer.id_issue_date,
        id_issue_place=customer.id_issue_place,
        nationality=customer.nationality,
        marital_status=customer.marital_status,
        phone_number=customer.phone_number,
        email=customer.email,
        permanent_address=customer.permanent_address,
        current_address=customer.current_address,
        occupation=customer.occupation,
        phone=customer.phone_number,
        company=customer.occupation,
        credit_score=customer.credit_score,
        employment_status=customer.employment_status,
        loan_type=application.loan_type if application else None,
        requested_loan_amount=float(application.loan_amount) if application and application.loan_amount is not None else None,
        requested_term_months=application.loan_term if application else None,
        annual_interest_rate=interest_rate,
        risk_level=risk_level_override or _infer_risk_level(customer.credit_score),
        application_status=application.loan_status if application else "pending",
        application_ref_no=application.application_ref_no if application else None,
        source_department_code=application.source_department_code if application else None,
        source_branch_code=application.source_branch_code if application else None,
        application_date=application.application_date if application else None,
        loan_purpose=application.loan_purpose if application else None,
        collateral_id=application.collateral_id if application else None,
        collateral_value=float(application.collateral_value) if application and application.collateral_value is not None else None,
        template_version=application.template_version if application else None,
        upload_batch_id=application.upload_batch_id if application else None,
        notes=None,
        created_by=None,
        approved_by=None,
        approved_at=None,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        employments=[],
    )


def _actor_label(user: Optional[UserDB]) -> Optional[str]:
    if not user:
        return None
    return _clean_text(user.full_name) or _clean_text(user.email) or _clean_text(user.username)


def _customer_actor_metadata(
    db: Any,
    *,
    customer_id: int,
    current_status: Optional[str],
) -> Dict[str, Any]:
    created_by = None
    approved_by = None
    approved_at = None
    fallback_terminal_actor = None
    fallback_terminal_at = None

    rows = (
        db.query(AuditLogDB, UserDB)
        .outerjoin(UserDB, UserDB.user_id == AuditLogDB.user_id)
        .filter(AuditLogDB.entity_type == "Customer", AuditLogDB.entity_id == customer_id)
        .order_by(AuditLogDB.performed_at.asc(), AuditLogDB.audit_id.asc())
        .all()
    )

    for audit, user in rows:
        actor = _actor_label(user)
        if created_by is None and audit.action == "INSERT":
            created_by = actor

        if audit.action not in {"UPDATE", "APPROVE_CUSTOMER", "REJECT_CUSTOMER"}:
            continue

        old_payload = _deserialize_audit_payload(audit.old_value)
        new_payload = _deserialize_audit_payload(audit.new_value)
        previous_status = _normalize_application_status(old_payload.get("application_status"))
        next_status = _normalize_application_status(new_payload.get("application_status"))

        if next_status not in {"approved", "rejected"} or next_status != current_status:
            continue

        fallback_terminal_actor = actor
        fallback_terminal_at = audit.performed_at

        if next_status != previous_status:
            approved_by = actor
            approved_at = audit.performed_at

    if approved_by is None and current_status in {"approved", "rejected"}:
        approved_by = fallback_terminal_actor
        approved_at = fallback_terminal_at

    return {
        "created_by": created_by,
        "approved_by": approved_by,
        "approved_at": approved_at,
    }


def _enrich_customer_read(db: Any, customer_read: CustomerRead) -> CustomerRead:
    metadata = _customer_actor_metadata(
        db,
        customer_id=customer_read.customer_id,
        current_status=_normalize_application_status(customer_read.application_status),
    )
    return customer_read.model_copy(update=metadata)


def _apply_customer_payload(customer: CustomerDB, payload: CustomerCreate | CustomerUpdate) -> None:
    customer.external_customer_ref = payload.external_customer_ref or customer.external_customer_ref
    customer.full_name = payload.full_name.strip() if getattr(payload, "full_name", None) else customer.full_name
    customer.date_of_birth = payload.date_of_birth or customer.date_of_birth
    customer.gender = _normalize_gender(payload.gender) or customer.gender
    customer.national_id = payload.national_id or customer.national_id
    customer.id_issue_date = payload.id_issue_date or customer.id_issue_date
    customer.id_issue_place = payload.id_issue_place or customer.id_issue_place
    customer.nationality = payload.nationality or customer.nationality
    customer.marital_status = payload.marital_status or customer.marital_status
    customer.phone_number = payload.phone_number or payload.phone or customer.phone_number
    customer.email = payload.email or customer.email
    customer.permanent_address = payload.permanent_address or customer.permanent_address
    customer.current_address = payload.current_address or customer.current_address
    customer.occupation = payload.occupation or payload.company or customer.occupation
    customer.monthly_income = payload.monthly_income if payload.monthly_income is not None else customer.monthly_income
    customer.credit_score = payload.credit_score if payload.credit_score is not None else customer.credit_score
    customer.employment_status = payload.employment_status or customer.employment_status
    customer.age = payload.age if payload.age is not None else (_calculate_age(payload.date_of_birth) or customer.age)
    customer.updated_at = datetime.utcnow()


def _apply_application_payload(
    application: LoanApplicationDB,
    payload: CustomerCreate | CustomerUpdate,
    *,
    customer_id: int,
    customer_monthly_income: Optional[float] = None,
) -> None:
    requested_amount = payload.requested_loan_amount
    requested_term = payload.requested_term_months

    if requested_amount is not None:
        application.loan_amount = requested_amount
    if requested_term is not None:
        application.loan_term = requested_term
    elif application.loan_term is None:
        application.loan_term = 12

    if payload.annual_interest_rate is not None:
        application.interest_rate = payload.annual_interest_rate

    application.customer_id = customer_id
    application.application_ref_no = payload.application_ref_no or application.application_ref_no or _build_application_ref(customer_id)
    application.source_department_code = payload.source_department_code or application.source_department_code
    application.source_branch_code = payload.source_branch_code or application.source_branch_code
    application.application_date = payload.application_date or application.application_date or date.today()
    application.loan_status = _normalize_application_status(payload.application_status) or application.loan_status or "pending"
    application.loan_purpose = payload.loan_purpose or application.loan_purpose
    application.loan_type = _normalize_loan_type(payload.loan_type) or application.loan_type
    application.collateral_id = payload.collateral_id or application.collateral_id
    if payload.collateral_value is not None:
        application.collateral_value = payload.collateral_value
    application.template_version = payload.template_version or application.template_version
    application.upload_batch_id = payload.upload_batch_id or application.upload_batch_id
    if application.interest_rate is None:
        inferred_rate = _recommended_interest_rate(
            loan_type=application.loan_type,
            loan_purpose=application.loan_purpose,
            loan_amount=float(application.loan_amount) if application.loan_amount is not None else None,
            loan_term=application.loan_term,
            monthly_income=(
                float(payload.monthly_income)
                if getattr(payload, "monthly_income", None) is not None
                else float(customer_monthly_income)
                if customer_monthly_income is not None
                else None
            ),
            collateral_value=float(application.collateral_value) if application.collateral_value is not None else None,
        )
        if inferred_rate is not None:
            application.interest_rate = inferred_rate


def _deserialize_audit_payload(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except Exception:
        return {"message": raw}
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def list_customers(
    page: int = 1,
    limit: Optional[int] = None,
    search_name: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> PaginatedCustomers:
    db = SessionLocal()
    try:
        query = db.query(CustomerDB).options(selectinload(CustomerDB.loan_applications))
        if search_name:
            pattern = f"%{search_name.strip()}%"
            query = query.filter(
                or_(
                    CustomerDB.full_name.ilike(pattern),
                    CustomerDB.email.ilike(pattern),
                    CustomerDB.phone_number.ilike(pattern),
                    CustomerDB.national_id.ilike(pattern),
                    CustomerDB.external_customer_ref.ilike(pattern),
                )
            )

        customers = query.order_by(desc(CustomerDB.created_at), desc(CustomerDB.customer_id)).all()
        prediction_level_map = _latest_prediction_level_map(db, [int(c.customer_id) for c in customers if c.customer_id is not None])
        items = [
            _to_customer_read(
                customer,
                risk_level_override=prediction_level_map.get(int(customer.customer_id)) if customer.customer_id is not None else None,
            )
            for customer in customers
        ]
        if risk_level:
            normalized_risk = risk_level.strip().lower()
            items = [item for item in items if (item.risk_level or "").lower() == normalized_risk]

        total = len(items)
        safe_page = max(1, page)
        if limit is None or limit <= 0:
            # No hard cap: return full result set when limit is not provided.
            return PaginatedCustomers(items=items, total=total, page=1, limit=max(total, 1))

        start = max(0, (safe_page - 1) * limit)
        end = start + limit
        return PaginatedCustomers(items=items[start:end], total=total, page=safe_page, limit=limit)
    finally:
        db.close()


def get_customer(customer_id: int) -> Optional[CustomerRead]:
    db = SessionLocal()
    try:
        customer = (
            db.query(CustomerDB)
            .options(selectinload(CustomerDB.loan_applications))
            .filter(CustomerDB.customer_id == customer_id)
            .first()
        )
        if not customer:
            return None
        prediction_level_map = _latest_prediction_level_map(db, [int(customer.customer_id)])
        return _enrich_customer_read(
            db,
            _to_customer_read(customer, risk_level_override=prediction_level_map.get(int(customer.customer_id))),
        )
    finally:
        db.close()


def create_customer(payload: CustomerCreate, created_by: str, created_by_user_id: Optional[int] = None) -> CustomerRead:
    db = SessionLocal()
    try:
        duplicate_reason = _detect_duplicate_customer(
            db,
            full_name=payload.full_name,
            email=payload.email,
            external_customer_ref=payload.external_customer_ref,
        )
        if duplicate_reason:
            raise ValueError(duplicate_reason)

        customer = CustomerDB(full_name=payload.full_name.strip(), created_at=datetime.utcnow())
        _apply_customer_payload(customer, payload)
        db.add(customer)
        db.flush()

        application = None
        if (
            _has_application_payload(payload)
            and payload.requested_loan_amount is not None
            and payload.requested_term_months is not None
        ):
            application = LoanApplicationDB(customer_id=customer.customer_id, loan_amount=payload.requested_loan_amount or 0, loan_term=payload.requested_term_months or 12, loan_status="pending")
            _apply_application_payload(
                application,
                payload,
                customer_id=customer.customer_id,
                customer_monthly_income=float(customer.monthly_income) if customer.monthly_income is not None else None,
            )
            db.add(application)
            db.flush()

        risk_level = _create_risk_prediction(db, customer=customer, application=application)
        customer_read = _to_customer_read(customer, application, risk_level_override=risk_level)
        log_action(
            db,
            user_id=created_by_user_id,
            action="INSERT",
            entity_type="Customer",
            entity_id=customer.customer_id,
            new_value=customer_read.model_dump(mode="json"),
        )
        customer_read = _enrich_customer_read(db, customer_read)
        db.commit()
        return customer_read
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    updated_by: str,
    updated_by_user_id: Optional[int] = None,
) -> Optional[CustomerRead]:
    db = SessionLocal()
    try:
        customer = (
            db.query(CustomerDB)
            .options(selectinload(CustomerDB.loan_applications))
            .filter(CustomerDB.customer_id == customer_id)
            .first()
        )
        if not customer:
            return None

        before_prediction_level = _latest_prediction_level_map(db, [int(customer.customer_id)]).get(int(customer.customer_id))
        before_customer = _to_customer_read(customer, risk_level_override=before_prediction_level)
        before = before_customer.model_dump(mode="json")
        previous_status = _normalize_application_status(before_customer.application_status)
        _apply_customer_payload(customer, payload)

        application = _latest_application(customer)
        if _has_application_payload(payload):
            if application is None:
                requested_amount = payload.requested_loan_amount
                requested_term = payload.requested_term_months
                status_only_update = (
                    payload.application_status is not None
                    and payload.requested_loan_amount is None
                    and payload.requested_term_months is None
                )
                if requested_amount is not None and requested_term is not None:
                    application = LoanApplicationDB(
                        customer_id=customer.customer_id,
                        loan_amount=requested_amount,
                        loan_term=requested_term,
                        loan_status="pending",
                    )
                    db.add(application)
                    db.flush()
                elif status_only_update:
                    # Allow approve/reject on imported customers that currently have no loan application row.
                    application = LoanApplicationDB(
                        customer_id=customer.customer_id,
                        loan_amount=0,
                        loan_term=12,
                        loan_status="pending",
                    )
                    db.add(application)
                    db.flush()
                else:
                    application = None
            if application is not None:
                _apply_application_payload(
                    application,
                    payload,
                    customer_id=customer.customer_id,
                    customer_monthly_income=float(customer.monthly_income) if customer.monthly_income is not None else None,
                )
                db.flush()

        risk_level = _create_risk_prediction(db, customer=customer, application=application)
        updated = _to_customer_read(customer, application, risk_level_override=risk_level)
        next_status = _normalize_application_status(updated.application_status)
        action = "UPDATE"
        if next_status != previous_status:
            if next_status == "approved":
                action = "APPROVE_CUSTOMER"
            elif next_status == "rejected":
                action = "REJECT_CUSTOMER"
        log_action(
            db,
            user_id=updated_by_user_id,
            action=action,
            entity_type="Customer",
            entity_id=customer.customer_id,
            old_value=before,
            new_value=updated.model_dump(mode="json"),
        )
        updated = _enrich_customer_read(db, updated)
        db.commit()
        return updated
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_customer_history(customer_id: int) -> List[CustomerHistoryItem]:
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLogDB, UserDB.email)
            .outerjoin(UserDB, UserDB.user_id == AuditLogDB.user_id)
            .filter(AuditLogDB.entity_type == "Customer", AuditLogDB.entity_id == customer_id)
            .order_by(desc(AuditLogDB.performed_at), desc(AuditLogDB.audit_id))
            .all()
        )
        return [
            CustomerHistoryItem(
                timestamp=audit.performed_at,
                changed_by=email or "system",
                changes=_deserialize_audit_payload(audit.new_value or audit.old_value),
            )
            for audit, email in rows
        ]
    finally:
        db.close()


def delete_customer(customer_id: int, deleted_by_user_id: Optional[int] = None) -> bool:
    db = SessionLocal()
    try:
        customer = (
            db.query(CustomerDB)
            .options(selectinload(CustomerDB.loan_applications))
            .filter(CustomerDB.customer_id == customer_id)
            .first()
        )
        if not customer:
            return False

        snapshot = _enrich_customer_read(db, _to_customer_read(customer)).model_dump(mode="json")
        application_ids = [
            application_id
            for application_id, in db.query(LoanApplicationDB.application_id)
            .filter(LoanApplicationDB.customer_id == customer_id)
            .all()
        ]
        facility_ids = [
            facility_id
            for facility_id, in db.query(LoanFacilityDB.facility_id)
            .filter(LoanFacilityDB.customer_id == customer_id)
            .all()
        ]

        prediction_ids = {
            prediction_id
            for prediction_id, in db.query(RiskPredictionDB.prediction_id)
            .filter(RiskPredictionDB.customer_id == customer_id)
            .all()
        }
        if application_ids:
            prediction_ids.update(
                prediction_id
                for prediction_id, in db.query(RiskPredictionDB.prediction_id)
                .filter(RiskPredictionDB.application_id.in_(application_ids))
                .all()
            )

        if prediction_ids:
            db.query(SHAPExplanationDB).filter(
                SHAPExplanationDB.prediction_id.in_(prediction_ids)
            ).delete(synchronize_session=False)

        if application_ids:
            db.query(RiskPredictionDB).filter(
                RiskPredictionDB.application_id.in_(application_ids)
            ).delete(synchronize_session=False)

        db.query(RiskPredictionDB).filter(
            RiskPredictionDB.customer_id == customer_id
        ).delete(synchronize_session=False)

        if facility_ids:
            db.query(AlertDB).filter(AlertDB.facility_id.in_(facility_ids)).delete(synchronize_session=False)
            db.query(LoanPaymentDB).filter(
                LoanPaymentDB.facility_id.in_(facility_ids)
            ).delete(synchronize_session=False)
            db.query(LoanDelinquencyDB).filter(
                LoanDelinquencyDB.facility_id.in_(facility_ids)
            ).delete(synchronize_session=False)
            db.query(LoanRepaymentScheduleDB).filter(
                LoanRepaymentScheduleDB.facility_id.in_(facility_ids)
            ).delete(synchronize_session=False)
            db.query(LoanFacilityDB).filter(
                LoanFacilityDB.facility_id.in_(facility_ids)
            ).delete(synchronize_session=False)

        db.query(AlertDB).filter(AlertDB.customer_id == customer_id).delete(synchronize_session=False)
        db.query(FinancialIndicatorDB).filter(
            FinancialIndicatorDB.customer_id == customer_id
        ).delete(synchronize_session=False)
        db.query(CustomerEmploymentDB).filter(
            CustomerEmploymentDB.customer_id == customer_id
        ).delete(synchronize_session=False)

        if application_ids:
            db.query(LoanApplicationDB).filter(
                LoanApplicationDB.application_id.in_(application_ids)
            ).delete(synchronize_session=False)

        log_action(
            db,
            user_id=deleted_by_user_id,
            action="DELETE",
            entity_type="Customer",
            entity_id=customer_id,
            old_value=snapshot,
        )
        db.query(CustomerDB).filter(CustomerDB.customer_id == customer_id).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def advanced_customer_search(body: CustomerSearchBody) -> PaginatedCustomers:
    search_name = None
    risk_level = None
    if isinstance(body.filters, dict):
        search_name = body.filters.get("search_name") or body.filters.get("full_name")
        risk_level = body.filters.get("risk_level")
    return list_customers(page=body.page, limit=body.limit, search_name=search_name, risk_level=risk_level)


def _read_dataframe(filename: str, content: bytes) -> pd.DataFrame:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    buffer = BytesIO(content)
    if suffix == "csv":
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            buffer.seek(0)
            try:
                return pd.read_csv(buffer, encoding=encoding)
            except Exception as exc:
                last_error = exc
        raise ValueError(f"Không thể đọc file CSV: {last_error}")

    if suffix in {"xlsx", "xls"}:
        buffer.seek(0)
        return pd.read_excel(buffer)

    raise ValueError("Chỉ hỗ trợ file .csv, .xlsx, .xls")


def _normalize_columns(df: pd.DataFrame) -> Dict[str, str]:
    normalized_to_original: Dict[str, str] = {}
    for column in df.columns:
        normalized = str(column).strip().lower()
        if normalized and normalized not in normalized_to_original:
            normalized_to_original[normalized] = str(column)
    return normalized_to_original


def _pick_column(columns: Dict[str, str], field: str) -> Optional[str]:
    for alias in IMPORT_COLUMN_ALIASES.get(field, [field]):
        key = alias.strip().lower()
        if key in columns:
            return columns[key]
    return None


def _resolve_import_row(row: pd.Series, columns: Dict[str, str]) -> Dict[str, Any]:
    def read(field: str) -> Any:
        selected = _pick_column(columns, field)
        return row.get(selected) if selected else None

    return {
        "external_customer_ref": _clean_text(read("external_customer_ref")),
        "full_name": _clean_text(read("full_name")),
        "date_of_birth": _parse_date(read("date_of_birth")),
        "gender": _normalize_gender(read("gender")),
        "national_id": _clean_text(read("national_id")),
        "id_issue_date": _parse_date(read("id_issue_date")),
        "id_issue_place": _clean_text(read("id_issue_place")),
        "nationality": _clean_text(read("nationality")),
        "marital_status": _clean_text(read("marital_status")),
        "phone_number": _clean_text(read("phone_number")),
        "email": _clean_text(read("email")),
        "permanent_address": _clean_text(read("permanent_address")),
        "current_address": _clean_text(read("current_address")),
        "occupation": _clean_text(read("occupation")),
        "monthly_income": _parse_float(read("monthly_income")),
        "credit_score": _parse_int(read("credit_score")),
        "application_ref_no": _clean_text(read("application_ref_no")),
        "source_department_code": _clean_text(read("source_department_code")),
        "source_branch_code": _clean_text(read("source_branch_code")),
        "application_date": _parse_date(read("application_date")),
        "loan_amount": _parse_float(read("loan_amount")),
        "loan_term": _parse_int(read("loan_term")) or 12,
        "interest_rate": _parse_float(read("interest_rate")),
        "loan_purpose": _clean_text(read("loan_purpose")),
        "loan_type": _normalize_loan_type(read("loan_type")),
        "collateral_id": _clean_text(read("collateral_id")),
        "collateral_value": _parse_float(read("collateral_value")),
        "template_version": _clean_text(read("template_version")) or "upload_v1",
    }


def _validate_import_row(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not data["full_name"]:
        errors.append("Thiếu họ tên (full_name)")
    if data["monthly_income"] is None or data["monthly_income"] <= 0:
        errors.append("monthly_income (thu nhập/tháng) phải có và lớn hơn 0")
    if data["loan_amount"] is None or data["loan_amount"] <= 0:
        errors.append("loan_amount (số tiền vay) phải có và lớn hơn 0")
    if data["loan_term"] is None or data["loan_term"] <= 0:
        errors.append("loan_term phải lớn hơn 0")
    if data["loan_type"] == "secured" and not data["collateral_value"] and not data["collateral_id"]:
        errors.append("Hồ sơ thế chấp phải có collateral_id hoặc collateral_value")
    return errors


def _categorize_import_row_failure(message: str) -> str:
    """For UI breakdown: duplicate_* vs validation vs unexpected."""
    m = (message or "").lower()
    if "trùng id trong file" in m or "trùng mã khách hàng tham chiếu" in m:
        return "duplicate_ref"
    if "trùng email" in m:
        return "duplicate_email"
    if "trùng tên khách hàng" in m:
        return "duplicate_name"
    if (
        "thiếu" in m
        or "phải có và lớn hơn 0" in m
        or "phải lớn hơn 0" in m
        or "collateral" in m
    ):
        return "validation"
    return "other"


def _summarize_import_error_categories(errors: List[Dict[str, Any]]) -> Dict[str, int]:
    keys = ("validation", "duplicate_ref", "duplicate_email", "duplicate_name", "other")
    counts = {k: 0 for k in keys}
    for entry in errors:
        cat = str(entry.get("category") or _categorize_import_row_failure(str(entry.get("message") or "")))
        if cat not in counts:
            cat = "other"
        counts[cat] += 1
    return counts


def _find_existing_customer(db: Any, data: Dict[str, Any]) -> Optional[CustomerDB]:
    criteria = []
    if data["national_id"]:
        criteria.append(CustomerDB.national_id == data["national_id"])
    if data["external_customer_ref"]:
        criteria.append(CustomerDB.external_customer_ref == data["external_customer_ref"])
    if data["phone_number"]:
        criteria.append(CustomerDB.phone_number == data["phone_number"])
    if data["email"]:
        criteria.append(CustomerDB.email == data["email"])
    if not criteria:
        return None
    return (
        db.query(CustomerDB)
        .options(selectinload(CustomerDB.loan_applications))
        .filter(or_(*criteria))
        .order_by(desc(CustomerDB.customer_id))
        .first()
    )


def _detect_duplicate_customer(
    db: Any,
    *,
    full_name: Optional[str],
    email: Optional[str],
    external_customer_ref: Optional[str],
    exclude_customer_id: Optional[int] = None,
) -> Optional[str]:
    normalized_name = _clean_text(full_name)
    normalized_email = _clean_text(email)
    normalized_ref = _clean_text(external_customer_ref)

    if normalized_ref:
        q = db.query(CustomerDB).filter(CustomerDB.external_customer_ref == normalized_ref)
        if exclude_customer_id is not None:
            q = q.filter(CustomerDB.customer_id != exclude_customer_id)
        if q.first():
            return f"Trùng mã khách hàng tham chiếu (ID): {normalized_ref}"

    if normalized_email:
        q = db.query(CustomerDB).filter(func.lower(CustomerDB.email) == normalized_email.lower())
        if exclude_customer_id is not None:
            q = q.filter(CustomerDB.customer_id != exclude_customer_id)
        if q.first():
            return f"Trùng email: {normalized_email}"

    if normalized_name:
        q = db.query(CustomerDB).filter(func.lower(CustomerDB.full_name) == normalized_name.lower())
        if exclude_customer_id is not None:
            q = q.filter(CustomerDB.customer_id != exclude_customer_id)
        if q.first():
            return f"Trùng tên khách hàng: {normalized_name}"

    return None


def import_customer_file(
    *,
    filename: str,
    content: bytes,
    created_by: str,
    created_by_user_id: Optional[int],
    upload_batch_id: str,
) -> Dict[str, Any]:
    df = _read_dataframe(filename, content)
    if df.empty and len(df.columns) == 0:
        raise ValueError("File không có dữ liệu để import.")

    columns = _normalize_columns(df)
    missing_required = [
        field
        for field in ("full_name", "monthly_income", "loan_amount")
        if _pick_column(columns, field) is None
    ]
    if missing_required:
        raise ValueError("Thiếu cột bắt buộc: " + ", ".join(missing_required))

    processed_count = 0
    success_count = 0
    error_count = 0
    imported_customers = 0
    imported_applications = 0
    import_errors: List[Dict[str, Any]] = []

    db = SessionLocal()
    try:
        seen_refs: set[str] = set()
        seen_emails: set[str] = set()
        seen_names: set[str] = set()
        for row_index, row in df.fillna("").iterrows():
            processed_count += 1
            data = _resolve_import_row(row, columns)
            row_errors = _validate_import_row(data)
            if row_errors:
                error_count += 1
                import_errors.append(
                    {
                        "row": row_index + 2,
                        "message": "; ".join(row_errors),
                        "category": "validation",
                    }
                )
                continue

            try:
                normalized_ref = _clean_text(data.get("external_customer_ref"))
                normalized_email = _clean_text(data.get("email"))
                normalized_name = _clean_text(data.get("full_name"))

                if normalized_ref:
                    ref_key = normalized_ref.lower()
                    if ref_key in seen_refs:
                        raise ValueError(f"Trùng ID trong file import: {normalized_ref}")
                    seen_refs.add(ref_key)
                if normalized_email:
                    email_key = normalized_email.lower()
                    if email_key in seen_emails:
                        raise ValueError(f"Trùng email trong file import: {normalized_email}")
                    seen_emails.add(email_key)
                if normalized_name:
                    name_key = normalized_name.lower()
                    if name_key in seen_names:
                        raise ValueError(f"Trùng tên khách hàng trong file import: {normalized_name}")
                    seen_names.add(name_key)

                duplicate_reason = _detect_duplicate_customer(
                    db,
                    full_name=normalized_name,
                    email=normalized_email,
                    external_customer_ref=normalized_ref,
                )
                if duplicate_reason:
                    raise ValueError(duplicate_reason)

                customer = CustomerDB(
                    full_name=data["full_name"],
                    created_at=datetime.utcnow(),
                )
                db.add(customer)
                created_customer = True

                customer_payload = CustomerCreate(
                    full_name=data["full_name"],
                    age=_calculate_age(data["date_of_birth"]),
                    monthly_income=float(data["monthly_income"]),
                    external_customer_ref=data["external_customer_ref"],
                    date_of_birth=data["date_of_birth"],
                    gender=data["gender"],
                    national_id=data["national_id"],
                    id_issue_date=data["id_issue_date"],
                    id_issue_place=data["id_issue_place"],
                    nationality=data["nationality"],
                    marital_status=data["marital_status"],
                    phone_number=data["phone_number"],
                    email=data["email"],
                    permanent_address=data["permanent_address"],
                    current_address=data["current_address"],
                    occupation=data["occupation"],
                    credit_score=data["credit_score"],
                    employment_status=data["occupation"],
                    loan_type=data["loan_type"],
                    requested_loan_amount=float(data["loan_amount"]),
                    requested_term_months=int(data["loan_term"]),
                    annual_interest_rate=data["interest_rate"],
                    application_status="pending",
                    application_ref_no=data["application_ref_no"],
                    source_department_code=data["source_department_code"],
                    source_branch_code=data["source_branch_code"],
                    application_date=data["application_date"],
                    loan_purpose=data["loan_purpose"],
                    collateral_id=data["collateral_id"],
                    collateral_value=data["collateral_value"],
                    template_version=data["template_version"],
                    upload_batch_id=upload_batch_id,
                )
                _apply_customer_payload(customer, customer_payload)
                db.flush()

                application = None
                if customer_payload.application_ref_no:
                    application = (
                        db.query(LoanApplicationDB)
                        .filter(LoanApplicationDB.application_ref_no == customer_payload.application_ref_no)
                        .first()
                    )

                if application is None:
                    application = LoanApplicationDB(
                        customer_id=customer.customer_id,
                        loan_amount=customer_payload.requested_loan_amount or 0,
                        loan_term=customer_payload.requested_term_months or 12,
                        loan_status="pending",
                    )
                    db.add(application)

                _apply_application_payload(
                    application,
                    customer_payload,
                    customer_id=customer.customer_id,
                    customer_monthly_income=float(customer.monthly_income) if customer.monthly_income is not None else None,
                )
                db.flush()

                risk_level = _create_risk_prediction(db, customer=customer, application=application)
                log_action(
                    db,
                    user_id=created_by_user_id,
                    action="INSERT" if created_customer else "UPDATE",
                    entity_type="Customer",
                    entity_id=customer.customer_id,
                    new_value=_to_customer_read(customer, application, risk_level_override=risk_level).model_dump(mode="json"),
                )
                db.commit()

                success_count += 1
                imported_applications += 1
                if created_customer:
                    imported_customers += 1
            except Exception as exc:
                db.rollback()
                error_count += 1
                msg = str(exc)
                import_errors.append(
                    {
                        "row": row_index + 2,
                        "message": msg,
                        "category": _categorize_import_row_failure(msg),
                    }
                )

        return {
            "processed_count": processed_count,
            "success_count": success_count,
            "error_count": error_count,
            "imported_customers": imported_customers,
            "imported_applications": imported_applications,
            "import_errors": import_errors,
            "error_reason_counts": _summarize_import_error_categories(import_errors),
        }
    finally:
        db.close()
