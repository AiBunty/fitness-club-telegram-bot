import psycopg2
from psycopg2 import InterfaceError, OperationalError
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from src.config import DATABASE_CONFIG

logger = logging.getLogger(__name__)

class DatabaseConnection:
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def get_connection(self):
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(**DATABASE_CONFIG)
            logger.info("Database connected")
        return self._connection

@contextmanager
def get_db_cursor(commit=True):
    db = DatabaseConnection()
    conn = db.get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        cursor.close()

def execute_query(query: str, params: tuple = None, fetch_one: bool = False):
    """Execute a query with a single automatic retry if connection was closed."""
    for attempt in range(2):
        try:
            with get_db_cursor() as cursor:
                cursor.execute(query, params or ())
                query_upper = query.strip().upper()
                if query_upper.startswith('SELECT') or 'RETURNING' in query_upper:
                    if fetch_one:
                        result = cursor.fetchone()
                        return dict(result) if result else None
                    results = cursor.fetchall()
                    return [dict(row) for row in results] if results else []
                return cursor.rowcount
        except (InterfaceError, OperationalError) as e:
            if attempt == 0:
                logger.warning(f"DB connection closed; reopening and retrying once. Details: {e}")
                DatabaseConnection()._connection = None  # force reconnect
                continue
            logger.error(f"Query failed after retry: {e}")
            raise
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

def get_connection():
    """Get database connection (for backward compatibility)"""
    db = DatabaseConnection()
    return db.get_connection()

def test_connection() -> bool:
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT 1")
            logger.info("Database connection OK")
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
