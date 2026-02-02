-- ============================================================================
-- SAMPLE DATA INSERTION - Credit Risk Database
-- ============================================================================
-- Purpose: Insert sample data for testing and development
-- Date: January 28, 2026
-- Target Database: CreditRiskDB
--
-- Workflow:
-- 1. Create roles
-- 2. Create users
-- 3. Create customers
-- 4. Create loan applications
-- 5. Create loan facilities (multi-facility per customer)
-- 6. Create repayment schedules
-- 7. Create payments (on-time and late)
-- 8. Create transaction logs
-- 9. Create delinquency records
-- 10. Create risk predictions
-- ============================================================================

USE CreditRiskDB;
GO

-- ============================================================================
-- STEP 1: INSERT ROLES
-- ============================================================================
PRINT 'STEP 1: Inserting roles...';

INSERT INTO Role (role_id, role_name, description)
VALUES 
  (1, 'Admin', 'System Administrator'),
  (2, 'Manager', 'Credit Manager / Portfolio Manager'),
  (3, 'Officer', 'Credit Officer'),
  (4, 'Customer', 'Loan Customer'),
  (5, 'Analyst', 'Risk Analyst');

PRINT 'Roles inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 2: INSERT USERS
-- ============================================================================
PRINT 'STEP 2: Inserting users...';

INSERT INTO [User] (role_id, username, password, email, created_at)
VALUES
  -- Admin users
  (1, 'admin_system', 'hashed_pwd_123', 'admin@creditbank.com', SYSUTCDATETIME()),
  
  -- Managers
  (2, 'manager_portfolio', 'hashed_pwd_456', 'manager.portfolio@creditbank.com', SYSUTCDATETIME()),
  (2, 'manager_credit', 'hashed_pwd_789', 'manager.credit@creditbank.com', SYSUTCDATETIME()),
  
  -- Officers
  (3, 'officer_nguyen', 'hashed_pwd_101', 'officer.nguyen@creditbank.com', SYSUTCDATETIME()),
  (3, 'officer_tran', 'hashed_pwd_102', 'officer.tran@creditbank.com', SYSUTCDATETIME()),
  
  -- Customers (will link to Customer table)
  (4, 'customer_nva', 'hashed_pwd_201', 'nguyen.va@email.com', SYSUTCDATETIME()),
  (4, 'customer_tvb', 'hashed_pwd_202', 'tran.vb@email.com', SYSUTCDATETIME()),
  (4, 'customer_lxc', 'hashed_pwd_203', 'le.xc@email.com', SYSUTCDATETIME()),
  (4, 'customer_pqd', 'hashed_pwd_204', 'pham.qd@email.com', SYSUTCDATETIME()),
  
  -- Analysts
  (5, 'analyst_risk', 'hashed_pwd_301', 'analyst.risk@creditbank.com', SYSUTCDATETIME());

PRINT 'Users inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 3: INSERT CUSTOMERS
-- ============================================================================
PRINT 'STEP 3: Inserting customers...';

INSERT INTO Customer (user_id, full_name, age, monthly_income, credit_score, employment_status, created_at)
VALUES
  -- Customer 1: Nguyễn Văn A - GOOD CREDIT, MULTI-FACILITY
  (6, N'Nguyễn Văn A', 35, 50000000.00, 720, 'Employed', SYSUTCDATETIME()),
  
  -- Customer 2: Trần Văn B - MEDIUM CREDIT, MULTI-FACILITY
  (7, N'Trần Văn B', 42, 35000000.00, 650, 'Employed', SYSUTCDATETIME()),
  
  -- Customer 3: Lê Xuân C - POOR CREDIT, SINGLE FACILITY
  (8, N'Lê Xuân C', 28, 25000000.00, 580, 'Self-employed', SYSUTCDATETIME()),
  
  -- Customer 4: Phạm Quốc D - VERY GOOD CREDIT, MULTI-FACILITY
  (9, N'Phạm Quốc D', 50, 75000000.00, 760, 'Manager', SYSUTCDATETIME());

PRINT 'Customers inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 4: INSERT LOAN APPLICATIONS
-- ============================================================================
PRINT 'STEP 4: Inserting loan applications...';

INSERT INTO Loan_Application (customer_id, loan_amount, loan_term, interest_rate, loan_status, loan_purpose, created_at)
VALUES
  -- Customer 1: Nguyễn Văn A - Multiple applications
  (1, 500000000.00, 36, 8.5, 'approved', 'Mua nhà', DATEADD(MONTH, -3, SYSUTCDATETIME())),
  (1, 50000000.00, 60, 12.0, 'approved', 'Thẻ tín dụng', DATEADD(MONTH, -2, SYSUTCDATETIME())),
  (1, 200000000.00, 24, 9.5, 'approved', 'Mua xe', DATEADD(MONTH, -1, SYSUTCDATETIME())),
  
  -- Customer 2: Trần Văn B - Two applications
  (2, 300000000.00, 36, 10.0, 'approved', 'Mua nhà', DATEADD(MONTH, -4, SYSUTCDATETIME())),
  (2, 75000000.00, 12, 15.0, 'approved', 'Vay tiêu dùng', DATEADD(MONTH, -2, SYSUTCDATETIME())),
  
  -- Customer 3: Lê Xuân C - Single application
  (3, 100000000.00, 24, 11.5, 'approved', 'Vay kinh doanh', DATEADD(MONTH, -5, SYSUTCDATETIME())),
  
  -- Customer 4: Phạm Quốc D - Three applications
  (4, 1000000000.00, 60, 7.5, 'approved', 'Mua nhà', DATEADD(MONTH, -6, SYSUTCDATETIME())),
  (4, 200000000.00, 36, 8.0, 'approved', 'Thẻ tín dụng premium', DATEADD(MONTH, -3, SYSUTCDATETIME())),
  (4, 150000000.00, 24, 9.0, 'approved', 'Mua xe', DATEADD(MONTH, -2, SYSUTCDATETIME()));

PRINT 'Loan applications inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 5: INSERT LOAN FACILITIES
-- ============================================================================
PRINT 'STEP 5: Inserting loan facilities...';

INSERT INTO Loan_Facility 
  (application_id, customer_id, facility_type, approved_amount, interest_rate, start_date, end_date, status, created_at)
VALUES
  -- Customer 1: Nguyễn Văn A - Facility 1 (Home Loan - ON-TIME)
  (1, 1, 'Term Loan', 500000000.00, 8.5, CAST('2023-11-01' AS DATETIME), CAST('2026-10-01' AS DATETIME), 'active', DATEADD(MONTH, -3, SYSUTCDATETIME())),
  
  -- Customer 1: Facility 2 (Credit Card - RECENTLY ACTIVATED)
  (2, 1, 'Revolving', 50000000.00, 12.0, CAST('2023-12-01' AS DATETIME), NULL, 'active', DATEADD(MONTH, -2, SYSUTCDATETIME())),
  
  -- Customer 1: Facility 3 (Car Loan - ON-TIME)
  (3, 1, 'Term Loan', 200000000.00, 9.5, CAST('2024-01-01' AS DATETIME), CAST('2026-01-01' AS DATETIME), 'active', DATEADD(MONTH, -1, SYSUTCDATETIME())),
  
  -- Customer 2: Trần Văn B - Facility 1 (Home Loan - 1-30 DAYS LATE)
  (4, 2, 'Term Loan', 300000000.00, 10.0, CAST('2023-10-01' AS DATETIME), CAST('2026-09-01' AS DATETIME), 'active', DATEADD(MONTH, -4, SYSUTCDATETIME())),
  
  -- Customer 2: Facility 2 (Consumption - 30-90 DAYS LATE)
  (5, 2, 'Term Loan', 75000000.00, 15.0, CAST('2024-01-01' AS DATETIME), CAST('2024-12-01' AS DATETIME), 'active', DATEADD(MONTH, -2, SYSUTCDATETIME())),
  
  -- Customer 3: Lê Xuân C - Facility 1 (Business Loan - 90+ DAYS LATE)
  (6, 3, 'Term Loan', 100000000.00, 11.5, CAST('2023-09-01' AS DATETIME), CAST('2025-09-01' AS DATETIME), 'active', DATEADD(MONTH, -5, SYSUTCDATETIME())),
  
  -- Customer 4: Phạm Quốc D - Facility 1 (Home Loan - EXCELLENT)
  (7, 4, 'Term Loan', 1000000000.00, 7.5, CAST('2023-08-01' AS DATETIME), CAST('2028-08-01' AS DATETIME), 'active', DATEADD(MONTH, -6, SYSUTCDATETIME())),
  
  -- Customer 4: Facility 2 (Premium Card - EXCELLENT)
  (8, 4, 'Revolving', 200000000.00, 8.0, CAST('2023-11-01' AS DATETIME), NULL, 'active', DATEADD(MONTH, -3, SYSUTCDATETIME())),
  
  -- Customer 4: Facility 3 (Car Loan - EXCELLENT)
  (9, 4, 'Term Loan', 150000000.00, 9.0, CAST('2023-12-01' AS DATETIME), CAST('2025-12-01' AS DATETIME), 'active', DATEADD(MONTH, -2, SYSUTCDATETIME()));

PRINT 'Loan facilities inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 6: INSERT REPAYMENT SCHEDULES
-- ============================================================================
PRINT 'STEP 6: Inserting repayment schedules...';

-- Helper: Calculate monthly payment
-- Formula: P * [r(1+r)^n] / [(1+r)^n - 1]
-- Simplified for sample data

INSERT INTO Loan_Repayment_Schedule 
  (facility_id, installment_no, due_date, principal_amount, interest_amount, total_due, remaining_balance, created_at)
VALUES
  -- Facility 1 (Customer 1 - Home Loan): 500M, 36 months, 8.5%
  -- Monthly: ~15.5M principal + ~3.5M interest = ~19M total
  (1, 1, '2023-12-01', 13333333.33, 3541666.67, 16875000.00, 486666666.67, SYSUTCDATETIME()),
  (1, 2, '2024-01-01', 13333333.33, 3470000.00, 16803333.33, 473333333.34, SYSUTCDATETIME()),
  (1, 3, '2024-02-01', 13333333.33, 3398333.33, 16731666.66, 460000000.01, SYSUTCDATETIME()),
  (1, 4, '2024-03-01', 13333333.33, 3326666.67, 16660000.00, 446666666.68, SYSUTCDATETIME()),
  (1, 5, '2024-04-01', 13333333.33, 3255000.00, 16588333.33, 433333333.35, SYSUTCDATETIME()),
  
  -- Facility 3 (Customer 1 - Car Loan): 200M, 24 months, 9.5%
  (3, 1, '2024-02-01', 8333333.33, 1583333.33, 9916666.66, 191666666.67, SYSUTCDATETIME()),
  (3, 2, '2024-03-01', 8333333.33, 1519166.67, 9852500.00, 183333333.34, SYSUTCDATETIME()),
  (3, 3, '2024-04-01', 8333333.33, 1455000.00, 9788333.33, 175000000.01, SYSUTCDATETIME()),
  
  -- Facility 4 (Customer 2 - Home Loan): 300M, 36 months, 10%
  (4, 1, '2023-11-01', 8333333.33, 2500000.00, 10833333.33, 291666666.67, SYSUTCDATETIME()),
  (4, 2, '2023-12-01', 8333333.33, 2430555.56, 10763888.89, 283333333.34, SYSUTCDATETIME()),
  (4, 3, '2024-01-01', 8333333.33, 2361111.11, 10694444.44, 275000000.01, SYSUTCDATETIME()),
  (4, 4, '2024-02-01', 8333333.33, 2291666.67, 10625000.00, 266666666.68, SYSUTCDATETIME()),
  (4, 5, '2024-03-01', 8333333.33, 2222222.22, 10555555.55, 258333333.35, SYSUTCDATETIME()),
  (4, 6, '2024-04-01', 8333333.33, 2152777.78, 10486111.11, 250000000.02, SYSUTCDATETIME()),
  
  -- Facility 5 (Customer 2 - Consumption): 75M, 12 months, 15%
  (5, 1, '2024-02-01', 6250000.00, 937500.00, 7187500.00, 68750000.00, SYSUTCDATETIME()),
  (5, 2, '2024-03-01', 6250000.00, 859375.00, 7109375.00, 62500000.00, SYSUTCDATETIME()),
  (5, 3, '2024-04-01', 6250000.00, 781250.00, 7031250.00, 56250000.00, SYSUTCDATETIME()),
  
  -- Facility 6 (Customer 3 - Business): 100M, 24 months, 11.5%
  (6, 1, '2023-10-01', 4166666.67, 958333.33, 5125000.00, 95833333.33, SYSUTCDATETIME()),
  (6, 2, '2023-11-01', 4166666.67, 916458.33, 5083125.00, 91666666.66, SYSUTCDATETIME()),
  (6, 3, '2023-12-01', 4166666.67, 874583.33, 5041250.00, 87500000.00, SYSUTCDATETIME());

PRINT 'Repayment schedules inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 7: INSERT LOAN PAYMENTS (Mix of On-time and Late)
-- ============================================================================
PRINT 'STEP 7: Inserting loan payments...';

INSERT INTO Loan_Payment 
  (facility_id, schedule_id, payment_date, amount_paid, principal_paid, interest_paid, payment_method, status, created_at)
VALUES
  -- Facility 1 (Customer 1 - ON-TIME): All payments made on time
  (1, 1, '2023-12-01', 16875000.00, 13333333.33, 3541666.67, 'transfer', 'completed', SYSUTCDATETIME()),
  (1, 2, '2024-01-01', 16803333.33, 13333333.33, 3470000.00, 'transfer', 'completed', SYSUTCDATETIME()),
  (1, 3, '2024-02-01', 16731666.66, 13333333.33, 3398333.33, 'transfer', 'completed', SYSUTCDATETIME()),
  (1, 4, '2024-03-01', 16660000.00, 13333333.33, 3326666.67, 'transfer', 'completed', SYSUTCDATETIME()),
  (1, 5, '2024-04-01', 16588333.33, 13333333.33, 3255000.00, 'transfer', 'completed', SYSUTCDATETIME()),
  
  -- Facility 3 (Customer 1 - ON-TIME): All payments on time
  (3, 6, '2024-02-01', 9916666.66, 8333333.33, 1583333.33, 'transfer', 'completed', SYSUTCDATETIME()),
  (3, 7, '2024-03-01', 9852500.00, 8333333.33, 1519166.67, 'transfer', 'completed', SYSUTCDATETIME()),
  (3, 8, '2024-04-01', 9788333.33, 8333333.33, 1455000.00, 'transfer', 'completed', SYSUTCDATETIME()),
  
  -- Facility 4 (Customer 2 - 1-30 DAYS LATE): First 3 on-time, then late
  (4, 9, '2023-11-01', 10833333.33, 8333333.33, 2500000.00, 'transfer', 'completed', SYSUTCDATETIME()),
  (4, 10, '2023-12-01', 10763888.89, 8333333.33, 2430555.56, 'transfer', 'completed', SYSUTCDATETIME()),
  (4, 11, '2024-01-01', 10694444.44, 8333333.33, 2361111.11, 'transfer', 'completed', SYSUTCDATETIME()),
  (4, 12, '2024-03-05', 10625000.00, 8333333.33, 2291666.67, 'transfer', 'completed', DATEADD(DAY, 33, SYSUTCDATETIME())), -- 33 days late
  (4, 13, '2024-04-01', 10555555.55, 8333333.33, 2222222.22, 'transfer', 'completed', SYSUTCDATETIME()),
  
  -- Facility 5 (Customer 2 - 30-90 DAYS LATE): Missing payments
  (5, 14, '2024-02-01', 7187500.00, 6250000.00, 937500.00, 'transfer', 'completed', SYSUTCDATETIME()),
  (5, 15, '2024-05-01', 7109375.00, 6250000.00, 859375.00, 'transfer', 'completed', DATEADD(DAY, 57, SYSUTCDATETIME())), -- 57 days late
  
  -- Facility 6 (Customer 3 - 90+ DAYS LATE): Severely delinquent
  (6, 16, '2023-10-01', 5125000.00, 4166666.67, 958333.33, 'transfer', 'completed', SYSUTCDATETIME()),
  -- Missing payment 2 and 3 - now 90+ days late
  (6, 17, '2024-02-01', 10000000.00, 8333333.34, 1666666.67, 'check', 'pending', SYSUTCDATETIME()); -- Partial payment much later

PRINT 'Loan payments inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 8: INSERT TRANSACTION LOGS (Time-series tracking)
-- ============================================================================
PRINT 'STEP 8: Inserting transaction logs...';

INSERT INTO Transaction_Log 
  (facility_id, transaction_type, amount, transaction_date, description, created_at)
VALUES
  -- Facility 1 (Customer 1): Payments
  (1, 'payment', 16875000.00, '2023-12-01', 'Monthly payment #1', SYSUTCDATETIME()),
  (1, 'payment', 16803333.33, '2024-01-01', 'Monthly payment #2', SYSUTCDATETIME()),
  (1, 'payment', 16731666.66, '2024-02-01', 'Monthly payment #3', SYSUTCDATETIME()),
  (1, 'interest_accrual', 3541666.67, '2023-12-01', 'Interest for month 1', SYSUTCDATETIME()),
  (1, 'interest_accrual', 3470000.00, '2024-01-01', 'Interest for month 2', SYSUTCDATETIME()),
  
  -- Facility 4 (Customer 2): Late payments tracked
  (4, 'payment', 10833333.33, '2023-11-01', 'Monthly payment on-time', SYSUTCDATETIME()),
  (4, 'payment', 10763888.89, '2023-12-01', 'Monthly payment on-time', SYSUTCDATETIME()),
  (4, 'payment', 10694444.44, '2024-01-01', 'Monthly payment on-time', SYSUTCDATETIME()),
  (4, 'penalty', 50000.00, '2024-03-01', 'Late payment fee (5 days)', SYSUTCDATETIME()),
  (4, 'payment', 10625000.00, '2024-03-05', 'Late payment (33 days)', SYSUTCDATETIME()),
  
  -- Facility 5 (Customer 2): Severely delinquent
  (5, 'payment', 7187500.00, '2024-02-01', 'Payment on-time', SYSUTCDATETIME()),
  (5, 'penalty', 100000.00, '2024-04-01', 'Late payment penalty (60 days)', SYSUTCDATETIME()),
  (5, 'interest_accrual', 859375.00, '2024-03-01', 'Interest accrual continued', SYSUTCDATETIME()),
  (5, 'payment', 7109375.00, '2024-05-01', 'Late payment (57 days)', SYSUTCDATETIME()),
  
  -- Facility 6 (Customer 3): Default scenario
  (6, 'payment', 5125000.00, '2023-10-01', 'Payment on-time', SYSUTCDATETIME()),
  (6, 'penalty', 200000.00, '2023-12-01', 'Late payment penalty (60+ days)', SYSUTCDATETIME()),
  (6, 'interest_accrual', 958333.33, '2023-11-01', 'Interest month 1', SYSUTCDATETIME()),
  (6, 'interest_accrual', 916458.33, '2023-12-01', 'Interest month 2', SYSUTCDATETIME()),
  (6, 'penalty', 500000.00, '2024-02-01', 'Default penalty (90+ days)', SYSUTCDATETIME()),
  (6, 'payment', 10000000.00, '2024-02-01', 'Partial payment after default', SYSUTCDATETIME());

PRINT 'Transaction logs inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 9: INSERT LOAN DELINQUENCY RECORDS
-- ============================================================================
PRINT 'STEP 9: Inserting loan delinquency records...';

INSERT INTO Loan_Delinquency 
  (facility_id, as_of_date, days_past_due, overdue_amount, risk_bucket, created_at)
VALUES
  -- Facility 1 (Customer 1 - ON-TIME): No delinquency
  (1, '2024-04-01', 0, 0.00, 'GROUP_1', SYSUTCDATETIME()),
  (1, '2024-05-01', 0, 0.00, 'GROUP_1', SYSUTCDATETIME()),
  
  -- Facility 3 (Customer 1 - ON-TIME): No delinquency
  (3, '2024-04-01', 0, 0.00, 'GROUP_1', SYSUTCDATETIME()),
  (3, '2024-05-01', 0, 0.00, 'GROUP_1', SYSUTCDATETIME()),
  
  -- Facility 4 (Customer 2 - 1-30 DAYS LATE): GROUP_2
  (4, '2024-03-15', 15, 10625000.00, 'GROUP_2', SYSUTCDATETIME()),
  (4, '2024-04-01', 1, 10625000.00, 'GROUP_2', SYSUTCDATETIME()),
  (4, '2024-05-01', 0, 0.00, 'GROUP_1', SYSUTCDATETIME()),
  
  -- Facility 5 (Customer 2 - 30-90 DAYS LATE): GROUP_3
  (5, '2024-03-01', 30, 7109375.00, 'GROUP_3', SYSUTCDATETIME()),
  (5, '2024-04-01', 61, 7109375.00, 'GROUP_3', SYSUTCDATETIME()),
  (5, '2024-05-01', 0, 0.00, 'GROUP_1', SYSUTCDATETIME()),
  
  -- Facility 6 (Customer 3 - 90+ DAYS DEFAULT): GROUP_4
  (6, '2023-12-01', 61, 10083125.00, 'GROUP_3', SYSUTCDATETIME()),
  (6, '2024-01-01', 92, 10083125.00, 'GROUP_4', SYSUTCDATETIME()),
  (6, '2024-02-01', 122, 10083125.00, 'GROUP_4', SYSUTCDATETIME());

PRINT 'Loan delinquency records inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 10: INSERT MONTHLY DELINQUENCY SNAPSHOTS (For classification)
-- ============================================================================
PRINT 'STEP 10: Inserting monthly delinquency snapshots...';

INSERT INTO Monthly_Delinquency 
  (facility_id, snapshot_month, days_past_due, risk_group, principal_overdue, interest_overdue, total_overdue, 
   on_time_payment_rate, violation_count, created_at)
VALUES
  -- Facility 1 (Customer 1 - EXCELLENT): All on-time
  (1, '2024-01-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (1, '2024-02-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (1, '2024-03-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (1, '2024-04-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  
  -- Facility 3 (Customer 1 - EXCELLENT): All on-time
  (3, '2024-02-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (3, '2024-03-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (3, '2024-04-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  
  -- Facility 4 (Customer 2 - SPECIAL MENTION): 1-30 days late
  (4, '2024-02-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (4, '2024-03-01', 15, 'GROUP_2', 10625000.00, 0.00, 10625000.00, 75.0, 1, SYSUTCDATETIME()),
  (4, '2024-04-01', 1, 'GROUP_2', 10625000.00, 0.00, 10625000.00, 75.0, 1, SYSUTCDATETIME()),
  (4, '2024-05-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 80.0, 1, SYSUTCDATETIME()),
  
  -- Facility 5 (Customer 2 - SUBSTANDARD): 30-90 days late
  (5, '2024-02-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (5, '2024-03-01', 30, 'GROUP_3', 7109375.00, 0.00, 7109375.00, 50.0, 2, SYSUTCDATETIME()),
  (5, '2024-04-01', 61, 'GROUP_3', 7109375.00, 0.00, 7109375.00, 33.0, 3, SYSUTCDATETIME()),
  (5, '2024-05-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 50.0, 3, SYSUTCDATETIME()),
  
  -- Facility 6 (Customer 3 - DOUBTFUL): 90+ days default
  (6, '2023-10-01', 0, 'GROUP_1', 0.00, 0.00, 0.00, 100.0, 0, SYSUTCDATETIME()),
  (6, '2023-11-01', 30, 'GROUP_3', 4166666.67, 0.00, 4166666.67, 50.0, 1, SYSUTCDATETIME()),
  (6, '2023-12-01', 61, 'GROUP_3', 8333333.34, 0.00, 8333333.34, 25.0, 2, SYSUTCDATETIME()),
  (6, '2024-01-01', 92, 'GROUP_4', 12500000.00, 0.00, 12500000.00, 0.0, 4, SYSUTCDATETIME()),
  (6, '2024-02-01', 122, 'GROUP_4', 10083125.00, 0.00, 10083125.00, 0.0, 5, SYSUTCDATETIME());

PRINT 'Monthly delinquency snapshots inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 11: INSERT LOAN STATUS MIGRATIONS (Track GROUP changes)
-- ============================================================================
PRINT 'STEP 11: Inserting loan status migrations...';

INSERT INTO Loan_Status_Migration 
  (facility_id, from_group, to_group, migration_date, reason)
VALUES
  -- Facility 4 (Customer 2): GROUP_1 → GROUP_2 → GROUP_1
  (4, 'GROUP_1', 'GROUP_2', '2024-03-01', 'Payment missed by 15 days'),
  (4, 'GROUP_2', 'GROUP_1', '2024-04-05', 'Made up late payment'),
  
  -- Facility 5 (Customer 2): GROUP_1 → GROUP_3 → GROUP_1
  (5, 'GROUP_1', 'GROUP_3', '2024-03-01', 'Payment 30-90 days late'),
  (5, 'GROUP_3', 'GROUP_1', '2024-05-01', 'Made full payment after default'),
  
  -- Facility 6 (Customer 3): GROUP_1 → GROUP_3 → GROUP_4 (stays in default)
  (6, 'GROUP_1', 'GROUP_3', '2023-11-01', 'Payment 30+ days late'),
  (6, 'GROUP_3', 'GROUP_4', '2024-01-01', 'Payment 90+ days late - DEFAULT');

PRINT 'Loan status migrations inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- STEP 12: INSERT RISK PREDICTIONS
-- ============================================================================
PRINT 'STEP 12: Inserting risk predictions...';

INSERT INTO RISK_PREDICTION 
  (application_id, customer_id, model_id, risk_score, risk_level, predicted_at)
VALUES
  -- Low Risk (Good credit)
  (1, 1, NULL, 0.25, 'low', DATEADD(MONTH, -3, SYSUTCDATETIME())),
  (2, 1, NULL, 0.35, 'low', DATEADD(MONTH, -2, SYSUTCDATETIME())),
  (3, 1, NULL, 0.28, 'low', DATEADD(MONTH, -1, SYSUTCDATETIME())),
  
  -- Medium Risk (Customer 2)
  (4, 2, NULL, 0.55, 'medium', DATEADD(MONTH, -4, SYSUTCDATETIME())),
  (5, 2, NULL, 0.62, 'medium', DATEADD(MONTH, -2, SYSUTCDATETIME())),
  
  -- High Risk (Poor credit)
  (6, 3, NULL, 0.75, 'high', DATEADD(MONTH, -5, SYSUTCDATETIME())),
  
  -- Very Low Risk (Excellent credit)
  (7, 4, NULL, 0.15, 'low', DATEADD(MONTH, -6, SYSUTCDATETIME())),
  (8, 4, NULL, 0.18, 'low', DATEADD(MONTH, -3, SYSUTCDATETIME())),
  (9, 4, NULL, 0.20, 'low', DATEADD(MONTH, -2, SYSUTCDATETIME()));

PRINT 'Risk predictions inserted: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
PRINT '';
PRINT '========== VERIFICATION ==========';
GO

PRINT 'Total Customers:';
SELECT COUNT(*) as customer_count FROM Customer;

PRINT 'Total Facilities (Multi-per-customer):';
SELECT c.customer_id, c.full_name, COUNT(lf.facility_id) as facility_count
FROM Customer c
LEFT JOIN Loan_Facility lf ON c.customer_id = lf.customer_id
GROUP BY c.customer_id, c.full_name
ORDER BY c.customer_id;

PRINT 'Risk Group Distribution (Latest):';
SELECT risk_group, COUNT(*) as facility_count, AVG(total_overdue) as avg_overdue
FROM Monthly_Delinquency
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM Monthly_Delinquency)
GROUP BY risk_group
ORDER BY risk_group;

PRINT 'Payment Status Summary:';
SELECT 
  lf.facility_id,
  c.full_name,
  lf.facility_type,
  COUNT(CASE WHEN lp.payment_date <= rs.due_date THEN 1 END) as on_time_payments,
  COUNT(CASE WHEN lp.payment_date > rs.due_date THEN 1 END) as late_payments,
  MAX(ld.days_past_due) as max_dpd,
  MAX(ld.risk_bucket) as current_risk_group
FROM Loan_Facility lf
JOIN Customer c ON lf.customer_id = c.customer_id
LEFT JOIN Loan_Repayment_Schedule rs ON lf.facility_id = rs.facility_id
LEFT JOIN Loan_Payment lp ON rs.schedule_id = lp.schedule_id
LEFT JOIN Loan_Delinquency ld ON lf.facility_id = ld.facility_id
GROUP BY lf.facility_id, c.full_name, lf.facility_type
ORDER BY lf.facility_id;

PRINT '';
PRINT '========== SAMPLE DATA INSERTION COMPLETE ==========';
PRINT 'Status: SUCCESS';
PRINT 'Total Customers: 4';
PRINT 'Total Facilities: 9 (Multi-facility scenario)';
PRINT 'Total Payments: 17';
PRINT 'Total Transactions: 20+';
PRINT 'Total Monthly Snapshots: 20';
PRINT 'Total Risk Migrations: 6';
PRINT '';
PRINT 'Next Steps:';
PRINT '1. Test ORM models in Python';
PRINT '2. Run API endpoints to fetch data';
PRINT '3. Implement classification service';
PRINT '4. Create dashboard KPI queries';
GO
