"""
Loan Approval Service - Orchestrates loan application approval process
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import (
    LoanApplicationDB,
    LoanFacilityDB,
    RiskPredictionDB,
)
from app.schemas.schemas import (
    LoanApplicationCreate,
    LoanApplicationRead,
    LoanFacilityCreate,
    LoanFacilityRead,
    RiskScoreDetail,
)
from app.services.loan_repo import LoanApplicationRepository
from app.services.risk_repo import RiskPredictionRepository
from app.services.services import simple_credit_risk_score, score_to_pd_lgd_ead
from app.schemas.schemas import RiskRequest


class LoanApprovalService:
    """Service for loan application approval workflow"""

    @staticmethod
    def apply_for_loan(
        db: Session,
        customer_id: int,
        loan_amount: float,
        loan_term: int,
        interest_rate: Optional[float] = None,
        loan_purpose: Optional[str] = None,
    ) -> LoanApplicationRead:
        """
        Step 1: Create loan application
        """
        loan_app = LoanApplicationCreate(
            customer_id=customer_id,
            loan_amount=loan_amount,
            loan_term=loan_term,
            interest_rate=interest_rate,
            loan_purpose=loan_purpose,
        )
        db_app = LoanApplicationRepository.create(db, loan_app)
        return LoanApplicationRead.from_orm(db_app)

    @staticmethod
    def score_application(
        db: Session,
        application_id: int,
        income: float,
        debt: float,
        age: int,
        credit_history_months: int,
    ) -> tuple[LoanApplicationDB, RiskPredictionDB]:
        """
        Step 2: Score the application using risk model
        """
        # Get application
        db_app = LoanApplicationRepository.get_by_id(db, application_id)
        if not db_app:
            raise ValueError(f"Application {application_id} not found")

        # Score using heuristic
        req = RiskRequest(
            income=income,
            debt=debt,
            age=age,
            credit_history_months=credit_history_months,
        )
        risk_data = simple_credit_risk_score(req)
        risk_score = risk_data["risk_score"]

        # Determine risk level
        if risk_score < 0.33:
            risk_level = "low"
        elif risk_score < 0.66:
            risk_level = "medium"
        else:
            risk_level = "high"

        # Save prediction
        db_prediction = RiskPredictionRepository.create(
            db,
            application_id=application_id,
            customer_id=db_app.customer_id,
            risk_score=risk_score,
            risk_level=risk_level,
        )

        return db_app, db_prediction

    @staticmethod
    def approve_application(
        db: Session,
        application_id: int,
        approved_amount: Optional[float] = None,
    ) -> tuple[LoanApplicationDB, Optional[LoanFacilityDB]]:
        """
        Step 3: Approve application and create facility
        """
        # Update application status
        db_app = LoanApplicationRepository.approve(db, application_id)
        if not db_app:
            raise ValueError(f"Application {application_id} not found")

        # Create facility
        facility = None
        if approved_amount:
            facility_create = LoanFacilityCreate(
                application_id=application_id,
                customer_id=db_app.customer_id,
                facility_type="term_loan",
                approved_amount=approved_amount,
                interest_rate=db_app.interest_rate,
            )
            facility = LoanApprovalService.create_facility(db, facility_create)

        return db_app, facility

    @staticmethod
    def reject_application(db: Session, application_id: int) -> LoanApplicationDB:
        """
        Step 3 (Alt): Reject application
        """
        db_app = LoanApplicationRepository.reject(db, application_id)
        if not db_app:
            raise ValueError(f"Application {application_id} not found")
        return db_app

    @staticmethod
    def create_facility(
        db: Session,
        facility_create: LoanFacilityCreate,
    ) -> LoanFacilityDB:
        """
        Create a loan facility (disbursed loan)
        """
        db_facility = LoanFacilityDB(
            application_id=facility_create.application_id,
            customer_id=facility_create.customer_id,
            facility_type=facility_create.facility_type or "term_loan",
            approved_amount=Decimal(str(facility_create.approved_amount)),
            interest_rate=Decimal(str(facility_create.interest_rate)) if facility_create.interest_rate else None,
            start_date=facility_create.start_date,
            end_date=facility_create.end_date,
            status="active",
        )
        db.add(db_facility)
        db.commit()
        db.refresh(db_facility)
        return db_facility

    @staticmethod
    def get_application_with_score(
        db: Session,
        application_id: int,
    ) -> dict:
        """
        Get application details with its risk score
        """
        db_app = LoanApplicationRepository.get_by_id(db, application_id)
        if not db_app:
            raise ValueError(f"Application {application_id} not found")

        prediction = RiskPredictionRepository.get_by_application(db, application_id)

        return {
            "application": LoanApplicationRead.from_orm(db_app),
            "risk_prediction": prediction,
        }

    @staticmethod
    def make_approval_decision(
        db: Session,
        application_id: int,
        risk_threshold: float = 0.66,  # High risk threshold
    ) -> dict:
        """
        Automated approval decision based on risk score
        """
        db_app = LoanApplicationRepository.get_by_id(db, application_id)
        if not db_app:
            raise ValueError(f"Application {application_id} not found")

        prediction = RiskPredictionRepository.get_by_application(db, application_id)
        if not prediction:
            raise ValueError(f"No risk prediction for application {application_id}")

        # Decision logic
        decision = "rejected"  # Default
        reason = ""

        if prediction.risk_score >= risk_threshold:
            decision = "rejected"
            reason = f"Risk score {prediction.risk_score:.2f} exceeds threshold {risk_threshold}"
        else:
            decision = "approved"
            reason = f"Risk score {prediction.risk_score:.2f} is acceptable"

        return {
            "application_id": application_id,
            "decision": decision,
            "reason": reason,
            "risk_score": float(prediction.risk_score),
            "risk_level": prediction.risk_level,
        }
