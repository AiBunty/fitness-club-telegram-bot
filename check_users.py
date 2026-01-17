from src.database.connection import execute_query

# Count users
result = execute_query("SELECT COUNT(*) as user_count FROM users")
if result:
    print(f"✅ Total Users in Database: {result[0]['user_count']}")
else:
    print("No users found")

# List users
users = execute_query("SELECT user_id, full_name, phone, fee_status FROM users LIMIT 10")
if users:
    print("\n📋 Recent Users:")
    for u in users:
        print(f"  • {u['full_name']} ({u['phone']}) - Status: {u['fee_status']}")
else:
    print("No users")
