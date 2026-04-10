-- Migration script: Add cache columns to Chat_Session table for AI chat optimization
-- Run this script to support the new caching feature

-- Check if columns exist before adding
IF NOT EXISTS (
    SELECT 1 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'Chat_Session' AND COLUMN_NAME = 'data_context_cached'
)
BEGIN
    ALTER TABLE Chat_Session
    ADD data_context_cached NVARCHAR(MAX) NULL;
    
    PRINT 'Column data_context_cached added successfully';
END
ELSE
BEGIN
    PRINT 'Column data_context_cached already exists';
END

IF NOT EXISTS (
    SELECT 1 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'Chat_Session' AND COLUMN_NAME = 'data_context_cached_at'
)
BEGIN
    ALTER TABLE Chat_Session
    ADD data_context_cached_at DATETIME NULL;
    
    PRINT 'Column data_context_cached_at added successfully';
END
ELSE
BEGIN
    PRINT 'Column data_context_cached_at already exists';
END

-- Verify migration
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Chat_Session'
ORDER BY ORDINAL_POSITION;

PRINT 'Migration completed successfully';
