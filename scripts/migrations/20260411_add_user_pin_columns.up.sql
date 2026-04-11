ALTER TABLE `User`
    ADD COLUMN `pin_hash` VARCHAR(255) NULL,
    ADD COLUMN `pin_updated_at` DATETIME NULL;
