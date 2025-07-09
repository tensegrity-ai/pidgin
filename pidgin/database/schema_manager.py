"""Schema manager with caching to avoid repeated schema checks."""

import threading
from typing import Set, Optional
import duckdb

from .schema import get_all_schemas
from ..io.logger import get_logger

logger = get_logger("schema_manager")


class SchemaManager:
    """Singleton schema manager that ensures schema is created only once per session."""
    
    _instance: Optional['SchemaManager'] = None
    _lock = threading.Lock()
    _initialized_databases: Set[str] = set()
    
    def __new__(cls):
        """Create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def ensure_schema(self, db: duckdb.DuckDBPyConnection, db_path: str) -> None:
        """Ensure schema exists for the given database connection.
        
        Args:
            db: DuckDB connection
            db_path: Database file path (used as cache key)
        """
        # Use absolute path as cache key
        import os
        cache_key = os.path.abspath(db_path)
        
        # Check if schema already ensured for this database
        if cache_key in self._initialized_databases:
            logger.debug(f"Schema already initialized for {cache_key}")
            return
        
        with self._lock:
            # Double-check inside lock
            if cache_key in self._initialized_databases:
                return
            
            logger.info(f"Initializing schema for {cache_key}")
            
            # Create all tables
            for schema_sql in get_all_schemas():
                db.execute(schema_sql)
            
            # Mark as initialized
            self._initialized_databases.add(cache_key)
            
            logger.info(f"Schema initialized for {cache_key}")
    
    def clear_cache(self) -> None:
        """Clear the schema cache (useful for testing)."""
        with self._lock:
            self._initialized_databases.clear()
            logger.debug("Schema cache cleared")
    
    def is_initialized(self, db_path: str) -> bool:
        """Check if schema is initialized for a database.
        
        Args:
            db_path: Database file path
            
        Returns:
            True if schema has been initialized
        """
        import os
        cache_key = os.path.abspath(db_path)
        return cache_key in self._initialized_databases


# Global instance
schema_manager = SchemaManager()