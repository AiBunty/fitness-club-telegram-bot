#!/usr/bin/env python3
"""
Test the fixed search_store_items_db_only function
"""
import os
os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
os.environ['ENV'] = 'remote'

import sys
sys.path.insert(0, '.')

from src.invoices_v2.search_items_db_only import search_store_items_db_only

print("=" * 80)
print("TEST: Store Item Search After Fix")
print("=" * 80)

test_cases = [
    ("6", "numeric search for serial 6"),
    ("2", "numeric search for serial 2"),
    ("protein", "text search for 'protein'"),
    ("item", "text search for 'item'"),
]

for query, description in test_cases:
    print(f"\n--- Test: {description} ---")
    print(f"Query: '{query}'")
    
    try:
        results = search_store_items_db_only(query)
        print(f"Results: {len(results)} items found")
        
        if results:
            for i, item in enumerate(results[:2], 1):
                print(f"  Result {i}: serial={item.get('serial_no')}, name={item.get('item_name')}, mrp={item.get('mrp')}")
        else:
            print(f"  ❌ No items found")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("Test complete!")
