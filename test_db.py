#!/usr/bin/env python3
"""Test database operations directly"""
import sys
import os

# Set environment before imports
os.environ['USE_LOCAL_DB'] = 'true'
os.environ['USE_REMOTE_DB'] = 'false'
os.environ['ENV'] = 'local'

sys.path.insert(0, '.')

print("Testing database connection...")
try:
    from src.database.store_items_operations import load_store_items_from_db
    items = load_store_items_from_db()
    print(f"✓ Successfully loaded {len(items)} items from database")
    if items:
        print("\nFirst 3 items:")
        for item in items[:3]:
            print(f"  - {item['name']} (MRP: Rs {item['mrp']})")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
