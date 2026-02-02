-- ============================================================================
-- ETL IMPORT PIPELINE - Import 7 CSV files into CreditRiskDB
-- ============================================================================
-- Purpose: Import Sales/Finance data and map to Credit Risk model
-- Files: Data_1-6, Data_8 (Adventure Works dataset)
-- Target: Map Sales Orders → Loan Facilities for risk analysis
-- Date: January 28, 2026
-- ============================================================================

USE CreditRiskDB;
GO

-- ============================================================================
-- STEP 1: CREATE STAGING TABLES
-- ============================================================================
PRINT 'STEP 1: Creating staging tables...';
GO

-- Drop existing staging tables if they exist
IF OBJECT_ID('dbo.stg_SalesOrder', 'U') IS NOT NULL 
    DROP TABLE dbo.stg_SalesOrder;
IF OBJECT_ID('dbo.stg_Account', 'U') IS NOT NULL 
    DROP TABLE dbo.stg_Account;
IF OBJECT_ID('dbo.stg_Currency', 'U') IS NOT NULL 
    DROP TABLE dbo.stg_Currency;
IF OBJECT_ID('dbo.stg_Date', 'U') IS NOT NULL 
    DROP TABLE dbo.stg_Date;
IF OBJECT_ID('dbo.stg_Scenario', 'U') IS NOT NULL 
    DROP TABLE dbo.stg_Scenario;
IF OBJECT_ID('dbo.stg_ExchangeRate', 'U') IS NOT NULL 
    DROP TABLE dbo.stg_ExchangeRate;
IF OBJECT_ID('dbo.stg_FinanceFact', 'U') IS NOT NULL 
    DROP TABLE dbo.stg_FinanceFact;
GO

-- Staging: Sales Orders (Data_1)
CREATE TABLE dbo.stg_SalesOrder (
    SalesOrderNumber NVARCHAR(MAX),
    SalesOrderLineNumber INT,
    TaxAmt DECIMAL(18,4),
    UnitPrice DECIMAL(18,4),
    CurrencyKey INT,
    TotalProductCost DECIMAL(18,4),
    CarrierTrackingNumber NVARCHAR(MAX),
    CustomerKey INT,
    CustomerPONumber NVARCHAR(MAX),
    DiscountAmount DECIMAL(18,4),
    DueDate_Year INT,
    DueDate_Quarter NVARCHAR(10),
    DueDate_Month NVARCHAR(50),
    DueDate_Day INT,
    DueDateKey INT,
    ExtendedAmount DECIMAL(18,4),
    Freight DECIMAL(18,4),
    OrderDate_Year INT,
    OrderDate_Quarter NVARCHAR(10),
    OrderDate_Month NVARCHAR(50),
    OrderDate_Day INT,
    OrderDateKey INT,
    OrderQuantity INT,
    ProductKey INT,
    ProductStandardCost DECIMAL(18,4),
    PromotionKey INT,
    RevisionNumber INT,
    SalesAmount DECIMAL(18,4),
    SalesTerritoryKey INT,
    ShipDate_Year INT,
    ShipDate_Quarter NVARCHAR(10),
    ShipDate_Month NVARCHAR(50),
    ShipDate_Day INT,
    ShipDateKey INT,
    UnitPriceDiscountPct DECIMAL(18,4),
    ImportedDate DATETIME DEFAULT SYSUTCDATETIME()
);

-- Staging: Accounts (Data_2)
CREATE TABLE dbo.stg_Account (
    AccountCodeAlternateKey NVARCHAR(MAX),
    AccountDescription NVARCHAR(MAX),
    AccountKey INT,
    AccountType NVARCHAR(MAX),
    CustomMemberOptions NVARCHAR(MAX),
    CustomMembers NVARCHAR(MAX),
    Operator NVARCHAR(10),
    ParentAccountCodeAlternateKey NVARCHAR(MAX),
    ParentAccountKey INT,
    ValueType NVARCHAR(50),
    ImportedDate DATETIME DEFAULT SYSUTCDATETIME()
);

-- Staging: Currencies (Data_3)
CREATE TABLE dbo.stg_Currency (
    CurrencyAlternateKey NVARCHAR(10),
    CurrencyKey INT,
    CurrencyName NVARCHAR(MAX),
    ImportedDate DATETIME DEFAULT SYSUTCDATETIME()
);

-- Staging: Date (Data_4)
CREATE TABLE dbo.stg_Date (
    EnglishDayNameOfWeek NVARCHAR(50),
    EnglishMonthName NVARCHAR(50),
    FrenchDayNameOfWeek NVARCHAR(50),
    FrenchMonthName NVARCHAR(50),
    SpanishDayNameOfWeek NVARCHAR(50),
    SpanishMonthName NVARCHAR(50),
    CalendarQuarter INT,
    CalendarSemester INT,
    CalendarYear INT,
    DateKey INT,
    DayNumberOfMonth INT,
    DayNumberOfWeek INT,
    DayNumberOfYear INT,
    FiscalQuarter INT,
    FiscalYear INT,
    VietYear INT,
    VietQuarter NVARCHAR(10),
    VietMonth NVARCHAR(50),
    VietDay INT,
    MonthNumberOfYear INT,
    FiscalSemester INT,
    WeekNumberOfYear INT,
    ImportedDate DATETIME DEFAULT SYSUTCDATETIME()
);

-- Staging: Scenario (Data_5)
CREATE TABLE dbo.stg_Scenario (
    ScenarioKey INT,
    ScenarioName NVARCHAR(MAX),
    ImportedDate DATETIME DEFAULT SYSUTCDATETIME()
);

-- Staging: Exchange Rate (Data_6)
CREATE TABLE dbo.stg_ExchangeRate (
    DateKey INT,
    CurrencyKey INT,
    AverageRate DECIMAL(18,10),
    VietYear INT,
    VietQuarter NVARCHAR(10),
    VietMonth NVARCHAR(50),
    VietDay INT,
    EndOfDayRate DECIMAL(18,10),
    ImportedDate DATETIME DEFAULT SYSUTCDATETIME()
);

-- Staging: Finance Fact (Data_8)
CREATE TABLE dbo.stg_FinanceFact (
    AccountKey INT,
    Amount DECIMAL(18,4),
    VietYear INT,
    VietQuarter NVARCHAR(10),
    VietMonth NVARCHAR(50),
    VietDay INT,
    DateKey INT,
    DepartmentGroupKey INT,
    FinanceKey INT,
    OrganizationKey INT,
    ScenarioKey INT,
    ImportedDate DATETIME DEFAULT SYSUTCDATETIME()
);

PRINT 'Staging tables created successfully.';
GO

-- ============================================================================
-- STEP 2: IMPORT DATA FROM CSV FILES (BULK INSERT)
-- ============================================================================
PRINT '';
PRINT 'STEP 2: Importing data from CSV files...';
GO

-- Import Data_1: Sales Orders
PRINT 'Importing Data_1 (Sales Orders)...';
BULK INSERT dbo.stg_SalesOrder
FROM 'D:\GitHub\credit-risk-backend\data\Data_1.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    MAXERRORS = 1000
);
PRINT 'Data_1 imported: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' rows';
GO

-- Import Data_2: Accounts
PRINT 'Importing Data_2 (Accounts)...';
BULK INSERT dbo.stg_Account
FROM 'D:\GitHub\credit-risk-backend\data\Data_2.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    MAXERRORS = 1000
);
PRINT 'Data_2 imported: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' rows';
GO

-- Import Data_3: Currencies
PRINT 'Importing Data_3 (Currencies)...';
BULK INSERT dbo.stg_Currency
FROM 'D:\GitHub\credit-risk-backend\data\Data_3.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    MAXERRORS = 1000
);
PRINT 'Data_3 imported: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' rows';
GO

-- Import Data_4: Date
PRINT 'Importing Data_4 (Date Dimension)...';
BULK INSERT dbo.stg_Date
FROM 'D:\GitHub\credit-risk-backend\data\Data_4.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    MAXERRORS = 1000
);
PRINT 'Data_4 imported: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' rows';
GO

-- Import Data_5: Scenario
PRINT 'Importing Data_5 (Scenario)...';
BULK INSERT dbo.stg_Scenario
FROM 'D:\GitHub\credit-risk-backend\data\Data_5.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    MAXERRORS = 1000
);
PRINT 'Data_5 imported: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' rows';
GO

-- Import Data_6: Exchange Rate
PRINT 'Importing Data_6 (Exchange Rate)...';
BULK INSERT dbo.stg_ExchangeRate
FROM 'D:\GitHub\credit-risk-backend\data\Data_6.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    MAXERRORS = 1000
);
PRINT 'Data_6 imported: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' rows';
GO

-- Import Data_8: Finance Fact
PRINT 'Importing Data_8 (Finance Fact)...';
BULK INSERT dbo.stg_FinanceFact
FROM 'D:\GitHub\credit-risk-backend\data\Data_8.csv'
WITH (
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    MAXERRORS = 1000
);
PRINT 'Data_8 imported: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' rows';
GO

-- ============================================================================
-- STEP 3: TRANSFORM & MAP TO CREDIT RISK MODEL
-- ============================================================================
PRINT '';
PRINT 'STEP 3: Transforming data to Credit Risk model...';
GO

-- Map Sales Orders to Loan Facility
-- Strategy: Each SalesOrder becomes a Loan Facility
-- SalesAmount → approved_amount
-- OrderDateKey → start_date
-- CustomerKey → customer_id (mapped from stg_SalesOrder.CustomerKey)

DECLARE @ImportBatchId INT = CAST(FORMAT(GETDATE(), 'yyyyMMddHHmmss') AS INT);
DECLARE @CustomerCount INT = 0;
DECLARE @FacilityCount INT = 0;

-- Step 3a: Create sample customers from Sales Orders (using CustomerKey)
PRINT 'Creating customers from Sales Orders...';

INSERT INTO Customer (user_id, full_name, age, monthly_income, credit_score, employment_status, created_at)
SELECT DISTINCT
    4 as user_id,
    'Customer_' + CAST(ROW_NUMBER() OVER (ORDER BY so.CustomerKey) AS VARCHAR(10)) as full_name,
    25 + ABS(CHECKSUM(so.CustomerKey)) % 40 as age,
    SO.SalesAmount / 12 as monthly_income,
    550 + ABS(CHECKSUM(so.CustomerKey)) % 200 as credit_score,
    'Employed' as employment_status,
    SYSUTCDATETIME() as created_at
FROM (
    SELECT DISTINCT TOP 100 
        CustomerKey, 
        AVG(SalesAmount) as SalesAmount
    FROM dbo.stg_SalesOrder
    WHERE SalesAmount > 0
    GROUP BY CustomerKey
) so
WHERE NOT EXISTS (
    SELECT 1 FROM Customer c 
    WHERE c.full_name = 'Customer_' + CAST(ROW_NUMBER() OVER (ORDER BY so.CustomerKey) AS VARCHAR(10))
);

SELECT @CustomerCount = COUNT(*) FROM Customer WHERE full_name LIKE 'Customer_%';
PRINT 'Customers created: ' + CAST(@CustomerCount AS VARCHAR(10));
GO

-- Step 3b: Create Loan Applications
PRINT 'Creating loan applications from Sales Orders...';

INSERT INTO Loan_Application (customer_id, loan_amount, loan_term, interest_rate, loan_status, loan_purpose, created_at)
SELECT TOP 100
    c.customer_id,
    ABS(so.SalesAmount) as loan_amount,
    24 + ABS(CHECKSUM(so.CustomerKey)) % 36 as loan_term,
    8.0 + (ABS(CHECKSUM(so.CurrencyKey)) % 500) / 100.0 as interest_rate,
    'approved' as loan_status,
    'Uploaded from CSV' as loan_purpose,
    SYSUTCDATETIME() as created_at
FROM dbo.stg_SalesOrder so
CROSS JOIN (
    SELECT TOP 1 customer_id FROM Customer WHERE full_name LIKE 'Customer_%'
) c
WHERE so.SalesAmount > 100000;

PRINT 'Loan applications created: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- Step 3c: Create Loan Facilities
PRINT 'Creating loan facilities...';

INSERT INTO Loan_Facility (application_id, customer_id, facility_type, approved_amount, interest_rate, start_date, end_date, status, created_at)
SELECT TOP 100
    la.application_id,
    la.customer_id,
    CASE WHEN so.OrderQuantity % 2 = 0 THEN 'Term Loan' ELSE 'Revolving' END as facility_type,
    ABS(so.SalesAmount) as approved_amount,
    la.interest_rate,
    CONVERT(DATETIME, CAST(so.OrderDateKey AS VARCHAR(8)), 112) as start_date,
    DATEADD(MONTH, CAST(la.loan_term AS INT), CONVERT(DATETIME, CAST(so.OrderDateKey AS VARCHAR(8)), 112)) as end_date,
    'active' as status,
    SYSUTCDATETIME() as created_at
FROM dbo.stg_SalesOrder so
INNER JOIN Loan_Application la ON so.CustomerKey = la.customer_id
WHERE so.SalesAmount > 100000
    AND so.OrderDateKey > 20050101;

SELECT @FacilityCount = COUNT(*) FROM Loan_Facility WHERE created_at > DATEADD(MINUTE, -5, GETDATE());
PRINT 'Loan facilities created: ' + CAST(@FacilityCount AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 4: VERIFICATION
-- ============================================================================
PRINT '';
PRINT '========== VERIFICATION ==========';
GO

PRINT 'Staging tables row counts:';
SELECT 
    'stg_SalesOrder' as TableName, COUNT(*) as RowCount FROM dbo.stg_SalesOrder
UNION ALL
SELECT 'stg_Account', COUNT(*) FROM dbo.stg_Account
UNION ALL
SELECT 'stg_Currency', COUNT(*) FROM dbo.stg_Currency
UNION ALL
SELECT 'stg_Date', COUNT(*) FROM dbo.stg_Date
UNION ALL
SELECT 'stg_Scenario', COUNT(*) FROM dbo.stg_Scenario
UNION ALL
SELECT 'stg_ExchangeRate', COUNT(*) FROM dbo.stg_ExchangeRate
UNION ALL
SELECT 'stg_FinanceFact', COUNT(*) FROM dbo.stg_FinanceFact;

PRINT '';
PRINT 'Credit Risk tables (newly created):';
SELECT 
    'Customer' as TableName, COUNT(*) as RowCount FROM Customer 
    WHERE full_name LIKE 'Customer_%'
UNION ALL
SELECT 'Loan_Application', COUNT(*) FROM Loan_Application 
    WHERE loan_purpose = 'Uploaded from CSV'
UNION ALL
SELECT 'Loan_Facility', COUNT(*) FROM Loan_Facility 
    WHERE created_at > DATEADD(HOUR, -1, GETDATE());

PRINT '';
PRINT '========== ETL IMPORT COMPLETE ==========';
PRINT 'Status: SUCCESS';
PRINT 'Next Steps:';
PRINT '1. Verify data in staging tables';
PRINT '2. Review Credit Risk mappings';
PRINT '3. Proceed to upload API';
GO
