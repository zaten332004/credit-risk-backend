-- Tạo database (nếu chưa có)
CREATE DATABASE CreditRiskDB;
-- GO
USE CreditRiskDB;
-- GO

-- 1. User
CREATE TABLE [dbo].[User] (
    user_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    role_id       INT               NOT NULL,           -- FK sau khi có bảng Role (nếu có)
    username      NVARCHAR(50)      NOT NULL UNIQUE,
    password      NVARCHAR(255)     NOT NULL,           -- Nên hash (bcrypt/Argon2)
    email         NVARCHAR(100)     NULL,
    created_at    DATETIME2         NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- 2. Customer
CREATE TABLE [dbo].[Customer] (
    customer_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id           BIGINT           NULL,             -- FK to User (nếu customer liên kết với user)
    full_name         NVARCHAR(150)    NOT NULL,
    age               INT              NULL,
    monthly_income    DECIMAL(18,2)    NULL,
    credit_score      INT              NULL,
    employment_status NVARCHAR(50)     NULL,             -- 'employed', 'self-employed', 'unemployed', etc.
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at        DATETIME2        NULL,

    CONSTRAINT FK_Customer_User FOREIGN KEY (user_id) REFERENCES [dbo].[User](user_id)
);
GO

-- 3. Customer_Employment
CREATE TABLE [dbo].[Customer_Employment] (
    employment_id     BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id       BIGINT           NOT NULL,
    company_name      NVARCHAR(200)    NULL,
    position          NVARCHAR(100)    NULL,
    years_of_experience INT            NULL,
    monthly_income    DECIMAL(18,2)    NULL,
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Employment_Customer FOREIGN KEY (customer_id) REFERENCES [dbo].[Customer](customer_id)
);
GO

-- 4. Loan_Application
CREATE TABLE [dbo].[Loan_Application] (
    application_id    BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id       BIGINT           NOT NULL,
    loan_amount       DECIMAL(18,2)    NOT NULL,
    loan_term         INT              NOT NULL,         -- months
    interest_rate     DECIMAL(10,4)    NULL,
    loan_status       NVARCHAR(50)     NOT NULL,         -- 'pending', 'approved', 'rejected', 'disbursed', etc.
    loan_purpose      NVARCHAR(200)    NULL,
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Application_Customer FOREIGN KEY (customer_id) REFERENCES [dbo].[Customer](customer_id)
);
GO

-- 5. Loan_Facility (khoản vay thực tế sau phê duyệt)
CREATE TABLE [dbo].[Loan_Facility] (
    facility_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    application_id    BIGINT           NULL,
    customer_id       BIGINT           NOT NULL,
    facility_type     NVARCHAR(50)     NULL,             -- 'term_loan', 'revolving', etc.
    approved_amount   DECIMAL(18,2)    NOT NULL,
    interest_rate     DECIMAL(10,4)    NULL,
    start_date        DATE             NULL,
    end_date          DATE             NULL,
    status            NVARCHAR(50)     NOT NULL,         -- 'active', 'closed', 'arrears'
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Facility_Application FOREIGN KEY (application_id) REFERENCES [dbo].[Loan_Application](application_id),
    CONSTRAINT FK_Facility_Customer    FOREIGN KEY (customer_id)    REFERENCES [dbo].[Customer](customer_id)
);
GO

-- 6. Loan_Repayment_Schedule
CREATE TABLE [dbo].[Loan_Repayment_Schedule] (
    schedule_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    facility_id       BIGINT           NOT NULL,
    installment_no    INT              NOT NULL,
    due_date          DATE             NOT NULL,
    principal_amount  DECIMAL(18,2)    NOT NULL,
    interest_amount   DECIMAL(18,2)    NOT NULL,
    total_due         DECIMAL(18,2)    NOT NULL,
    remaining_balance DECIMAL(18,2)    NOT NULL,
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Schedule_Facility FOREIGN KEY (facility_id) REFERENCES [dbo].[Loan_Facility](facility_id)
);
GO

-- 7. Loan_Payment
CREATE TABLE [dbo].[Loan_Payment] (
    payment_id        BIGINT IDENTITY(1,1) PRIMARY KEY,
    facility_id       BIGINT           NOT NULL,
    schedule_id       BIGINT           NULL,
    payment_date      DATE             NOT NULL,
    amount_paid       DECIMAL(18,2)    NOT NULL,
    principal_paid    DECIMAL(18,2)    NULL,
    interest_paid     DECIMAL(18,2)    NULL,
    payment_method    NVARCHAR(50)     NULL,
    status            NVARCHAR(50)     NULL,             -- 'paid', 'partial', 'late'
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Payment_Facility  FOREIGN KEY (facility_id)  REFERENCES [dbo].[Loan_Facility](facility_id),
    CONSTRAINT FK_Payment_Schedule  FOREIGN KEY (schedule_id)  REFERENCES [dbo].[Loan_Repayment_Schedule](schedule_id)
);
GO

-- 8. Loan_Delinquency
CREATE TABLE [dbo].[Loan_Delinquency] (
    delinquency_id    BIGINT IDENTITY(1,1) PRIMARY KEY,
    facility_id       BIGINT           NOT NULL,
    as_of_date        DATE             NOT NULL,
    days_past_due     INT              NOT NULL,
    overdue_amount    DECIMAL(18,2)    NULL,
    risk_bucket       NVARCHAR(20)     NULL,             -- 'Current', '1-30', '31-60', '61-90', '90+'
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Delinquency_Facility FOREIGN KEY (facility_id) REFERENCES [dbo].[Loan_Facility](facility_id)
);
GO

-- 9. Alert
CREATE TABLE [dbo].[Alert] (
    alert_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    facility_id       BIGINT           NULL,
    customer_id       BIGINT           NULL,
    alert_type        NVARCHAR(50)     NOT NULL,         -- 'high_pd', 'delinquency', 'overdue'
    severity          NVARCHAR(20)     NOT NULL,         -- 'low', 'medium', 'high'
    message           NVARCHAR(500)    NULL,
    is_resolved       BIT              NOT NULL DEFAULT 0,
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    resolved_at       DATETIME2        NULL,

    CONSTRAINT FK_Alert_Facility  FOREIGN KEY (facility_id) REFERENCES [dbo].[Loan_Facility](facility_id),
    CONSTRAINT FK_Alert_Customer  FOREIGN KEY (customer_id) REFERENCES [dbo].[Customer](customer_id)
);
GO

-- 10. FINANCIAL_INDICATOR
CREATE TABLE [dbo].[FINANCIAL_INDICATOR] (
    indicator_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id       BIGINT           NOT NULL,
    debt_to_income    DECIMAL(10,4)    NULL,
    monthly_expense   DECIMAL(18,2)    NULL,
    asset_value       DECIMAL(18,2)    NULL,
    updated_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Financial_Customer FOREIGN KEY (customer_id) REFERENCES [dbo].[Customer](customer_id)
);
GO

-- 11. LINEAR_MODEL
CREATE TABLE [dbo].[LINEAR_MODEL] (
    model_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    model_name        NVARCHAR(100)    NOT NULL,
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    r_squared         DECIMAL(10,6)    NULL,
    mse               DECIMAL(18,6)    NULL
);
GO

-- 12. REGRESSION_COEFFICIENT
CREATE TABLE [dbo].[REGRESSION_COEFFICIENT] (
    coefficient_id    BIGINT IDENTITY(1,1) PRIMARY KEY,
    model_id          BIGINT           NOT NULL,
    feature_name      NVARCHAR(100)    NOT NULL,
    beta_value        DECIMAL(18,6)    NOT NULL,

    CONSTRAINT FK_Coefficient_Model FOREIGN KEY (model_id) REFERENCES [dbo].[LINEAR_MODEL](model_id)
);
GO

-- 13. RISK_PREDICTION
CREATE TABLE [dbo].[RISK_PREDICTION] (
    prediction_id     BIGINT IDENTITY(1,1) PRIMARY KEY,
    application_id    BIGINT           NULL,
    customer_id       BIGINT           NULL,
    model_id          BIGINT           NULL,
    risk_score        DECIMAL(10,6)    NOT NULL,
    risk_level        NVARCHAR(20)     NULL,             -- 'low', 'medium', 'high'
    predicted_at      DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Prediction_Application FOREIGN KEY (application_id) REFERENCES [dbo].[Loan_Application](application_id),
    CONSTRAINT FK_Prediction_Customer    FOREIGN KEY (customer_id)    REFERENCES [dbo].[Customer](customer_id),
    CONSTRAINT FK_Prediction_Model       FOREIGN KEY (model_id)       REFERENCES [dbo].[LINEAR_MODEL](model_id)
);
GO

-- 14. SHAP_Explanation
CREATE TABLE [dbo].[SHAP_Explanation] (
    explain_id        BIGINT IDENTITY(1,1) PRIMARY KEY,
    prediction_id     BIGINT           NOT NULL,
    feature_name      NVARCHAR(100)    NOT NULL,
    shap_value        DECIMAL(18,6)    NOT NULL,
    contribution_type NVARCHAR(20)     NULL,             -- 'positive', 'negative'
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_SHAP_Prediction FOREIGN KEY (prediction_id) REFERENCES [dbo].[RISK_PREDICTION](prediction_id)
);
GO

-- 15. Chat_History
CREATE TABLE [dbo].[Chat_History] (
    chat_id           BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id           BIGINT           NOT NULL,
    message           NVARCHAR(MAX)    NOT NULL,
    bot_response      NVARCHAR(MAX)    NULL,
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Chat_User FOREIGN KEY (user_id) REFERENCES [dbo].[User](user_id)
);
GO

-- 16. Model_Version
CREATE TABLE [dbo].[Model_Version] (
    model_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    model_name        NVARCHAR(100)    NOT NULL,
    version_tag       NVARCHAR(50)     NOT NULL,         -- 'v1.2.3'
    training_date     DATE             NULL,
    is_active         BIT              NOT NULL DEFAULT 1,
    metrics_json      NVARCHAR(MAX)    NULL,             -- JSON lưu AUC, KS, Gini, etc.
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- 17. Portfolio_Snapshot
CREATE TABLE [dbo].[Portfolio_Snapshot] (
    snapshot_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    snapshot_date     DATE             NOT NULL,
    total_exposure    DECIMAL(20,2)    NULL,
    npl_ratio         DECIMAL(10,4)    NULL,
    total_npl         DECIMAL(20,2)    NULL,
    avg_credit_score  DECIMAL(10,2)    NULL,
    created_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- 18. Audit_Log (cơ bản)
CREATE TABLE [dbo].[Audit_Log] (
    audit_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id           BIGINT           NULL,
    action            NVARCHAR(50)     NOT NULL,         -- 'INSERT', 'UPDATE', 'DELETE'
    entity_type       NVARCHAR(100)    NOT NULL,
    entity_id         BIGINT           NULL,
    old_value         NVARCHAR(MAX)    NULL,
    new_value         NVARCHAR(MAX)    NULL,
    performed_at      DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Audit_User FOREIGN KEY (user_id) REFERENCES [dbo].[User](user_id)
);
GO