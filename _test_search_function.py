#!/usr/bin/env python3
"""
Direct test of search_store_items_db_only() function
"""
import os
import sys

os.environ['USE_LOCAL_DB'] = 'false'
os.environ['USE_REMOTE_DB'] = 'true'
os.environ['ENV'] = 'remote'

sys.path.insert(0, '.')

print("=" * 80)
print("DIRECT FUNCTION TEST: search_store_items_db_only()")
print("=" * 80)

try:
    from src.invoices_v2.search_items_db_only import search_store_items_db_only
    from src.database.connection import execute_query
    
    # Test 1: Check if function can be imported
    print("\n✓ Function imported successfully")
    
    # Test 2: Check schema detection
    print("\n" + "=" * 80)
    print("SCHEMA DETECTION TEST:")
    print("=" * 80)
    
    try:
        from src.invoices_v2.search_items_db_only import _get_store_items_schema
        schema = _get_store_items_schema()
        
        print(f"\n✓ Schema detection executed:")
        for key, val in schema.items():
            status = "✓" if val else "✗"
            print(f"  {status} {key}: {val}")
    except Exception as e:
        print(f"\n❌ Schema detection error: {e}")
    
    # Test 3: Run actual search for serial #2
    print("\n" + "=" * 80)
    print("SEARCH FUNCTION TEST (Serial #2):")
    print("=" * 80)
    
    results = search_store_items_db_only("2")
    
    print(f"\n  Search term: '2'")
    print(f"  Results returned: {len(results) if results else 0}")
    
    if results:
        print(f"\n  ✓ Items found:")
        for item in results:
            print(f"\n    Item details:")
            for key, val in item.items():
                print(f"      {key}: {val}")
    else:
        print(f"\n  ❌ No items found!")
    
    # Test 4: Try text search
    print("\n" + "=" * 80)
    print("SEARCH FUNCTION TEST (Text: 'protein'):")
    print("=" * 80)
    
    results_text = search_store_items_db_only("protein")
    
    print(f"\n  Search term: 'protein'")
    print(f"  Results returned: {len(results_text) if results_text else 0}")
    
    if results_text:
        print(f"\n  ✓ Items found:")
        for i, item in enumerate(results_text[:3]):  # Show first 3
            print(f"    {i+1}. {item.get('item_name')} (Serial #{item.get('serial_no')})")
    
    # Test 5: Call raw execute_query to verify connection
    print("\n" + "=" * 80)
    print("RAW DATABASE QUERY TEST:")
    print("=" * 80)
    
    raw_results = execute_query("SELECT COUNT(*) as count FROM store_items", fetch_one=True)
    
    if raw_results:
        print(f"\n  ✓ Direct DB query works")
        print(f"    Total items: {raw_results.get('count')}")
    else:
        print(f"\n  ❌ Direct DB query failed")
    
    print("\n" + "=" * 80)
    print("✓ FUNCTION TEST COMPLETE")
    print("=" * 80)

except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
