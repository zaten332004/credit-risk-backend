-- ============================================================================
-- ALTER TABLE USER - ADD MISSING COLUMNS FOR REGISTRATION WORKFLOW
-- ============================================================================
-- Database: CreditRiskDB
-- Add columns needed for user registration, email verification, and admin approval

USE CreditRiskDB;
GO

PRINT '========================================';
PRINT 'ADDING MISSING COLUMNS TO USER TABLE';
PRINT '========================================';
PRINT '';

-- Check current columns
PRINT 'Current columns in [User] table:';
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'User'
ORDER BY ORDINAL_POSITION;

PRINT '';
PRINT '========================================';
PRINT 'Adding new columns...';
PRINT '========================================';
PRINT '';

-- Add phone column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'phone')
BEGIN
    ALTER TABLE [User] ADD phone NVARCHAR(20) NULL;
    PRINT '✓ Added column: phone';
END
ELSE
BEGIN
    PRINT '⚠️  Column phone already exists';
END

-- Add full_name column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'full_name')
BEGIN
    ALTER TABLE [User] ADD full_name NVARCHAR(100) NULL;
    PRINT '✓ Added column: full_name';
END
ELSE
BEGIN
    PRINT '⚠️  Column full_name already exists';
END

-- Add user_type column (analyst, manager)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'user_type')
BEGIN
    ALTER TABLE [User] ADD user_type NVARCHAR(20) NULL;
    PRINT '✓ Added column: user_type';
END
ELSE
BEGIN
    PRINT '⚠️  Column user_type already exists';
END

-- Add status column (pending, approved, rejected, verified)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'status')
BEGIN
    ALTER TABLE [User] ADD status NVARCHAR(20) NULL DEFAULT 'pending';
    PRINT '✓ Added column: status';
END
ELSE
BEGIN
    PRINT '⚠️  Column status already exists';
END

-- Add verification_token column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'verification_token')
BEGIN
    ALTER TABLE [User] ADD verification_token NVARCHAR(255) NULL;
    PRINT '✓ Added column: verification_token';
END
ELSE
BEGIN
    PRINT '⚠️  Column verification_token already exists';
END

-- Add verification_sent_at column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'verification_sent_at')
BEGIN
    ALTER TABLE [User] ADD verification_sent_at DATETIME2(7) NULL;
    PRINT '✓ Added column: verification_sent_at';
END
ELSE
BEGIN
    PRINT '⚠️  Column verification_sent_at already exists';
END

-- Add is_email_verified column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'is_email_verified')
BEGIN
    ALTER TABLE [User] ADD is_email_verified BIT DEFAULT 0;
    PRINT '✓ Added column: is_email_verified';
END
ELSE
BEGIN
    PRINT '⚠️  Column is_email_verified already exists';
END

-- Add approved_by column (user_id of admin who approved)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'approved_by')
BEGIN
    ALTER TABLE [User] ADD approved_by BIGINT NULL;
    PRINT '✓ Added column: approved_by';
END
ELSE
BEGIN
    PRINT '⚠️  Column approved_by already exists';
END

-- Add approved_at column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'approved_at')
BEGIN
    ALTER TABLE [User] ADD approved_at DATETIME2(7) NULL;
    PRINT '✓ Added column: approved_at';
END
ELSE
BEGIN
    PRINT '⚠️  Column approved_at already exists';
END

-- Add rejection_reason column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'rejection_reason')
BEGIN
    ALTER TABLE [User] ADD rejection_reason NVARCHAR(500) NULL;
    PRINT '✓ Added column: rejection_reason';
END
ELSE
BEGIN
    PRINT '⚠️  Column rejection_reason already exists';
END

-- Add updated_at column
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'updated_at')
BEGIN
    ALTER TABLE [User] ADD updated_at DATETIME2(7) NULL;
    PRINT '✓ Added column: updated_at';
END
ELSE
BEGIN
    PRINT '⚠️  Column updated_at already exists';
END

PRINT '';
PRINT '========================================';
PRINT 'FINAL USER TABLE STRUCTURE:';
PRINT '========================================';
PRINT '';

SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'User'
ORDER BY ORDINAL_POSITION;

PRINT '';
PRINT '========================================';
PRINT 'Column addition complete!';
PRINT '========================================';
