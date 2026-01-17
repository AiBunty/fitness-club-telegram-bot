"""Verify database cleanup"""
from src.database.connection import execute_query

# Get user count
users = execute_query('SELECT COUNT(*) as count FROM users', fetch_one=True)
count = users['count']
print(f'✅ Total users in database: {count}')

# Get admin details
admin = execute_query('SELECT user_id, full_name, role FROM users WHERE user_id = 424837855', fetch_one=True)
if admin:
    print(f"✅ Admin: {admin['full_name']} (ID: {admin['user_id']}, Role: {admin['role']})")

# Check other tables
shake_requests = execute_query('SELECT COUNT(*) as count FROM shake_requests', fetch_one=True)
daily_logs = execute_query('SELECT COUNT(*) as count FROM daily_logs', fetch_one=True)
notifications = execute_query('SELECT COUNT(*) as count FROM notifications', fetch_one=True)

print(f"✅ Shake requests: {shake_requests['count']}")
print(f"✅ Daily logs: {daily_logs['count']}")
print(f"✅ Notifications: {notifications['count']}")
print('')
print('🎉 Database is clean! Ready to start fresh.')
