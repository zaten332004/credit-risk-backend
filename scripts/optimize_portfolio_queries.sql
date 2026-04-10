-- Optimization script for portfolio and risk queries
-- Thêm indexes để tối ưu hóa queries chậm

-- 1. Index cho Loan_Facility - thường được query bằng customer_id, status
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Loan_Facility_Customer_Status')
CREATE INDEX IX_Loan_Facility_Customer_Status ON Loan_Facility (customer_id, status)
INCLUDE (approved_amount, facility_id);

-- 2. Index cho Risk_Prediction - thường được group by risk_level
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Risk_Prediction_Level')
CREATE INDEX IX_Risk_Prediction_Level ON Risk_Prediction (risk_level)
INCLUDE (prediction_id, customer_id);

-- 3. Index cho Customer - dùng trong aggregations
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Customer_CreditScore')
CREATE INDEX IX_Customer_CreditScore ON Customer (customer_id, credit_score)
INCLUDE (full_name, monthly_income);

-- 4. Index cho Portfolio_Snapshot - dùng để lấy snapshot mới nhất
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Portfolio_Snapshot_Date')
CREATE INDEX IX_Portfolio_Snapshot_Date ON Portfolio_Snapshot (snapshot_date DESC)
INCLUDE (total_exposure, npl_ratio, total_npl);

-- 5. Index cho Chat_Session - cache lookup
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Chat_Session_User')
CREATE INDEX IX_Chat_Session_User ON Chat_Session (user_id)
INCLUDE (created_at, last_interaction, data_context_cached_at);

-- 6. Index cho Chat_History - history lookup
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Chat_History_Session')
CREATE INDEX IX_Chat_History_Session ON Chat_History (session_id, created_at DESC);

-- 7. Thêm constraint nếu cần: khóa ngoại cho Portfolio_Snapshot (nếu chưa có)
-- ALTER TABLE Portfolio_Snapshot ADD CONSTRAINT FK_Portfolio_Snapshot_Customer 
-- FOREIGN KEY (customer_id) REFERENCES Customer(customer_id);

PRINT 'Optimization indexes created successfully';
