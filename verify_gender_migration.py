#!/usr/bin/env python3
"""Verify gender column was added to users table"""

from src.database.connection import execute_query

# Check if gender column exists
check_query = """
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'users' 
    ORDER BY ordinal_position
"""

result = execute_query(check_query)
if result:
    print("✅ Users table columns:")
    for row in result:
        # Handle both tuple and dict results
        if isinstance(row, dict):
            print(f"   - {row.get('column_name')}: {row.get('data_type')}")
        else:
            print(f"   - {row[0]}: {row[1]}")
    
    # Check if gender is in the list
    columns = []
    for row in result:
        if isinstance(row, dict):
            columns.append(row.get('column_name'))
        else:
            columns.append(row[0])
    
    if 'gender' in columns:
        print("\n✅ Gender column successfully added!")
    else:
        print("\n❌ Gender column not found!")
else:
    print("❌ Could not retrieve table structure")
