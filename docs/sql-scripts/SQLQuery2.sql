CREATE INDEX IX_Customer_Email ON [dbo].[User](email);
CREATE INDEX IX_Loan_Application_Status ON [dbo].[Loan_Application](loan_status);
CREATE INDEX IX_Loan_Facility_Status ON [dbo].[Loan_Facility](status);
CREATE INDEX IX_Alert_Resolved ON [dbo].[Alert](is_resolved, created_at);
CREATE INDEX IX_Delinquency_AsOfDate ON [dbo].[Loan_Delinquency](as_of_date);


-- Kiểm tra các constraint của bảng User
SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_NAME = 'User';

-- Xem tất cả cột và constraint
EXEC sp_columns 'User';

USE CreditRiskDB;
GO

-- Xóa constraint FK_User_Role nếu tồn tại
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS 
           WHERE CONSTRAINT_NAME = 'FK_User_Role')
    ALTER TABLE [dbo].[User] DROP CONSTRAINT FK_User_Role;
GO

-- Nếu bảng Role không tồn tại, tạo nó
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Role')
BEGIN
    CREATE TABLE [dbo].[Role] (
        role_id INT PRIMARY KEY,
        role_name NVARCHAR(50) NOT NULL UNIQUE,
        description NVARCHAR(500)
    );
    
    -- Insert default roles
    INSERT INTO [dbo].[Role] VALUES 
        (1, 'Admin', 'System Administrator'),
        (2, 'Manager', 'Risk Manager'),
        (3, 'Analyst', 'Credit Analyst'),
        (4, 'Viewer', 'Read-only access');
END
GO

-- Thêm foreign key constraint
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS 
               WHERE CONSTRAINT_NAME = 'FK_User_Role')
    ALTER TABLE [dbo].[User] 
    ADD CONSTRAINT FK_User_Role 
    FOREIGN KEY (role_id) REFERENCES [dbo].[Role](role_id);
GO

USE CreditRiskDB;
GO

-- Xóa default constraint cũ (nếu có)
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE 
           WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'created_at')
BEGIN
    DECLARE @ConstraintName NVARCHAR(200);
    SELECT @ConstraintName = CONSTRAINT_NAME 
    FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE 
    WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'created_at';
    EXEC ('ALTER TABLE [dbo].[User] DROP CONSTRAINT ' + @ConstraintName);
END
GO

-- Thêm default constraint mới
ALTER TABLE [dbo].[User] 
ADD CONSTRAINT DF_User_CreatedAt DEFAULT SYSUTCDATETIME() FOR created_at;
GO

-- Tương tự cho Customer
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE 
           WHERE TABLE_NAME = 'Customer' AND COLUMN_NAME = 'created_at')
BEGIN
    DECLARE @ConstraintName NVARCHAR(200);
    SELECT @ConstraintName = CONSTRAINT_NAME 
    FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE 
    WHERE TABLE_NAME = 'Customer' AND COLUMN_NAME = 'created_at';
    EXEC ('ALTER TABLE [dbo].[Customer] DROP CONSTRAINT ' + @ConstraintName);
END
GO

ALTER TABLE [dbo].[Customer] 
ADD CONSTRAINT DF_Customer_CreatedAt DEFAULT SYSUTCDATETIME() FOR created_at;
GO

-- Nên thêm unique index:
CREATE UNIQUE INDEX IX_Financial_Customer_Latest ON [dbo].[FINANCIAL_INDICATOR](customer_id, updated_at DESC);


CREATE TABLE [dbo].[Chat_Session] (
    session_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    user_id BIGINT NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    last_interaction DATETIME2 NULL,
    
    CONSTRAINT FK_Session_User FOREIGN KEY (user_id) REFERENCES [dbo].[User](user_id)
);
GO

-- Update bảng Chat_History:
ALTER TABLE [dbo].[Chat_History] ADD session_id UNIQUEIDENTIFIER NULL;
ALTER TABLE [dbo].[Chat_History] ADD CONSTRAINT FK_Chat_Session 
    FOREIGN KEY (session_id) REFERENCES [dbo].[Chat_Session](session_id);

    -- customer_id + application_id có thể dư. Nên giữ một:
-- Application → Customer, nên có thể loại bỏ customer_id:
ALTER TABLE [dbo].[RISK_PREDICTION] DROP COLUMN customer_id;
-- Hoặc nếu cần prediction không liên kết với application, giữ customer_id


CREATE TABLE [dbo].[Alert_Subscription] (
    subscription_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    alert_type NVARCHAR(50) NOT NULL,
    alert_severity NVARCHAR(20) NOT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Subscription_User FOREIGN KEY (user_id) REFERENCES [dbo].[User](user_id)
);
GO

-- Thêm cascade delete policy:
ALTER TABLE [dbo].[Customer_Employment] 
    ADD CONSTRAINT FK_Employment_Customer_Cascade 
    FOREIGN KEY (customer_id) REFERENCES [dbo].[Customer](customer_id) 
    ON DELETE CASCADE;

    ALTER TABLE [dbo].[LINEAR_MODEL] ADD version_tag NVARCHAR(50);
ALTER TABLE [dbo].[LINEAR_MODEL] ADD is_active BIT DEFAULT 1;
-- Loại bỏ bảng Model_Version