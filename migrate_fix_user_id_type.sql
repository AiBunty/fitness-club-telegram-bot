-- SQL Migration: Fix user_id Type for Telegram ID Support
-- Issue: INT (32-bit) overflows with large Telegram IDs (10+ digits = 64-bit)
-- Solution: Convert user_id to BIGINT (64-bit) to support Telegram IDs up to 9,223,372,036,854,775,807

SET foreign_key_checks = 0;

-- Backup current data (if needed)
-- CREATE TABLE users_backup AS SELECT * FROM users;

-- Convert user_id to BIGINT
ALTER TABLE users MODIFY COLUMN user_id BIGINT NOT NULL;

-- Verify other tables reference user_id correctly
ALTER TABLE daily_logs MODIFY COLUMN user_id BIGINT NOT NULL;
ALTER TABLE points_transactions MODIFY COLUMN user_id BIGINT NOT NULL;
ALTER TABLE shake_requests MODIFY COLUMN user_id BIGINT NOT NULL;
ALTER TABLE attendance_queue MODIFY COLUMN user_id BIGINT NOT NULL;
ALTER TABLE meal_photos MODIFY COLUMN user_id BIGINT NOT NULL;
ALTER TABLE shake_credits MODIFY COLUMN user_id BIGINT NOT NULL;

-- Verify invoices table (if exists)
-- ALTER TABLE invoices MODIFY COLUMN user_id BIGINT;
-- ALTER TABLE invoice_items MODIFY COLUMN user_id BIGINT;

-- Verify foreign key constraints still exist
ALTER TABLE daily_logs 
  ADD CONSTRAINT fk_daily_logs_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

SET foreign_key_checks = 1;

-- Verify the fix
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'user_id';

-- Output: Should show "user_id | bigint | NO"
