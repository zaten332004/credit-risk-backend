-- ======================================================================
-- MIGRATION: Add avatar storage for user profiles
-- Apply this to the current CreditRiskDB without recreating the schema
-- ======================================================================

USE CreditRiskDB;

ALTER TABLE `User`
ADD COLUMN `avatar_path` VARCHAR(255) NULL AFTER `phone`;
