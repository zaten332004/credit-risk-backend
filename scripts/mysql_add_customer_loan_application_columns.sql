-- MySQL: add customer/application intake columns for batch loan uploads.
-- Safe to re-run: each column/index is created only if it does not already exist.

SET @db = DATABASE();

-- ============================================================================
-- Customer
-- ============================================================================

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'external_customer_ref'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `external_customer_ref` VARCHAR(50) NULL AFTER `user_id`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'date_of_birth'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `date_of_birth` DATE NULL AFTER `full_name`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'gender'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `gender` VARCHAR(20) NULL AFTER `date_of_birth`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'national_id'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `national_id` VARCHAR(20) NULL AFTER `gender`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'id_issue_date'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `id_issue_date` DATE NULL AFTER `national_id`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'id_issue_place'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `id_issue_place` VARCHAR(255) NULL AFTER `id_issue_date`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'nationality'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `nationality` VARCHAR(100) NULL AFTER `id_issue_place`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'marital_status'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `marital_status` VARCHAR(50) NULL AFTER `nationality`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'phone_number'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `phone_number` VARCHAR(20) NULL AFTER `marital_status`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'email'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `email` VARCHAR(255) NULL AFTER `phone_number`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'permanent_address'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `permanent_address` VARCHAR(500) NULL AFTER `email`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'current_address'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `current_address` VARCHAR(500) NULL AFTER `permanent_address`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND COLUMN_NAME = 'occupation'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Customer` ADD COLUMN `occupation` VARCHAR(100) NULL AFTER `current_address`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- Loan_Application
-- ============================================================================

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'application_ref_no'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `application_ref_no` VARCHAR(50) NULL AFTER `application_id`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'source_department_code'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `source_department_code` VARCHAR(30) NULL AFTER `customer_id`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'source_branch_code'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `source_branch_code` VARCHAR(30) NULL AFTER `source_department_code`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'application_date'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `application_date` DATE NULL AFTER `source_branch_code`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'loan_type'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `loan_type` VARCHAR(50) NULL AFTER `loan_purpose`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'collateral_id'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `collateral_id` VARCHAR(50) NULL AFTER `loan_type`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'collateral_value'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `collateral_value` DECIMAL(18, 2) NULL AFTER `collateral_id`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'template_version'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `template_version` VARCHAR(20) NULL AFTER `collateral_value`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND COLUMN_NAME = 'upload_batch_id'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Loan_Application` ADD COLUMN `upload_batch_id` VARCHAR(64) NULL AFTER `template_version`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- Backfill / indexes
-- ============================================================================

UPDATE `Loan_Application`
SET `application_date` = DATE(`created_at`)
WHERE `application_date` IS NULL
  AND `application_id` > 0;

SET @index_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND INDEX_NAME = 'IX_Customer_ExternalRef'
);
SET @sql := IF(
  @index_exists = 0,
  'CREATE INDEX `IX_Customer_ExternalRef` ON `Customer` (`external_customer_ref`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Customer' AND INDEX_NAME = 'IX_Customer_NationalId'
);
SET @sql := IF(
  @index_exists = 0,
  'CREATE INDEX `IX_Customer_NationalId` ON `Customer` (`national_id`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND INDEX_NAME = 'IX_Loan_Application_RefNo'
);
SET @sql := IF(
  @index_exists = 0,
  'CREATE INDEX `IX_Loan_Application_RefNo` ON `Loan_Application` (`application_ref_no`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND INDEX_NAME = 'IX_Loan_Application_Date'
);
SET @sql := IF(
  @index_exists = 0,
  'CREATE INDEX `IX_Loan_Application_Date` ON `Loan_Application` (`application_date`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Loan_Application' AND INDEX_NAME = 'IX_Loan_Application_UploadBatch'
);
SET @sql := IF(
  @index_exists = 0,
  'CREATE INDEX `IX_Loan_Application_UploadBatch` ON `Loan_Application` (`upload_batch_id`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
