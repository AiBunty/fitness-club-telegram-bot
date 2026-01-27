-- ============================================================================
-- STEP 1: Backup Cloud MySQL (MANDATORY)
-- ============================================================================
-- Execute via your hosting panel (e.g., StackCP, AWS RDS, or CLI):
--
-- For SSH/CLI dump (before running migrations):
--   mysqldump -h mysql.gb.stackcp.com -P 42152 -u FItnessBot-313935eecd -p \
--   FItnessBot-313935eecd > backup_pre_migration_$(date +%s).sql
--
-- For StackCP: Use web panel snapshot feature
--
-- ⚠️ DO NOT proceed without backup in place.
-- ============================================================================


-- ============================================================================
-- STEP 2a: Apply Migration 001 (Accounts Receivable Schema)
-- ============================================================================
-- Copy-paste from migrations/001_fix_ar_schema.sql into your MySQL client
-- Verify: No errors, tables created successfully
-- ============================================================================


-- ============================================================================
-- STEP 2b: Apply Migration 002 (Subscription Schema)
-- ============================================================================
-- Copy-paste from migrations/002_fix_subscription_schema.sql into your MySQL client
-- Verify: No errors, tables created successfully
-- ============================================================================


-- ============================================================================
-- STEP 3: Validate Schema
-- ============================================================================
-- Run these queries to confirm columns, PKs, FKs exist:

-- 3.1 Verify accounts_receivable structure
DESCRIBE accounts_receivable;
-- Expected columns: receivable_id, user_id, receivable_type, source_id, 
--                   bill_amount, discount_amount, final_amount, status, 
--                   due_date, created_at, updated_at

-- 3.2 Verify ar_transactions structure
DESCRIBE ar_transactions;
-- Expected columns: transaction_id, receivable_id, method, amount, reference, 
--                   created_by, created_at

-- 3.3 Verify subscription_requests structure
DESCRIBE subscription_requests;
-- Expected columns: id, user_id, plan_id, amount, payment_method, status, 
--                   fee_status, requested_at, approved_at, rejection_reason

-- 3.4 Verify subscriptions structure
DESCRIBE subscriptions;
-- Expected columns: id, user_id, plan_id, amount, start_date, end_date, status, 
--                   grace_period_end, created_at, updated_at

-- 3.5 Verify subscription_payments structure
DESCRIBE subscription_payments;
-- Expected columns: id, user_id, request_id, amount, payment_method, reference, 
--                   screenshot_file_id, status, paid_at, created_at

-- 3.6 Verify foreign keys
SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME IN ('accounts_receivable', 'ar_transactions', 'subscription_requests', 
                     'subscriptions', 'subscription_payments')
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- Expected:
-- fk_ar_user: accounts_receivable.user_id → users.user_id
-- fk_art_receivable: ar_transactions.receivable_id → accounts_receivable.receivable_id
-- fk_subr_user: subscription_requests.user_id → users.user_id
-- fk_sub_user: subscriptions.user_id → users.user_id
-- fk_subp_user: subscription_payments.user_id → users.user_id
-- fk_subp_request: subscription_payments.request_id → subscription_requests.id

-- 3.7 Verify tables are empty (expected post-migration)
SELECT 
  (SELECT COUNT(*) FROM accounts_receivable) AS ar_count,
  (SELECT COUNT(*) FROM ar_transactions) AS art_count,
  (SELECT COUNT(*) FROM subscription_requests) AS sr_count,
  (SELECT COUNT(*) FROM subscriptions) AS sub_count,
  (SELECT COUNT(*) FROM subscription_payments) AS sp_count;
-- Expected: 0, 0, 0, 0, 0

-- ============================================================================
-- STEP 4: Verify users table has fee_status and fee_paid_date
-- ============================================================================
DESCRIBE users;
-- If fee_status and fee_paid_date columns are missing, add them:
-- ALTER TABLE users ADD COLUMN fee_status VARCHAR(50) DEFAULT 'unpaid';
-- ALTER TABLE users ADD COLUMN fee_paid_date TIMESTAMP NULL;

-- ============================================================================
-- End of Validation Steps
-- ============================================================================
