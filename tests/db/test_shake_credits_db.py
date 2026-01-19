import os
import pytest

from src.config import DATABASE_CONFIG
from src.database.connection import get_db_cursor, execute_query
from src.database.shake_credits_operations import consume_credit, add_credits


DB_TESTS_ENABLED = os.getenv('RUN_DB_TESTS', '0') == '1'


@pytest.mark.skipif(not DB_TESTS_ENABLED, reason="DB integration tests disabled (set RUN_DB_TESTS=1)")
def test_shake_credit_ledger_consume_roundtrip():
    """DB-level test: create a test user credit ledger, add credits, consume one, verify ledger changes.

    This test requires a reachable Postgres DB with the application's schema present.
    It is guarded by `RUN_DB_TESTS=1` environment variable to avoid accidental production changes.
    """
    test_user_id = -999999  # negative test id to avoid colliding with real users

    # Ensure tables exist
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT to_regclass('public.shake_credits') as exists_sc")
        sc_exists = cur.fetchone().get('exists_sc') is not None
        cur.execute("SELECT to_regclass('public.shake_transactions') as exists_st")
        st_exists = cur.fetchone().get('exists_st') is not None

    if not (sc_exists and st_exists):
        pytest.skip('Required tables (shake_credits, shake_transactions) not present in target DB')

    # Clean any prior test artifacts
    execute_query("DELETE FROM shake_transactions WHERE user_id = %s", (test_user_id,))
    execute_query("DELETE FROM shake_credits WHERE user_id = %s", (test_user_id,))

    try:
        # Initialize credits row
        execute_query(
            "INSERT INTO shake_credits (user_id, total_credits, used_credits, available_credits, last_updated) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (user_id) DO UPDATE SET total_credits=EXCLUDED.total_credits RETURNING credit_id",
            (test_user_id, 0, 0, 0),
            fetch_one=True,
        )

        # Add credits via the public API (creates ledger entry)
        ok = add_credits(test_user_id, 3, 'test', 'Integration test credits')
        assert ok is True

        # Consume one credit via API (should be atomic)
        ok2 = consume_credit(test_user_id, 'Integration test consume')
        assert ok2 is True

        # Verify ledger sum equals 2 (3 added, 1 consumed)
        res = execute_query("SELECT COALESCE(SUM(credit_change),0) as avail FROM shake_transactions WHERE user_id = %s", (test_user_id,), fetch_one=True)
        assert int(res.get('avail', 0)) == 2

    finally:
        # Cleanup test data
        execute_query("DELETE FROM shake_transactions WHERE user_id = %s", (test_user_id,))
        execute_query("DELETE FROM shake_credits WHERE user_id = %s", (test_user_id,))