"""
Loan application listing, approved-loan workbench, and manual payment recording.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import selectinload

from app.db.models import (
    CustomerDB,
    LoanApplicationDB,
    LoanFacilityDB,
    LoanPaymentDB,
    LoanRepaymentScheduleDB,
)
from app.db.session import SessionLocal
from app.schemas.schemas import CustomerUpdate, LoanApplicationRead
from app.services.customer_intake_service import (
    _apply_application_payload,
    _normalize_loan_type,
    _create_risk_prediction,
)
from app.services.audit_service import log_action
from app.services.repayment_schedule_service import (
    ensure_facility_and_repayment_schedule,
    resolve_approval_anchor_date,
)


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def list_loan_applications_for_customer(customer_id: int) -> List[LoanApplicationRead]:
    db = SessionLocal()
    try:
        apps = (
            db.query(LoanApplicationDB)
            .filter(LoanApplicationDB.customer_id == customer_id)
            .order_by(desc(LoanApplicationDB.created_at), desc(LoanApplicationDB.application_id))
            .all()
        )
        return [LoanApplicationRead.model_validate(a, from_attributes=True) for a in apps]
    finally:
        db.close()


def create_loan_application_for_customer(
    customer_id: int,
    *,
    requested_loan_amount: float,
    requested_term_months: int,
    loan_purpose: str,
    loan_type: Optional[str] = None,
    annual_interest_rate: Optional[float] = None,
    collateral_id: Optional[str] = None,
    collateral_value: Optional[float] = None,
    created_by: str,
    created_by_user_id: Optional[int] = None,
):
    """Add a new pending Loan_Application for an existing customer."""
    db = SessionLocal()
    try:
        customer = (
            db.query(CustomerDB)
            .options(selectinload(CustomerDB.loan_applications))
            .filter(CustomerDB.customer_id == customer_id)
            .first()
        )
        if not customer:
            raise ValueError("Customer not found")

        application = LoanApplicationDB(
            customer_id=customer_id,
            loan_amount=requested_loan_amount,
            loan_term=requested_term_months,
            loan_status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(application)
        db.flush()

        payload = CustomerUpdate(
            requested_loan_amount=requested_loan_amount,
            requested_term_months=requested_term_months,
            loan_purpose=loan_purpose,
            loan_type=_normalize_loan_type(loan_type) if loan_type else None,
            annual_interest_rate=annual_interest_rate,
            collateral_id=collateral_id,
            collateral_value=collateral_value,
            application_status="pending",
        )
        _apply_application_payload(
            application,
            payload,
            customer_id=customer_id,
            customer_monthly_income=float(customer.monthly_income) if customer.monthly_income is not None else None,
        )
        db.flush()

        risk_score, risk_level = _create_risk_prediction(db, customer=customer, application=application)
        log_action(
            db,
            user_id=created_by_user_id,
            action="INSERT",
            entity_type="Loan_Application",
            entity_id=int(application.application_id),
            new_value={"customer_id": customer_id, "application_ref_no": application.application_ref_no},
        )
        db.commit()
        db.refresh(application)
        return LoanApplicationRead.model_validate(application, from_attributes=True)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _paid_for_schedule(db: Session, schedule_id: int) -> Decimal:
    rows = (
        db.query(func.coalesce(func.sum(LoanPaymentDB.amount_paid), 0))
        .filter(LoanPaymentDB.schedule_id == schedule_id)
        .scalar()
    )
    return Decimal(str(rows or 0))


def _installment_state(db: Session, row: LoanRepaymentScheduleDB, today: date) -> Dict[str, Any]:
    total_due = Decimal(str(row.total_due or 0))
    paid = _paid_for_schedule(db, int(row.schedule_id))
    if paid + Decimal("0.001") >= total_due:
        state = "paid"
        dpd = 0
    elif paid > 0:
        state = "partial"
        dpd = max(0, (today - row.due_date).days) if row.due_date < today else 0
    else:
        if row.due_date < today:
            state = "overdue"
            dpd = (today - row.due_date).days
        else:
            state = "upcoming"
            dpd = 0
    return {"state": state, "dpd": dpd, "paid": float(paid), "total_due": float(total_due)}


def list_approved_loan_workbench(limit: int = 500) -> List[Dict[str, Any]]:
    """
    One row per approved/disbursed application with facility + next schedule summary.
    """
    db = SessionLocal()
    try:
        today = date.today()
        apps = (
            db.query(LoanApplicationDB)
            .options(selectinload(LoanApplicationDB.customer))
            .filter(
                func.lower(LoanApplicationDB.loan_status).in_(["approved", "disbursed"]),
            )
            .order_by(desc(LoanApplicationDB.created_at), desc(LoanApplicationDB.application_id))
            .limit(limit)
            .all()
        )
        out: List[Dict[str, Any]] = []
        for app in apps:
            customer = app.customer
            cid = _safe_int(app.customer_id)
            if cid is None and customer is not None:
                cid = _safe_int(getattr(customer, "customer_id", None))
            if cid is not None:
                anchor = resolve_approval_anchor_date(db, customer_id=int(cid), application=app)
                ensure_facility_and_repayment_schedule(
                    db,
                    application=app,
                    customer_id=int(cid),
                    approval_anchor=anchor,
                )
            facility = (
                db.query(LoanFacilityDB)
                .filter(LoanFacilityDB.application_id == app.application_id)
                .order_by(LoanFacilityDB.facility_id.desc())
                .first()
            )
            next_row: Optional[LoanRepaymentScheduleDB] = None
            next_meta: Dict[str, Any] = {}
            if facility:
                schedules = (
                    db.query(LoanRepaymentScheduleDB)
                    .filter(LoanRepaymentScheduleDB.facility_id == facility.facility_id)
                    .order_by(LoanRepaymentScheduleDB.installment_no)
                    .all()
                )
                for sch in schedules:
                    meta = _installment_state(db, sch, today)
                    if meta["state"] != "paid":
                        next_row = sch
                        next_meta = meta
                        break
                if next_row is None and schedules:
                    last = schedules[-1]
                    next_meta = _installment_state(db, last, today)
                    next_row = last

            dpd_raw = next_meta.get("dpd", 0)
            installment_dpd = int(_safe_int(dpd_raw) or 0)
            out.append(
                {
                    "application_id": int(app.application_id),
                    "application_ref_no": app.application_ref_no,
                    "customer_id": cid,
                    "customer_name": customer.full_name if customer else None,
                    "loan_status": app.loan_status,
                    "loan_type": app.loan_type,
                    "loan_purpose": app.loan_purpose,
                    "loan_amount": float(app.loan_amount) if app.loan_amount is not None else None,
                    "loan_term": _safe_int(app.loan_term),
                    "facility_id": _safe_int(facility.facility_id) if facility else None,
                    "next_installment_no": _safe_int(next_row.installment_no) if next_row else None,
                    "next_due_date": next_row.due_date.isoformat() if next_row and next_row.due_date else None,
                    "installment_state": next_meta.get("state"),
                    "installment_dpd": installment_dpd,
                    "next_total_due": next_meta.get("total_due"),
                    "next_paid": next_meta.get("paid"),
                }
            )
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_repayment_facility_for_application(application_id: int) -> Dict[str, Any]:
    """
    Create or load the loan facility + repayment schedule for an approved/disbursed application.
    Used when the workbench row had no facility_id (e.g. customer_id was missing on first list load).
    """
    db = SessionLocal()
    try:
        app = (
            db.query(LoanApplicationDB)
            .options(selectinload(LoanApplicationDB.customer))
            .filter(LoanApplicationDB.application_id == application_id)
            .first()
        )
        if not app:
            raise ValueError("Application not found")
        st = str(app.loan_status or "").strip().lower()
        if st not in {"approved", "disbursed"}:
            raise ValueError("Application is not approved or disbursed")
        customer = app.customer
        cid = _safe_int(app.customer_id)
        if cid is None and customer is not None:
            cid = _safe_int(getattr(customer, "customer_id", None))
        if cid is None:
            raise ValueError(
                "Application has no customer; link a customer on the profile before recording payments"
            )
        anchor = resolve_approval_anchor_date(db, customer_id=int(cid), application=app)
        fac = ensure_facility_and_repayment_schedule(
            db,
            application=app,
            customer_id=int(cid),
            approval_anchor=anchor,
        )
        if not fac:
            raise ValueError("Could not create loan facility for this application")
        db.commit()
        return {"facility_id": int(fac.facility_id), "application_id": int(application_id)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def record_loan_payment(
    *,
    facility_id: int,
    schedule_id: Optional[int],
    payment_date: date,
    amount_paid: float,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    recorded_by_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        facility = db.query(LoanFacilityDB).filter(LoanFacilityDB.facility_id == facility_id).first()
        if not facility:
            raise ValueError("Facility not found")

        if schedule_id is not None:
            sch = (
                db.query(LoanRepaymentScheduleDB)
                .filter(
                    LoanRepaymentScheduleDB.schedule_id == schedule_id,
                    LoanRepaymentScheduleDB.facility_id == facility_id,
                )
                .first()
            )
            if not sch:
                raise ValueError("schedule_id does not belong to this facility")

        amt = Decimal(str(amount_paid))
        if amt <= 0:
            raise ValueError("amount_paid must be positive")

        pay_status = (status or "").strip().lower() or None
        if pay_status not in {None, "", "paid", "partial", "late"}:
            raise ValueError("status must be paid, partial, or late")

        row = LoanPaymentDB(
            facility_id=facility_id,
            schedule_id=schedule_id,
            payment_date=payment_date,
            amount_paid=amt,
            payment_method=payment_method,
            status=pay_status or "paid",
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.flush()

        log_action(
            db,
            user_id=recorded_by_user_id,
            action="INSERT",
            entity_type="Loan_Payment",
            entity_id=row.payment_id,
            new_value={
                "facility_id": facility_id,
                "schedule_id": schedule_id,
                "amount_paid": float(amt),
                "payment_date": payment_date.isoformat(),
            },
        )
        db.commit()
        db.refresh(row)
        return {
            "payment_id": int(row.payment_id),
            "facility_id": int(row.facility_id),
            "schedule_id": int(row.schedule_id) if row.schedule_id is not None else None,
            "amount_paid": float(row.amount_paid),
            "payment_date": row.payment_date.isoformat(),
            "status": row.status,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
