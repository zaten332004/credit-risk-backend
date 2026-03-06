"""
Script để tạo tất cả tables trong database từ SQLAlchemy models.
Chạy lệnh: python -m app.db.init_db
"""

from app.db.session import Base, engine
from app.db.models import (
    CustomerDB,
    LoanDB,
    RiskScoreDB,
    UserDB,
    AlertDB,
    UserRegistrationDB,
    RoleDB,
    LoanApplicationDB,
    LoanFacilityDB,
    LoanRepaymentScheduleDB,
    LoanPaymentDB,
    LoanDelinquencyDB,
    FinancialIndicatorDB,
    LinearModelDB,
    RegressionCoefficientDB,
    RiskPredictionDB,
    SHAPExplanationDB,
    ChatSessionDB,
    ChatHistoryDB,
    AuditLogDB,
    PortfolioSnapshotDB,
    AlertSubscriptionDB,
)


def init_db():
    """
    Tạo tất cả tables dựa trên SQLAlchemy models.
    Lưu ý: Chỉ tạo tables, KHÔNG tạo database instance.
    Database 'CreditRiskDB' phải được tạo trước trong SQL Server.
    """
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")


if __name__ == "__main__":
    init_db()
