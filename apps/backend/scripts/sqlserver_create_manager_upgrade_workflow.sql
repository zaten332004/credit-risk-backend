-- Create tables for analyst -> manager upgrade workflow
-- Safe to run multiple times.

IF OBJECT_ID('dbo.Manager_Upgrade_Request', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Manager_Upgrade_Request (
        request_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        target_user_id BIGINT NOT NULL,
        purpose NVARCHAR(1000) NOT NULL,
        status NVARCHAR(20) NOT NULL DEFAULT 'pending',
        requested_by_role NVARCHAR(20) NOT NULL DEFAULT 'analyst',
        nominated_by BIGINT NULL,
        approved_by BIGINT NULL,
        approved_at DATETIME2 NULL,
        rejection_reason NVARCHAR(1000) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL,
        CONSTRAINT FK_ManagerUpgradeRequest_TargetUser FOREIGN KEY (target_user_id) REFERENCES dbo.[User](user_id),
        CONSTRAINT FK_ManagerUpgradeRequest_Nominator FOREIGN KEY (nominated_by) REFERENCES dbo.[User](user_id),
        CONSTRAINT FK_ManagerUpgradeRequest_Approver FOREIGN KEY (approved_by) REFERENCES dbo.[User](user_id)
    );
END;
GO

IF OBJECT_ID('dbo.Manager_Upgrade_Vote', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Manager_Upgrade_Vote (
        vote_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        request_id BIGINT NOT NULL,
        manager_user_id BIGINT NOT NULL,
        vote NVARCHAR(20) NOT NULL,
        note NVARCHAR(1000) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_ManagerUpgradeVote_Request FOREIGN KEY (request_id) REFERENCES dbo.Manager_Upgrade_Request(request_id),
        CONSTRAINT FK_ManagerUpgradeVote_Manager FOREIGN KEY (manager_user_id) REFERENCES dbo.[User](user_id),
        CONSTRAINT UQ_ManagerUpgradeVote_Request_Manager UNIQUE (request_id, manager_user_id)
    );
END;
GO
