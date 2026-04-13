"""
Generate Loan_Facility + Loan_Repayment_Schedule after application approval (MVP).

Equal-principal amortization: fixed principal per month, interest on beginning balance.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import LoanApplicationDB, LoanFacilityDB, LoanRepaymentScheduleDB


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


def ensure_facility_and_repayment_schedule(
    db: Session,
    *,
    application: LoanApplicationDB,
    customer_id: int,
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
        start = application.application_date or date.today()
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
    first_due = _add_months(facility.start_date or application.application_date or date.today(), 1)

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
