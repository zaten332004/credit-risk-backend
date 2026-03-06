"""
Comprehensive Credit Risk Management Service
Integrates all modules: Customers, Loans, Risk Classification, Provisioning
"""
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum

from app.services.risk_classification_service import RiskClassificationService


class LoanStatus(Enum):
    """Loan status values"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    CLOSED = "closed"
    SUSPENDED = "suspended"
    DEFAULTED = "defaulted"


class DelinquencyStatus(Enum):
    """Delinquency status"""
    CURRENT = "current"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class EscalationLevel(Enum):
    """Escalation levels for collections"""
    NONE = 0
    NOTICE = 1
    FORMAL_DEMAND = 2
    LEGAL_ACTION = 3


@dataclass
class CustomerProfile:
    """Customer profile with summary"""
    customer_id: int
    full_name: str
    age: int
    monthly_income: float
    credit_score: int
    employment_status: str
    total_outstanding: float
    total_violations: int
    on_time_payment_rate: float
    recent_risk_upgrades: int
    recent_risk_downgrades: int


@dataclass
class LoanProfile:
    """Comprehensive loan information"""
    facility_id: int
    customer_id: int
    facility_amount: float
    disbursed_amount: float
    interest_rate: float
    facility_status: str
    principal_outstanding: float
    interest_outstanding: float
    penalty_outstanding: float
    days_overdue: int
    risk_group_id: int
    risk_level: str
    provision_rate: float
    provision_amount: float


@dataclass
class PortfolioMetrics:
    """Portfolio-level metrics"""
    total_loans: int
    total_outstanding: float
    total_provisions: float
    total_npl: float
    npl_ratio: float
    average_pd: float
    weighted_average_risk_score: float
    
    # By group
    group_1_count: int
    group_2_count: int
    group_3_count: int
    group_4_count: int
    group_5_count: int
    
    # Outstanding by group
    group_1_outstanding: float
    group_2_outstanding: float
    group_3_outstanding: float
    group_4_outstanding: float
    group_5_outstanding: float


class CreditRiskManagementService:
    """
    Comprehensive service for credit risk management
    Handles: customer management, loan lifecycle, risk classification, provisioning
    """
    
    @staticmethod
    def classify_facility(
        facility_id: int,
        days_overdue: int,
        principal_outstanding: float
    ) -> Dict:
        """
        Classify a loan facility into risk group and calculate provision
        """
        # Classify by days overdue
        classification = RiskClassificationService.classify_by_days_overdue(days_overdue)
        
        # Calculate provision
        provision_amount, remaining_amount = RiskClassificationService.calculate_provisions(
            principal_outstanding,
            classification.risk_group_id
        )
        
        return {
            "facility_id": facility_id,
            "risk_group_id": classification.risk_group_id,
            "risk_group_name": classification.risk_group_name,
            "risk_level": classification.risk_level,
            "days_overdue": days_overdue,
            "provision_rate": classification.provision_rate,
            "principal_outstanding": principal_outstanding,
            "provision_amount": provision_amount,
            "remaining_amount": remaining_amount,
            "classification_date": classification.classification_date
        }
    
    @staticmethod
    def calculate_customer_dti(monthly_income: float, total_outstanding: float) -> float:
        """
        Calculate DTI Ratio (Debt to Income)
        DTI = Total Outstanding / Monthly Income * 100
        """
        if monthly_income == 0:
            return 0
        
        return (total_outstanding / monthly_income) * 100
    
    @staticmethod
    def assess_customer_creditworthiness(
        age: int,
        credit_score: int,
        employment_status: str,
        dti_ratio: float,
        on_time_payment_rate: float
    ) -> Dict:
        """
        Assess customer creditworthiness based on multiple factors
        """
        risk_factors = []
        risk_score = 0
        
        # Age assessment
        if age < 25 or age > 65:
            risk_factors.append("Age outside optimal range (25-65)")
            risk_score += 15
        
        # Credit score assessment
        if credit_score < 300:
            risk_factors.append("Poor credit score (< 300)")
            risk_score += 30
        elif credit_score < 600:
            risk_factors.append("Fair credit score (300-600)")
            risk_score += 20
        elif credit_score < 750:
            risk_factors.append("Good credit score (600-750)")
            risk_score += 10
        else:
            risk_factors.append("Excellent credit score (750+)")
            risk_score += 0
        
        # Employment status assessment
        if employment_status.lower() == "unemployed":
            risk_factors.append("Unemployed status")
            risk_score += 25
        elif employment_status.lower() == "self-employed":
            risk_factors.append("Self-employed (higher risk)")
            risk_score += 10
        
        # DTI ratio assessment
        if dti_ratio > 50:
            risk_factors.append("Very high DTI ratio (> 50%)")
            risk_score += 25
        elif dti_ratio > 40:
            risk_factors.append("High DTI ratio (> 40%)")
            risk_score += 15
        elif dti_ratio > 30:
            risk_factors.append("Moderate DTI ratio (30-40%)")
            risk_score += 5
        
        # Payment history assessment
        if on_time_payment_rate < 70:
            risk_factors.append("Poor payment history (< 70%)")
            risk_score += 20
        elif on_time_payment_rate < 85:
            risk_factors.append("Fair payment history (70-85%)")
            risk_score += 10
        elif on_time_payment_rate < 95:
            risk_factors.append("Good payment history (85-95%)")
            risk_score += 5
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = "Very High"
            recommendation = "DECLINE"
        elif risk_score >= 60:
            risk_level = "High"
            recommendation = "REVIEW"
        elif risk_score >= 40:
            risk_level = "Medium"
            recommendation = "APPROVE with conditions"
        elif risk_score >= 20:
            risk_level = "Low"
            recommendation = "APPROVE"
        else:
            risk_level = "Very Low"
            recommendation = "APPROVE"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "risk_factors": risk_factors
        }
    
    @staticmethod
    def calculate_monthly_delinquency_stats(
        total_facilities: int,
        delinquent_facilities: int,
        total_outstanding: float,
        total_delinquent: float
    ) -> Dict:
        """
        Calculate monthly delinquency statistics
        """
        if total_facilities == 0:
            delinquency_rate = 0
        else:
            delinquency_rate = (delinquent_facilities / total_facilities) * 100
        
        if total_outstanding == 0:
            npl_ratio = 0
        else:
            npl_ratio = (total_delinquent / total_outstanding) * 100
        
        return {
            "total_facilities": total_facilities,
            "delinquent_facilities": delinquent_facilities,
            "delinquency_rate": delinquency_rate,
            "total_outstanding": total_outstanding,
            "total_delinquent": total_delinquent,
            "npl_ratio": npl_ratio,
            "healthy_facilities": total_facilities - delinquent_facilities
        }
    
    @staticmethod
    def calculate_portfolio_metrics(
        facilities: List[LoanProfile]
    ) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio metrics
        """
        total_loans = len(facilities)
        total_outstanding = 0
        total_provisions = 0
        total_npl = 0
        risk_scores = []
        
        # Initialize group counters
        group_counts = {i: 0 for i in range(1, 6)}
        group_outstanding = {i: 0.0 for i in range(1, 6)}
        
        for facility in facilities:
            total_outstanding += facility.principal_outstanding
            total_provisions += facility.provision_amount
            
            # NPL = Group 3-5
            if facility.risk_group_id >= 3:
                total_npl += facility.principal_outstanding
            
            # Count by group
            group_counts[facility.risk_group_id] += 1
            group_outstanding[facility.risk_group_id] += facility.principal_outstanding
            
            # For weighted average risk score (assuming facility.risk_group_id as proxy)
            risk_scores.append(facility.risk_group_id)
        
        # Calculate ratios
        npl_ratio = (total_npl / total_outstanding * 100) if total_outstanding > 0 else 0
        average_pd = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        weighted_average_risk_score = average_pd  # Simplified
        
        return PortfolioMetrics(
            total_loans=total_loans,
            total_outstanding=total_outstanding,
            total_provisions=total_provisions,
            total_npl=total_npl,
            npl_ratio=npl_ratio,
            average_pd=average_pd,
            weighted_average_risk_score=weighted_average_risk_score,
            group_1_count=group_counts[1],
            group_2_count=group_counts[2],
            group_3_count=group_counts[3],
            group_4_count=group_counts[4],
            group_5_count=group_counts[5],
            group_1_outstanding=group_outstanding[1],
            group_2_outstanding=group_outstanding[2],
            group_3_outstanding=group_outstanding[3],
            group_4_outstanding=group_outstanding[4],
            group_5_outstanding=group_outstanding[5]
        )
    
    @staticmethod
    def determine_escalation_action(
        days_overdue: int,
        escalation_level: int
    ) -> Dict:
        """
        Determine appropriate escalation action for delinquent account
        """
        actions = []
        recommended_level = escalation_level
        
        if days_overdue < 10:
            action = "No action - within acceptable range"
            recommended_level = EscalationLevel.NONE.value
        
        elif days_overdue < 30:
            actions = [
                "Send payment reminder SMS/Email",
                "Review account for risk signals"
            ]
            recommended_level = EscalationLevel.NOTICE.value
            action = "NOTICE"
        
        elif days_overdue < 60:
            actions = [
                "Send formal payment notice",
                "Document communication",
                "Review for possible forbearance options"
            ]
            recommended_level = EscalationLevel.FORMAL_DEMAND.value
            action = "FORMAL DEMAND"
        
        elif days_overdue < 90:
            actions = [
                "Send second formal notice",
                "Increase contact frequency",
                "Consider collection agency referral"
            ]
            recommended_level = EscalationLevel.FORMAL_DEMAND.value
            action = "FORMAL DEMAND (escalated)"
        
        else:  # 90+ days
            actions = [
                "Refer to legal department",
                "Initiate collection proceedings",
                "Consider write-off",
                "Report to credit bureau"
            ]
            recommended_level = EscalationLevel.LEGAL_ACTION.value
            action = "LEGAL ACTION"
        
        return {
            "days_overdue": days_overdue,
            "current_escalation_level": escalation_level,
            "recommended_escalation_level": recommended_level,
            "recommended_action": action,
            "action_items": actions
        }
    
    @staticmethod
    def generate_risk_report(
        portfolio_metrics: PortfolioMetrics,
        risk_threshold_npl: float = 5.0
    ) -> Dict:
        """
        Generate comprehensive risk report for portfolio
        """
        report = {
            "report_date": datetime.utcnow(),
            "portfolio_metrics": {
                "total_loans": portfolio_metrics.total_loans,
                "total_outstanding": portfolio_metrics.total_outstanding,
                "total_provisions": portfolio_metrics.total_provisions,
                "npl_ratio": round(portfolio_metrics.npl_ratio, 2),
                "average_risk_score": round(portfolio_metrics.weighted_average_risk_score, 4)
            },
            "risk_breakdown": {
                "group_1": {
                    "name": "Nợ đủ tiêu chuẩn (Group 1)",
                    "count": portfolio_metrics.group_1_count,
                    "outstanding": portfolio_metrics.group_1_outstanding
                },
                "group_2": {
                    "name": "Nợ cần chú ý (Group 2)",
                    "count": portfolio_metrics.group_2_count,
                    "outstanding": portfolio_metrics.group_2_outstanding
                },
                "group_3": {
                    "name": "Nợ dưới tiêu chuẩn (Group 3)",
                    "count": portfolio_metrics.group_3_count,
                    "outstanding": portfolio_metrics.group_3_outstanding
                },
                "group_4": {
                    "name": "Nợ nghi ngờ (Group 4)",
                    "count": portfolio_metrics.group_4_count,
                    "outstanding": portfolio_metrics.group_4_outstanding
                },
                "group_5": {
                    "name": "Nợ mất vốn (Group 5)",
                    "count": portfolio_metrics.group_5_count,
                    "outstanding": portfolio_metrics.group_5_outstanding
                }
            },
            "risk_assessment": {
                "npl_threshold": risk_threshold_npl,
                "npl_ratio": round(portfolio_metrics.npl_ratio, 2),
                "risk_status": "ALERT" if portfolio_metrics.npl_ratio > risk_threshold_npl else "NORMAL",
                "recommendation": "Immediate action required - NPL ratio exceeds threshold"
                                 if portfolio_metrics.npl_ratio > risk_threshold_npl
                                 else "Portfolio within acceptable risk limits"
            }
        }
        
        return report


if __name__ == "__main__":
    # Test examples
    print("=" * 80)
    print("CREDIT RISK MANAGEMENT SERVICE - TEST EXAMPLES")
    print("=" * 80)
    print()
    
    # Example 1: Classify a facility
    print("Example 1: Classify a facility overdue 100 days, VND 500M outstanding")
    print("-" * 80)
    classification = CreditRiskManagementService.classify_facility(
        facility_id=1001,
        days_overdue=100,
        principal_outstanding=500_000_000
    )
    for key, value in classification.items():
        if isinstance(value, float) and key in ['principal_outstanding', 'provision_amount', 'remaining_amount']:
            print(f"  {key}: VND {value:,.0f}")
        else:
            print(f"  {key}: {value}")
    print()
    
    # Example 2: Assess customer creditworthiness
    print("Example 2: Assess customer creditworthiness")
    print("-" * 80)
    assessment = CreditRiskManagementService.assess_customer_creditworthiness(
        age=35,
        credit_score=680,
        employment_status="Employed",
        dti_ratio=35.5,
        on_time_payment_rate=92.0
    )
    print(f"  Risk Score: {assessment['risk_score']}")
    print(f"  Risk Level: {assessment['risk_level']}")
    print(f"  Recommendation: {assessment['recommendation']}")
    print(f"  Risk Factors: {', '.join(assessment['risk_factors'])}")
    print()
    
    # Example 3: Calculate monthly delinquency
    print("Example 3: Monthly delinquency statistics")
    print("-" * 80)
    delinq = CreditRiskManagementService.calculate_monthly_delinquency_stats(
        total_facilities=1000,
        delinquent_facilities=85,
        total_outstanding=5_000_000_000,
        total_delinquent=120_000_000
    )
    print(f"  Total Facilities: {delinq['total_facilities']}")
    print(f"  Delinquent Facilities: {delinq['delinquent_facilities']}")
    print(f"  Delinquency Rate: {delinq['delinquency_rate']:.2f}%")
    print(f"  NPL Ratio: {delinq['npl_ratio']:.2f}%")
    print()
    
    # Example 4: Escalation action
    print("Example 4: Determine escalation action for 75 days overdue")
    print("-" * 80)
    escalation = CreditRiskManagementService.determine_escalation_action(
        days_overdue=75,
        escalation_level=1
    )
    print(f"  Recommended Action: {escalation['recommended_action']}")
    print(f"  Action Items:")
    for item in escalation['action_items']:
        print(f"    - {item}")
    print()
    
    print("=" * 80)
    print("✓ All test cases completed successfully!")
    print("=" * 80)
