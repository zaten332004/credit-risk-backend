"""
Risk Analysis Service - Calculate risk scores and classifications
Implements: Risk scoring model, GROUP classification, dashboard metrics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    LoanFacilityDB as LoanFacility, 
    LoanDelinquencyDB as LoanDelinquency, 
    CustomerDB as Customer, 
    LoanApplicationDB as Loan_Application,
    LoanPaymentDB as Loan_Payment
)

logger = logging.getLogger(__name__)


class RiskAnalysisService:
    """Service to analyze and calculate credit risk metrics"""
    
    # Risk classification thresholds (based on days past due)
    RISK_GROUPS = {
        'GROUP_1': {'name': 'NORMAL', 'min_dpd': 0, 'max_dpd': 0},
        'GROUP_2': {'name': 'SPECIAL MENTION', 'min_dpd': 1, 'max_dpd': 30},
        'GROUP_3': {'name': 'SUBSTANDARD', 'min_dpd': 31, 'max_dpd': 90},
        'GROUP_4': {'name': 'DOUBTFUL', 'min_dpd': 91, 'max_dpd': 999}
    }
    
    @staticmethod
    def calculate_risk_score(
        income: float,
        debt_obligation: float,
        age: int,
        credit_history_months: int = 12,
        employment_status: str = 'Employed'
    ) -> Dict[str, float]:
        """
        Calculate risk score using heuristic model
        
        Formula:
        - DTI Score (60%): Debt-to-Income ratio
        - Age Score (20%): Younger = higher risk
        - History Score (20%): Longer history = lower risk
        
        Args:
            income: Monthly income
            debt_obligation: Monthly debt obligations
            age: Customer age
            credit_history_months: Months of credit history
            employment_status: Employment status
            
        Returns:
            Dictionary with risk_score (0-1), risk_level, component scores
        """
        
        # Validate inputs
        if income <= 0:
            income = 1000000  # Default
        if debt_obligation < 0:
            debt_obligation = 0
        if age < 18:
            age = 25
        elif age > 150:
            age = 65
        
        # Component 1: Debt-to-Income Ratio (60% weight)
        dti = (debt_obligation / income) * 100
        
        if dti > 60:
            dti_score = 1.0  # Very high risk
        elif dti > 40:
            dti_score = 0.7
        elif dti > 20:
            dti_score = 0.4
        else:
            dti_score = 0.1
        
        # Component 2: Age Score (20% weight)
        # Younger = higher risk
        if age < 25:
            age_score = 0.6
        elif age < 35:
            age_score = 0.4
        elif age < 50:
            age_score = 0.2
        else:
            age_score = 0.3  # Very old = higher risk
        
        # Component 3: Credit History (20% weight)
        # Longer history = lower risk
        if credit_history_months < 6:
            history_score = 0.8
        elif credit_history_months < 12:
            history_score = 0.5
        elif credit_history_months < 24:
            history_score = 0.3
        else:
            history_score = 0.1
        
        # Employment bonus/penalty
        employment_adjustment = {
            'Employed': -0.05,
            'Self-employed': 0.05,
            'Unemployed': 0.15,
            'Retired': -0.1
        }.get(employment_status, 0)
        
        # Calculate final risk score (weighted average)
        risk_score = (
            (dti_score * 0.60) +
            (age_score * 0.20) +
            (history_score * 0.20) +
            employment_adjustment
        )
        
        # Clamp to 0-1 range
        risk_score = max(0.0, min(1.0, risk_score))
        
        # Determine risk level
        if risk_score < 0.33:
            risk_level = 'low'
        elif risk_score < 0.66:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        return {
            'risk_score': float(risk_score),
            'risk_level': risk_level,
            'dti_score': float(dti_score),
            'age_score': float(age_score),
            'history_score': float(history_score),
            'dti_ratio': float(dti),
            'components': {
                'dti': {'weight': 0.60, 'score': float(dti_score)},
                'age': {'weight': 0.20, 'score': float(age_score)},
                'history': {'weight': 0.20, 'score': float(history_score)}
            }
        }
    
    @staticmethod
    def classify_loan_group(
        days_past_due: int,
        delinquency_count: int = 0,
        overdue_amount: float = 0
    ) -> str:
        """
        Classify loan into risk GROUP (1-4)
        
        Args:
            days_past_due: Number of days past due
            delinquency_count: Number of delinquency incidents
            overdue_amount: Amount overdue
            
        Returns:
            Risk group: GROUP_1, GROUP_2, GROUP_3, or GROUP_4
        """
        
        if days_past_due == 0:
            return 'GROUP_1'
        elif days_past_due <= 30:
            return 'GROUP_2'
        elif days_past_due <= 90:
            return 'GROUP_3'
        else:
            return 'GROUP_4'
    
    @staticmethod
    def get_facility_risk_metrics(
        db: Session,
        facility_id: int
    ) -> Dict:
        """
        Calculate comprehensive risk metrics for a facility
        
        Args:
            db: SQLAlchemy session
            facility_id: Loan facility ID
            
        Returns:
            Dictionary with risk metrics
        """
        
        facility = db.query(LoanFacility).filter_by(
            facility_id=facility_id
        ).first()
        
        if not facility:
            return {'error': f'Facility {facility_id} not found'}
        
        customer = db.query(Customer).filter_by(
            customer_id=facility.customer_id
        ).first()
        
        # Get delinquency data
        latest_delinquency = db.query(LoanDelinquency).filter_by(
            facility_id=facility_id
        ).order_by(LoanDelinquency.as_of_date.desc()).first()
        
        # Get payment history
        total_payments = db.query(func.count(LoanFacility.facility_id)).filter_by(
            facility_id=facility_id
        ).scalar() or 0
        
        # Calculate on-time payment rate
        on_time_payments = db.query(func.count()).filter(
            LoanDelinquency.facility_id == facility_id,
            LoanDelinquency.days_past_due == 0
        ).scalar() or 0
        
        on_time_rate = (on_time_payments / total_payments * 100) if total_payments > 0 else 0
        
        # Risk metrics
        days_past_due = latest_delinquency.days_past_due if latest_delinquency else 0
        risk_group = RiskAnalysisService.classify_loan_group(days_past_due)
        
        return {
            'facility_id': facility_id,
            'customer_id': facility.customer_id,
            'facility_type': facility.facility_type,
            'approved_amount': float(facility.approved_amount),
            'interest_rate': float(facility.interest_rate),
            'status': facility.status,
            'days_past_due': days_past_due,
            'risk_group': risk_group,
            'risk_group_name': RiskAnalysisService.RISK_GROUPS[risk_group]['name'],
            'on_time_payment_rate': float(on_time_rate),
            'total_payments': total_payments,
            'on_time_payments': on_time_payments,
            'overdue_amount': float(latest_delinquency.overdue_amount) if latest_delinquency else 0
        }
    
    @staticmethod
    def get_portfolio_risk_summary(db: Session) -> Dict:
        """
        Calculate portfolio-level risk metrics
        
        Args:
            db: SQLAlchemy session
            
        Returns:
            Dictionary with portfolio summary
        """
        
        # Total facilities and amount
        total_facilities = db.query(func.count(LoanFacility.facility_id)).scalar()
        total_amount = db.query(func.sum(LoanFacility.approved_amount)).scalar() or 0
        
        # Distribution by GROUP
        group_distribution = {}
        for group_code in ['GROUP_1', 'GROUP_2', 'GROUP_3', 'GROUP_4']:
            count = db.query(func.count(LoanDelinquency.facility_id)).filter(
                LoanDelinquency.delinquency_class == group_code
            ).scalar() or 0
            
            group_distribution[group_code] = {
                'name': RiskAnalysisService.RISK_GROUPS[group_code]['name'],
                'count': count,
                'percentage': (count / total_facilities * 100) if total_facilities > 0 else 0
            }
        
        # Average metrics
        avg_dpd = db.query(func.avg(LoanDelinquency.days_past_due)).scalar() or 0
        avg_on_time_rate = 100  # Placeholder, calculate from actual data
        
        # Risk trend
        risk_trend = {
            'group_1_trend': 0,  # Calculate from migration table
            'group_2_trend': 0,
            'group_3_trend': 0,
            'group_4_trend': 0
        }
        
        return {
            'portfolio_summary': {
                'total_facilities': total_facilities,
                'total_amount': float(total_amount),
                'average_dpd': float(avg_dpd),
                'average_on_time_rate': float(avg_on_time_rate)
            },
            'group_distribution': group_distribution,
            'risk_trend': risk_trend,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def get_customer_risk_profile(
        db: Session,
        customer_id: int
    ) -> Dict:
        """
        Get comprehensive risk profile for a customer
        
        Args:
            db: SQLAlchemy session
            customer_id: Customer ID
            
        Returns:
            Dictionary with customer risk profile
        """
        
        customer = db.query(Customer).filter_by(
            customer_id=customer_id
        ).first()
        
        if not customer:
            return {'error': f'Customer {customer_id} not found'}
        
        # Get all facilities
        facilities = db.query(LoanFacility).filter_by(
            customer_id=customer_id
        ).all()
        
        facility_risks = []
        total_exposure = 0
        worst_group = 'GROUP_1'
        
        for facility in facilities:
            risk = RiskAnalysisService.get_facility_risk_metrics(db, facility.facility_id)
            facility_risks.append(risk)
            total_exposure += float(facility.approved_amount)
            
            # Track worst risk group
            group_level = int(risk['risk_group'][-1])
            worst_level = int(worst_group[-1])
            if group_level > worst_level:
                worst_group = risk['risk_group']
        
        # Calculate overall risk score
        overall_risk_score = RiskAnalysisService.calculate_risk_score(
            income=float(customer.monthly_income),
            debt_obligation=total_exposure / 12,
            age=customer.age,
            employment_status=customer.employment_status
        )
        
        return {
            'customer_id': customer_id,
            'name': customer.full_name,
            'age': customer.age,
            'monthly_income': float(customer.monthly_income),
            'credit_score': customer.credit_score,
            'employment_status': customer.employment_status,
            'total_exposure': float(total_exposure),
            'num_facilities': len(facilities),
            'worst_risk_group': worst_group,
            'overall_risk_score': overall_risk_score['risk_score'],
            'overall_risk_level': overall_risk_score['risk_level'],
            'facilities': facility_risks
        }
    
    @staticmethod
    def track_group_migration(
        db: Session,
        facility_id: int,
        new_group: str,
        reason: str = "Automatic classification"
    ) -> bool:
        """
        Record GROUP migration for tracking
        
        Args:
            db: SQLAlchemy session
            facility_id: Loan facility ID
            new_group: New GROUP classification
            reason: Reason for migration
            
        Returns:
            True if migration recorded
        """
        
        # Get current group
        latest_delinquency = db.query(LoanDelinquency).filter_by(
            facility_id=facility_id
        ).order_by(LoanDelinquency.as_of_date.desc()).first()
        
        if not latest_delinquency:
            return False
        
        current_group = latest_delinquency.risk_bucket
        
        if current_group != new_group:
            migration = LoanStatusMigration(
                facility_id=facility_id,
                from_group=current_group,
                to_group=new_group,
                migration_date=datetime.now(),
                reason=reason
            )
            db.add(migration)
            db.commit()
            logger.info(f"Migration recorded: {facility_id} {current_group}→{new_group}")
            return True
        
        return False
