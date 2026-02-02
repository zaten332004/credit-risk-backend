-- ============================================================================
-- CREATE RISK CLASSIFICATION TABLES - SBV Circular 11/2021/TT-NHNN
-- ============================================================================
-- Based on SBV regulations for loan risk classification
-- Database: CreditRiskDB

USE CreditRiskDB;
GO

PRINT '========================================';
PRINT 'CREATING RISK CLASSIFICATION TABLES';
PRINT '========================================';
PRINT '';

-- ============================================================================
-- 1. RISK_GROUP Table
-- ============================================================================
PRINT 'Creating Risk_Group table...';

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
GO

-- Insert risk group data
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
GO

PRINT '✓ Risk_Group table created and populated';
PRINT '';

-- ============================================================================
-- 2. LOAN_CLASSIFICATION Table
-- ============================================================================
PRINT 'Creating Loan_Classification table...';

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
GO

CREATE NONCLUSTERED INDEX [IX_LoanClassification_Facility] ON [Loan_Classification]([facility_id] ASC)
GO

CREATE NONCLUSTERED INDEX [IX_LoanClassification_Group] ON [Loan_Classification]([group_id] ASC)
GO

PRINT '✓ Loan_Classification table created';
PRINT '';

-- ============================================================================
-- 3. LOAN_DELINQUENCY Table
-- ============================================================================
PRINT 'Creating Loan_Delinquency table...';

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
GO

CREATE NONCLUSTERED INDEX [IX_LoanDelinquency_Facility] ON [Loan_Delinquency]([facility_id] ASC)
GO

CREATE NONCLUSTERED INDEX [IX_LoanDelinquency_Status] ON [Loan_Delinquency]([delinquency_status] ASC)
GO

PRINT '✓ Loan_Delinquency table created';
PRINT '';

-- ============================================================================
-- 4. PROVISION_ALLOCATION Table
-- ============================================================================
PRINT 'Creating Provision_Allocation table...';

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
GO

CREATE NONCLUSTERED INDEX [IX_ProvisionAllocation_Facility] ON [Provision_Allocation]([facility_id] ASC)
GO

CREATE NONCLUSTERED INDEX [IX_ProvisionAllocation_Period] ON [Provision_Allocation]([allocation_period] ASC)
GO

PRINT '✓ Provision_Allocation table created';
PRINT '';

-- ============================================================================
-- DISPLAY SUMMARY
-- ============================================================================
PRINT '========================================';
PRINT 'TABLES CREATED SUCCESSFULLY:';
PRINT '========================================';
PRINT '';
PRINT '✓ Risk_Group (5 risk groups)';
PRINT '✓ Loan_Classification';
PRINT '✓ Loan_Delinquency';
PRINT '✓ Provision_Allocation';
PRINT '';

PRINT 'Risk Groups Summary:';
SELECT 
    [group_id] AS [ID],
    [group_name] AS [Group Name],
    [group_name_en] AS [English Name],
    [days_from] AS [Days From],
    [days_to] AS [Days To],
    [risk_level] AS [Risk Level],
    CONCAT(CONVERT(VARCHAR(5), [provision_rate]), '%') AS [Provision Rate]
FROM [Risk_Group]
ORDER BY [group_id]
GO

PRINT '';
PRINT '========================================';
