-- Create optional pinned sessions table.
-- This avoids breaking existing deployments because Chat_Session schema is unchanged.
-- Adjust schema if not dbo.

IF OBJECT_ID('dbo.Chat_Session_Pin', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Chat_Session_Pin (
    session_id UNIQUEIDENTIFIER NOT NULL,
    user_id BIGINT NOT NULL,
    pinned_at DATETIME2(7) NOT NULL CONSTRAINT DF_Chat_Session_Pin_pinned_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Chat_Session_Pin PRIMARY KEY (session_id),
    CONSTRAINT FK_Chat_Session_Pin_Session FOREIGN KEY (session_id) REFERENCES dbo.Chat_Session(session_id),
    CONSTRAINT FK_Chat_Session_Pin_User FOREIGN KEY (user_id) REFERENCES dbo.[User](user_id)
  );
END

