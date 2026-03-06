"""
Create Risk Classification Tables in Database
Based on SBV Circular 11/2021/TT-NHNN
"""
import sys
sys.path.insert(0, '../')

from sqlalchemy import text
from app.db.session import engine

def create_risk_tables():
    """Create risk classification tables"""
    
    with engine.connect() as connection:
        try:
            transaction = connection.begin()
            
            print("=" * 80)
            print("CREATING RISK CLASSIFICATION TABLES")
            print("=" * 80)
            print()
            
            # 1. Create Risk_Group table
            print("1. Creating Risk_Group table...")
            
            risk_group_sql = """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Risk_Group')
            BEGIN
                CREATE TABLE [Risk_Group](
                    [group_id] INT PRIMARY KEY,
                    [group_name] NVARCHAR(100) NOT NULL UNIQUE,
                    [group_name_en] NVARCHAR(100) NULL,
                    [description] NVARCHAR(MAX) NULL,
                    [description_vn] NVARCHAR(MAX) NULL,
                    [days_from] INT NOT NULL,
                    [days_to] INT NOT NULL,
                    [risk_level] NVARCHAR(50) NOT NULL,
                    [provision_rate] NUMERIC(5, 2) NOT NULL,
                    [color] NVARCHAR(20) NULL,
                    [icon] NVARCHAR(50) NULL,
                    [created_at] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
                    [updated_at] DATETIME2(7) NULL
                )
            END
            """
            
            connection.execute(text(risk_group_sql))
            print("   ✓ Risk_Group table created")
            
            # Insert risk group data
            print("   Inserting risk groups...")
            
            # Clear existing data first
            connection.execute(text("DELETE FROM [Risk_Group]"))
            
            risk_data_sql = """
            INSERT INTO [Risk_Group] (group_id, group_name, group_name_en, description, description_vn, days_from, days_to, risk_level, provision_rate, color, icon)
            VALUES
                (1, N'Nợ đủ tiêu chuẩn', 'Standard Loans', 
                 'Within due date or overdue less than 10 days', 
                 N'Trong hạn hoặc quá hạn dưới 10 ngày',
                 0, 9, N'Rất thấp', 0.00, 'green', 'check_circle'),
                
                (2, N'Nợ cần chú ý', 'Loans Requiring Attention',
                 'Overdue from 10 to less than 90 days',
                 N'Quá hạn từ 10 ngày đến dưới 90 ngày',
                 10, 89, N'Thấp', 0.01, 'yellow', 'warning'),
                
                (3, N'Nợ dưới tiêu chuẩn', 'Substandard Loans',
                 'Overdue from 91 to 180 days (Beginning of bad debt)',
                 N'Quá hạn từ 91 đến 180 ngày (Bắt đầu là nợ xấu)',
                 91, 180, N'Trung bình cao', 0.25, 'orange', 'info'),
                
                (4, N'Nợ nghi ngờ', 'Doubtful Loans',
                 'Overdue from 181 to 360 days',
                 N'Quá hạn từ 181 đến 360 ngày',
                 181, 360, N'Cao', 0.50, 'red', 'error_outline'),
                
                (5, N'Nợ có khả năng mất vốn', 'Loss Loans',
                 'Overdue over 360 days or unrecoverable',
                 N'Quá hạn trên 360 ngày hoặc mất khả năng thu hồi',
                 361, 999999, N'Rất cao', 1.00, 'dark_red', 'cancel')
            """
            
            connection.execute(text(risk_data_sql))
            print("   ✓ Risk groups inserted (5 groups)")
            print()
            
            # 2. Create Loan_Classification table
            print("2. Creating Loan_Classification table...")
            
            classification_sql = """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Loan_Classification')
            BEGIN
                CREATE TABLE [Loan_Classification](
                    [classification_id] BIGINT IDENTITY(1,1) PRIMARY KEY,
                    [facility_id] BIGINT NOT NULL,
                    [group_id] INT NOT NULL,
                    [days_overdue] INT NOT NULL,
                    [outstanding_principal] NUMERIC(18, 2) NULL,
                    [provision_amount] NUMERIC(18, 2) NULL,
                    [classification_status] NVARCHAR(50) NOT NULL DEFAULT 'active',
                    [classified_by] BIGINT NULL,
                    [classified_at] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
                    [updated_at] DATETIME2(7) NULL,
                    [notes] NVARCHAR(MAX) NULL,
                    CONSTRAINT FK_LoanClassification_Facility FOREIGN KEY (facility_id) REFERENCES [Loan_Facility](facility_id),
                    CONSTRAINT FK_LoanClassification_RiskGroup FOREIGN KEY (group_id) REFERENCES [Risk_Group](group_id),
                    CONSTRAINT FK_LoanClassification_User FOREIGN KEY (classified_by) REFERENCES [User](user_id)
                )
            END
            """
            
            connection.execute(text(classification_sql))
            print("   ✓ Loan_Classification table created")
            print()
            
            # 3. Create Loan_Delinquency table
            print("3. Creating Loan_Delinquency table...")
            
            delinquency_sql = """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Loan_Delinquency')
            BEGIN
                CREATE TABLE [Loan_Delinquency](
                    [delinquency_id] BIGINT IDENTITY(1,1) PRIMARY KEY,
                    [facility_id] BIGINT NOT NULL,
                    [original_due_date] DATETIME2(7) NOT NULL,
                    [last_payment_date] DATETIME2(7) NULL,
                    [current_overdue_days] INT NOT NULL DEFAULT 0,
                    [principal_outstanding] NUMERIC(18, 2) NOT NULL,
                    [interest_outstanding] NUMERIC(18, 2) NOT NULL DEFAULT 0,
                    [penalty_outstanding] NUMERIC(18, 2) NOT NULL DEFAULT 0,
                    [delinquency_status] NVARCHAR(50) NOT NULL DEFAULT 'current',
                    [escalation_level] INT NOT NULL DEFAULT 0,
                    [delinquency_start_date] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
                    [last_action_date] DATETIME2(7) NULL,
                    [expected_resolution_date] DATETIME2(7) NULL,
                    [created_at] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
                    [updated_at] DATETIME2(7) NULL,
                    [notes] NVARCHAR(MAX) NULL,
                    CONSTRAINT FK_LoanDelinquency_Facility FOREIGN KEY (facility_id) REFERENCES [Loan_Facility](facility_id)
                )
            END
            """
            
            connection.execute(text(delinquency_sql))
            print("   ✓ Loan_Delinquency table created")
            print()
            
            # 4. Create Provision_Allocation table
            print("4. Creating Provision_Allocation table...")
            
            provision_sql = """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Provision_Allocation')
            BEGIN
                CREATE TABLE [Provision_Allocation](
                    [provision_id] BIGINT IDENTITY(1,1) PRIMARY KEY,
                    [facility_id] BIGINT NOT NULL,
                    [risk_group_id] INT NOT NULL,
                    [outstanding_amount] NUMERIC(18, 2) NOT NULL,
                    [provision_rate] NUMERIC(5, 2) NOT NULL,
                    [provision_amount] NUMERIC(18, 2) NOT NULL,
                    [allocation_period] NVARCHAR(20) NOT NULL,
                    [allocation_date] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
                    [is_released] INT DEFAULT 0,
                    [release_date] DATETIME2(7) NULL,
                    [allocated_by] BIGINT NULL,
                    [created_at] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
                    [updated_at] DATETIME2(7) NULL,
                    [notes] NVARCHAR(MAX) NULL,
                    CONSTRAINT FK_ProvisionAllocation_Facility FOREIGN KEY (facility_id) REFERENCES [Loan_Facility](facility_id),
                    CONSTRAINT FK_ProvisionAllocation_RiskGroup FOREIGN KEY (risk_group_id) REFERENCES [Risk_Group](group_id),
                    CONSTRAINT FK_ProvisionAllocation_User FOREIGN KEY (allocated_by) REFERENCES [User](user_id)
                )
            END
            """
            
            connection.execute(text(provision_sql))
            print("   ✓ Provision_Allocation table created")
            print()
            
            transaction.commit()
            
            # Display summary
            print("=" * 80)
            print("RISK GROUPS SUMMARY")
            print("=" * 80)
            print()
            
            summary_query = text("""
                SELECT 
                    [group_id],
                    [group_name],
                    [group_name_en],
                    [days_from],
                    [days_to],
                    [risk_level],
                    CAST([provision_rate] AS VARCHAR(5)) + '%' AS [provision_rate]
                FROM [Risk_Group]
                ORDER BY [group_id]
            """)
            
            result = connection.execute(summary_query)
            groups = result.fetchall()
            
            print(f"{'ID':<4} {'Group Name':<30} {'Days Range':<15} {'Risk Level':<15} {'Provision':<10}")
            print("-" * 74)
            
            for group in groups:
                group_id = group[0]
                group_name = group[1]
                group_name_en = group[2]
                days_from = group[3]
                days_to = group[4]
                risk_level = group[5]
                provision_rate = group[6]
                
                days_range = f"{days_from}-{days_to}" if days_to < 999999 else f"{days_from}+"
                print(f"{group_id:<4} {group_name:<30} {days_range:<15} {risk_level:<15} {provision_rate:<10}")
            
            print()
            print("=" * 80)
            print("✓ All risk classification tables created successfully!")
            print("=" * 80)
            
        except Exception as e:
            transaction.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    create_risk_tables()
