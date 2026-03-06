"""
Database models for Risk Classification System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class RiskGroupDB(Base):
    """Risk Classification Groups (SBV Circular 11/2021/TT-NHNN)"""
    
    __tablename__ = "Risk_Group"
    
    group_id = Column(Integer, primary_key=True)
    group_name = Column(String(100), nullable=False, unique=True)
    group_name_en = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    description_vn = Column(Text, nullable=True)
    
    # Days overdue range
    days_from = Column(Integer, nullable=False)
    days_to = Column(Integer, nullable=False)
    
    # Risk metrics
    risk_level = Column(String(50), nullable=False)  # Very Low, Low, Medium-High, High, Very High
    provision_rate = Column(Numeric(5, 2), nullable=False)  # 0-100 percentage
    
    # UI Properties
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    # Relationships
    loan_classifications = relationship("LoanClassificationDB", back_populates="risk_group")


class LoanClassificationDB(Base):
    """Loan Risk Classification Record"""
    
    __tablename__ = "Loan_Classification"
    
    classification_id = Column(BigInteger, primary_key=True, autoincrement=True)
    facility_id = Column(BigInteger, ForeignKey("Loan_Facility.facility_id"), nullable=False)
    
    # Classification details
    group_id = Column(Integer, ForeignKey("Risk_Group.group_id"), nullable=False)
    days_overdue = Column(Integer, nullable=False)
    
    # Financial impact
    outstanding_principal = Column(Numeric(18, 2), nullable=True)
    provision_amount = Column(Numeric(18, 2), nullable=True)
    
    # Status
    classification_status = Column(String(50), nullable=False, default="active")  # active, archived, reassessed
    
    # Audit
    classified_by = Column(BigInteger, ForeignKey("User.user_id"), nullable=True)
    classified_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    risk_group = relationship("RiskGroupDB", back_populates="loan_classifications")
    facility = relationship("LoanFacilityDB", back_populates="classifications")


class LoanDelinquencyDB(Base):
    """Loan Delinquency Tracking"""
    
    __tablename__ = "Loan_Delinquency"
    
    delinquency_id = Column(BigInteger, primary_key=True, autoincrement=True)
    facility_id = Column(BigInteger, ForeignKey("Loan_Facility.facility_id"), nullable=False)
    
    # Delinquency period
    original_due_date = Column(DateTime, nullable=False)
    last_payment_date = Column(DateTime, nullable=True)
    current_overdue_days = Column(Integer, nullable=False, default=0)
    
    # Amount details
    principal_outstanding = Column(Numeric(18, 2), nullable=False)
    interest_outstanding = Column(Numeric(18, 2), nullable=False, default=0)
    penalty_outstanding = Column(Numeric(18, 2), nullable=False, default=0)
    
    # Status and action
    delinquency_status = Column(String(50), nullable=False, default="current")  # current, resolved, escalated
    escalation_level = Column(Integer, nullable=False, default=0)  # 0=none, 1=notice, 2=formal demand, 3=legal action
    
    # Dates
    delinquency_start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_action_date = Column(DateTime, nullable=True)
    expected_resolution_date = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    facility = relationship("LoanFacilityDB", back_populates="delinquencies")


class ProvisionAllocationDB(Base):
    """Loan Loss Provision Allocation"""
    
    __tablename__ = "Provision_Allocation"
    
    provision_id = Column(BigInteger, primary_key=True, autoincrement=True)
    facility_id = Column(BigInteger, ForeignKey("Loan_Facility.facility_id"), nullable=False)
    risk_group_id = Column(Integer, ForeignKey("Risk_Group.group_id"), nullable=False)
    
    # Provision calculation
    outstanding_amount = Column(Numeric(18, 2), nullable=False)
    provision_rate = Column(Numeric(5, 2), nullable=False)  # 0-100 percentage
    provision_amount = Column(Numeric(18, 2), nullable=False)
    
    # Period
    allocation_period = Column(String(20), nullable=False)  # YYYY-MM format
    allocation_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Status
    is_released = Column(Integer, default=0)  # 0=allocated, 1=released
    release_date = Column(DateTime, nullable=True)
    
    # Audit
    allocated_by = Column(BigInteger, ForeignKey("User.user_id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    facility = relationship("LoanFacilityDB", back_populates="provisions")
    risk_group = relationship("RiskGroupDB")
