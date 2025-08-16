"""Schema manager with caching to avoid repeated schema checks."""

import os
import threading
from typing import Set

import duckdb

from ..io.logger import get_logger
from .schema import get_all_schemas

logger = get_logger("schema_manager")


class SchemaManager:
    """Schema manager that ensures schema is created only once per session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._initialized_databases: Set[str] = set()

    def ensure_schema(self, db: duckdb.DuckDBPyConnection, db_path: str) -> None:
        """Ensure schema exists for the given database connection.

        Args:
            db: DuckDB connection
            db_path: Database file path (used as cache key)
        """
        # Use absolute path as cache key
        cache_key = os.path.abspath(db_path)

        # Check if schema already ensured for this database
        if cache_key in self._initialized_databases:
            logger.debug(f"Schema already initialized for {cache_key}")
            return

        with self._lock:
            # Double-check inside lock
            if cache_key in self._initialized_databases:
                return

            logger.debug(f"Initializing schema for {cache_key}")

            # Create all tables
            for schema_sql in get_all_schemas():
                db.execute(schema_sql)

            # Mark as initialized
            self._initialized_databases.add(cache_key)

            logger.debug(f"Schema initialized for {cache_key}")

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
        cache_key = os.path.abspath(db_path)
        return cache_key in self._initialized_databases
