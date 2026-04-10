-- ======================================================================
-- CREDIT RISK MANAGEMENT SYSTEM - CANONICAL MySQL Database Schema (v1.0)
-- Single MySQL source of truth for schema import and ERD generation
-- Keep foreign keys unique here to avoid duplicate relationships in diagrams
-- Converted from SQL Server 2025 to MySQL 8.0+
-- ======================================================================
-- Purpose: Complete schema for credit risk assessment and loan management
-- Target DB: MySQL 8.0+ with utf8mb4 collation
-- Created: Feb 26, 2025
-- ======================================================================

-- ======================================================================
-- DATABASE TARGET (RAILWAY DEPLOY SAFE)
-- ======================================================================
-- Railway usually provides a pre-created database/schema via DATABASE_URL.
-- Do NOT run DROP/CREATE DATABASE in Railway SQL editor.
-- Run this script against the selected target database directly.
-- Optional for local/manual execution:
--   CREATE DATABASE IF NOT EXISTS CreditRiskDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--   USE CreditRiskDB;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ======================================================================
-- CLEAN SLATE (RERUN SAFE)
-- ======================================================================
DROP TABLE IF EXISTS `Portfolio_Risk_Summary`;
DROP TABLE IF EXISTS `Portfolio_Snapshot`;
DROP TABLE IF EXISTS `Audit_Log`;
DROP TABLE IF EXISTS `Chat_History`;
DROP TABLE IF EXISTS `Chat_Session`;
DROP TABLE IF EXISTS `Model_Version`;
DROP TABLE IF EXISTS `SHAP_Explanation`;
DROP TABLE IF EXISTS `RISK_PREDICTION`;
DROP TABLE IF EXISTS `REGRESSION_COEFFICIENT`;
DROP TABLE IF EXISTS `LINEAR_MODEL`;
DROP TABLE IF EXISTS `Loan_Approval_Limit`;
DROP TABLE IF EXISTS `Loan_Pricing_Rule`;
DROP TABLE IF EXISTS `Loan_Product_Requirement`;
DROP TABLE IF EXISTS `Loan_Product`;
DROP TABLE IF EXISTS `Monthly_Delinquency`;
DROP TABLE IF EXISTS `Transaction_Log`;
DROP TABLE IF EXISTS `Alert`;
DROP TABLE IF EXISTS `Provision_Allocation`;
DROP TABLE IF EXISTS `Loan_Status_Migration`;
DROP TABLE IF EXISTS `Loan_Delinquency`;
DROP TABLE IF EXISTS `Loan_Payment`;
DROP TABLE IF EXISTS `Loan_Repayment_Schedule`;
DROP TABLE IF EXISTS `Loan_Classification`;
DROP TABLE IF EXISTS `Loan_Facility`;
DROP TABLE IF EXISTS `Risk_Group`;
DROP TABLE IF EXISTS `Loan_Application`;
DROP TABLE IF EXISTS `Customer_Payment_Statistics`;
DROP TABLE IF EXISTS `FINANCIAL_INDICATOR`;
DROP TABLE IF EXISTS `Customer_Employment`;
DROP TABLE IF EXISTS `Customer`;
DROP TABLE IF EXISTS `User`;
DROP TABLE IF EXISTS `Role`;

-- ======================================================================
-- SQL SERVER CONNECTION CONFIGURATION (COMMENTED FOR REFERENCE)
-- ======================================================================
-- To use SQL Server 2025 instead, configure in app connection:
-- 
-- # For .NET/Python applications:
-- SQLSERVER_CONNECTION = "Server=<your-server>;Database=CreditRiskDB;User Id=<user>;Password=<password>;"
-- 
-- # For direct SQL Server execution:
-- USE [CreditRiskDB]
-- GO
-- COLLATE SQL_Latin1_General_CP1_CI_AS
-- 
-- This schema is now compatible with MySQL 8.0+
-- ======================================================================

-- ======================================================================
-- CORE TABLES: Role & User Management
-- ======================================================================

CREATE TABLE `Role` (
  `role_id` INT NOT NULL,
  `role_name` VARCHAR(50) NOT NULL,
  `description` VARCHAR(500) NULL,
  PRIMARY KEY (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `User` (
  `user_id` BIGINT NOT NULL AUTO_INCREMENT,
  `role_id` INT NULL,
  `username` VARCHAR(100) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `email` VARCHAR(150) NULL,
  `full_name` VARCHAR(150) NULL,
  `phone` VARCHAR(20) NULL,
  `avatar_path` VARCHAR(255) NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
  `user_type` VARCHAR(20) NULL,
  `verification_token` VARCHAR(255) NULL,
  `verification_sent_at` DATETIME(6) NULL,
  `is_email_verified` BOOLEAN NOT NULL DEFAULT FALSE,
  `approved_by` BIGINT NULL,
  `approved_at` DATETIME(6) NULL,
  `rejection_reason` VARCHAR(500) NULL,
  `is_active` BOOLEAN DEFAULT TRUE,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NULL ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`user_id`),
  CONSTRAINT `FK_User_Role` FOREIGN KEY (`role_id`) REFERENCES `Role` (`role_id`),
  CONSTRAINT `FK_User_ApprovedBy` FOREIGN KEY (`approved_by`) REFERENCES `User` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- CORE TABLES: Customer & Lending
-- ======================================================================

CREATE TABLE `Customer` (
  `customer_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NULL,
  `external_customer_ref` VARCHAR(50) NULL,
  `full_name` VARCHAR(150) NOT NULL,
  `date_of_birth` DATE NULL,
  `gender` VARCHAR(20) NULL,
  `national_id` VARCHAR(20) NULL,
  `id_issue_date` DATE NULL,
  `id_issue_place` VARCHAR(255) NULL,
  `nationality` VARCHAR(100) NULL,
  `marital_status` VARCHAR(50) NULL,
  `phone_number` VARCHAR(20) NULL,
  `email` VARCHAR(255) NULL,
  `permanent_address` VARCHAR(500) NULL,
  `current_address` VARCHAR(500) NULL,
  `occupation` VARCHAR(100) NULL,
  `age` INT NULL,
  `monthly_income` DECIMAL(18, 2) NULL,
  `credit_score` INT NULL,
  `employment_status` VARCHAR(50) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NULL ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`customer_id`),
  CONSTRAINT `FK_Customer_User` FOREIGN KEY (`user_id`) REFERENCES `User` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Customer_Employment` (
  `employment_id` BIGINT NOT NULL AUTO_INCREMENT,
  `customer_id` BIGINT NOT NULL,
  `company_name` VARCHAR(200) NULL,
  `position` VARCHAR(100) NULL,
  `years_of_experience` INT NULL,
  `monthly_income` DECIMAL(18, 2) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`employment_id`),
  CONSTRAINT `FK_Employment_Customer` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `FINANCIAL_INDICATOR` (
  `indicator_id` BIGINT NOT NULL AUTO_INCREMENT,
  `customer_id` BIGINT NOT NULL,
  `debt_to_income` DECIMAL(10, 4) NULL,
  `monthly_expense` DECIMAL(18, 2) NULL,
  `asset_value` DECIMAL(18, 2) NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`indicator_id`),
  CONSTRAINT `FK_Financial_Customer` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Customer_Payment_Statistics` (
  `stat_id` BIGINT NOT NULL AUTO_INCREMENT,
  `customer_id` BIGINT NOT NULL,
  `total_facilities` INT NULL,
  `total_outstanding` DECIMAL(20, 2) NULL,
  `average_on_time_rate` DECIMAL(5, 2) NULL,
  `total_violations` INT NULL,
  `highest_risk_group` VARCHAR(20) NULL,
  `facilities_upgraded_last_month` INT NULL,
  `facilities_downgraded_last_month` INT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`stat_id`),
  CONSTRAINT `FK_CustStats_Customer` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- CORE TABLES: Loan Application & Risk Classification
-- ======================================================================

CREATE TABLE `Loan_Application` (
  `application_id` BIGINT NOT NULL AUTO_INCREMENT,
  `application_ref_no` VARCHAR(50) NULL,
  `customer_id` BIGINT NOT NULL,
  `source_department_code` VARCHAR(30) NULL,
  `source_branch_code` VARCHAR(30) NULL,
  `application_date` DATE NULL,
  `loan_amount` DECIMAL(18, 2) NOT NULL,
  `loan_term` INT NOT NULL,
  `interest_rate` DECIMAL(10, 4) NULL,
  `loan_status` VARCHAR(50) NOT NULL,
  `loan_purpose` VARCHAR(200) NULL,
  `loan_type` VARCHAR(50) NULL,
  `collateral_id` VARCHAR(50) NULL,
  `collateral_value` DECIMAL(18, 2) NULL,
  `template_version` VARCHAR(20) NULL,
  `upload_batch_id` VARCHAR(64) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`application_id`),
  CONSTRAINT `FK_Application_Customer` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Risk Group: Danh mÃƒÂ¡Ã‚Â»Ã‚Â¥c phÃƒÆ’Ã‚Â¢n loÃƒÂ¡Ã‚ÂºÃ‚Â¡i rÃƒÂ¡Ã‚Â»Ã‚Â§i ro (1=Safe, 2=Fair, 3=Watch, 4=Default)
CREATE TABLE `Risk_Group` (
  `group_id` INT NOT NULL,
  `group_name` VARCHAR(100) NOT NULL,
  `group_name_en` VARCHAR(100) NULL,
  `description` LONGTEXT NULL,
  `description_vn` LONGTEXT NULL,
  `days_from` INT NOT NULL,
  `days_to` INT NOT NULL,
  `risk_level` VARCHAR(50) NOT NULL,
  `provision_rate` NUMERIC(5, 2) NOT NULL,
  `color` VARCHAR(20) NULL,
  `icon` VARCHAR(50) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NULL ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`group_id`),
  UNIQUE KEY `UQ_RiskGroup_GroupName` (`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- REVISED LOGIC: Loan_Application now has direct risk classification
-- Instead of routing through Loan_Facility -> Customer relationship
-- Customer submits Loan_Application -> System classifies directly using Risk_Group
-- ======================================================================

CREATE TABLE `Loan_Facility` (
  `facility_id` BIGINT NOT NULL AUTO_INCREMENT,
  `application_id` BIGINT NULL,
  `customer_id` BIGINT NOT NULL,
  `facility_type` VARCHAR(50) NULL,
  `approved_amount` DECIMAL(18, 2) NOT NULL,
  `interest_rate` DECIMAL(10, 4) NULL,
  `start_date` DATE NULL,
  `end_date` DATE NULL,
  `status` VARCHAR(50) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`facility_id`),
  CONSTRAINT `FK_Facility_Application` FOREIGN KEY (`application_id`) REFERENCES `Loan_Application` (`application_id`),
  CONSTRAINT `FK_Facility_Customer` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Loan_Classification: PhÃƒÆ’Ã‚Â¢n loÃƒÂ¡Ã‚ÂºÃ‚Â¡i trÃƒÂ¡Ã‚Â»Ã‚Â±c tiÃƒÂ¡Ã‚ÂºÃ‚Â¿p tÃƒÂ¡Ã‚Â»Ã‚Â« Loan_Application
CREATE TABLE `Loan_Classification` (
  `classification_id` BIGINT NOT NULL AUTO_INCREMENT,
  `application_id` BIGINT NULL,
  `facility_id` BIGINT NULL,
  `group_id` INT NOT NULL,
  `classification_type` VARCHAR(30) NOT NULL DEFAULT 'application',
  `days_overdue` INT NOT NULL,
  `outstanding_principal` NUMERIC(18, 2) NULL,
  `provision_amount` NUMERIC(18, 2) NULL,
  `classification_status` VARCHAR(50) NOT NULL DEFAULT 'active',
  `classified_by` BIGINT NULL,
  `classified_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NULL ON UPDATE CURRENT_TIMESTAMP(6),
  `notes` LONGTEXT NULL,
  PRIMARY KEY (`classification_id`),
  CONSTRAINT `FK_LoanClassification_Application` FOREIGN KEY (`application_id`) REFERENCES `Loan_Application` (`application_id`),
  CONSTRAINT `FK_LoanClassification_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`),
  CONSTRAINT `FK_LoanClassification_RiskGroup` FOREIGN KEY (`group_id`) REFERENCES `Risk_Group` (`group_id`),
  CONSTRAINT `CK_LoanClassification_Type`
    CHECK (`classification_type` IN ('application', 'facility')),
  CONSTRAINT `CK_LoanClassification_Target`
    CHECK (
      (`classification_type` = 'application' AND `application_id` IS NOT NULL AND `facility_id` IS NULL)
      OR
      (`classification_type` = 'facility' AND `facility_id` IS NOT NULL AND `application_id` IS NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Loan_Repayment_Schedule` (
  `schedule_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NOT NULL,
  `installment_no` INT NOT NULL,
  `due_date` DATE NOT NULL,
  `principal_amount` DECIMAL(18, 2) NOT NULL,
  `interest_amount` DECIMAL(18, 2) NOT NULL,
  `total_due` DECIMAL(18, 2) NOT NULL,
  `remaining_balance` DECIMAL(18, 2) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`schedule_id`),
  CONSTRAINT `FK_Schedule_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Loan_Payment` (
  `payment_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NOT NULL,
  `schedule_id` BIGINT NULL,
  `payment_date` DATE NOT NULL,
  `amount_paid` DECIMAL(18, 2) NOT NULL,
  `principal_paid` DECIMAL(18, 2) NULL,
  `interest_paid` DECIMAL(18, 2) NULL,
  `payment_method` VARCHAR(50) NULL,
  `status` VARCHAR(50) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`payment_id`),
  CONSTRAINT `FK_Payment_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`),
  CONSTRAINT `FK_Payment_Schedule` FOREIGN KEY (`schedule_id`) REFERENCES `Loan_Repayment_Schedule` (`schedule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Loan_Delinquency` (
  `delinquency_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NOT NULL,
  `as_of_date` DATE NOT NULL,
  `days_past_due` INT NOT NULL,
  `overdue_amount` DECIMAL(18, 2) NULL,
  `risk_bucket` VARCHAR(20) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`delinquency_id`),
  CONSTRAINT `FK_Delinquency_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Loan_Status_Migration` (
  `migration_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NOT NULL,
  `from_group` VARCHAR(20) NULL,
  `to_group` VARCHAR(20) NOT NULL,
  `migration_date` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `reason` VARCHAR(500) NULL,
  PRIMARY KEY (`migration_id`),
  CONSTRAINT `FK_Migration_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Provision_Allocation` (
  `provision_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NOT NULL,
  `risk_group_id` INT NOT NULL,
  `outstanding_amount` NUMERIC(18, 2) NOT NULL,
  `provision_rate` NUMERIC(5, 2) NOT NULL,
  `provision_amount` NUMERIC(18, 2) NOT NULL,
  `allocation_period` VARCHAR(20) NOT NULL,
  `allocation_date` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `is_released` INT NULL,
  `release_date` DATETIME(6) NULL,
  `allocated_by` BIGINT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NULL ON UPDATE CURRENT_TIMESTAMP(6),
  `notes` LONGTEXT NULL,
  PRIMARY KEY (`provision_id`),
  CONSTRAINT `FK_ProvisionAllocation_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`),
  CONSTRAINT `FK_ProvisionAllocation_RiskGroup` FOREIGN KEY (`risk_group_id`) REFERENCES `Risk_Group` (`group_id`),
  CONSTRAINT `FK_ProvisionAllocation_User` FOREIGN KEY (`allocated_by`) REFERENCES `User` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Alert` (
  `alert_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NULL,
  `customer_id` BIGINT NULL,
  `alert_type` VARCHAR(50) NOT NULL,
  `severity` VARCHAR(20) NOT NULL,
  `message` VARCHAR(500) NULL,
  `is_resolved` BOOLEAN NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `resolved_at` DATETIME(6) NULL,
  PRIMARY KEY (`alert_id`),
  CONSTRAINT `FK_Alert_Customer` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`),
  CONSTRAINT `FK_Alert_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Transaction_Log` (
  `log_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NOT NULL,
  `transaction_type` VARCHAR(50) NULL,
  `amount` DECIMAL(18, 2) NULL,
  `description` VARCHAR(500) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`log_id`),
  CONSTRAINT `FK_Transaction_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Monthly_Delinquency` (
  `snapshot_id` BIGINT NOT NULL AUTO_INCREMENT,
  `facility_id` BIGINT NOT NULL,
  `snapshot_month` DATE NOT NULL,
  `days_past_due` INT NOT NULL,
  `risk_group` VARCHAR(20) NULL,
  `principal_overdue` DECIMAL(18, 2) NULL,
  `interest_overdue` DECIMAL(18, 2) NULL,
  `total_overdue` DECIMAL(18, 2) NULL,
  `on_time_payment_rate` DECIMAL(5, 2) NULL,
  `violation_count` INT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`snapshot_id`),
  CONSTRAINT `FK_Monthly_Delinquency_Facility` FOREIGN KEY (`facility_id`) REFERENCES `Loan_Facility` (`facility_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- CORE TABLES: Product Policy
-- ======================================================================

CREATE TABLE `Loan_Product` (
  `product_id` INT NOT NULL AUTO_INCREMENT,
  `product_code` VARCHAR(20) NOT NULL UNIQUE,
  `product_name` VARCHAR(100) NOT NULL,
  `product_name_en` VARCHAR(100) NOT NULL,
  `category` VARCHAR(20) NOT NULL,
  `min_amount` NUMERIC(18, 0) NOT NULL,
  `max_amount` NUMERIC(18, 0) NOT NULL,
  `min_term_months` INT NOT NULL,
  `max_term_months` INT NOT NULL,
  `min_interest_rate` NUMERIC(5, 2) NOT NULL,
  `max_interest_rate` NUMERIC(5, 2) NOT NULL,
  `typical_interest_rate` NUMERIC(5, 2) NULL,
  `promotion_interest_rate` NUMERIC(5, 2) NULL,
  `collateral_required` BOOLEAN NULL,
  `collateral_type` VARCHAR(50) NULL,
  `ltv_ratio` NUMERIC(5, 2) NULL,
  `max_dti_ratio` NUMERIC(5, 2) NOT NULL,
  `min_credit_score` INT NOT NULL,
  `processing_time_days` INT NOT NULL,
  `approval_authority` VARCHAR(50) NOT NULL,
  `description` LONGTEXT NULL,
  `eligible_customers` VARCHAR(500) NULL,
  `required_documents` LONGTEXT NULL,
  `risk_factors` LONGTEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` BOOLEAN NOT NULL,
  PRIMARY KEY (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Loan_Product_Requirement` (
  `requirement_id` INT NOT NULL AUTO_INCREMENT,
  `product_id` INT NOT NULL,
  `requirement_type` VARCHAR(50) NOT NULL,
  `requirement_code` VARCHAR(50) NOT NULL,
  `requirement_name` VARCHAR(200) NOT NULL,
  `requirement_description` LONGTEXT NULL,
  `is_mandatory` BOOLEAN NULL,
  `minimum_value` NUMERIC(18, 2) NULL,
  `maximum_value` NUMERIC(18, 2) NULL,
  `document_type` VARCHAR(100) NULL,
  `collateral_category` VARCHAR(50) NULL,
  `effective_from` DATETIME NOT NULL,
  `effective_to` DATETIME NULL,
  `is_active` BOOLEAN NOT NULL,
  PRIMARY KEY (`requirement_id`),
  CONSTRAINT `FK_ProductRequirement_Product` FOREIGN KEY (`product_id`) REFERENCES `Loan_Product` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Loan_Pricing_Rule` (
  `rule_id` INT NOT NULL AUTO_INCREMENT,
  `product_id` INT NOT NULL,
  `customer_type` VARCHAR(50) NOT NULL,
  `credit_score_min` INT NOT NULL,
  `credit_score_max` INT NOT NULL,
  `base_interest_rate` NUMERIC(5, 2) NOT NULL,
  `risk_premium` NUMERIC(5, 2) NOT NULL,
  `final_interest_rate` NUMERIC(5, 2) NOT NULL,
  `loyalty_discount` NUMERIC(5, 2) NULL,
  `early_repayment_discount` NUMERIC(5, 2) NULL,
  `effective_from` DATETIME NOT NULL,
  `effective_to` DATETIME NULL,
  `is_active` BOOLEAN NOT NULL,
  PRIMARY KEY (`rule_id`),
  CONSTRAINT `FK_PricingRule_Product` FOREIGN KEY (`product_id`) REFERENCES `Loan_Product` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Loan_Approval_Limit` (
  `limit_id` INT NOT NULL AUTO_INCREMENT,
  `product_id` INT NOT NULL,
  `approval_level` VARCHAR(50) NOT NULL,
  `min_approval_amount` NUMERIC(18, 0) NOT NULL,
  `max_approval_amount` NUMERIC(18, 0) NOT NULL,
  `min_customer_credit_score` INT NOT NULL,
  `max_dti_ratio` NUMERIC(5, 2) NOT NULL,
  `required_documents` LONGTEXT NULL,
  `max_processing_days` INT NOT NULL,
  `is_active` BOOLEAN NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`limit_id`),
  CONSTRAINT `FK_ApprovalLimit_Product` FOREIGN KEY (`product_id`) REFERENCES `Loan_Product` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- CORE TABLES: Risk/ML Model
-- ======================================================================

CREATE TABLE `LINEAR_MODEL` (
  `model_id` BIGINT NOT NULL AUTO_INCREMENT,
  `model_name` VARCHAR(100) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `r_squared` DECIMAL(10, 6) NULL,
  `mse` DECIMAL(18, 6) NULL,
  `version_tag` VARCHAR(50) NULL,
  `is_active` BOOLEAN NULL,
  PRIMARY KEY (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `REGRESSION_COEFFICIENT` (
  `coefficient_id` BIGINT NOT NULL AUTO_INCREMENT,
  `model_id` BIGINT NOT NULL,
  `feature_name` VARCHAR(100) NOT NULL,
  `beta_value` DECIMAL(18, 6) NOT NULL,
  PRIMARY KEY (`coefficient_id`),
  CONSTRAINT `FK_Coefficient_Model` FOREIGN KEY (`model_id`) REFERENCES `LINEAR_MODEL` (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `RISK_PREDICTION` (
  `prediction_id` BIGINT NOT NULL AUTO_INCREMENT,
  `application_id` BIGINT NULL,
  `customer_id` BIGINT NULL,
  `model_id` BIGINT NULL,
  `risk_score` DECIMAL(10, 6) NOT NULL,
  `risk_level` VARCHAR(20) NULL,
  `predicted_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`prediction_id`),
  CONSTRAINT `FK_Prediction_Application` FOREIGN KEY (`application_id`) REFERENCES `Loan_Application` (`application_id`),
  CONSTRAINT `FK_Prediction_Customer` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`customer_id`),
  CONSTRAINT `FK_Prediction_Model` FOREIGN KEY (`model_id`) REFERENCES `LINEAR_MODEL` (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `SHAP_Explanation` (
  `explanation_id` BIGINT NOT NULL AUTO_INCREMENT,
  `prediction_id` BIGINT NOT NULL,
  `feature_name` VARCHAR(100) NULL,
  `shap_value` DECIMAL(18, 6) NULL,
  `feature_value` VARCHAR(500) NULL,
  PRIMARY KEY (`explanation_id`),
  CONSTRAINT `FK_SHAP_Prediction` FOREIGN KEY (`prediction_id`) REFERENCES `RISK_PREDICTION` (`prediction_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Model_Version` (
  `model_id` BIGINT NOT NULL AUTO_INCREMENT,
  `model_name` VARCHAR(100) NOT NULL,
  `version_tag` VARCHAR(50) NOT NULL,
  `training_date` DATE NULL,
  `is_active` BOOLEAN NOT NULL,
  `metrics_json` LONGTEXT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- CORE TABLES: Chat & Support
-- ======================================================================

CREATE TABLE `Chat_Session` (
  `session_id` CHAR(36) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `last_interaction` DATETIME(6) NULL ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`session_id`),
  CONSTRAINT `FK_Session_User` FOREIGN KEY (`user_id`) REFERENCES `User` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Chat_History` (
  `chat_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `message` LONGTEXT NOT NULL,
  `bot_response` LONGTEXT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `session_id` CHAR(36) NULL,
  PRIMARY KEY (`chat_id`),
  CONSTRAINT `FK_Chat_Session` FOREIGN KEY (`session_id`) REFERENCES `Chat_Session` (`session_id`),
  CONSTRAINT `FK_Chat_User` FOREIGN KEY (`user_id`) REFERENCES `User` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Audit_Log` (
  `audit_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NULL,
  `action` VARCHAR(50) NOT NULL,
  `entity_type` VARCHAR(100) NOT NULL,
  `entity_id` BIGINT NULL,
  `old_value` LONGTEXT NULL,
  `new_value` LONGTEXT NULL,
  `performed_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`audit_id`),
  CONSTRAINT `FK_Audit_User` FOREIGN KEY (`user_id`) REFERENCES `User` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- PORTFOLIO AGGREGATION TABLES (REPORTING)
-- ======================================================================

CREATE TABLE `Portfolio_Snapshot` (
  `snapshot_id` BIGINT NOT NULL AUTO_INCREMENT,
  `snapshot_date` DATE NOT NULL,
  `total_exposure` DECIMAL(20, 2) NULL,
  `npl_ratio` DECIMAL(10, 4) NULL,
  `total_npl` DECIMAL(20, 2) NULL,
  `avg_credit_score` DECIMAL(10, 2) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`snapshot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `Portfolio_Risk_Summary` (
  `summary_id` BIGINT NOT NULL AUTO_INCREMENT,
  `summary_date` DATE NOT NULL,
  `total_facilities` INT NULL,
  `group_1_count` INT NULL,
  `group_2_count` INT NULL,
  `group_3_count` INT NULL,
  `group_4_count` INT NULL,
  `total_outstanding` DECIMAL(20, 2) NULL,
  `group_3_4_outstanding` DECIMAL(20, 2) NULL,
  `npl_ratio` DECIMAL(5, 2) NULL,
  `par_30` DECIMAL(5, 2) NULL,
  `par_90` DECIMAL(5, 2) NULL,
  `on_time_payment_rate` DECIMAL(5, 2) NULL,
  `migrated_to_group_2` INT NULL,
  `migrated_to_group_3` INT NULL,
  `migrated_to_group_4` INT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`summary_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================================================
-- INDEXES for Performance Optimization
-- ======================================================================

CREATE INDEX `idx_customer_user_id` ON `Customer` (`user_id`);
CREATE INDEX `idx_customer_employment_customer_id` ON `Customer_Employment` (`customer_id`);
CREATE INDEX `idx_financial_indicator_customer_id` ON `FINANCIAL_INDICATOR` (`customer_id`);
CREATE INDEX `idx_loan_application_customer_id` ON `Loan_Application` (`customer_id`);
CREATE INDEX `idx_loan_facility_customer_id` ON `Loan_Facility` (`customer_id`);
CREATE INDEX `idx_loan_facility_application_id` ON `Loan_Facility` (`application_id`);
CREATE INDEX `idx_loan_classification_application_id` ON `Loan_Classification` (`application_id`);
CREATE INDEX `idx_loan_classification_facility_id` ON `Loan_Classification` (`facility_id`);
CREATE INDEX `idx_loan_classification_group_id` ON `Loan_Classification` (`group_id`);
CREATE INDEX `idx_loan_repayment_facility_id` ON `Loan_Repayment_Schedule` (`facility_id`);
CREATE INDEX `idx_loan_payment_facility_id` ON `Loan_Payment` (`facility_id`);
CREATE INDEX `idx_loan_delinquency_facility_id` ON `Loan_Delinquency` (`facility_id`);
CREATE INDEX `idx_risk_prediction_customer_id` ON `RISK_PREDICTION` (`customer_id`);
CREATE INDEX `idx_risk_prediction_application_id` ON `RISK_PREDICTION` (`application_id`);
CREATE INDEX `idx_chat_session_user_id` ON `Chat_Session` (`user_id`);
CREATE INDEX `idx_chat_history_user_id` ON `Chat_History` (`user_id`);
CREATE INDEX `idx_chat_history_session_id` ON `Chat_History` (`session_id`);
CREATE INDEX `idx_audit_log_user_id` ON `Audit_Log` (`user_id`);

-- ======================================================================
-- INITIAL DATA SETUP: Risk Groups Reference Data
-- ======================================================================

INSERT INTO `Risk_Group` (`group_id`, `group_name`, `group_name_en`, `description`, `description_vn`, `days_from`, `days_to`, `risk_level`, `provision_rate`, `color`, `icon`) VALUES
(1, 'Nợ đủ tiêu chuẩn', 'Standard Loans', 'Within due date or overdue less than 10 days', 'Trong hạn hoặc quá hạn dưới 10 ngày', 0, 9, 'Rất thấp', 0.00, 'green', 'check_circle'),
(2, 'Nợ cần chú ý', 'Loans Requiring Attention', 'Overdue from 10 to less than 90 days', 'Quá hạn từ 10 ngày đến dưới 90 ngày', 10, 89, 'Thấp', 0.01, 'yellow', 'warning'),
(3, 'Nợ dưới tiêu chuẩn', 'Substandard Loans', 'Overdue from 91 to 180 days (Beginning of bad debt)', 'Quá hạn từ 91 đến 180 ngày (Bắt đầu là nợ xấu)', 91, 180, 'Trung bình cao', 0.25, 'orange', 'info'),
(4, 'Nợ nghi ngờ', 'Doubtful Loans', 'Overdue from 181 to 360 days', 'Quá hạn từ 181 đến 360 ngày', 181, 360, 'Cao', 0.50, 'red', 'error_outline'),
(5, 'Nợ có khả năng mất vốn', 'Loss Loans', 'Overdue over 360 days or unrecoverable', 'Quá hạn trên 360 ngày hoặc mất khả năng thu hồi', 361, 999999, 'Rất cao', 1.00, 'dark_red', 'cancel')
ON DUPLICATE KEY UPDATE
  `group_name` = VALUES(`group_name`),
  `group_name_en` = VALUES(`group_name_en`),
  `description` = VALUES(`description`),
  `description_vn` = VALUES(`description_vn`),
  `days_from` = VALUES(`days_from`),
  `days_to` = VALUES(`days_to`),
  `risk_level` = VALUES(`risk_level`),
  `provision_rate` = VALUES(`provision_rate`),
  `color` = VALUES(`color`),
  `icon` = VALUES(`icon`);

-- ======================================================================
-- INITIAL DATA SETUP: Roles Reference Data
-- ======================================================================

UPDATE `Role`
SET `role_name` = 'admin',
    `description` = 'System administrator with full access'
WHERE `role_id` = 1;

UPDATE `Role`
SET `role_name` = 'manager',
    `description` = 'Manager role for portfolio and approval workflow'
WHERE `role_id` = 2;

UPDATE `Role`
SET `role_name` = 'risk analyst',
    `description` = 'Risk analyst role for credit assessment and classification'
WHERE `role_id` = 3;

UPDATE `Role`
SET `role_name` = 'viewer',
    `description` = 'Read-only role for monitoring and reporting'
WHERE `role_id` = 4;

INSERT INTO `Role` (`role_id`, `role_name`, `description`)
SELECT 1, 'admin', 'System administrator with full access'
WHERE NOT EXISTS (SELECT 1 FROM `Role` WHERE `role_id` = 1);

INSERT INTO `Role` (`role_id`, `role_name`, `description`)
SELECT 2, 'manager', 'Manager role for portfolio and approval workflow'
WHERE NOT EXISTS (SELECT 1 FROM `Role` WHERE `role_id` = 2);

INSERT INTO `Role` (`role_id`, `role_name`, `description`)
SELECT 3, 'risk analyst', 'Risk analyst role for credit assessment and classification'
WHERE NOT EXISTS (SELECT 1 FROM `Role` WHERE `role_id` = 3);

INSERT INTO `Role` (`role_id`, `role_name`, `description`)
SELECT 4, 'viewer', 'Read-only role for monitoring and reporting'
WHERE NOT EXISTS (SELECT 1 FROM `Role` WHERE `role_id` = 4);

UPDATE `User`
SET `role_id` = 4
WHERE `role_id` IS NOT NULL
  AND `role_id` NOT IN (1, 2, 3, 4);

DELETE FROM `Role`
WHERE `role_id` NOT IN (1, 2, 3, 4);

-- ======================================================================
-- INITIAL DATA SETUP: Default Login Accounts
-- Viewer is a read-only reference role and does not require a default login
-- ======================================================================

INSERT INTO `User` (
  `role_id`,
  `username`,
  `password_hash`,
  `email`,
  `full_name`,
  `status`,
  `user_type`,
  `is_email_verified`,
  `approved_at`,
  `is_active`
) VALUES
(1, 'admin', 'Admin@123456', 'admin@creditrisk.local', 'System Admin', 'approved', 'admin', TRUE, CURRENT_TIMESTAMP(6), TRUE),
(2, 'manager', 'Manager@123456', 'manager@creditrisk.local', 'Portfolio Manager', 'approved', 'manager', TRUE, CURRENT_TIMESTAMP(6), TRUE),
(3, 'risk_analyst', 'RiskAnalyst@123456', 'risk.analyst@creditrisk.local', 'Risk Analyst', 'approved', 'analyst', TRUE, CURRENT_TIMESTAMP(6), TRUE)
ON DUPLICATE KEY UPDATE
  `role_id` = VALUES(`role_id`),
  `password_hash` = VALUES(`password_hash`),
  `email` = VALUES(`email`),
  `full_name` = VALUES(`full_name`),
  `status` = VALUES(`status`),
  `user_type` = VALUES(`user_type`),
  `is_email_verified` = VALUES(`is_email_verified`),
  `approved_at` = VALUES(`approved_at`),
  `is_active` = VALUES(`is_active`);

-- ======================================================================
-- END OF SCHEMA DEFINITION
-- Database is now ready for application initialization
-- ======================================================================

SET FOREIGN_KEY_CHECKS = 1;
