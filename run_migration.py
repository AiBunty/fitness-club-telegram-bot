#!/usr/bin/env python3
"""Quick migration runner"""
import sqlite3
import json
from pathlib import Path

LOCAL_DB = 'fitness_club.db'
print(f"Connecting to {LOCAL_DB}...")
conn = sqlite3.connect(LOCAL_DB)
cursor = conn.cursor()

print("Creating store_items table...")
cursor.execute('''
CREATE TABLE IF NOT EXISTS store_items (
    serial INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hsn TEXT NOT NULL,
    mrp REAL NOT NULL,
    gst REAL NOT NULL DEFAULT 18.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, hsn)
)
''')

print("Creating indexes...")
cursor.execute('CREATE INDEX IF NOT EXISTS idx_store_items_name ON store_items(name)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_store_items_hsn ON store_items(hsn)')

print("Loading JSON data...")
json_path = Path('data/store_items.json')
items = json.loads(json_path.read_text(encoding='utf-8'))

print(f"Migrating {len(items)} items...")
migrated = 0
for item in items:
    gst_value = item.get('gst', item.get('gst_percent', 18.0))
    cursor.execute('''
    INSERT OR REPLACE INTO store_items (serial, name, hsn, mrp, gst, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    ''', (item.get('serial'), item['name'], item['hsn'], item['mrp'], gst_value))
    migrated += 1

conn.commit()
count = cursor.execute('SELECT COUNT(*) FROM store_items').fetchone()[0]
print(f"\n✅ Migration complete!")
print(f"   - {migrated} items migrated from JSON")
print(f"   - {count} total items in database")

# Show first 5 items
print("\nFirst 5 items in database:")
cursor.execute('SELECT serial, name, mrp, gst FROM store_items ORDER BY serial LIMIT 5')
for row in cursor.fetchall():
    print(f"   #{row[0]}: {row[1]} - Rs {row[2]} (GST {row[3]}%)")

conn.close()
print("\n✅ Database ready!")
