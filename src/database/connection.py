import psycopg2
from psycopg2 import InterfaceError, OperationalError, pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from src.config import DATABASE_CONFIG

logger = logging.getLogger(__name__)

class DatabaseConnectionPool:
    """Thread-safe connection pool for concurrent user access"""
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
        return cls._instance
    
    def get_pool(self):
        if self._pool is None or self._pool.closed:
            # Create pool with min 5 connections, max 50 connections
            # Supports 200+ concurrent users with safety margin
            db_config = dict(DATABASE_CONFIG)
            # Add connection timeout
            db_config['connect_timeout'] = 10
            logger.info(f"[DB] Attempting connection to {db_config.get('host')}:{db_config.get('port')}...")
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=5,
                maxconn=50,
                **db_config
            )
            logger.info("Database connection pool created (5-50 connections)")
        return self._pool
    
    def close_pool(self):
        """Close all connections in the pool"""
        if self._pool:
            self._pool.closeall()
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
    try:
        # Get connection from pool (blocks if all connections busy)
        conn = pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        # Try rollback if possible; if the connection is already closed, discard it
        try:
            if conn:
                conn.rollback()
        except (InterfaceError, OperationalError) as rollback_exc:
            logger.warning(f"Rollback failed - connection closed or broken: {rollback_exc}")
            # Try to remove/close this connection from the pool so it's not reused
            try:
                if conn:
                    try:
                        pool.putconn(conn, close=True)
                        logger.info("Closed broken DB connection and removed from pool")
                    except Exception as close_exc:
                        logger.debug(f"Error closing broken connection: {close_exc}")
                    finally:
                        # Ensure we don't try to reuse this connection further
                        conn = None
            except Exception as close_exc:
                logger.debug(f"Error closing broken connection (outer): {close_exc}")
                conn = None

        logger.error(f"Database error: {e}")
        raise
    finally:
        # Close cursor if open
        try:
            if cursor:
                cursor.close()
        except Exception as cur_exc:
            logger.debug(f"Error closing cursor: {cur_exc}")

        # Return connection to pool only if it's still valid (conn may have been closed above)
        try:
            if conn and getattr(conn, "closed", 1) == 0:
                pool.putconn(conn)
        except Exception as put_exc:
            logger.debug(f"Error returning connection to pool: {put_exc}")

def execute_query(query: str, params: tuple = None, fetch_one: bool = False, retry_count: int = 0):
    """Execute a query using connection pool - supports concurrent users with auto-retry on connection errors"""
    max_retries = 2
    
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
        error_msg = str(e)
        logger.error(f"Query failed: {error_msg}")
        
        # Retry on SSL/connection errors
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
    return pool.getconn()


def release_connection(conn):
    """Return connection to pool after use
    
    Args:
        conn: Connection object obtained from get_connection()
    """
    if conn is None:
        return
    
    pool_manager = DatabaseConnectionPool()
    pool = pool_manager.get_pool()
    
    try:
        # Check if connection is still valid
        if getattr(conn, "closed", 1) == 0:
            pool.putconn(conn)
            logger.debug("Connection returned to pool")
        else:
            # Connection is closed, remove from pool
            pool.putconn(conn, close=True)
            logger.warning("Closed connection removed from pool")
    except Exception as e:
        logger.error(f"Error returning connection to pool: {e}")


def get_db_connection():
    """Compatibility shim for older tests/modules expecting `get_db_connection`.

    Delegates to `get_connection()` to preserve existing pool behaviour.
    IMPORTANT: Always call release_connection(conn) when done!
    """
    return get_connection()

def test_connection() -> bool:
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT 1")
            logger.info("Database connection OK")
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
