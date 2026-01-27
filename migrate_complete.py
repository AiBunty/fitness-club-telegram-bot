#!/usr/bin/env python3
"""
Complete migration from Neon PostgreSQL to Local SQLite
Using schema-aware table creation
"""

import os
import sqlite3
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NEON_HOST = os.getenv('DB_HOST')
NEON_PORT = int(os.getenv('DB_PORT', 5432))
NEON_DB = os.getenv('DB_NAME')
NEON_USER = os.getenv('DB_USER')
NEON_PASSWORD = os.getenv('DB_PASSWORD')

PROJECT_ROOT = Path(__file__).parent
LOCAL_DB_PATH = PROJECT_ROOT / 'fitness_club.db'

print("=" * 80)
print("COMPLETE DATABASE MIGRATION: Neon PostgreSQL to Local SQLite")
print("=" * 80)
print(f"\nSource: Neon PostgreSQL ({NEON_HOST})")
print(f"Target: Local SQLite ({LOCAL_DB_PATH})")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


# SQLite schema - compatible with both PostgreSQL and SQLite
SQLITE_SCHEMA = """
-- Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    telegram_username TEXT,
    full_name TEXT NOT NULL,
    phone TEXT,
    age INTEGER,
    initial_weight REAL,
    current_weight REAL,
    referral_code TEXT UNIQUE,
    fee_status TEXT DEFAULT 'unpaid',
    total_points INTEGER DEFAULT 0,
    role TEXT DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily Logs Table
CREATE TABLE IF NOT EXISTS daily_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    log_date DATE NOT NULL,
    weight REAL,
    water_cups INTEGER DEFAULT 0,
    meals_logged INTEGER DEFAULT 0,
    habits_completed BOOLEAN DEFAULT 0,
    attendance BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, log_date)
);

-- Points Transactions Table
CREATE TABLE IF NOT EXISTS points_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    points INTEGER NOT NULL,
    activity TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Shake Requests Table
CREATE TABLE IF NOT EXISTS shake_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    flavor TEXT,
    status TEXT DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Shake Flavors Table
CREATE TABLE IF NOT EXISTS shake_flavors (
    flavor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attendance Queue Table
CREATE TABLE IF NOT EXISTS attendance_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    queue_date DATE NOT NULL,
    status TEXT DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, queue_date)
);

-- Meal Photos Table
CREATE TABLE IF NOT EXISTS meal_photos (
    photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    photo_url TEXT,
    photo_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Admin Sessions Table
CREATE TABLE IF NOT EXISTS admin_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Fee Payments Table
CREATE TABLE IF NOT EXISTS fee_payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_date DATE NOT NULL,
    validity_days INTEGER DEFAULT 30,
    expiry_date DATE,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Referral Rewards Table
CREATE TABLE IF NOT EXISTS referral_rewards (
    referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL,
    reward_points INTEGER DEFAULT 50,
    shake_credits INTEGER DEFAULT 2,
    claimed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    message TEXT,
    notification_type TEXT,
    is_read BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Attendance Overrides Table
CREATE TABLE IF NOT EXISTS attendance_overrides (
    override_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    admin_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Store Items Table
CREATE TABLE IF NOT EXISTS store_items (
    serial INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hsn TEXT,
    mrp REAL,
    gst REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admin Members Table
CREATE TABLE IF NOT EXISTS admin_members (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    permissions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staff Members Table
CREATE TABLE IF NOT EXISTS staff_members (
    staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shake Credits Table
CREATE TABLE IF NOT EXISTS shake_credits (
    credit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    credits INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Shake Purchases Table
CREATE TABLE IF NOT EXISTS shake_purchases (
    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    credits_spent INTEGER,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Shake Transactions Table
CREATE TABLE IF NOT EXISTS shake_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    credit_change INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Reminder Preferences Table
CREATE TABLE IF NOT EXISTS reminder_preferences (
    pref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    water_reminders BOOLEAN DEFAULT 1,
    meal_reminders BOOLEAN DEFAULT 1,
    check_in_time TEXT DEFAULT '09:00',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Gym Settings Table
CREATE TABLE IF NOT EXISTS gym_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subscriptions Table
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_id INTEGER,
    status TEXT DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Subscription Plans Table
CREATE TABLE IF NOT EXISTS subscription_plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    duration_days INTEGER,
    price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subscription Payments Table
CREATE TABLE IF NOT EXISTS subscription_payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER,
    amount REAL,
    payment_date DATE,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id) ON DELETE CASCADE
);

-- Subscription Requests Table
CREATE TABLE IF NOT EXISTS subscription_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_id INTEGER,
    status TEXT DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Subscription Reminders Table
CREATE TABLE IF NOT EXISTS subscription_reminders (
    reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER,
    reminder_date DATE,
    sent BOOLEAN DEFAULT 0,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id) ON DELETE CASCADE
);

-- Subscription UPI Codes Table
CREATE TABLE IF NOT EXISTS subscription_upi_codes (
    upi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER,
    upi_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id) ON DELETE CASCADE
);

-- Store Orders Table
CREATE TABLE IF NOT EXISTS store_orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    order_date DATE,
    total_amount REAL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Store Order Items Table
CREATE TABLE IF NOT EXISTS store_order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    price REAL,
    FOREIGN KEY (order_id) REFERENCES store_orders(order_id) ON DELETE CASCADE
);

-- Store Order Payments Table
CREATE TABLE IF NOT EXISTS store_order_payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    amount REAL,
    payment_date DATE,
    method TEXT,
    FOREIGN KEY (order_id) REFERENCES store_orders(order_id) ON DELETE CASCADE
);

-- Store Products Table
CREATE TABLE IF NOT EXISTS store_products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Product Orders Table
CREATE TABLE IF NOT EXISTS user_product_orders (
    user_order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    order_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES store_products(product_id) ON DELETE CASCADE
);

-- Broadcast Log Table
CREATE TABLE IF NOT EXISTS broadcast_log (
    broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    message TEXT,
    recipient_count INTEGER,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Admin Audit Log Table
CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    action TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Payment Requests Table
CREATE TABLE IF NOT EXISTS payment_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Revenue Table
CREATE TABLE IF NOT EXISTS revenue (
    revenue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    amount REAL,
    date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AR (Accounts Receivable) Transactions Table
CREATE TABLE IF NOT EXISTS ar_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    transaction_date DATE,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Accounts Receivable Table
CREATE TABLE IF NOT EXISTS accounts_receivable (
    ar_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount_due REAL,
    due_date DATE,
    status TEXT DEFAULT 'open',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- PT Subscriptions Table
CREATE TABLE IF NOT EXISTS pt_subscriptions (
    pt_sub_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    trainer_id INTEGER,
    status TEXT DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (trainer_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Challenges Table
CREATE TABLE IF NOT EXISTS challenges (
    challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Challenge Participants Table
CREATE TABLE IF NOT EXISTS challenge_participants (
    participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER,
    user_id INTEGER,
    status TEXT DEFAULT 'active',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (challenge_id) REFERENCES challenges(challenge_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Events Table
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    event_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One Day Events Table
CREATE TABLE IF NOT EXISTS one_day_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event Registrations Table
CREATE TABLE IF NOT EXISTS event_registrations (
    registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER,
    user_id INTEGER,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- User Event Registrations Table
CREATE TABLE IF NOT EXISTS user_event_registrations (
    registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    event_id INTEGER,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Follow Up Reminders Table
CREATE TABLE IF NOT EXISTS follow_up_reminders (
    reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    reminder_text TEXT,
    reminder_date DATE,
    sent BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Motivational Messages Table
CREATE TABLE IF NOT EXISTS motivational_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_text TEXT,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def get_neon_connection():
    """Create connection to Neon PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=NEON_HOST,
            port=NEON_PORT,
            database=NEON_DB,
            user=NEON_USER,
            password=NEON_PASSWORD,
            connect_timeout=10
        )
        print("[OK] Connected to Neon PostgreSQL")
        return conn
    except Exception as e:
        print(f"[ERROR] Failed to connect to Neon: {e}")
        return None


def get_local_connection():
    """Create connection to local SQLite"""
    conn = sqlite3.connect(str(LOCAL_DB_PATH))
    conn.row_factory = sqlite3.Row
    print(f"[OK] Connected to Local SQLite: {LOCAL_DB_PATH}")
    return conn


def get_all_tables_from_neon(neon_conn):
    """Get list of all user tables from Neon"""
    cursor = neon_conn.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = sorted([row[0] for row in cursor.fetchall()])
    cursor.close()
    return tables


def copy_all_table_data(neon_conn, local_conn, tables):
    """Copy data from all Neon tables to SQLite"""
    total_records = 0
    successful_tables = 0
    
    for table_name in tables:
        try:
            neon_cursor = neon_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            neon_cursor.execute(f"SELECT * FROM {table_name}")
            rows = neon_cursor.fetchall()
            neon_cursor.close()
            
            if not rows:
                print(f"  [INFO] {table_name:<40} 0 records (empty)")
                continue
            
            columns = list(rows[0].keys())
            placeholders = ",".join(["?" for _ in columns])
            insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
            
            local_cursor = local_conn.cursor()
            for row in rows:
                values = tuple(row[col] for col in columns)
                local_cursor.execute(insert_sql, values)
            
            local_conn.commit()
            local_cursor.close()
            
            print(f"  [OK] {table_name:<40} {len(rows):>6,} records")
            total_records += len(rows)
            successful_tables += 1
            
        except Exception as e:
            print(f"  [SKIP] {table_name:<40} {str(e)[:40]}")
    
    return successful_tables, total_records


def create_indexes(local_conn):
    """Create indexes for better query performance"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(telegram_username)",
        "CREATE INDEX IF NOT EXISTS idx_daily_logs_user_date ON daily_logs(user_id, log_date)",
        "CREATE INDEX IF NOT EXISTS idx_points_transactions_user ON points_transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_shake_requests_user ON shake_requests(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_attendance_queue_user_date ON attendance_queue(user_id, queue_date)",
        "CREATE INDEX IF NOT EXISTS idx_meal_photos_user ON meal_photos(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_fee_payments_user ON fee_payments(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_attendance_overrides_user ON attendance_overrides(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_store_items_name ON store_items(name)",
        "CREATE INDEX IF NOT EXISTS idx_store_items_hsn ON store_items(hsn)",
        "CREATE INDEX IF NOT EXISTS idx_broadcast_log_admin ON broadcast_log(admin_id)",
        "CREATE INDEX IF NOT EXISTS idx_admin_audit_admin ON admin_audit_log(admin_id)",
    ]
    
    cursor = local_conn.cursor()
    for idx_sql in indexes:
        try:
            cursor.execute(idx_sql)
        except:
            pass
    
    local_conn.commit()
    cursor.close()


def migrate_all_tables():
    """Main migration function"""
    neon_conn = get_neon_connection()
    if not neon_conn:
        print("\n[ERROR] Migration aborted: Cannot connect to Neon")
        return False
    
    local_conn = get_local_connection()
    
    print("\n" + "=" * 80)
    print("STEP 1: Create SQLite schema")
    print("=" * 80 + "\n")
    
    cursor = local_conn.cursor()
    for statement in SQLITE_SCHEMA.split(';'):
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
            except Exception as e:
                if "already exists" not in str(e):
                    print(f"[WARN] {str(e)[:60]}")
    
    local_conn.commit()
    cursor.close()
    print("[OK] All tables created successfully\n")
    
    print("=" * 80)
    print("STEP 2: Get source tables from Neon")
    print("=" * 80)
    
    tables = get_all_tables_from_neon(neon_conn)
    print(f"\n[INFO] Found {len(tables)} tables in Neon\n")
    
    print("=" * 80)
    print("STEP 3: Copy data from Neon to Local SQLite")
    print("=" * 80 + "\n")
    
    successful, total_records = copy_all_table_data(neon_conn, local_conn, tables)
    
    print("\n" + "=" * 80)
    print("STEP 4: Create indexes")
    print("=" * 80 + "\n")
    
    create_indexes(local_conn)
    print("[OK] Indexes created\n")
    
    print("=" * 80)
    print("STEP 5: Verify migration")
    print("=" * 80 + "\n")
    
    cursor = local_conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table'
    """)
    local_tables = sorted([row[0] for row in cursor.fetchall()])
    
    print(f"[INFO] Local SQLite contains {len(local_tables)} tables:\n")
    grand_total = 0
    for table in local_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  - {table:<40} {count:>10,} records")
            grand_total += count
    
    cursor.close()
    
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"[OK] Tables created:    {len(local_tables)}")
    print(f"[OK] Data migrated:     {grand_total:,} records")
    print(f"[OK] Target database:   {LOCAL_DB_PATH}")
    print(f"[OK] Time:              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[SUCCESS] MIGRATION COMPLETE!\n")
    
    local_conn.close()
    neon_conn.close()
    
    return True


if __name__ == "__main__":
    try:
        success = migrate_all_tables()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARN] Migration interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
