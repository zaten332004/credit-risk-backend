"""
Generate Loan_Facility + Loan_Repayment_Schedule after application approval (MVP).

Equal-principal amortization: fixed principal per month, interest on beginning balance.
"""
from __future__ import annotations

import calendar
import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.db.models import AuditLogDB, LoanApplicationDB, LoanFacilityDB, LoanRepaymentScheduleDB


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_equal_principal_schedule_rows(
    *,
    principal: Decimal,
    term_months: int,
    annual_rate_percent: Decimal,
    first_due_date: date,
) -> List[Tuple[int, date, Decimal, Decimal, Decimal, Decimal]]:
    """
    Returns list of tuples:
    (installment_no, due_date, principal_amount, interest_amount, total_due, remaining_balance_after)
    """
    if term_months <= 0:
        return []
    principal = _money(principal)
    if principal <= 0:
        return []

    monthly_rate = (annual_rate_percent / Decimal("100")) / Decimal("12")
    base_principal = (principal / Decimal(term_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    rows: List[Tuple[int, date, Decimal, Decimal, Decimal, Decimal]] = []
    balance = principal

    for i in range(1, term_months + 1):
        if i == term_months:
            princ = _money(balance)
        else:
            princ = min(base_principal, balance)
        interest = _money(balance * monthly_rate)
        total = _money(princ + interest)
        due = _add_months(first_due_date, i - 1)
        new_balance = _money(balance - princ)
        rows.append((i, due, princ, interest, total, new_balance))
        balance = new_balance

    return rows


def _facility_for_application(db: Session, application_id: int) -> Optional[LoanFacilityDB]:
    return (
        db.query(LoanFacilityDB)
        .filter(LoanFacilityDB.application_id == application_id)
        .order_by(LoanFacilityDB.facility_id.desc())
        .first()
    )


def _parse_iso_date(value: object) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            if "T" in s:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
            return date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def resolve_approval_anchor_date(db: Session, *, customer_id: int, application: LoanApplicationDB) -> date:
    """
    Calendar day used as anchor: first installment due = same day next month (_add_months(anchor, 1)).
    Prefer audit snapshot (approved_at / APPROVE_CUSTOMER time) for this application_id, else application_date, else created_at.
    """
    application_id = int(application.application_id)
    rows = (
        db.query(AuditLogDB)
        .filter(
            AuditLogDB.entity_type == "Customer",
            AuditLogDB.entity_id == int(customer_id),
            AuditLogDB.action == "APPROVE_CUSTOMER",
        )
        .order_by(asc(AuditLogDB.performed_at))
        .all()
    )
    for row in rows:
        raw = row.new_value
        if not raw:
            continue
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        aid = data.get("application_id")
        if aid is None:
            continue
        if int(aid) != application_id:
            continue
        st = str(data.get("application_status") or "").strip().lower()
        if st and st != "approved":
            continue
        anchor = _parse_iso_date(data.get("approved_at"))
        if anchor:
            return anchor
        if row.performed_at:
            return row.performed_at.date()
    if application.application_date:
        return application.application_date
    if getattr(application, "created_at", None):
        return application.created_at.date()
    return date.today()


def ensure_facility_and_repayment_schedule(
    db: Session,
    *,
    application: LoanApplicationDB,
    customer_id: int,
    approval_anchor: Optional[date] = None,
) -> Optional[LoanFacilityDB]:
    """
    When application is approved (or disbursed), ensure one facility exists and schedule rows are created.
    Idempotent: if schedule rows already exist for the facility, returns facility without inserting duplicates.
    """
    status = str(application.loan_status or "").strip().lower()
    if status not in {"approved", "disbursed"}:
        return None

    facility = _facility_for_application(db, int(application.application_id))
    if facility is None:
        start = approval_anchor or application.application_date or date.today()
        approved_amt = application.loan_amount or Decimal("0")
        facility = LoanFacilityDB(
            application_id=application.application_id,
            customer_id=customer_id,
            facility_type="term_loan",
            approved_amount=approved_amt,
            interest_rate=application.interest_rate,
            start_date=start,
            end_date=_add_months(start, int(application.loan_term or 0)) if application.loan_term else None,
            status="active",
            created_at=datetime.utcnow(),
        )
        db.add(facility)
        db.flush()

    existing_schedules = (
        db.query(LoanRepaymentScheduleDB)
        .filter(LoanRepaymentScheduleDB.facility_id == facility.facility_id)
        .count()
    )
    if existing_schedules > 0:
        return facility

    principal = Decimal(str(facility.approved_amount or 0))
    term = int(application.loan_term or 0) or 1
    rate = Decimal(str(facility.interest_rate or application.interest_rate or 0))
    anchor = approval_anchor or facility.start_date or application.application_date or date.today()
    first_due = _add_months(anchor, 1)

    rows = build_equal_principal_schedule_rows(
        principal=principal,
        term_months=term,
        annual_rate_percent=rate,
        first_due_date=first_due,
    )

    for installment_no, due_date, princ, interest, total_due, remaining in rows:
        db.add(
            LoanRepaymentScheduleDB(
                facility_id=facility.facility_id,
                installment_no=installment_no,
                due_date=due_date,
                principal_amount=princ,
                interest_amount=interest,
                total_due=total_due,
                remaining_balance=remaining,
                created_at=datetime.utcnow(),
            )
        )
    db.flush()
    return facility
