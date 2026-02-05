#!/usr/bin/env python3
import os

os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
os.environ['ENV'] = 'remote'

from src.config import DATABASE_CONFIG
import pymysql

log = []

conn = pymysql.connect(
    host=DATABASE_CONFIG['host'],
    port=DATABASE_CONFIG['port'],
    user=DATABASE_CONFIG['user'],
    password=DATABASE_CONFIG['password'],
    database=DATABASE_CONFIG['database']
)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE users ADD COLUMN telegram_id BIGINT NULL")
    conn.commit()
    log.append("Added telegram_id column")
except Exception as e:
    log.append(f"telegram_id column add skipped: {e}")

cur.execute("UPDATE users SET telegram_id = user_id WHERE telegram_id IS NULL")
conn.commit()
log.append(f"Backfilled telegram_id rows: {cur.rowcount}")

try:
    cur.execute("ALTER TABLE users ADD UNIQUE INDEX idx_users_telegram_id (telegram_id)")
    conn.commit()
    log.append("Added unique index on telegram_id")
except Exception as e:
    log.append(f"Unique index add skipped: {e}")

cur.execute("SELECT COUNT(*) FROM users WHERE telegram_id IS NULL")
log.append(f"telegram_id NULL count: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM users")
log.append(f"total users: {cur.fetchone()[0]}")

cur.close()
conn.close()

with open("migration_status.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log))

print("\n".join(log))
