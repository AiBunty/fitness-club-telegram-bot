#!/usr/bin/env python
"""Check current fee status of users"""

from src.database.connection import execute_query

query = '''
SELECT user_id, full_name, phone, fee_status, approval_status, fee_paid_date
FROM users 
WHERE phone IN ('9420492380', '9158243377', '8378962788', '919330033000')
ORDER BY full_name
'''

print("\nCurrent User Fee Status:")
print("-" * 90)
print(f"{'Name':<25} | {'Phone':<15} | {'Fee Status':<10} | {'Paid Date':<20}")
print("-" * 90)

results = execute_query(query)
if results:
    for user in results:
        phone = user['phone'] if user['phone'] else 'N/A'
        fee_status = user['fee_status'] if user['fee_status'] else 'unpaid'
        paid_date = user['fee_paid_date'] if user['fee_paid_date'] else 'Never'
        print(f"{user['full_name']:<25} | {phone:<15} | {fee_status:<10} | {str(paid_date):<20}")
else:
    print("No users found")

print("-" * 90)
print("\nThese should be 'paid' if admin has approved payments!")
