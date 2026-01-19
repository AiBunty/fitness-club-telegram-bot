"""
Migration: create `events`, `event_registrations`, and `revenue` tables

Run: python migrate_events_and_revenue.py
"""
import psycopg2
from src.config import DATABASE_CONFIG

SQL = [
    """
    CREATE TABLE IF NOT EXISTS events (
        event_id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        price NUMERIC(12,2) DEFAULT 0.0,
        is_paid BOOLEAN DEFAULT FALSE,
        start_date DATE,
        end_date DATE,
        capacity INTEGER,
        status TEXT DEFAULT 'active',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS event_registrations (
        registration_id SERIAL PRIMARY KEY,
        event_id INTEGER REFERENCES events(event_id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, confirmed, cancelled
        receivable_id INTEGER NULL,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS revenue (
        revenue_id SERIAL PRIMARY KEY,
        source_type TEXT NOT NULL,
        source_id INTEGER NOT NULL,
        amount NUMERIC(12,2) NOT NULL,
        recorded_by INTEGER,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
    CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date);
    CREATE INDEX IF NOT EXISTS idx_event_reg_user ON event_registrations(user_id);
    """,
]


def run():
    conn = None
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        for s in SQL:
            cur.execute(s)
        conn.commit()
        print("Migrations applied: events, event_registrations, revenue")
    except Exception as e:
        print("Migration failed:", e)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    run()
