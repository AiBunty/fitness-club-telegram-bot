"""
Integration tests for payment approval flows.

These tests run against the staging database configured in `src.config.DATABASE_CONFIG`.
Each test opens a DB transaction and rolls back at the end so tests are non-destructive.
Run with: `pytest -q tests/integration/test_payment_approvals.py`
"""
import psycopg2
import pytest
from src.config import DATABASE_CONFIG


def get_conn():
    return psycopg2.connect(**DATABASE_CONFIG)


def test_store_order_payment_and_credit_rollback():
    conn = get_conn()
    try:
        conn.autocommit = False
        cur = conn.cursor()

        # Create a temporary user
        cur.execute("INSERT INTO users (user_id, full_name) VALUES (%s, %s) RETURNING user_id", (9999999999, 'Test User'))
        uid = cur.fetchone()[0]

        # Insert minimal store_order row (use store_orders schema)
        cur.execute("INSERT INTO store_orders (user_id, total_amount, payment_method, order_status, created_at) VALUES (%s, %s, %s, %s, NOW()) RETURNING order_id",
                (uid, 100.00, 'ONLINE', 'PENDING'))
        order_id = cur.fetchone()[0]

        # Mark as paid
        cur.execute("UPDATE store_orders SET order_status='PAID' WHERE order_id=%s RETURNING order_status", (order_id,))
        paid = cur.fetchone()
        assert paid[0] == 'PAID'

        # Reset to credit and test credit flow
        cur.execute("UPDATE store_orders SET order_status='CREDIT' WHERE order_id=%s RETURNING order_status", (order_id,))
        credit = cur.fetchone()
        assert credit[0] == 'CREDIT'

        # If we reach here, test passes — rollback below
        conn.rollback()
    finally:
        conn.close()


def test_shake_credit_approval_rollback():
    conn = get_conn()
    try:
        conn.autocommit = False
        cur = conn.cursor()

        # Create temp user
        cur.execute("INSERT INTO users (user_id, full_name) VALUES (%s, %s) RETURNING user_id", (9999999998, 'Shake User'))
        uid = cur.fetchone()[0]

        # Insert a shake request minimal row
        cur.execute("INSERT INTO shake_requests (user_id, flavor, status, requested_at) VALUES (%s, %s, %s, NOW()) RETURNING request_id",
                    (uid, 'TestFlavor', 'pending'))
        shake_id = cur.fetchone()[0]

        # Simulate admin approving credit terms
        cur.execute("UPDATE shake_requests SET payment_terms='credit', payment_status='pending', payment_due_date = NOW() + INTERVAL '7 days' WHERE request_id=%s RETURNING payment_terms, payment_status", (shake_id,))
        row = cur.fetchone()
        assert row[0] == 'credit'

        conn.rollback()
    finally:
        conn.close()
