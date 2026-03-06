-- Fix Vietnamese/Unicode being stored as "????" in chat history.
-- Root cause: SQL Server columns using non-Unicode types (VARCHAR/TEXT) instead of NVARCHAR.
--
-- Run this against your SQL Server database (adjust schema if not dbo).

-- 1) Inspect current column types
SELECT
  TABLE_SCHEMA,
  TABLE_NAME,
  COLUMN_NAME,
  DATA_TYPE,
  CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Chat_History'
  AND COLUMN_NAME IN ('message', 'bot_response');

-- 2) Convert to Unicode-capable types
-- NOTE: This changes schema only; already-saved "????" rows cannot be recovered.
ALTER TABLE dbo.Chat_History ALTER COLUMN message NVARCHAR(MAX) NOT NULL;
ALTER TABLE dbo.Chat_History ALTER COLUMN bot_response NVARCHAR(MAX) NULL;

