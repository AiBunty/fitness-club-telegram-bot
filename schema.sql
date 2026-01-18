-- Fitness Club Bot Database Schema
-- PostgreSQL 15+

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    telegram_username VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    age INT,
    initial_weight DECIMAL(5,2),
    current_weight DECIMAL(5,2),
    referral_code VARCHAR(20) UNIQUE,
    fee_status VARCHAR(50) DEFAULT 'unpaid',
    total_points INT DEFAULT 0,
    role VARCHAR(50) DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily Logs Table
CREATE TABLE IF NOT EXISTS daily_logs (
    log_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    log_date DATE NOT NULL,
    weight DECIMAL(5,2),
    water_cups INT DEFAULT 0,
    meals_logged INT DEFAULT 0,
    habits_completed BOOLEAN DEFAULT FALSE,
    attendance BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, log_date)
);

-- Points Transactions Table
CREATE TABLE IF NOT EXISTS points_transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    points INT NOT NULL,
    activity VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Shake Requests Table
CREATE TABLE IF NOT EXISTS shake_requests (
    request_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    flavor VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Shake Flavors Table
CREATE TABLE IF NOT EXISTS shake_flavors (
    flavor_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default shake flavors
INSERT INTO shake_flavors (name, is_active) VALUES
('Chocolate', TRUE),
('Vanilla', TRUE),
('Strawberry', TRUE),
('Banana', TRUE),
('Mango', TRUE)
ON CONFLICT DO NOTHING;

-- Attendance Queue Table
CREATE TABLE IF NOT EXISTS attendance_queue (
    queue_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    queue_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by BIGINT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, queue_date)
);

-- Meal Photos Table
CREATE TABLE IF NOT EXISTS meal_photos (
    photo_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    photo_url VARCHAR(500),
    photo_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Admin Sessions Table
CREATE TABLE IF NOT EXISTS admin_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Fee Payments Table
CREATE TABLE IF NOT EXISTS fee_payments (
    payment_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    validity_days INT DEFAULT 30,
    expiry_date DATE,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Referral Rewards Table
CREATE TABLE IF NOT EXISTS referral_rewards (
    referral_id SERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    referred_id BIGINT NOT NULL,
    reward_points INT DEFAULT 50,
    shake_credits INT DEFAULT 2,
    claimed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(255),
    message TEXT,
    notification_type VARCHAR(100),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(telegram_username);
CREATE INDEX IF NOT EXISTS idx_daily_logs_user_date ON daily_logs(user_id, log_date);
CREATE INDEX IF NOT EXISTS idx_points_transactions_user ON points_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_shake_requests_user ON shake_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_attendance_queue_user_date ON attendance_queue(user_id, queue_date);
CREATE INDEX IF NOT EXISTS idx_meal_photos_user ON meal_photos(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_fee_payments_user ON fee_payments(user_id);

-- Attendance Overrides Table (QR system manual overrides)
CREATE TABLE IF NOT EXISTS attendance_overrides (
    override_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    admin_id BIGINT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attendance_overrides_user ON attendance_overrides(user_id);
CREATE INDEX IF NOT EXISTS idx_attendance_overrides_admin ON attendance_overrides(admin_id);
CREATE INDEX IF NOT EXISTS idx_attendance_overrides_date ON attendance_overrides(created_at);

-- Create Leaderboard View
CREATE OR REPLACE VIEW leaderboard AS
SELECT 
    u.user_id,
    u.full_name,
    u.telegram_username,
    u.total_points,
    RANK() OVER (ORDER BY u.total_points DESC) as rank
FROM users u
WHERE u.fee_status = 'paid'
ORDER BY u.total_points DESC;

-- Create Active Members View
CREATE OR REPLACE VIEW active_members AS
SELECT 
    u.user_id,
    u.full_name,
    u.fee_status,
    u.total_points,
    COALESCE(dl.log_date, NULL) as last_activity
FROM users u
LEFT JOIN daily_logs dl ON u.user_id = dl.user_id
WHERE u.fee_status = 'paid'
ORDER BY u.created_at DESC;
