ALTER TABLE `User` ADD COLUMN `rejection_reason` VARCHAR(500) NULL DEFAULT NULL AFTER `approved_at`;
