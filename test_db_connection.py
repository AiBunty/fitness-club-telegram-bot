import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST')
dbname = os.getenv('DB_NAME')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASS')
port = int(os.getenv('DB_PORT', 3306))

print(f"Attempting to connect to: {host}:{port}")
print(f"Database: {dbname}")
print(f"User: {user}")

try:
    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=dbname,
        port=port,
        connect_timeout=5  # 5 second timeout
    )
    print('✓ Connection successful!')
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    print('✓ Query executed successfully!')
    conn.close()
except pymysql.MySQLError as e:
    print(f'✗ MySQL Error: {e}')
except Exception as e:
    print(f'✗ Connection failed: {e}')
