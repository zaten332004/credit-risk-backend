USE CreditRiskDB;
GO

-- Xóa default constraint cũ trên User.created_at
DECLARE @ConstraintName NVARCHAR(200);
SELECT @ConstraintName = CONSTRAINT_NAME 
FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE 
WHERE TABLE_NAME = 'User' AND COLUMN_NAME = 'created_at' 
  AND CONSTRAINT_NAME LIKE 'DF%';

IF @ConstraintName IS NOT NULL
    EXEC ('ALTER TABLE [dbo].[User] DROP CONSTRAINT ' + @ConstraintName);
GO

-- Xóa default constraint cũ trên Customer.created_at
DECLARE @ConstraintName NVARCHAR(200);
SELECT @ConstraintName = CONSTRAINT_NAME 
FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE 
WHERE TABLE_NAME = 'Customer' AND COLUMN_NAME = 'created_at' 
  AND CONSTRAINT_NAME LIKE 'DF%';

IF @ConstraintName IS NOT NULL
    EXEC ('ALTER TABLE [dbo].[Customer] DROP CONSTRAINT ' + @ConstraintName);
GO

-- Hoặc cách đơn giản hơn - xóa theo tên cụ thể:
IF OBJECT_ID('DF_User_created_at', 'D') IS NOT NULL
    ALTER TABLE [dbo].[User] DROP CONSTRAINT DF_User_created_at;

IF OBJECT_ID('DF_Customer_created_at', 'D') IS NOT NULL
    ALTER TABLE [dbo].[Customer] DROP CONSTRAINT DF_Customer_created_at;
GO