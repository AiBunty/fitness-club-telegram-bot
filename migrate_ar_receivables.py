"""
Migration: Create accounts_receivable table for unified billing/dues
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import execute_query


def migrate():
    ddl = """
    CREATE TABLE IF NOT EXISTS accounts_receivable (
        receivable_id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        receivable_type VARCHAR(50) NOT NULL, -- e.g., 'subscription', 'shake_purchase'
        source_id BIGINT, -- optional link to product-specific table
        bill_amount NUMERIC(12,2) NOT NULL,
        discount_amount NUMERIC(12,2) DEFAULT 0,
        final_amount NUMERIC(12,2) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending', -- pending|partial|paid|cancelled
        due_date DATE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        CONSTRAINT fk_receivable_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_ar_user ON accounts_receivable(user_id);
    CREATE INDEX IF NOT EXISTS idx_ar_status ON accounts_receivable(status);
    CREATE INDEX IF NOT EXISTS idx_ar_due ON accounts_receivable(due_date);
    """

    try:
        execute_query(ddl)
        print("✅ accounts_receivable table created/verified")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    ok = migrate()
    sys.exit(0 if ok else 1)
