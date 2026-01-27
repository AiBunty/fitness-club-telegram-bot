#!/usr/bin/env python3
"""
Migration: Create store_items table for invoices (simplified)
Migrates existing JSON store items to database
"""

import json
import logging
from pathlib import Path
from src.database.connection import execute_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_store_items():
    """Create store_items table and migrate JSON data"""
    
    # Create store_items table (simplified for invoice use)
    create_table_query = """
    CREATE TABLE IF NOT EXISTS store_items (
        serial SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        hsn VARCHAR(50) NOT NULL,
        mrp DECIMAL(10, 2) NOT NULL,
        gst DECIMAL(5, 2) NOT NULL DEFAULT 18.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(name, hsn)
    );
    """
    
    # Create indexes
    create_indexes_query = """
    CREATE INDEX IF NOT EXISTS idx_store_items_name ON store_items(name);
    CREATE INDEX IF NOT EXISTS idx_store_items_hsn ON store_items(hsn);
    """
    
    try:
        print("Creating store_items table...")
        execute_query(create_table_query)
        print("[OK] store_items table created")
        
        print("Creating indexes...")
        execute_query(create_indexes_query)
        print("[OK] Indexes created")
        
        # Load existing JSON data
        json_path = Path(__file__).parent / 'data' / 'store_items.json'
        if json_path.exists():
            print(f"\nMigrating data from {json_path}...")
            with open(json_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
            
            # Insert items
            insert_query = """
            INSERT INTO store_items (serial, name, hsn, mrp, gst)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name, hsn) DO UPDATE SET
                mrp = EXCLUDED.mrp,
                gst = EXCLUDED.gst,
                updated_at = CURRENT_TIMESTAMP
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
                    logger.error(f"Error migrating item {item.get('name')}: {e}")
            
            print(f"[OK] Migrated {migrated}/{len(items)} items from JSON")
        else:
            print("[INFO] No JSON file found, skipping data migration")
        
        # Reset serial sequence to continue from max
        reset_sequence_query = """
        SELECT setval('store_items_serial_seq', COALESCE((SELECT MAX(serial) FROM store_items), 0) + 1, false);
        """
        execute_query(reset_sequence_query)
        print("[OK] Serial sequence reset")
        
        print("\n[SUCCESS] Store items migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    migrate_store_items()
