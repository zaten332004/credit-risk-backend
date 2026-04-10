"""
Loan Approval Router - API endpoints for loan application and approval
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, get_current_analyst_user, get_current_manager_user
from app.db.session import get_db
from app.schemas.schemas import (
    LoanApplicationCreate,
    LoanApplicationRead,
    RiskRequest,
    RiskScoreDetail,
    User,
)
from app.services.loan_approval_service import LoanApprovalService

router = APIRouter(prefix="/api/v1/loan", tags=["loan"])


@router.post("/apply", response_model=LoanApplicationRead, status_code=201)
async def apply_for_loan(
    customer_id: int,
    loan_amount: float,
    loan_term: int,
    loan_purpose: str = "",
    current_user: User = Depends(get_current_analyst_user),  # Analyst+ có thể tạo hồ sơ vay
    db: Session = Depends(get_db),
) -> LoanApplicationRead:
    """
    Create a new loan application
    """
    try:
        result = LoanApprovalService.apply_for_loan(
            db=db,
            customer_id=customer_id,
            loan_amount=loan_amount,
            loan_term=loan_term,
            loan_purpose=loan_purpose,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/score/{application_id}", response_model=RiskScoreDetail)
async def score_loan_application(
    application_id: int,
    risk_data: RiskRequest,
    current_user: User = Depends(get_current_analyst_user),  # Analyst+ có thể score
    db: Session = Depends(get_db),
) -> RiskScoreDetail:
    """
    Score a loan application using risk model
    """
    try:
        db_app, db_prediction = LoanApprovalService.score_application(
            db=db,
            application_id=application_id,
            income=risk_data.income,
            debt=risk_data.debt,
            age=risk_data.age,
            credit_history_months=risk_data.credit_history_months,
        )

        # Convert risk_score to PD/LGD/EAD
        from app.services.services import score_to_pd_lgd_ead
        
        return score_to_pd_lgd_ead(float(db_prediction.risk_score))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/approve/{application_id}")
async def approve_loan_application(
    application_id: int,
    approved_amount: float,
    current_user: User = Depends(get_current_manager_user),  # Chỉ Manager+ có thể duyệt
    db: Session = Depends(get_db),
):
    """
    Approve a loan application and create facility
    """
    try:
        db_app, facility = LoanApprovalService.approve_application(
            db=db,
            application_id=application_id,
            approved_amount=approved_amount,
        )
        return {
            "status": "approved",
            "application_id": application_id,
            "facility_id": facility.facility_id if facility else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/reject/{application_id}")
async def reject_loan_application(
    application_id: int,
    reason: str = "",
    current_user: User = Depends(get_current_manager_user),  # Chỉ Manager+ có thể từ chối
    db: Session = Depends(get_db),
):
    """
    Reject a loan application
    """
    try:
        db_app = LoanApprovalService.reject_application(db, application_id)
        return {
            "status": "rejected",
            "application_id": application_id,
            "reason": reason,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/decision/{application_id}")
async def get_approval_decision(
    application_id: int,
    risk_threshold: float = 0.66,
    current_user: User = Depends(get_current_analyst_user),  # Analyst+ có thể xem quyết định
    db: Session = Depends(get_db),
):
    """
    Get automated approval decision for application
    """
    try:
        decision = LoanApprovalService.make_approval_decision(
            db=db,
            application_id=application_id,
            risk_threshold=risk_threshold,
        )
        return decision
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{application_id}")
async def get_application_details(
    application_id: int,
    current_user: User = Depends(get_current_analyst_user),  # Analyst+ có thể xem chi tiết
    db: Session = Depends(get_db),
):
    """
    Get loan application with risk score details
    """
    try:
        details = LoanApprovalService.get_application_with_score(db, application_id)
        return details
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
