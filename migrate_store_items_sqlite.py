#!/usr/bin/env python3
"""
Standalone migration: Create store_items table for invoices
Run this while bot is running - uses direct psycopg2
"""

import json
import os
from pathlib import Path

# Use local SQLite if available, otherwise skip DB part
try:
    import sqlite3
    LOCAL_DB = Path(__file__).parent / 'data' / 'fitness_club_local.db'
    
    def execute_query(query, params=None):
        conn = sqlite3.connect(LOCAL_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        result = cursor.fetchall()
        conn.close()
        return [dict(row) for row in result] if result else []
    
    def migrate_store_items():
        """Create store_items table and migrate JSON data"""
        
        # Create store_items table (simplified for invoice use)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS store_items (
            serial INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hsn TEXT NOT NULL,
            mrp REAL NOT NULL,
            gst REAL NOT NULL DEFAULT 18.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, hsn)
        );
        """
        
        # Create indexes
        create_indexes_query = """
        CREATE INDEX IF NOT EXISTS idx_store_items_name ON store_items(name);
        """
        create_indexes_query2 = """
        CREATE INDEX IF NOT EXISTS idx_store_items_hsn ON store_items(hsn);
        """
        
        try:
            print("Creating store_items table...")
            execute_query(create_table_query)
            print("[OK] store_items table created")
            
            print("Creating indexes...")
            execute_query(create_indexes_query)
            execute_query(create_indexes_query2)
            print("[OK] Indexes created")
            
            # Load existing JSON data
            json_path = Path(__file__).parent / 'data' / 'store_items.json'
            if json_path.exists():
                print(f"\nMigrating data from {json_path}...")
                with open(json_path, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                
                # Insert items
                insert_query = """
                INSERT OR REPLACE INTO store_items (serial, name, hsn, mrp, gst)
                VALUES (?, ?, ?, ?, ?)
                """
                
                migrated = 0
                for item in items:
                    try:
                        # Handle both 'gst' and 'gst_percent' fields
                        gst_value = item.get('gst') or item.get('gst_percent', 18.0)
                        execute_query(insert_query, (
                            item.get('serial'),
                            item.get('name'),
                            item.get('hsn'),
                            float(item.get('mrp', 0)),
                            float(gst_value)
                        ))
                        migrated += 1
                    except Exception as e:
                        print(f"Error migrating item {item.get('name')}: {e}")
                
                print(f"[OK] Migrated {migrated}/{len(items)} items from JSON")
            else:
                print("[INFO] No JSON file found, skipping data migration")
            
            print("\n[SUCCESS] Store items migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    if __name__ == "__main__":
        migrate_store_items()

except ImportError:
    print("sqlite3 not available, skipping migration")
