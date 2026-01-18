"""
Migration: Create ar_transactions table for split/multi-method payments
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import execute_query


def migrate():
    ddl = """
    CREATE TABLE IF NOT EXISTS ar_transactions (
        transaction_id SERIAL PRIMARY KEY,
        receivable_id INTEGER NOT NULL,
        method VARCHAR(20) NOT NULL, -- cash|upi|card|bank
        amount NUMERIC(12,2) NOT NULL,
        reference TEXT, -- e.g., UPI txn id
        created_by BIGINT, -- admin user id
        created_at TIMESTAMP DEFAULT NOW(),
        CONSTRAINT fk_ar_receivable FOREIGN KEY (receivable_id) REFERENCES accounts_receivable(receivable_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_ar_tx_receivable ON ar_transactions(receivable_id);
    CREATE INDEX IF NOT EXISTS idx_ar_tx_method ON ar_transactions(method);
    CREATE INDEX IF NOT EXISTS idx_ar_tx_created_at ON ar_transactions(created_at);
    """

    try:
        execute_query(ddl)
        print("✅ ar_transactions table created/verified")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    ok = migrate()
    sys.exit(0 if ok else 1)
