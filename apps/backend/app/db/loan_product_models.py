"""
Database Models for Loan Products
"""
from sqlalchemy import Column, String, NUMERIC, Integer, Boolean, TEXT, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class LoanProductDB(Base):
    """Loan Product Type"""
    __tablename__ = "Loan_Product"
    
    product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(20), unique=True, nullable=False, comment="Product code (e.g., TIN_CHAP_01)")
    product_name = Column(String(100), nullable=False, comment="Vietnamese product name")
    product_name_en = Column(String(100), nullable=False, comment="English product name")
    category = Column(String(20), nullable=False, comment="unsecured / secured")
    
    # Amount limits
    min_amount = Column(NUMERIC(18, 0), nullable=False, comment="Minimum loan amount (VND)")
    max_amount = Column(NUMERIC(18, 0), nullable=False, comment="Maximum loan amount (VND)")
    
    # Term limits
    min_term_months = Column(Integer, nullable=False, comment="Minimum term in months")
    max_term_months = Column(Integer, nullable=False, comment="Maximum term in months")
    
    # Interest rate
    min_interest_rate = Column(NUMERIC(5, 2), nullable=False, comment="Minimum annual interest rate %")
    max_interest_rate = Column(NUMERIC(5, 2), nullable=False, comment="Maximum annual interest rate %")
    typical_interest_rate = Column(NUMERIC(5, 2), nullable=True, comment="Typical interest rate %")
    promotion_interest_rate = Column(NUMERIC(5, 2), nullable=True, comment="Promotional rate %")
    
    # Collateral
    collateral_required = Column(Boolean, default=False, comment="Is collateral required?")
    collateral_type = Column(String(50), nullable=True, comment="Type of collateral (real_estate, vehicle, savings)")
    ltv_ratio = Column(NUMERIC(5, 2), nullable=True, comment="Loan-to-Value ratio (0-100)")
    
    # Customer criteria
    max_dti_ratio = Column(NUMERIC(5, 2), nullable=False, comment="Maximum Debt-to-Income ratio %")
    min_credit_score = Column(Integer, nullable=False, comment="Minimum credit score required")
    
    # Processing
    processing_time_days = Column(Integer, nullable=False, comment="Typical processing time in days")
    approval_authority = Column(String(50), nullable=False, comment="Approval authority level")
    
    # Description
    description = Column(TEXT, nullable=True, comment="Product description")
    eligible_customers = Column(String(500), nullable=True, comment="Comma-separated eligible customer types")
    required_documents = Column(TEXT, nullable=True, comment="Required documents list")
    risk_factors = Column(TEXT, nullable=True, comment="Key risk factors")
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    # loan_facilities = relationship("LoanFacilityDB", back_populates="product")
    pricing_rules = relationship("LoanPricingRuleDB", back_populates="product")


class LoanPricingRuleDB(Base):
    """Interest Rate Pricing Rules by Customer Segment"""
    __tablename__ = "Loan_Pricing_Rule"
    
    rule_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("Loan_Product.product_id"), nullable=False)
    
    # Customer segment
    customer_type = Column(String(50), nullable=False, comment="individual / business / self_employed")
    credit_score_min = Column(Integer, nullable=False, comment="Minimum credit score for this tier")
    credit_score_max = Column(Integer, nullable=False, comment="Maximum credit score for this tier")
    
    # Pricing
    base_interest_rate = Column(NUMERIC(5, 2), nullable=False, comment="Base interest rate %")
    risk_premium = Column(NUMERIC(5, 2), nullable=False, comment="Risk premium adjustment %")
    final_interest_rate = Column(NUMERIC(5, 2), nullable=False, comment="Final interest rate % (base + premium)")
    
    # Discounts
    loyalty_discount = Column(NUMERIC(5, 2), default=0, comment="Discount for existing customers %")
    early_repayment_discount = Column(NUMERIC(5, 2), default=0, comment="Discount for early repayment %")
    
    # Effective period
    effective_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    effective_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    product = relationship("LoanProductDB", back_populates="pricing_rules")


class LoanApprovalLimitDB(Base):
    """Approval limits by authority level"""
    __tablename__ = "Loan_Approval_Limit"
    
    limit_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("Loan_Product.product_id"), nullable=False)
    
    # Authority level
    approval_level = Column(String(50), nullable=False, comment="branch_manager / credit_committee / senior_management")
    
    # Amount limits
    min_approval_amount = Column(NUMERIC(18, 0), nullable=False, comment="Minimum amount for this level")
    max_approval_amount = Column(NUMERIC(18, 0), nullable=False, comment="Maximum amount this level can approve")
    
    # Customer criteria for higher amounts
    min_customer_credit_score = Column(Integer, nullable=False, comment="Minimum credit score required")
    max_dti_ratio = Column(NUMERIC(5, 2), nullable=False, comment="Maximum DTI ratio allowed")
    
    # Process
    required_documents = Column(TEXT, nullable=True, comment="Additional required documents")
    max_processing_days = Column(Integer, nullable=False, comment="Maximum approval time in days")
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LoanApprovalDB(Base):
    """Loan Application & Approval Record"""
    __tablename__ = "Loan_Approval"
    
    approval_id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("Loan_Facility.facility_id"), nullable=True, comment="Link to facility if approved")
    product_id = Column(Integer, ForeignKey("Loan_Product.product_id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("Customer.customer_id"), nullable=False)
    
    # Application details
    requested_amount = Column(NUMERIC(18, 2), nullable=False)
    requested_term_months = Column(Integer, nullable=False)
    approved_amount = Column(NUMERIC(18, 2), nullable=True, comment="Amount actually approved")
    approved_term_months = Column(Integer, nullable=True)
    approved_rate = Column(NUMERIC(5, 2), nullable=True, comment="Approved interest rate %")
    
    # Approval status
    status = Column(String(20), nullable=False, comment="pending / approved / rejected / cancelled")
    
    # Decision
    approved_by = Column(Integer, ForeignKey("User.user_id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(TEXT, nullable=True)
    
    # Conditions
    special_conditions = Column(TEXT, nullable=True, comment="Any special approval conditions")
    required_collateral_value = Column(NUMERIC(18, 2), nullable=True)
    loan_to_value_approved = Column(NUMERIC(5, 2), nullable=True, comment="Approved LTV %")
    
    # Timeline
    application_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_date = Column(DateTime, nullable=True)
    decision_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    product = relationship("LoanProductDB")  # back_populates="loan_approvals"


class LoanProductRequirementDB(Base):
    """Product-specific requirements"""
    __tablename__ = "Loan_Product_Requirement"
    
    requirement_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("Loan_Product.product_id"), nullable=False)
    
    # Requirement details
    requirement_type = Column(String(50), nullable=False, comment="document / collateral / ratio / score")
    requirement_code = Column(String(50), nullable=False)
    requirement_name = Column(String(200), nullable=False)
    requirement_description = Column(TEXT, nullable=True)
    
    # Validation rules
    is_mandatory = Column(Boolean, default=True, comment="Is this requirement mandatory?")
    minimum_value = Column(NUMERIC(18, 2), nullable=True, comment="Minimum value if applicable")
    maximum_value = Column(NUMERIC(18, 2), nullable=True)
    
    # For documents
    document_type = Column(String(100), nullable=True)
    
    # For collateral
    collateral_category = Column(String(50), nullable=True)
    
    # Effective period
    effective_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    effective_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
