"""
Migration: Add Shake Credit System
Creates tables for shake credits and transactions
"""

from src.database.connection import execute_query

def migrate():
    """Create shake credit system tables"""
    
    # 1. Create shake_credits table
    print("Creating shake_credits table...")
    query1 = """
        CREATE TABLE IF NOT EXISTS shake_credits (
            credit_id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE,
            total_credits INT DEFAULT 0,
            used_credits INT DEFAULT 0,
            available_credits INT DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    execute_query(query1)
    print("✓ shake_credits table created")
    
    # 2. Create shake_transactions table
    print("Creating shake_transactions table...")
    query2 = """
        CREATE TABLE IF NOT EXISTS shake_transactions (
            transaction_id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            credit_change INT NOT NULL,
            transaction_type VARCHAR(100) NOT NULL,
            description TEXT,
            reference_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    execute_query(query2)
    print("✓ shake_transactions table created")
    
    # 3. Create shake_purchases table (for credit purchase requests)
    print("Creating shake_purchases table...")
    query3 = """
        CREATE TABLE IF NOT EXISTS shake_purchases (
            purchase_id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            credits_requested INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            approved_by BIGINT,
            approved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """
    execute_query(query3)
    print("✓ shake_purchases table created")
    
    # 4. Update shake_requests to include credit tracking
    print("Updating shake_requests table...")
    query4 = """
        ALTER TABLE shake_requests 
        ADD COLUMN IF NOT EXISTS credit_used BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS used_date DATE,
        ADD COLUMN IF NOT EXISTS notes TEXT
    """
    execute_query(query4)
    print("✓ shake_requests table updated")
    
    # 5. Create indexes for performance
    print("Creating indexes...")
    queries = [
        "CREATE INDEX IF NOT EXISTS idx_shake_credits_user ON shake_credits(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_shake_transactions_user ON shake_transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_shake_purchases_user ON shake_purchases(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_shake_purchases_status ON shake_purchases(status)",
    ]
    for q in queries:
        execute_query(q)
    print("✓ Indexes created")
    
    print("\n✅ Migration complete - Shake credit system tables created!")

if __name__ == "__main__":
    migrate()
