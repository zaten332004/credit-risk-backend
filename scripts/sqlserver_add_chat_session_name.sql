IF COL_LENGTH('dbo.Chat_Session', 'session_name') IS NULL
BEGIN
  ALTER TABLE dbo.Chat_Session
  ADD session_name NVARCHAR(255) NULL;
END;
