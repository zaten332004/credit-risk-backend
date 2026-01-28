"""
Customer Repository - Database operations for Customer entity
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import CustomerDB, CustomerEmploymentDB
from app.schemas.schemas import CustomerCreate, CustomerRead, CustomerUpdate


class CustomerRepository:
    """Repository pattern for Customer operations"""

    @staticmethod
    def create(db: Session, customer: CustomerCreate) -> CustomerDB:
        """Create a new customer"""
        db_customer = CustomerDB(
            full_name=customer.full_name,
            age=customer.age,
            monthly_income=customer.monthly_income,
            credit_score=customer.credit_score,
            employment_status=customer.employment_status,
        )
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        return db_customer

    @staticmethod
    def get_by_id(db: Session, customer_id: int) -> Optional[CustomerDB]:
        """Get customer by ID"""
        return db.query(CustomerDB).filter(CustomerDB.customer_id == customer_id).first()

    @staticmethod
    def list_all(
        db: Session,
        page: int = 1,
        limit: int = 20,
        search_name: Optional[str] = None,
    ) -> tuple[List[CustomerDB], int]:
        """List all customers with pagination and optional search"""
        query = db.query(CustomerDB)

        if search_name:
            query = query.filter(CustomerDB.full_name.ilike(f"%{search_name}%"))

        total = query.count()
        customers = query.offset((page - 1) * limit).limit(limit).all()
        return customers, total

    @staticmethod
    def update(db: Session, customer_id: int, customer_update: CustomerUpdate) -> Optional[CustomerDB]:
        """Update customer"""
        db_customer = db.query(CustomerDB).filter(CustomerDB.customer_id == customer_id).first()
        if not db_customer:
            return None

        update_data = customer_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_customer, field, value)

        db.commit()
        db.refresh(db_customer)
        return db_customer

    @staticmethod
    def delete(db: Session, customer_id: int) -> bool:
        """Delete customer"""
        db_customer = db.query(CustomerDB).filter(CustomerDB.customer_id == customer_id).first()
        if not db_customer:
            return False

        db.delete(db_customer)
        db.commit()
        return True
