import os
import sys
import traceback

os.environ["USE_LOCAL_DB"] = "false"
os.environ["USE_REMOTE_DB"] = "true"
os.environ["ENV"] = "remote"

try:
    from src.config import DATABASE_CONFIG
    import pymysql

    conn = pymysql.connect(
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
        database=DATABASE_CONFIG["database"],
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT table_name, table_rows
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name IN (%s, %s)
        ORDER BY table_name
        """,
        (DATABASE_CONFIG["database"], "store_products", "store_items"),
    )
    rows = cur.fetchall()
    print(rows)
    cur.close()
    conn.close()
except Exception as exc:
    print(f"ERROR: {exc}")
    traceback.print_exc()
    sys.exit(1)
