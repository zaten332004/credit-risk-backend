"""
Loan Application Repository - Database operations for Loan Application entity
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import LoanApplicationDB, LoanFacilityDB
from app.schemas.schemas import LoanApplicationCreate, LoanApplicationRead


class LoanApplicationRepository:
    """Repository pattern for Loan Application operations"""

    @staticmethod
    def create(db: Session, loan_app: LoanApplicationCreate) -> LoanApplicationDB:
        """Create a new loan application"""
        db_application = LoanApplicationDB(
            customer_id=loan_app.customer_id,
            loan_amount=loan_app.loan_amount,
            loan_term=loan_app.loan_term,
            interest_rate=loan_app.interest_rate,
            loan_purpose=loan_app.loan_purpose,
            loan_status="pending",  # Initial status
        )
        db.add(db_application)
        db.commit()
        db.refresh(db_application)
        return db_application

    @staticmethod
    def get_by_id(db: Session, application_id: int) -> Optional[LoanApplicationDB]:
        """Get loan application by ID"""
        return (
            db.query(LoanApplicationDB)
            .filter(LoanApplicationDB.application_id == application_id)
            .first()
        )

    @staticmethod
    def list_by_customer(
        db: Session,
        customer_id: int,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[List[LoanApplicationDB], int]:
        """List loan applications for a customer"""
        query = db.query(LoanApplicationDB).filter(
            LoanApplicationDB.customer_id == customer_id
        )

        total = query.count()
        applications = query.offset((page - 1) * limit).limit(limit).all()
        return applications, total

    @staticmethod
    def list_by_status(
        db: Session,
        status: str,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[List[LoanApplicationDB], int]:
        """List loan applications by status"""
        query = db.query(LoanApplicationDB).filter(
            LoanApplicationDB.loan_status == status
        )

        total = query.count()
        applications = query.offset((page - 1) * limit).limit(limit).all()
        return applications, total

    @staticmethod
    def update_status(
        db: Session,
        application_id: int,
        status: str,
    ) -> Optional[LoanApplicationDB]:
        """Update loan application status"""
        db_application = (
            db.query(LoanApplicationDB)
            .filter(LoanApplicationDB.application_id == application_id)
            .first()
        )

        if not db_application:
            return None

        db_application.loan_status = status
        db.commit()
        db.refresh(db_application)
        return db_application

    @staticmethod
    def approve(db: Session, application_id: int) -> Optional[LoanApplicationDB]:
        """Approve a loan application"""
        return LoanApplicationRepository.update_status(db, application_id, "approved")

    @staticmethod
    def reject(db: Session, application_id: int) -> Optional[LoanApplicationDB]:
        """Reject a loan application"""
        return LoanApplicationRepository.update_status(db, application_id, "rejected")
