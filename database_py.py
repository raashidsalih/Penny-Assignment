"""Database connection and query execution utilities."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config_py import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and query execution."""
    
    def __init__(self):
        """Initialize database connection pool."""
        self.pool: Optional[ConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        # Prevent re-initialization if pool exists and is open
        if self.pool and not self.pool.closed:
            return

        try:
            self.pool = ConnectionPool(
                conninfo=config.database_url,
                min_size=2,
                max_size=10,
                timeout=30,
                kwargs={"row_factory": dict_row}
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            try:
                conn.rollback()
            except Exception:
                pass  # If connection is already closed/broken, ignore
            
            self.pool.putconn(conn)
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Execute a SQL query and return results."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    
                    if cur.description:
                        results = cur.fetchall()
                        return True, results, None
                    else:
                        conn.commit()
                        return True, [], None
                        
        except psycopg.errors.SyntaxError as e:
            return False, None, f"SQL Syntax Error: {str(e)}"
        except Exception as e:
            return False, None, f"Database Error: {str(e)}"
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close(self):
        """Close the connection pool."""
        if self.pool:
            self.pool.close()

# Global instance
db_manager = DatabaseManager()