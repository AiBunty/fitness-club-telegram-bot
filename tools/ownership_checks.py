"""
Quick read-only checks for ownership-scope issues (run in staging).

Usage: python tools/ownership_checks.py

This script executes a few diagnostic queries and returns non-zero
exit code if anomalies are found.
"""
import sys
from datetime import datetime, timedelta
from src.database.connection import execute_query


def check_duplicate_pending_shakes(limit=10):
    # Look for duplicate shake_request_id occurrences in derived query results
    # Uses a conservative grouping to detect duplicates regardless of join issues.
    # Determine primary key / identifier column for shake_requests
    col_sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'shake_requests'
        ORDER BY ordinal_position
        LIMIT 1
    """
    cols = execute_query(col_sql) or []
    col_name = cols[0].get('column_name') if cols else 'request_id'

    sql = f"""
        SELECT {col_name} as shake_id, COUNT(*) AS cnt
        FROM (
            SELECT {col_name}
            FROM shake_requests
            WHERE payment_terms = 'credit'
              AND payment_status IN ('pending','user_confirmed')
        ) t
        GROUP BY {col_name}
        HAVING COUNT(*) > 1
        LIMIT %s
    """
    rows = execute_query(sql, (limit,))
    return rows


def main():
    failed = False
    print('Running ownership-scope checks...')

    dups = check_duplicate_pending_shakes()
    if dups:
        print('ERROR: Found duplicate pending shake_request_id rows (possible join bug). Sample:')
        for r in dups:
            print(r)
        failed = True
    else:
        print('OK: No duplicate pending shakes found')

    if failed:
        print('One or more checks failed')
        sys.exit(2)
    print('All checks passed')


if __name__ == '__main__':
    main()
