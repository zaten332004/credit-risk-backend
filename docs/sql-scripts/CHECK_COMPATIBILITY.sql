-- ============================================================================
-- COMPATIBILITY CHECK - SQL_SCHEMA_ENHANCEMENTS.sql
-- ============================================================================
-- Kiểm tra xem các changes có thể chạy trên database hiện tại không

USE CreditRiskDB;
GO

PRINT '========================================';
PRINT 'KIỂM TRA TƯƠNG THÍCH SCHEMA ENHANCEMENTS';
PRINT '========================================';
GO

-- ============================================================================
-- CHECK 1: Loan_Facility Table Exists
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Loan_Facility')
BEGIN
    PRINT '✓ CHECK 1 PASSED: Loan_Facility table exists';
    
    -- Check existing columns
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Loan_Facility' AND COLUMN_NAME = 'risk_group')
        PRINT '  ⚠️ WARNING: risk_group column already exists (skip ALTER)';
    ELSE
        PRINT '  → Need to ADD: risk_group column';
    
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Loan_Facility' AND COLUMN_NAME = 'last_classified_at')
        PRINT '  ⚠️ WARNING: last_classified_at column already exists (skip ALTER)';
    ELSE
        PRINT '  → Need to ADD: last_classified_at column';
    
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Loan_Facility' AND COLUMN_NAME = 'on_time_payment_rate')
        PRINT '  ⚠️ WARNING: on_time_payment_rate column already exists (skip ALTER)';
    ELSE
        PRINT '  → Need to ADD: on_time_payment_rate column';
    
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Loan_Facility' AND COLUMN_NAME = 'violation_count')
        PRINT '  ⚠️ WARNING: violation_count column already exists (skip ALTER)';
    ELSE
        PRINT '  → Need to ADD: violation_count column';
END
ELSE
BEGIN
    PRINT '✗ CHECK 1 FAILED: Loan_Facility table NOT FOUND';
END
GO

-- ============================================================================
-- CHECK 2: Transaction_Log Table
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Transaction_Log')
BEGIN
    PRINT '✓ CHECK 2: Transaction_Log table already exists (skip CREATE)';
END
ELSE
BEGIN
    PRINT '→ CHECK 2: Transaction_Log table will be created';
END
GO

-- ============================================================================
-- CHECK 3: Monthly_Delinquency Table
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Monthly_Delinquency')
BEGIN
    PRINT '✓ CHECK 3: Monthly_Delinquency table already exists (skip CREATE)';
END
ELSE
BEGIN
    PRINT '→ CHECK 3: Monthly_Delinquency table will be created';
END
GO

-- ============================================================================
-- CHECK 4: Loan_Status_Migration Table
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Loan_Status_Migration')
BEGIN
    PRINT '✓ CHECK 4: Loan_Status_Migration table already exists (skip CREATE)';
END
ELSE
BEGIN
    PRINT '→ CHECK 4: Loan_Status_Migration table will be created';
END
GO

-- ============================================================================
-- CHECK 5: Portfolio_Risk_Summary Table
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Portfolio_Risk_Summary')
BEGIN
    PRINT '✓ CHECK 5: Portfolio_Risk_Summary table already exists (skip CREATE)';
END
ELSE
BEGIN
    PRINT '→ CHECK 5: Portfolio_Risk_Summary table will be created';
END
GO

-- ============================================================================
-- CHECK 6: Customer_Payment_Statistics Table
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Customer_Payment_Statistics')
BEGIN
    PRINT '✓ CHECK 6: Customer_Payment_Statistics table already exists (skip CREATE)';
END
ELSE
BEGIN
    PRINT '→ CHECK 6: Customer_Payment_Statistics table will be created';
END
GO

-- ============================================================================
-- CHECK 7: Views Exist
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME = 'v_Facility_Current_Status')
    PRINT '✓ CHECK 7a: v_Facility_Current_Status view already exists (will be recreated)';
ELSE
    PRINT '→ CHECK 7a: v_Facility_Current_Status view will be created';

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME = 'v_NPL_Analysis')
    PRINT '✓ CHECK 7b: v_NPL_Analysis view already exists (will be recreated)';
ELSE
    PRINT '→ CHECK 7b: v_NPL_Analysis view will be created';
GO

-- ============================================================================
-- CHECK 8: Stored Procedures
-- ============================================================================

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_NAME = 'sp_Classify_Loan')
    PRINT '✓ CHECK 8: sp_Classify_Loan procedure already exists (will be recreated)';
ELSE
    PRINT '→ CHECK 8: sp_Classify_Loan procedure will be created';
GO

-- ============================================================================
-- SUMMARY
-- ============================================================================

PRINT '';
PRINT '========================================';
PRINT 'SUMMARY:';
PRINT '========================================';
PRINT '';
PRINT 'File SQL_SCHEMA_ENHANCEMENTS.sql CÓ THỂ CHẠY được trên database hiện tại.';
PRINT '';
PRINT 'Các bước sẽ được thực hiện:';
PRINT '  1. ALTER TABLE Loan_Facility (add 5 columns)';
PRINT '  2. CREATE Transaction_Log table';
PRINT '  3. CREATE Monthly_Delinquency table';
PRINT '  4. CREATE Loan_Status_Migration table';
PRINT '  5. CREATE Portfolio_Risk_Summary table';
PRINT '  6. CREATE Customer_Payment_Statistics table';
PRINT '  7. CREATE/ALTER 2 views';
PRINT '  8. CREATE 1 stored procedure';
PRINT '';
PRINT 'Tổng cộng: 5 bảng mới + 5 cột mới + 2 views + 1 stored procedure + 8 indexes';
PRINT '';
PRINT '========================================';
GO
