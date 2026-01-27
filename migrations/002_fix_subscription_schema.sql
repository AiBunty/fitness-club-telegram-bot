-- ============================================================================
-- Migration: Fix Subscription Tables Schema
-- Date: 2026-01-27
-- Purpose: Align subscription_requests, subscriptions, and subscription_payments
--          tables with application code expectations (subscription_operations.py)
-- ============================================================================

-- ASSUMPTIONS:
-- 1. Old subscription_requests, subscriptions, subscription_payments incompatible
-- 2. Application code defines PK as 'id' (not request_id, subscription_id, payment_id)
-- 3. plan_id must be TEXT (plan_30, plan_90, plan_180), not INT
-- 4. Users table already exists with user_id (PK)
-- 5. Foreign keys enforced

-- ============================================================================
-- STEP 1: Drop existing subscription tables
-- ============================================================================
DROP TABLE IF EXISTS subscription_payments;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS subscription_requests;

-- ============================================================================
-- STEP 2: Recreate subscription_requests
-- ============================================================================
-- Stores user subscription plan requests awaiting admin approval
-- payment_method: 'cash', 'upi', or 'manual' (pending payment method determination)
CREATE TABLE subscription_requests (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique request ID',
    user_id INT NOT NULL COMMENT 'FK to users.user_id',
    plan_id VARCHAR(50) NOT NULL COMMENT 'Plan code: plan_30, plan_90, plan_180',
    amount DOUBLE NOT NULL COMMENT 'Subscription amount in rupees',
    payment_method VARCHAR(50) COMMENT 'cash, upi, or manual',
    status VARCHAR(50) DEFAULT 'pending' COMMENT 'pending, approved, rejected',
    fee_status VARCHAR(50) COMMENT 'Optional: tracks fee approval state',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When user requested',
    approved_at TIMESTAMP NULL COMMENT 'When admin approved (null if pending)',
    rejection_reason TEXT COMMENT 'If rejected, reason why',
    
    CONSTRAINT fk_subr_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_plan_id CHECK (plan_id IN ('plan_30', 'plan_90', 'plan_180')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'approved', 'rejected')),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_requested_at (requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Subscription Requests: tracks subscription plan requests from users';

-- ============================================================================
-- STEP 3: Recreate subscriptions
-- ============================================================================
-- Stores active subscription records after admin approval
-- grace_period_end: typically end_date + 7 days (for late renewal grace)
CREATE TABLE subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique subscription ID',
    user_id INT NOT NULL COMMENT 'FK to users.user_id',
    plan_id VARCHAR(50) NOT NULL COMMENT 'Plan code: plan_30, plan_90, plan_180',
    amount DOUBLE NOT NULL COMMENT 'Subscription amount in rupees',
    start_date DATETIME NOT NULL COMMENT 'When subscription becomes active',
    end_date DATETIME NOT NULL COMMENT 'When subscription expires',
    status VARCHAR(50) DEFAULT 'active' COMMENT 'active, locked, or expired',
    grace_period_end DATETIME COMMENT 'End date + 7 days for renewal grace',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When subscription created',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update',
    
    CONSTRAINT fk_sub_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT chk_plan_id CHECK (plan_id IN ('plan_30', 'plan_90', 'plan_180')),
    CONSTRAINT chk_status CHECK (status IN ('active', 'locked', 'expired')),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_end_date (end_date),
    UNIQUE KEY uk_user_active (user_id, status) COMMENT 'One active subscription per user'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Subscriptions: active subscription records after approval';

-- ============================================================================
-- STEP 4: Recreate subscription_payments
-- ============================================================================
-- Stores payment records for subscription requests
-- This is separate from AR ledger (ar_transactions) but mirrors into it
-- request_id: links to subscription_requests.id for tracking approval flow
CREATE TABLE subscription_payments (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique payment ID',
    user_id INT NOT NULL COMMENT 'FK to users.user_id',
    request_id INT NOT NULL COMMENT 'FK to subscription_requests.id',
    amount DOUBLE NOT NULL COMMENT 'Payment amount in rupees',
    payment_method VARCHAR(50) NOT NULL COMMENT 'cash or upi',
    reference VARCHAR(255) COMMENT 'Transaction reference (UPI ID, check #, etc)',
    screenshot_file_id VARCHAR(255) COMMENT 'Telegram file_id for UPI screenshot',
    status VARCHAR(50) DEFAULT 'pending' COMMENT 'pending or completed',
    paid_at TIMESTAMP NULL COMMENT 'When payment was received/confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When payment recorded',
    
    CONSTRAINT fk_subp_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_subp_request FOREIGN KEY (request_id) REFERENCES subscription_requests(id) ON DELETE CASCADE,
    CONSTRAINT chk_method CHECK (payment_method IN ('cash', 'upi')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'completed')),
    INDEX idx_user_id (user_id),
    INDEX idx_request_id (request_id),
    INDEX idx_status (status),
    INDEX idx_paid_at (paid_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Subscription Payments: payment records linked to subscription requests';

-- ============================================================================
-- End of Migration
-- ============================================================================
-- After this migration runs:
-- - subscription_requests, subscriptions, subscription_payments aligned with code
-- - approve_subscription() can create receivables and mirror payment_lines into AR
-- - Subscription approval flows (cash / upi / split / no-lines) work correctly
-- - /ar_reports can query subscription receivables via AR tables
