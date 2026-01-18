"""
Migration: Add Payment Terms to Shake Orders
Adds payment_status column to track whether order is paid or on credit terms
"""

from src.database.connection import execute_query

def migrate():
    """Add payment_status and follow_up tracking to shake_requests table"""
    
    print("Adding payment tracking columns to shake_requests...")
    query = """
        ALTER TABLE shake_requests
        ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) DEFAULT 'pending',
        ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(50) DEFAULT 'pending',
        ADD COLUMN IF NOT EXISTS payment_due_date DATE,
        ADD COLUMN IF NOT EXISTS payment_approved_by BIGINT,
        ADD COLUMN IF NOT EXISTS follow_up_reminder_sent BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS overdue_reminder_count INT DEFAULT 0
    """
    execute_query(query)
    print("✓ Payment tracking columns added to shake_requests")
    
    # Create follow-up reminders table
    print("Creating follow_up_reminders table...")
    query2 = """
        CREATE TABLE IF NOT EXISTS follow_up_reminders (
            reminder_id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            shake_request_id INT,
            reminder_type VARCHAR(50) NOT NULL,
            message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_responded BOOLEAN DEFAULT FALSE,
            admin_approved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (shake_request_id) REFERENCES shake_requests(request_id) ON DELETE CASCADE
        )
    """
    execute_query(query2)
    print("✓ follow_up_reminders table created")
    
    # Create index for follow-up reminders
    print("Creating indexes...")
    query3 = """
        CREATE INDEX IF NOT EXISTS idx_follow_up_user ON follow_up_reminders(user_id);
        CREATE INDEX IF NOT EXISTS idx_follow_up_shake ON follow_up_reminders(shake_request_id);
        CREATE INDEX IF NOT EXISTS idx_shake_requests_payment_status ON shake_requests(payment_status)
    """
    execute_query(query3)
    print("✓ Indexes created")
    
    print("\n✅ Migration complete - Payment terms tracking added!")

if __name__ == "__main__":
    migrate()
