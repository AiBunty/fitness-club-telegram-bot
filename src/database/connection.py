import pymysql
from pymysql import InterfaceError, OperationalError
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
import sqlite3
from pathlib import Path
from src.config import DATABASE_CONFIG, USE_REMOTE_DB, USE_LOCAL_DB
import threading

logger = logging.getLogger(__name__)

# SQLite database path for local mode
# connection.py is at: src/database/connection.py
# .parent = src/database/
# .parent.parent = src/
# .parent.parent.parent = fitness-club-telegram-bot/ (project root)
LOCAL_DB_PATH = Path(__file__).resolve().parent.parent.parent / 'fitness_club.db'

# Guard to run SQLite schema check once per process
_sqlite_schema_checked = False


def _ensure_sqlite_reminder_schema(conn: sqlite3.Connection) -> None:
    """Ensure reminder_profile exists with required columns in local SQLite mode."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(reminder_profile)")
        cols = [row[1] for row in cursor.fetchall()]  # row[1] is column name

        # Create table if missing
        if not cols:
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reminder_profile (
                        user_id INTEGER PRIMARY KEY,
                        weight_enabled INTEGER DEFAULT 1,
                        weight_time TEXT DEFAULT '06:00',
                        water_enabled INTEGER DEFAULT 1,
                        water_interval_minutes INTEGER DEFAULT 60,
                        lunch_enabled INTEGER DEFAULT 0,
                        lunch_time TEXT DEFAULT '13:00',
                        dinner_enabled INTEGER DEFAULT 0,
                        dinner_time TEXT DEFAULT '20:00',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
                cursor.execute("PRAGMA table_info(reminder_profile)")
                cols = [row[1] for row in cursor.fetchall()]
                logger.info("[DB] created reminder_profile table with default columns for local mode")
            except Exception as create_err:
                logger.error(f"[DB] Failed to create reminder_preferences table: {create_err}")
                return

        desired = {
            'weight_enabled': "ALTER TABLE reminder_profile ADD COLUMN weight_enabled INTEGER DEFAULT 1",
            'weight_time': "ALTER TABLE reminder_profile ADD COLUMN weight_time TEXT DEFAULT '06:00'",
            'water_enabled': "ALTER TABLE reminder_profile ADD COLUMN water_enabled INTEGER DEFAULT 1",
            'water_interval_minutes': "ALTER TABLE reminder_profile ADD COLUMN water_interval_minutes INTEGER DEFAULT 60",
            'lunch_enabled': "ALTER TABLE reminder_profile ADD COLUMN lunch_enabled INTEGER DEFAULT 0",
            'lunch_time': "ALTER TABLE reminder_profile ADD COLUMN lunch_time TEXT DEFAULT '13:00'",
            'dinner_enabled': "ALTER TABLE reminder_profile ADD COLUMN dinner_enabled INTEGER DEFAULT 0",
            'dinner_time': "ALTER TABLE reminder_profile ADD COLUMN dinner_time TEXT DEFAULT '20:00'",
            'updated_at': "ALTER TABLE reminder_profile ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP",
        }

        for col_name, alter_sql in desired.items():
            if col_name not in cols:
                try:
                    cursor.execute(alter_sql)
                    logger.info(f"[DB] Added missing column {col_name} to reminder_profile")
                except Exception as add_err:
                    logger.error(f"[DB] Failed to add column {col_name}: {add_err}")
        conn.commit()
    except Exception as e:
        logger.error(f"[DB] Failed reminder_profile schema check: {e}")

class DatabaseConnectionPool:
    """Thread-safe connection pool for concurrent user access"""
    _instance = None
    _pool = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
        return cls._instance
    
    def get_pool(self):
        # In local mode, we use SQLite instead of MySQL
        if USE_LOCAL_DB and not USE_REMOTE_DB:
            logger.info("[DB] local mode active, using SQLite")
            return None  # Return None to indicate SQLite mode, not MySQL pool

        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    # Create MySQL connection pool
                    db_config = dict(DATABASE_CONFIG)
                    db_config['cursorclass'] = DictCursor
                    db_config['autocommit'] = False
                    db_config['charset'] = 'utf8mb4'
                    db_config['connect_timeout'] = 30
                    db_config['read_timeout'] = 30
                    db_config['write_timeout'] = 30
                    
                    logger.info(f"[DB] Attempting connection to {db_config.get('host')}:{db_config.get('port')}...")
                    # Create a simple pool structure
                    self._pool = {
                        'config': db_config,
                        'connections': []
                    }
                    logger.info("Database connection pool initialized for MySQL")
        return self._pool
    
    def close_pool(self):
        """Close all connections in the pool"""
        if self._pool:
            for conn in self._pool.get('connections', []):
                try:
                    conn.close()
                except:
                    pass
            self._pool = None
            logger.info("Database connection pool closed")

# Backward compatibility alias
DatabaseConnection = DatabaseConnectionPool

@contextmanager
def get_db_cursor(commit=True):
    """Get a cursor from the connection pool with timeout handling"""
    pool_manager = DatabaseConnectionPool()
    pool = pool_manager.get_pool()
    conn = None
    cursor = None

    # If running in local-mode, use SQLite
    global _sqlite_schema_checked

    if pool is None and USE_LOCAL_DB:
        try:
            conn = sqlite3.connect(LOCAL_DB_PATH)
            conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
            if not _sqlite_schema_checked:
                _ensure_sqlite_reminder_schema(conn)
                _sqlite_schema_checked = True
            cursor = conn.cursor()
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"SQLite error: {e}")
            raise
        finally:
            try:
                if cursor:
                    cursor.close()
            except:
                pass
            try:
                if conn:
                    conn.close()
            except:
                pass
    else:
        # MySQL mode
        try:
            pool_config = pool['config']
            conn = pymysql.connect(**pool_config)
            cursor = conn.cursor()
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            # Try rollback if possible
            try:
                if conn:
                    conn.rollback()
            except (InterfaceError, OperationalError) as rollback_exc:
                logger.warning(f"Rollback failed - connection closed or broken: {rollback_exc}")
                try:
                    if conn:
                        conn.close()
                        logger.info("Closed broken DB connection")
                        conn = None
                except Exception as close_exc:
                    logger.debug(f"Error closing broken connection: {close_exc}")
                    conn = None

            logger.error(f"Database error: {e}")
            raise
        finally:
            # Close cursor and connection
            try:
                if cursor:
                    cursor.close()
            except Exception as cur_exc:
                logger.debug(f"Error closing cursor: {cur_exc}")

            try:
                if conn:
                    conn.close()
            except Exception as conn_exc:
                logger.debug(f"Error closing connection: {conn_exc}")

def execute_query(query: str, params: tuple = None, fetch_one: bool = False, retry_count: int = 0):
    """Execute a query using connection pool - supports concurrent users with auto-retry on connection errors
    
    Automatically converts PostgreSQL syntax (%s) to SQLite syntax (?) when in local mode.
    """
    max_retries = 2
    
    # Convert PostgreSQL %s placeholders to SQLite ? placeholders in local mode
    if USE_LOCAL_DB and not USE_REMOTE_DB:
        query = query.replace('%s', '?')
    
    try:
        with get_db_cursor() as cursor:
            if cursor is None:
                # Should not happen anymore with SQLite support
                q = query.strip().upper()
                if q.startswith('SELECT') or 'RETURNING' in q:
                    return None if fetch_one else []
                return 0
            cursor.execute(query, params or ())
            query_upper = query.strip().upper()
            if query_upper.startswith('SELECT') or 'RETURNING' in query_upper:
                if fetch_one:
                    result = cursor.fetchone()
                    return dict(result) if result else None
                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []
            return cursor.rowcount
    except (InterfaceError, OperationalError, sqlite3.Error) as e:
        error_msg = str(e)
        logger.error(f"Query failed: {error_msg}")
        
        # Skip retry logic for SQLite errors (local mode)
        if isinstance(e, sqlite3.Error):
            raise
        
        # Retry on SSL/connection errors (PostgreSQL only)
        if retry_count < max_retries and ('SSL' in error_msg or 'closed unexpectedly' in error_msg or 'connection' in error_msg.lower()):
            logger.warning(f"Connection error detected, retrying... (attempt {retry_count + 1}/{max_retries})")
            # Force recreate the connection pool
            pool_manager = DatabaseConnectionPool()
            if pool_manager._pool:
                try:
                    pool_manager._pool.closeall()
                except:
                    pass
                pool_manager._pool = None
            
            # Retry the query
            return execute_query(query, params, fetch_one, retry_count + 1)
        
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        raise

def get_connection():
    """Get database connection from pool (for backward compatibility)
    
    IMPORTANT: Always call release_connection(conn) when done!
    """
    pool_manager = DatabaseConnectionPool()
    pool = pool_manager.get_pool()
    if pool is None:
        logger.info("[DB] get_connection called in local mode - returning None")
        return None
    
    # Create new MySQL connection
    try:
        pool_config = pool['config']
        conn = pymysql.connect(**pool_config)
        return conn
    except Exception as e:
        logger.error(f"Failed to get connection: {e}")
        raise


def release_connection(conn):
    """Return connection to pool after use (for MySQL, just close it)
    
    Args:
        conn: Connection object obtained from get_connection()
    """
    if conn is None:
        return

    try:
        conn.close()
        logger.debug("Connection closed")
    except Exception as e:
        logger.error(f"Error closing connection: {e}")


def get_db_connection():
    """Compatibility shim for older tests/modules expecting `get_db_connection`.

    Delegates to `get_connection()` to preserve existing pool behaviour.
    IMPORTANT: Always call release_connection(conn) when done!
    """
    return get_connection()

def test_connection() -> bool:
    # In local/test mode, consider DB test passed but log reason
    if USE_LOCAL_DB and not USE_REMOTE_DB:
        logger.info("[DB] local mode active - skipping DB connectivity test")
        return True

    try:
        with get_db_cursor(commit=False) as cursor:
            if cursor is None:
                logger.info("[DB] No DB pool available during test_connection")
                return True
            cursor.execute("SELECT 1")
            logger.info("Database connection OK")
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
