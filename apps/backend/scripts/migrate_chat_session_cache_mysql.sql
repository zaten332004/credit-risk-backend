-- MySQL: add AI chat session cache columns (matches SQLAlchemy ChatSessionDB / apps/backend/app/db/models.py)
-- Run once against your CRAI DB. Safe to re-run: skips if columns already exist.

SET @db = DATABASE();

-- data_context_cached
SET @exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Chat_Session' AND COLUMN_NAME = 'data_context_cached'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE `Chat_Session` ADD COLUMN `data_context_cached` LONGTEXT NULL AFTER `last_interaction`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- data_context_cached_at
SET @exists2 := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'Chat_Session' AND COLUMN_NAME = 'data_context_cached_at'
);
SET @sql2 := IF(
  @exists2 = 0,
  'ALTER TABLE `Chat_Session` ADD COLUMN `data_context_cached_at` DATETIME(6) NULL AFTER `data_context_cached`',
  'SELECT 1'
);
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;
