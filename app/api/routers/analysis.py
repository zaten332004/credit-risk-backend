"""
Analysis Router - FastAPI endpoints for risk analysis and dashboard
Endpoints: POST /analyze/portfolio, POST /analyze/customer, GET /dashboard/summary
"""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.services.risk_analysis_service import RiskAnalysisService
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])


# Request/Response Models
class RiskScoreRequest(BaseModel):
    income: float
    debt_obligation: float
    age: int
    credit_history_months: int = 12
    employment_status: str = "Employed"


class RiskScoreResponse(BaseModel):
    risk_score: float
    risk_level: str
    dti_ratio: float
    components: dict
    timestamp: datetime = datetime.now()


class FacilityRiskResponse(BaseModel):
    facility_id: int
    customer_id: int
    facility_type: str
    approved_amount: float
    interest_rate: float
    status: str
    days_past_due: int
    risk_group: str
    risk_group_name: str
    on_time_payment_rate: float
    overdue_amount: float


class PortfolioSummaryResponse(BaseModel):
    portfolio_summary: dict
    group_distribution: dict
    risk_trend: dict
    timestamp: datetime


class CustomerRiskResponse(BaseModel):
    customer_id: int
    name: str
    age: int
    monthly_income: float
    credit_score: int
    employment_status: str
    total_exposure: float
    num_facilities: int
    worst_risk_group: str
    overall_risk_score: float
    overall_risk_level: str
    facilities: list


@router.post("/risk-score", response_model=RiskScoreResponse, summary="Calculate risk score")
async def calculate_risk_score(
    request: RiskScoreRequest,
    current_user = Depends(get_current_user)
) -> RiskScoreResponse:
    """
    Calculate risk score based on customer financial metrics
    
    **Parameters:**
    - `income`: Monthly income (float)
    - `debt_obligation`: Monthly debt obligations (float)
    - `age`: Customer age (int, 18-150)
    - `credit_history_months`: Months of credit history (default: 12)
    - `employment_status`: Employment status (Employed|Self-employed|Unemployed|Retired)
    
    **Returns:**
    - RiskScoreResponse with calculated score and components
    
    **Formula:**
    - Risk Score = (DTI × 60%) + (Age × 20%) + (History × 20%)
    - DTI: Debt-to-Income Ratio
    - Age Score: Inverse relationship (younger = higher risk)
    - History Score: Longer history = lower risk
    
    **Example:**
    ```
    POST /api/analyze/risk-score
    {
        "income": 50000000,
        "debt_obligation": 10000000,
        "age": 35,
        "credit_history_months": 24,
        "employment_status": "Employed"
    }
    ```
    
    **Response:**
    ```json
    {
        "risk_score": 0.28,
        "risk_level": "low",
        "dti_ratio": 20.0,
        "components": {
            "dti": {"weight": 0.6, "score": 0.4},
            "age": {"weight": 0.2, "score": 0.2},
            "history": {"weight": 0.2, "score": 0.3}
        },
        "timestamp": "2026-01-28T10:30:00"
    }
    ```
    """
    
    try:
        result = RiskAnalysisService.calculate_risk_score(
            income=request.income,
            debt_obligation=request.debt_obligation,
            age=request.age,
            credit_history_months=request.credit_history_months,
            employment_status=request.employment_status
        )
        
        return RiskScoreResponse(
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            dti_ratio=result['dti_ratio'],
            components=result['components']
        )
        
    except Exception as e:
        logger.error(f"Error calculating risk score: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/facility/{facility_id}", response_model=FacilityRiskResponse, summary="Get facility risk")
async def get_facility_risk(
    facility_id: int,
    db: Session = Depends(SessionLocal),
    current_user = Depends(get_current_user)
) -> FacilityRiskResponse:
    """
    Get detailed risk metrics for a specific loan facility
    
    **Parameters:**
    - `facility_id`: Loan facility ID (int)
    
    **Returns:**
    - FacilityRiskResponse with risk metrics
    
    **Example:**
    ```
    GET /api/analyze/facility/1
    ```
    
    **Response:**
    ```json
    {
        "facility_id": 1,
        "customer_id": 1,
        "facility_type": "Term Loan",
        "approved_amount": 500000000,
        "interest_rate": 8.5,
        "status": "active",
        "days_past_due": 0,
        "risk_group": "GROUP_1",
        "risk_group_name": "NORMAL",
        "on_time_payment_rate": 100.0,
        "overdue_amount": 0
    }
    ```
    """
    
    try:
        result = RiskAnalysisService.get_facility_risk_metrics(db, facility_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return FacilityRiskResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting facility risk: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/portfolio", response_model=PortfolioSummaryResponse, summary="Get portfolio risk summary")
async def get_portfolio_summary(
    db: Session = Depends(SessionLocal),
    current_user = Depends(get_current_user)
) -> PortfolioSummaryResponse:
    """
    Get portfolio-level risk summary and GROUP distribution
    
    **Returns:**
    - PortfolioSummaryResponse with portfolio metrics
    
    **Example:**
    ```
    GET /api/analyze/portfolio
    ```
    
    **Response:**
    ```json
    {
        "portfolio_summary": {
            "total_facilities": 9,
            "total_amount": 2325000000,
            "average_dpd": 15.5,
            "average_on_time_rate": 85.0
        },
        "group_distribution": {
            "GROUP_1": {"name": "NORMAL", "count": 3, "percentage": 33.3},
            "GROUP_2": {"name": "SPECIAL MENTION", "count": 2, "percentage": 22.2},
            "GROUP_3": {"name": "SUBSTANDARD", "count": 2, "percentage": 22.2},
            "GROUP_4": {"name": "DOUBTFUL", "count": 2, "percentage": 22.2}
        },
        "risk_trend": {...},
        "timestamp": "2026-01-28T10:30:00"
    }
    ```
    """
    
    try:
        result = RiskAnalysisService.get_portfolio_risk_summary(db)
        return PortfolioSummaryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/customer/{customer_id}", response_model=CustomerRiskResponse, summary="Get customer risk profile")
async def get_customer_risk(
    customer_id: int,
    db: Session = Depends(SessionLocal),
    current_user = Depends(get_current_user)
) -> CustomerRiskResponse:
    """
    Get comprehensive risk profile for a customer
    
    **Parameters:**
    - `customer_id`: Customer ID (int)
    
    **Returns:**
    - CustomerRiskResponse with detailed profile
    
    **Example:**
    ```
    GET /api/analyze/customer/1
    ```
    
    **Response:**
    ```json
    {
        "customer_id": 1,
        "name": "Nguyễn Văn A",
        "age": 35,
        "monthly_income": 50000000,
        "credit_score": 720,
        "employment_status": "Employed",
        "total_exposure": 750000000,
        "num_facilities": 3,
        "worst_risk_group": "GROUP_1",
        "overall_risk_score": 0.28,
        "overall_risk_level": "low",
        "facilities": [...]
    }
    ```
    """
    
    try:
        result = RiskAnalysisService.get_customer_risk_profile(db, customer_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return CustomerRiskResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customer risk: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/dashboard/summary", summary="Get dashboard summary")
async def get_dashboard_summary(
    db: Session = Depends(SessionLocal),
    current_user = Depends(get_current_user)
) -> dict:
    """
    Get complete dashboard summary with all key metrics
    
    **Returns:**
    - Dictionary with dashboard data
    
    **Example:**
    ```
    GET /api/analyze/dashboard/summary
    ```
    
    **Response:**
    ```json
    {
        "portfolio": {...},
        "risk_distribution": {...},
        "top_risks": [...],
        "key_metrics": {...},
        "timestamp": "2026-01-28T10:30:00"
    }
    ```
    """
    
    try:
        portfolio_summary = RiskAnalysisService.get_portfolio_risk_summary(db)
        
        return {
            'portfolio': portfolio_summary['portfolio_summary'],
            'group_distribution': portfolio_summary['group_distribution'],
            'risk_trend': portfolio_summary['risk_trend'],
            'dashboard_type': 'summary',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
