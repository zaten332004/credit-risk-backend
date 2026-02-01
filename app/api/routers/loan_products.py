"""
API Router for Loan Products
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.loan_product_models import LoanProductDB, LoanPricingRuleDB
from app.core.security import verify_token
from app.services.loan_product_service import LoanProductService

router = APIRouter(prefix="/api/v1/products", tags=["Loan Products"])


# Schemas
class LoanProductSchema(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    product_name_en: str
    category: str
    min_amount: float
    max_amount: float
    min_term_months: int
    max_term_months: int
    min_interest_rate: float
    max_interest_rate: float
    typical_interest_rate: Optional[float]
    collateral_required: bool
    collateral_type: Optional[str]
    ltv_ratio: Optional[float]
    max_dti_ratio: float
    min_credit_score: int
    processing_time_days: int
    
    class Config:
        from_attributes = True


class RecommendationRequest(BaseModel):
    age: int
    annual_income: float
    monthly_income: float
    credit_score: int
    customer_type: str  # individual, business, self_employed
    collateral_available: Optional[str] = None
    dti_ratio: Optional[float] = 0.0


class LoanScenarioRequest(BaseModel):
    product_id: int
    loan_amount: float
    annual_interest_rate: float
    term_months: int


class LoanComparisonRequest(BaseModel):
    loan_amount: float
    term_months: int


class MaxLoanRequest(BaseModel):
    product_id: int
    monthly_income: float
    annual_income: float
    collateral_value: Optional[float] = None


class MonthlyPaymentResponse(BaseModel):
    monthly_payment: float
    total_interest: float
    total_amount_paid: float
    daily_interest: float


class LoanScenarioResponse(BaseModel):
    product: str
    loan_amount: float
    interest_rate: float
    term_months: int
    monthly_payment: float
    total_interest: float
    total_amount_paid: float
    daily_interest: float


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Endpoints

@router.get("/", response_model=List[LoanProductSchema])
async def get_all_products(db: Session = Depends(get_db)):
    """Get all available loan products"""
    products = db.query(LoanProductDB).filter(LoanProductDB.is_active == True).all()
    return products


@router.get("/{product_id}", response_model=LoanProductSchema)
async def get_product_details(product_id: int, db: Session = Depends(get_db)):
    """Get specific loan product details"""
    product = db.query(LoanProductDB).filter(
        LoanProductDB.product_id == product_id,
        LoanProductDB.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.post("/recommend")
async def recommend_products(request: RecommendationRequest):
    """
    Recommend suitable loan products for a customer
    
    Request:
    - age: Customer age
    - annual_income: Annual income in VND
    - monthly_income: Monthly income in VND
    - credit_score: Credit score (0-999)
    - customer_type: 'individual', 'business', 'self_employed'
    - collateral_available: Optional collateral type ('real_estate', 'vehicle', 'savings_account')
    - dti_ratio: Current Debt-to-Income ratio (0-100)
    """
    try:
        recommendations = LoanProductService.recommend_product_for_customer(
            age=request.age,
            annual_income=request.annual_income,
            monthly_income=request.monthly_income,
            credit_score=request.credit_score,
            customer_type=request.customer_type,
            collateral_available=request.collateral_available,
            dti_ratio=request.dti_ratio or 0
        )
        
        return {
            "success": True,
            "count": len(recommendations),
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculate-max-loan")
async def calculate_max_loan(request: MaxLoanRequest):
    """
    Calculate maximum loan amount for a specific product
    
    Request:
    - product_id: Product ID
    - monthly_income: Monthly income in VND
    - annual_income: Annual income in VND
    - collateral_value: Optional collateral value in VND
    """
    try:
        max_amount, reason = LoanProductService.calculate_max_loan_amount(
            product_id=request.product_id,
            monthly_income=request.monthly_income,
            annual_income=request.annual_income,
            collateral_value=request.collateral_value
        )
        
        return {
            "success": True,
            "product_id": request.product_id,
            "max_loan_amount": max_amount,
            "reason": reason
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculate-payment", response_model=MonthlyPaymentResponse)
async def calculate_monthly_payment(request: LoanScenarioRequest):
    """
    Calculate monthly payment for a loan
    
    Request:
    - product_id: Product ID
    - loan_amount: Loan amount in VND
    - annual_interest_rate: Annual interest rate (%)
    - term_months: Loan term in months
    """
    try:
        scenario = LoanProductService.generate_loan_scenario(
            product_id=request.product_id,
            loan_amount=request.loan_amount,
            annual_interest_rate=request.annual_interest_rate,
            term_months=request.term_months
        )
        
        return MonthlyPaymentResponse(
            monthly_payment=scenario["monthly_payment"],
            total_interest=scenario["total_interest"],
            total_amount_paid=scenario["total_amount_paid"],
            daily_interest=scenario["daily_interest"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/loan-scenario", response_model=LoanScenarioResponse)
async def generate_loan_scenario(request: LoanScenarioRequest):
    """
    Generate detailed loan scenario
    
    Request:
    - product_id: Product ID
    - loan_amount: Loan amount in VND
    - annual_interest_rate: Annual interest rate (%)
    - term_months: Loan term in months
    """
    try:
        scenario = LoanProductService.generate_loan_scenario(
            product_id=request.product_id,
            loan_amount=request.loan_amount,
            annual_interest_rate=request.annual_interest_rate,
            term_months=request.term_months
        )
        
        return LoanScenarioResponse(**scenario)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compare")
async def compare_products(request: LoanComparisonRequest):
    """
    Compare all available products for given loan amount and term
    
    Request:
    - loan_amount: Loan amount in VND
    - term_months: Loan term in months
    
    Response:
    List of products sorted by monthly payment (lowest first)
    """
    try:
        comparisons = LoanProductService.compare_products(
            loan_amount=request.loan_amount,
            term_months=request.term_months
        )
        
        if not comparisons:
            raise HTTPException(
                status_code=404,
                detail="No products available for this amount and term"
            )
        
        return {
            "success": True,
            "loan_amount": request.loan_amount,
            "term_months": request.term_months,
            "comparison_count": len(comparisons),
            "comparisons": comparisons
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pricing-rules/{product_id}")
async def get_pricing_rules(product_id: int, db: Session = Depends(get_db)):
    """Get pricing rules for a specific product by credit score tier"""
    rules = db.query(LoanPricingRuleDB).filter(
        LoanPricingRuleDB.product_id == product_id,
        LoanPricingRuleDB.is_active == True
    ).order_by(LoanPricingRuleDB.credit_score_max.desc()).all()
    
    if not rules:
        raise HTTPException(status_code=404, detail="No pricing rules found for this product")
    
    return [
        {
            "customer_type": rule.customer_type,
            "credit_score_range": f"{rule.credit_score_min}-{rule.credit_score_max}",
            "base_rate": rule.base_interest_rate,
            "risk_premium": rule.risk_premium,
            "final_rate": rule.final_interest_rate,
            "loyalty_discount": rule.loyalty_discount,
            "early_repayment_discount": rule.early_repayment_discount
        }
        for rule in rules
    ]


@router.get("/search")
async def search_products(
    category: Optional[str] = Query(None, description="unsecured or secured"),
    min_amount: Optional[float] = Query(None, description="Minimum loan amount"),
    max_rate: Optional[float] = Query(None, description="Maximum interest rate"),
    db: Session = Depends(get_db)
):
    """Search products by criteria"""
    query = db.query(LoanProductDB).filter(LoanProductDB.is_active == True)
    
    if category:
        query = query.filter(LoanProductDB.category == category)
    
    if min_amount:
        query = query.filter(LoanProductDB.max_amount >= min_amount)
    
    if max_rate:
        query = query.filter(LoanProductDB.min_interest_rate <= max_rate)
    
    products = query.all()
    
    return {
        "success": True,
        "count": len(products),
        "products": [
            {
                "product_id": p.product_id,
                "product_name": p.product_name,
                "category": p.category,
                "interest_rate": f"{p.min_interest_rate:.1f}%-{p.max_interest_rate:.1f}%",
                "max_amount": p.max_amount
            }
            for p in products
        ]
    }
