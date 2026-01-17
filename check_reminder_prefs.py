"""Check reminder_preferences table"""
import psycopg2
from src.config import DATABASE_CONFIG as DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'reminder_preferences'
        )
    """)
    exists = cursor.fetchone()[0]
    print(f"Table exists: {exists}")
    
    if exists:
        # Get table schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'reminder_preferences'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print("\nTable Schema:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM reminder_preferences")
        count = cursor.fetchone()[0]
        print(f"\nTotal rows: {count}")
        
        # Get some sample data
        cursor.execute("SELECT * FROM reminder_preferences LIMIT 3")
        rows = cursor.fetchall()
        print(f"\nSample data (first 3 rows):")
        for row in rows:
            print(f"  {row}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
