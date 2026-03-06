"""
Risk Prediction Repository - Database operations for Risk Prediction entity
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import RiskPredictionDB
from app.schemas.schemas import RiskScoreDetail


class RiskPredictionRepository:
    """Repository pattern for Risk Prediction operations"""

    @staticmethod
    def create(
        db: Session,
        customer_id: Optional[int] = None,
        application_id: Optional[int] = None,
        model_id: Optional[int] = None,
        risk_score: float = 0.0,
        risk_level: Optional[str] = None,
    ) -> RiskPredictionDB:
        """Create a new risk prediction"""
        db_prediction = RiskPredictionDB(
            customer_id=customer_id,
            application_id=application_id,
            model_id=model_id,
            risk_score=risk_score,
            risk_level=risk_level,
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)
        return db_prediction

    @staticmethod
    def get_by_id(db: Session, prediction_id: int) -> Optional[RiskPredictionDB]:
        """Get risk prediction by ID"""
        return (
            db.query(RiskPredictionDB)
            .filter(RiskPredictionDB.prediction_id == prediction_id)
            .first()
        )

    @staticmethod
    def get_by_customer(db: Session, customer_id: int) -> Optional[RiskPredictionDB]:
        """Get latest risk prediction for a customer"""
        return (
            db.query(RiskPredictionDB)
            .filter(RiskPredictionDB.customer_id == customer_id)
            .order_by(RiskPredictionDB.predicted_at.desc())
            .first()
        )

    @staticmethod
    def get_by_application(db: Session, application_id: int) -> Optional[RiskPredictionDB]:
        """Get risk prediction for a loan application"""
        return (
            db.query(RiskPredictionDB)
            .filter(RiskPredictionDB.application_id == application_id)
            .order_by(RiskPredictionDB.predicted_at.desc())
            .first()
        )

    @staticmethod
    def list_by_customer(
        db: Session,
        customer_id: int,
        limit: int = 10,
    ) -> List[RiskPredictionDB]:
        """List recent risk predictions for a customer"""
        return (
            db.query(RiskPredictionDB)
            .filter(RiskPredictionDB.customer_id == customer_id)
            .order_by(RiskPredictionDB.predicted_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_by_risk_level(
        db: Session,
        risk_level: str,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[List[RiskPredictionDB], int]:
        """List predictions by risk level"""
        query = db.query(RiskPredictionDB).filter(
            RiskPredictionDB.risk_level == risk_level
        )

        total = query.count()
        predictions = query.offset((page - 1) * limit).limit(limit).all()
        return predictions, total
