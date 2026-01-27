-- ============================================================================
-- Migration: Fix Accounts Receivable Schema
-- Date: 2026-01-27
-- Purpose: Align accounts_receivable and ar_transactions tables with 
--          application code expectations (ar_operations.py)
-- ============================================================================

-- ASSUMPTIONS:
-- 1. MySQL is the only supported database (no backwards compat needed)
-- 2. Application code (ar_operations.py) defines the authoritative schema
-- 3. Old accounts_receivable and ar_transactions data is superseded
-- 4. Foreign keys enforced; users table already exists with user_id (PK)

-- ============================================================================
-- STEP 1: Drop existing AR tables (old schema incompatible)
-- ============================================================================
DROP TABLE IF EXISTS ar_transactions;
DROP TABLE IF EXISTS accounts_receivable;

-- ============================================================================
-- STEP 2: Recreate accounts_receivable with correct schema
-- ============================================================================
-- Stores receivables (amounts owed) keyed to invoices or subscriptions
-- Status: 'pending' (no payment), 'partial' (some payment), 'paid' (full payment)
-- Derived from ar_transactions using stored procedures or application logic
CREATE TABLE accounts_receivable (
    receivable_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique receivable ID',
    user_id INT NOT NULL COMMENT 'FK to users.user_id',
    receivable_type VARCHAR(50) NOT NULL COMMENT 'invoice or subscription',
    source_id INT COMMENT 'invoice_id or subscription_request_id',
    bill_amount DOUBLE NOT NULL COMMENT 'Original bill amount before discount',
    discount_amount DOUBLE DEFAULT 0.0 COMMENT 'Discount applied',
    final_amount DOUBLE NOT NULL COMMENT 'Amount due (bill_amount - discount_amount)',
    status VARCHAR(50) DEFAULT 'pending' COMMENT 'pending, partial, or paid',
    due_date DATE COMMENT 'When payment is due',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When receivable created',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last status update',
    
    CONSTRAINT fk_ar_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_type CHECK (receivable_type IN ('invoice', 'subscription')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'partial', 'paid')),
    INDEX idx_user_id (user_id),
    INDEX idx_type_source (receivable_type, source_id),
    INDEX idx_status (status),
    INDEX idx_due_date (due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Accounts Receivable: tracks amounts owed by users for invoices/subscriptions';

-- ============================================================================
-- STEP 3: Recreate ar_transactions with correct schema
-- ============================================================================
-- Stores payment/transaction lines: each row represents one payment
-- Multiple rows per receivable = split payment
-- Status derived from sum(amount) vs final_amount in associated receivable
CREATE TABLE ar_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique transaction ID',
    receivable_id INT NOT NULL COMMENT 'FK to accounts_receivable.receivable_id',
    method VARCHAR(50) NOT NULL COMMENT 'Payment method: cash or upi',
    amount DOUBLE NOT NULL COMMENT 'Amount paid in this transaction',
    reference VARCHAR(255) COMMENT 'Payment reference (e.g., UPI ID, check number)',
    created_by INT COMMENT 'Admin ID who recorded payment',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When payment recorded',
    
    CONSTRAINT fk_art_receivable FOREIGN KEY (receivable_id) REFERENCES accounts_receivable(receivable_id) ON DELETE CASCADE,
    CONSTRAINT chk_method CHECK (method IN ('cash', 'upi')),
    INDEX idx_receivable_id (receivable_id),
    INDEX idx_method (method),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='AR Transactions: individual payment lines for receivables';

-- ============================================================================
-- STEP 4: Verify users table has fee_status and fee_paid_date
-- ============================================================================
-- Note: If these columns don't exist, add them:
-- ALTER TABLE users ADD COLUMN fee_status VARCHAR(50) DEFAULT 'unpaid';
-- ALTER TABLE users ADD COLUMN fee_paid_date TIMESTAMP NULL;

-- ============================================================================
-- End of Migration
-- ============================================================================
-- After this migration runs:
-- - accounts_receivable and ar_transactions are aligned with ar_operations.py
-- - Invoice confirmation flows can create/update AR records safely
-- - Subscription approval flows can mirror payment_lines into AR
-- - /ar_reports can query receivables and transactions without schema errors
