#!/usr/bin/env python3
"""
Update UPI ID in database
"""

from src.database.connection import execute_query

# Check if table exists and has data
result = execute_query('SELECT * FROM gym_settings LIMIT 1', fetch_one=True)
if result:
    print(f'Current UPI ID in DB: {result}')
else:
    print('No records found, inserting...')
    execute_query("INSERT INTO gym_settings (id, upi_id, gym_name) VALUES (1, '9158243377@ybl', 'Fitness Club Gym')")

# Update with new UPI ID
execute_query("UPDATE gym_settings SET upi_id = '9158243377@ybl' WHERE id = 1")
print('✓ Database updated with new UPI ID: 9158243377@ybl')

# Verify
result = execute_query('SELECT upi_id FROM gym_settings WHERE id = 1', fetch_one=True)
if result:
    upi_id = result.get('upi_id') if isinstance(result, dict) else result[0]
    print(f'✓ Verified: UPI ID is now {upi_id}')
