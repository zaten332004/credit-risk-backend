from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, Date, DateTime, Numeric, ForeignKey, Integer, String, Text, BigInteger
from sqlalchemy.orm import relationship

from app.db.session import Base


# ============================================================================
# Role
# ============================================================================
class RoleDB(Base):
    __tablename__ = "Role"

    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), nullable=False, unique=True)
    description = Column(String(500), nullable=True)

    users = relationship("UserDB", back_populates="role")


# ============================================================================
# User
# ============================================================================
class UserDB(Base):
    __tablename__ = "User"

    user_id = Column(BigInteger, primary_key=True)
    role_id = Column(Integer, ForeignKey("Role.role_id"), nullable=True)  # nullable for pending registrations
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Registration workflow fields
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected, verified
    user_type = Column(String(20), nullable=True)  # 'analyst' or 'manager' - auto-filled from registration_type
    verification_token = Column(String(255), nullable=True)
    verification_sent_at = Column(DateTime, nullable=True)
    is_email_verified = Column(Boolean, default=False)
    approved_by = Column(BigInteger, ForeignKey("User.user_id"), nullable=True)  # admin who approved
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(500), nullable=True)
    
    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    role = relationship("RoleDB", back_populates="users")
    chat_messages = relationship("ChatHistoryDB", back_populates="user")
    audit_logs = relationship("AuditLogDB", back_populates="user")
    chat_sessions = relationship("ChatSessionDB", back_populates="user")
    alert_subscriptions = relationship("AlertSubscriptionDB", back_populates="user")


# ============================================================================
# Customer
# ============================================================================
class CustomerDB(Base):
    __tablename__ = "Customer"

    customer_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("User.user_id"), nullable=True)
    full_name = Column(String(150), nullable=False)
    age = Column(Integer, nullable=True)
    monthly_income = Column(Numeric(18, 2), nullable=True)
    credit_score = Column(Integer, nullable=True)
    employment_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    employments = relationship("CustomerEmploymentDB", back_populates="customer")
    loan_applications = relationship("LoanApplicationDB", back_populates="customer")
    loan_facilities = relationship("LoanFacilityDB", back_populates="customer")
    financial_indicators = relationship("FinancialIndicatorDB", back_populates="customer")
    risk_predictions = relationship("RiskPredictionDB", back_populates="customer")
    alerts = relationship("AlertDB", back_populates="customer")


# ============================================================================
# Customer Employment
# ============================================================================
class CustomerEmploymentDB(Base):
    __tablename__ = "Customer_Employment"

    employment_id = Column(BigInteger, primary_key=True)
    customer_id = Column(BigInteger, ForeignKey("Customer.customer_id"), nullable=False)
    company_name = Column(String(200), nullable=True)
    position = Column(String(100), nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    monthly_income = Column(Numeric(18, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    customer = relationship("CustomerDB", back_populates="employments")


# ============================================================================
# Loan Application
# ============================================================================
class LoanApplicationDB(Base):
    __tablename__ = "Loan_Application"

    application_id = Column(BigInteger, primary_key=True)
    customer_id = Column(BigInteger, ForeignKey("Customer.customer_id"), nullable=False)
    loan_amount = Column(Numeric(18, 2), nullable=False)
    loan_term = Column(Integer, nullable=False)  # months
    interest_rate = Column(Numeric(10, 4), nullable=True)
    loan_status = Column(String(50), nullable=False)  # pending, approved, rejected, disbursed
    loan_purpose = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    customer = relationship("CustomerDB", back_populates="loan_applications")
    facilities = relationship("LoanFacilityDB", back_populates="application")
    risk_predictions = relationship("RiskPredictionDB", back_populates="application")


# ============================================================================
# Loan Facility
# ============================================================================
class LoanFacilityDB(Base):
    __tablename__ = "Loan_Facility"

    facility_id = Column(BigInteger, primary_key=True)
    application_id = Column(BigInteger, ForeignKey("Loan_Application.application_id"), nullable=True)
    customer_id = Column(BigInteger, ForeignKey("Customer.customer_id"), nullable=False)
    facility_type = Column(String(50), nullable=True)  # term_loan, revolving, etc.
    approved_amount = Column(Numeric(18, 2), nullable=False)
    interest_rate = Column(Numeric(10, 4), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=False)  # active, closed, arrears
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    application = relationship("LoanApplicationDB", back_populates="facilities")
    customer = relationship("CustomerDB", back_populates="loan_facilities")
    repayment_schedules = relationship("LoanRepaymentScheduleDB", back_populates="facility")
    payments = relationship("LoanPaymentDB", back_populates="facility")
    delinquencies = relationship("LoanDelinquencyDB", back_populates="facility")
    alerts = relationship("AlertDB", back_populates="facility")


# ============================================================================
# Loan Repayment Schedule
# ============================================================================
class LoanRepaymentScheduleDB(Base):
    __tablename__ = "Loan_Repayment_Schedule"

    schedule_id = Column(BigInteger, primary_key=True)
    facility_id = Column(BigInteger, ForeignKey("Loan_Facility.facility_id"), nullable=False)
    installment_no = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    principal_amount = Column(Numeric(18, 2), nullable=False)
    interest_amount = Column(Numeric(18, 2), nullable=False)
    total_due = Column(Numeric(18, 2), nullable=False)
    remaining_balance = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    facility = relationship("LoanFacilityDB", back_populates="repayment_schedules")
    payments = relationship("LoanPaymentDB", back_populates="schedule")


# ============================================================================
# Loan Payment
# ============================================================================
class LoanPaymentDB(Base):
    __tablename__ = "Loan_Payment"

    payment_id = Column(BigInteger, primary_key=True)
    facility_id = Column(BigInteger, ForeignKey("Loan_Facility.facility_id"), nullable=False)
    schedule_id = Column(BigInteger, ForeignKey("Loan_Repayment_Schedule.schedule_id"), nullable=True)
    payment_date = Column(Date, nullable=False)
    amount_paid = Column(Numeric(18, 2), nullable=False)
    principal_paid = Column(Numeric(18, 2), nullable=True)
    interest_paid = Column(Numeric(18, 2), nullable=True)
    payment_method = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)  # paid, partial, late
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    facility = relationship("LoanFacilityDB", back_populates="payments")
    schedule = relationship("LoanRepaymentScheduleDB", back_populates="payments")


# ============================================================================
# Loan Delinquency
# ============================================================================
class LoanDelinquencyDB(Base):
    __tablename__ = "Loan_Delinquency"

    delinquency_id = Column(BigInteger, primary_key=True)
    facility_id = Column(BigInteger, ForeignKey("Loan_Facility.facility_id"), nullable=False)
    as_of_date = Column(Date, nullable=False)
    days_past_due = Column(Integer, nullable=False)
    overdue_amount = Column(Numeric(18, 2), nullable=True)
    risk_bucket = Column(String(20), nullable=True)  # Current, 1-30, 31-60, 61-90, 90+
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    facility = relationship("LoanFacilityDB", back_populates="delinquencies")


# ============================================================================
# Alert
# ============================================================================
class AlertDB(Base):
    __tablename__ = "Alert"

    alert_id = Column(BigInteger, primary_key=True)
    facility_id = Column(BigInteger, ForeignKey("Loan_Facility.facility_id"), nullable=True)
    customer_id = Column(BigInteger, ForeignKey("Customer.customer_id"), nullable=True)
    alert_type = Column(String(50), nullable=False)  # high_pd, delinquency, overdue
    severity = Column(String(20), nullable=False)  # low, medium, high
    message = Column(String(500), nullable=True)
    is_resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    facility = relationship("LoanFacilityDB", back_populates="alerts")
    customer = relationship("CustomerDB", back_populates="alerts")


# ============================================================================
# Alert Subscription
# ============================================================================
class AlertSubscriptionDB(Base):
    __tablename__ = "Alert_Subscription"

    subscription_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("User.user_id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    alert_severity = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("UserDB", back_populates="alert_subscriptions")


# ============================================================================
# Financial Indicator
# ============================================================================
class FinancialIndicatorDB(Base):
    __tablename__ = "FINANCIAL_INDICATOR"

    indicator_id = Column(BigInteger, primary_key=True)
    customer_id = Column(BigInteger, ForeignKey("Customer.customer_id"), nullable=False)
    debt_to_income = Column(Numeric(10, 4), nullable=True)
    monthly_expense = Column(Numeric(18, 2), nullable=True)
    asset_value = Column(Numeric(18, 2), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    customer = relationship("CustomerDB", back_populates="financial_indicators")


# ============================================================================
# Linear Model
# ============================================================================
class LinearModelDB(Base):
    __tablename__ = "LINEAR_MODEL"

    model_id = Column(BigInteger, primary_key=True)
    model_name = Column(String(100), nullable=False)
    version_tag = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    r_squared = Column(Numeric(10, 6), nullable=True)
    mse = Column(Numeric(18, 6), nullable=True)

    coefficients = relationship("RegressionCoefficientDB", back_populates="model")
    predictions = relationship("RiskPredictionDB", back_populates="model")


# ============================================================================
# Regression Coefficient
# ============================================================================
class RegressionCoefficientDB(Base):
    __tablename__ = "REGRESSION_COEFFICIENT"

    coefficient_id = Column(BigInteger, primary_key=True)
    model_id = Column(BigInteger, ForeignKey("LINEAR_MODEL.model_id"), nullable=False)
    feature_name = Column(String(100), nullable=False)
    beta_value = Column(Numeric(18, 6), nullable=False)

    model = relationship("LinearModelDB", back_populates="coefficients")


# ============================================================================
# Risk Prediction
# ============================================================================
class RiskPredictionDB(Base):
    __tablename__ = "RISK_PREDICTION"

    prediction_id = Column(BigInteger, primary_key=True)
    application_id = Column(BigInteger, ForeignKey("Loan_Application.application_id"), nullable=True)
    customer_id = Column(BigInteger, ForeignKey("Customer.customer_id"), nullable=True)
    model_id = Column(BigInteger, ForeignKey("LINEAR_MODEL.model_id"), nullable=True)
    risk_score = Column(Numeric(10, 6), nullable=False)
    risk_level = Column(String(20), nullable=True)  # low, medium, high
    predicted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    application = relationship("LoanApplicationDB", back_populates="risk_predictions")
    customer = relationship("CustomerDB", back_populates="risk_predictions")
    model = relationship("LinearModelDB", back_populates="predictions")
    shap_explanations = relationship("SHAPExplanationDB", back_populates="prediction")


# ============================================================================
# SHAP Explanation
# ============================================================================
class SHAPExplanationDB(Base):
    __tablename__ = "SHAP_Explanation"

    explain_id = Column(BigInteger, primary_key=True)
    prediction_id = Column(BigInteger, ForeignKey("RISK_PREDICTION.prediction_id"), nullable=False)
    feature_name = Column(String(100), nullable=False)
    shap_value = Column(Numeric(18, 6), nullable=False)
    contribution_type = Column(String(20), nullable=True)  # positive, negative
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    prediction = relationship("RiskPredictionDB", back_populates="shap_explanations")


# ============================================================================
# Chat Session (Gemini AI Chatbot) - khớp DB thật: session_id GUID, user_id, created_at, last_interaction
# ============================================================================
class ChatSessionDB(Base):
    __tablename__ = "Chat_Session"

    session_id = Column(String(36), primary_key=True)  # uniqueidentifier trong SQL Server, lưu dạng "uuid-string"
    user_id = Column(BigInteger, ForeignKey("User.user_id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_interaction = Column(DateTime, nullable=True)

    user = relationship("UserDB", back_populates="chat_sessions")
    messages = relationship("ChatHistoryDB", back_populates="session", cascade="all, delete-orphan")


# ============================================================================
# Chat History - khớp DB thật: chat_id, user_id, message, bot_response, created_at, session_id
# ============================================================================
class ChatHistoryDB(Base):
    __tablename__ = "Chat_History"

    chat_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("Chat_Session.session_id"), nullable=True)
    user_id = Column(BigInteger, ForeignKey("User.user_id"), nullable=False)
    message = Column(Text, nullable=False)  # user message
    bot_response = Column(Text, nullable=True)   # assistant reply
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("ChatSessionDB", back_populates="messages", foreign_keys=[session_id])
    user = relationship("UserDB", back_populates="chat_messages")


# ============================================================================
# Portfolio Snapshot
# ============================================================================
class PortfolioSnapshotDB(Base):
    __tablename__ = "Portfolio_Snapshot"

    snapshot_id = Column(BigInteger, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    total_exposure = Column(Numeric(20, 2), nullable=True)
    npl_ratio = Column(Numeric(10, 4), nullable=True)
    total_npl = Column(Numeric(20, 2), nullable=True)
    avg_credit_score = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ============================================================================
# Audit Log
# ============================================================================
class AuditLogDB(Base):
    __tablename__ = "Audit_Log"

    audit_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("User.user_id"), nullable=True)
    action = Column(String(50), nullable=False)  # INSERT, UPDATE, DELETE
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(BigInteger, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    performed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("UserDB", back_populates="audit_logs")


