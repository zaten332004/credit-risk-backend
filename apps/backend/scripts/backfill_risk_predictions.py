from __future__ import annotations

from datetime import datetime

from app.db.models import CustomerDB, LoanApplicationDB, RiskPredictionDB
from app.db.session import SessionLocal
from app.schemas.schemas import RiskRequest
from app.services import services


def latest_application(customer: CustomerDB) -> LoanApplicationDB | None:
    applications = sorted(
        customer.loan_applications or [],
        key=lambda item: (
            item.application_date or datetime.min.date(),
            item.created_at or datetime.min,
            item.application_id or 0,
        ),
        reverse=True,
    )
    return applications[0] if applications else None


def infer_risk(customer: CustomerDB, application: LoanApplicationDB | None) -> tuple[float, str]:
    monthly_income = float(customer.monthly_income) if customer.monthly_income is not None else 0.0
    loan_amount = float(application.loan_amount) if application and application.loan_amount is not None else 0.0
    age = int(customer.age or 30)
    loan_term = int(application.loan_term) if application and application.loan_term is not None else 12
    interest_rate = float(application.interest_rate) if application and application.interest_rate is not None else None
    collateral_value = float(application.collateral_value) if application and application.collateral_value is not None else None

    req = RiskRequest(
        income=max(monthly_income, 0.0),
        debt=max(loan_amount, 0.0),
        age=max(age, 18),
        credit_history_months=max(loan_term, 1),
        credit_score=customer.credit_score if customer.credit_score is not None else None,
        loan_type=application.loan_type if application else None,
        interest_rate=interest_rate,
        loan_term_months=loan_term if application else None,
        collateral_value=collateral_value,
        employment_status=customer.employment_status,
    )
    result = services.simple_credit_risk_score(req)
    score = float(result.get("risk_score", 0.0))
    label = str(result.get("risk_label", "medium")).strip().lower()
    if label not in {"low", "medium", "high"}:
        label = "medium"
    return score, label


def main() -> None:
    db = SessionLocal()
    try:
        customers = db.query(CustomerDB).all()
        inserted = 0
        skipped = 0
        for customer in customers:
            if customer.customer_id is None:
                skipped += 1
                continue
            application = latest_application(customer)
            score, level = infer_risk(customer, application)
            db.add(
                RiskPredictionDB(
                    customer_id=int(customer.customer_id),
                    application_id=application.application_id if application else None,
                    risk_score=score,
                    risk_level=level,
                    predicted_at=datetime.now(),
                )
            )
            inserted += 1

        db.commit()
        print(f"Backfill completed. inserted={inserted}, skipped={skipped}, total_customers={len(customers)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
