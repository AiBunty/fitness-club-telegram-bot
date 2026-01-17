#!/usr/bin/env python3
"""
Initialize database schema by running schema.sql
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Load and execute schema.sql"""
    schema_file = project_root / "schema.sql"
    
    if not schema_file.exists():
        logger.error(f"Schema file not found: {schema_file}")
        return False
    
    try:
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        logger.info("Creating database schema...")
        
        # Get connection
        db = DatabaseConnection()
        conn = db.get_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Execute schema SQL statement by statement
        statements = schema_sql.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                    logger.info(f"✅ Executed: {statement[:50]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Statement skipped: {str(e)[:100]}")
        
        cursor.close()
        conn.commit()
        logger.info("✅ Database schema created successfully!")
        
        # Verify tables
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        
        logger.info(f"✅ Total tables created: {len(table_names)}")
        for name in table_names:
            logger.info(f"   - {name}")
        
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
