-- ============================================================================
-- CREDIT RISK DATABASE - SCHEMA ENHANCEMENTS
-- ============================================================================
-- Mục đích: Thêm tables và columns để support:
-- 1. Loan Classification (GROUP 1-4)
-- 2. Time-series Transaction tracking
-- 3. Delinquency Snapshots
-- 4. Migration Tracking
-- ============================================================================

USE CreditRiskDB;
GO

-- ============================================================================
-- 1. UPDATE Loan_Facility - Add Classification Columns
-- ============================================================================

ALTER TABLE [dbo].[Loan_Facility] ADD (
    risk_group VARCHAR(20) DEFAULT 'GROUP_1',
    last_classified_at DATETIME2 DEFAULT SYSUTCDATETIME(),
    classification_reason VARCHAR(500),
    on_time_payment_rate DECIMAL(5,2) DEFAULT 100.0,
    violation_count INT DEFAULT 0
);

CREATE INDEX IX_Loan_Facility_RiskGroup ON [dbo].[Loan_Facility](risk_group, status);
GO

-- ============================================================================
-- 2. NEW TABLE - Transaction_Log (Time-Series Tracking)
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Transaction_Log')
BEGIN
    CREATE TABLE [dbo].[Transaction_Log] (
        transaction_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        facility_id BIGINT NOT NULL,
        transaction_type VARCHAR(50) NOT NULL,  -- 'payment', 'interest_accrual', 'fee', 'charge_off'
        amount DECIMAL(18,2) NOT NULL,
        transaction_date DATETIME2 NOT NULL,
        description VARCHAR(500),
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT FK_Transaction_Facility FOREIGN KEY (facility_id) 
            REFERENCES [dbo].[Loan_Facility](facility_id) ON DELETE CASCADE
    );
    
    CREATE INDEX IX_Transaction_Facility_Date ON [dbo].[Transaction_Log](facility_id, transaction_date DESC);
    CREATE INDEX IX_Transaction_Type ON [dbo].[Transaction_Log](transaction_type);
END
GO

-- ============================================================================
-- 3. NEW TABLE - Monthly_Delinquency (Snapshot per Month)
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Monthly_Delinquency')
BEGIN
    CREATE TABLE [dbo].[Monthly_Delinquency] (
        snapshot_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        facility_id BIGINT NOT NULL,
        snapshot_month DATE NOT NULL,  -- First day of month (e.g., 2026-01-01)
        
        -- Status
        days_past_due INT NOT NULL,
        risk_group VARCHAR(20),  -- GROUP_1, 2, 3, 4
        
        -- Amounts
        principal_overdue DECIMAL(18,2),
        interest_overdue DECIMAL(18,2),
        total_overdue DECIMAL(18,2),
        
        -- Metrics
        on_time_payment_rate DECIMAL(5,2),  -- 0-100
        violation_count INT,
        
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT FK_Monthly_Delinquency_Facility FOREIGN KEY (facility_id) 
            REFERENCES [dbo].[Loan_Facility](facility_id) ON DELETE CASCADE,
        
        CONSTRAINT UQ_Monthly_Delinquency_Facility_Month UNIQUE (facility_id, snapshot_month)
    );
    
    CREATE INDEX IX_Monthly_Delinquency_Month ON [dbo].[Monthly_Delinquency](snapshot_month DESC);
    CREATE INDEX IX_Monthly_Delinquency_RiskGroup ON [dbo].[Monthly_Delinquency](risk_group);
END
GO

-- ============================================================================
-- 4. NEW TABLE - Loan_Status_Migration (Track Group Changes)
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Loan_Status_Migration')
BEGIN
    CREATE TABLE [dbo].[Loan_Status_Migration] (
        migration_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        facility_id BIGINT NOT NULL,
        from_group VARCHAR(20),  -- GROUP_1, 2, 3, 4, NULL
        to_group VARCHAR(20) NOT NULL,
        migration_date DATETIME2 NOT NULL,
        reason VARCHAR(500),
        
        CONSTRAINT FK_Migration_Facility FOREIGN KEY (facility_id) 
            REFERENCES [dbo].[Loan_Facility](facility_id) ON DELETE CASCADE
    );
    
    CREATE INDEX IX_Migration_Facility_Date ON [dbo].[Loan_Status_Migration](facility_id, migration_date DESC);
    CREATE INDEX IX_Migration_Groups ON [dbo].[Loan_Status_Migration](from_group, to_group);
END
GO

-- ============================================================================
-- 5. NEW TABLE - Portfolio_Risk_Summary (Daily/Weekly Aggregation)
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Portfolio_Risk_Summary')
BEGIN
    CREATE TABLE [dbo].[Portfolio_Risk_Summary] (
        summary_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        summary_date DATE NOT NULL,
        
        -- Loan Counts
        total_facilities INT,
        group_1_count INT,
        group_2_count INT,
        group_3_count INT,
        group_4_count INT,
        
        -- Amounts
        total_outstanding DECIMAL(20,2),
        group_3_4_outstanding DECIMAL(20,2),
        
        -- Metrics
        npl_ratio DECIMAL(5,2),  -- Non-Performing Loan ratio %
        par_30 DECIMAL(5,2),     -- Principal at Risk > 30 days
        par_90 DECIMAL(5,2),     -- Principal at Risk > 90 days
        on_time_payment_rate DECIMAL(5,2),
        
        -- Migration
        migrated_to_group_2 INT,
        migrated_to_group_3 INT,
        migrated_to_group_4 INT,
        
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT UQ_Summary_Date UNIQUE (summary_date)
    );
    
    CREATE INDEX IX_Portfolio_Summary_Date ON [dbo].[Portfolio_Risk_Summary](summary_date DESC);
END
GO

-- ============================================================================
-- 6. NEW TABLE - Customer_Payment_Statistics (Summary per Customer)
-- ============================================================================

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Customer_Payment_Statistics')
BEGIN
    CREATE TABLE [dbo].[Customer_Payment_Statistics] (
        stat_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        customer_id BIGINT NOT NULL,
        
        -- Statistics
        total_facilities INT,
        total_outstanding DECIMAL(20,2),
        average_on_time_rate DECIMAL(5,2),
        total_violations INT,
        highest_risk_group VARCHAR(20),
        
        -- Trend
        facilities_upgraded_last_month INT,  -- Moved to lower group
        facilities_downgraded_last_month INT,  -- Moved to higher group
        
        updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT FK_CustStats_Customer FOREIGN KEY (customer_id) 
            REFERENCES [dbo].[Customer](customer_id) ON DELETE CASCADE,
        
        CONSTRAINT UQ_Customer_Payment_Statistics UNIQUE (customer_id)
    );
    
    CREATE INDEX IX_CustStats_HighestRisk ON [dbo].[Customer_Payment_Statistics](highest_risk_group);
END
GO

-- ============================================================================
-- 7. VIEWS - For Easy Querying
-- ============================================================================

-- View: Current Facility Status
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME = 'v_Facility_Current_Status')
    DROP VIEW [dbo].[v_Facility_Current_Status];
GO

CREATE VIEW [dbo].[v_Facility_Current_Status] AS
SELECT 
    f.facility_id,
    f.customer_id,
    c.full_name,
    f.facility_type,
    f.approved_amount,
    f.status,
    f.risk_group,
    f.on_time_payment_rate,
    f.violation_count,
    f.last_classified_at,
    ld.days_past_due,
    ld.overdue_amount,
    ld.risk_bucket
FROM [dbo].[Loan_Facility] f
INNER JOIN [dbo].[Customer] c ON f.customer_id = c.customer_id
LEFT JOIN [dbo].[Loan_Delinquency] ld ON f.facility_id = ld.facility_id
    AND ld.delinquency_id = (
        SELECT MAX(delinquency_id) 
        FROM [dbo].[Loan_Delinquency] 
        WHERE facility_id = f.facility_id
    );
GO

-- View: NPL Analysis
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME = 'v_NPL_Analysis')
    DROP VIEW [dbo].[v_NPL_Analysis];
GO

CREATE VIEW [dbo].[v_NPL_Analysis] AS
SELECT 
    COUNT(*) AS total_facilities,
    SUM(CASE WHEN risk_group = 'GROUP_1' THEN 1 ELSE 0 END) AS group_1_count,
    SUM(CASE WHEN risk_group = 'GROUP_2' THEN 1 ELSE 0 END) AS group_2_count,
    SUM(CASE WHEN risk_group = 'GROUP_3' THEN 1 ELSE 0 END) AS group_3_count,
    SUM(CASE WHEN risk_group = 'GROUP_4' THEN 1 ELSE 0 END) AS group_4_count,
    SUM(approved_amount) AS total_outstanding,
    SUM(CASE WHEN risk_group IN ('GROUP_3', 'GROUP_4') THEN approved_amount ELSE 0 END) AS npl_amount,
    ROUND(
        100.0 * SUM(CASE WHEN risk_group IN ('GROUP_3', 'GROUP_4') THEN approved_amount ELSE 0 END) 
        / SUM(approved_amount), 2
    ) AS npl_ratio_pct
FROM [dbo].[Loan_Facility]
WHERE status = 'active';
GO

-- ============================================================================
-- 8. STORED PROCEDURES - For Classification Logic
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_NAME = 'sp_Classify_Loan')
    DROP PROCEDURE [dbo].[sp_Classify_Loan];
GO

CREATE PROCEDURE [dbo].[sp_Classify_Loan]
    @facility_id BIGINT
AS
BEGIN
    DECLARE @days_past_due INT;
    @violation_count INT;
    @on_time_rate DECIMAL(5,2);
    @new_group VARCHAR(20);
    @old_group VARCHAR(20);
    
    -- Get latest delinquency info
    SELECT TOP 1 
        @days_past_due = days_past_due
    FROM [dbo].[Loan_Delinquency]
    WHERE facility_id = @facility_id
    ORDER BY as_of_date DESC;
    
    SET @days_past_due = ISNULL(@days_past_due, 0);
    
    -- Get violation count (last 6 months)
    SELECT @violation_count = COUNT(*)
    FROM [dbo].[Loan_Status_Migration]
    WHERE facility_id = @facility_id
        AND migration_date >= DATEADD(MONTH, -6, GETDATE());
    
    SET @violation_count = ISNULL(@violation_count, 0);
    
    -- Get on-time payment rate
    -- TODO: Implement actual calculation
    SET @on_time_rate = 100.0;
    
    -- Classification logic
    IF @days_past_due <= 0 AND @on_time_rate >= 90
        SET @new_group = 'GROUP_1'
    ELSE IF @days_past_due BETWEEN 1 AND 30
        SET @new_group = 'GROUP_2'
    ELSE IF @days_past_due BETWEEN 31 AND 90
        SET @new_group = 'GROUP_3'
    ELSE
        SET @new_group = 'GROUP_4';
    
    -- Get current group
    SELECT @old_group = risk_group
    FROM [dbo].[Loan_Facility]
    WHERE facility_id = @facility_id;
    
    -- Update facility if group changed
    IF @old_group <> @new_group
    BEGIN
        UPDATE [dbo].[Loan_Facility]
        SET 
            risk_group = @new_group,
            last_classified_at = GETDATE(),
            on_time_payment_rate = @on_time_rate,
            violation_count = @violation_count
        WHERE facility_id = @facility_id;
        
        -- Record migration
        INSERT INTO [dbo].[Loan_Status_Migration] 
            (facility_id, from_group, to_group, migration_date, reason)
        VALUES 
            (@facility_id, @old_group, @new_group, GETDATE(), 
             'Auto-classification: DPD=' + CAST(@days_past_due AS VARCHAR));
    END
    ELSE
    BEGIN
        UPDATE [dbo].[Loan_Facility]
        SET 
            last_classified_at = GETDATE(),
            on_time_payment_rate = @on_time_rate,
            violation_count = @violation_count
        WHERE facility_id = @facility_id;
    END
END
GO

-- ============================================================================
-- 9. CREATE INDEXES for Performance
-- ============================================================================

CREATE INDEX IX_Loan_Facility_Customer ON [dbo].[Loan_Facility](customer_id, status);
CREATE INDEX IX_Loan_Payment_Facility_Date ON [dbo].[Loan_Payment](facility_id, payment_date DESC);
CREATE INDEX IX_Loan_Delinquency_Facility_Date ON [dbo].[Loan_Delinquency](facility_id, as_of_date DESC);

GO

PRINT '✓ Database schema updated successfully!';
PRINT 'New tables: Transaction_Log, Monthly_Delinquency, Loan_Status_Migration, Portfolio_Risk_Summary, Customer_Payment_Statistics';
PRINT 'New columns in Loan_Facility: risk_group, classification_reason, on_time_payment_rate, violation_count';
PRINT 'New views: v_Facility_Current_Status, v_NPL_Analysis';
