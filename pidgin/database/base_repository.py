"""Base repository with common database operations."""

import json
from typing import Any, Dict, List, Optional, Tuple

import duckdb

from ..io.logger import get_logger

logger = get_logger("base_repository")

# Optional query profiling (imported only when needed)
try:
    from .query_profiler import query_profiler

    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False


class BaseRepository:
    """Base repository with common database operations.

    Provides connection management, schema helpers, and common query patterns
    for all repository implementations.
    """

    # Whitelist of valid table names to prevent SQL injection
    VALID_TABLES = {
        "conversations",
        "conversation_turns",
        "experiments",
        "metrics",
        "thinking_traces",
        "token_usage",
    }

    def __init__(self, db: duckdb.DuckDBPyConnection, enable_profiling: bool = False):
        """Initialize with DuckDB connection.

        Args:
            db: Active DuckDB connection
            enable_profiling: Whether to enable query profiling
        """
        self.db = db
        self.enable_profiling = enable_profiling and PROFILING_AVAILABLE

    def execute(self, query: str, params: Optional[List[Any]] = None):
        """Execute a query with optional parameters.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            Query result
        """
        if self.enable_profiling:
            with query_profiler.profile_query(query, params):
                if params is None:
                    return self.db.execute(query)
                return self.db.execute(query, params)
        else:
            if params is None:
                return self.db.execute(query)
            return self.db.execute(query, params)

    def fetchone(
        self, query: str, params: Optional[List[Any]] = None
    ) -> Optional[Tuple]:
        """Execute query and fetch one result.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            Single row as tuple or None
        """
        result = self.execute(query, params).fetchone()
        return result

    def fetchall(self, query: str, params: Optional[List[Any]] = None) -> List[Tuple]:
        """Execute query and fetch all results.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            List of rows as tuples
        """
        return self.execute(query, params).fetchall()

    def row_to_dict(self, row: Tuple, cursor=None) -> Dict[str, Any]:
        """Convert a database row to dictionary.

        Args:
            row: Database row tuple
            cursor: Cursor with description (uses self.db if not provided)

        Returns:
            Dictionary with column names as keys
        """
        if not row:
            return {}

        if cursor is None:
            cursor = self.db

        cols = [desc[0] for desc in cursor.description]
        return dict(zip(cols, row))

    def parse_json_field(self, value: Any) -> Any:
        """Parse a JSON field, returning original value if parsing fails.

        Args:
            value: Value to parse

        Returns:
            Parsed JSON or original value
        """
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def exists(self, table: str, **conditions) -> bool:
        """Check if a record exists with given conditions.

        Args:
            table: Table name
            **conditions: Column=value conditions

        Returns:
            True if record exists
        """
        if not conditions:
            raise ValueError("At least one condition is required")

        where_parts = [f"{col} = ?" for col in conditions.keys()]
        where_clause = " AND ".join(where_parts)
        # Validate table name against whitelist
        if table not in self.VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")

        query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"  # nosec B608

        result = self.fetchone(query, list(conditions.values()))
        return result[0] > 0 if result else False

    def count(self, table: str, **conditions) -> int:
        """Count records matching conditions.

        Args:
            table: Table name
            **conditions: Column=value conditions

        Returns:
            Number of matching records
        """
        if conditions:
            where_parts = [f"{col} = ?" for col in conditions.keys()]
            where_clause = " WHERE " + " AND ".join(where_parts)
            params = list(conditions.values())
        else:
            where_clause = ""
            params = []

        # Validate table name against whitelist
        if table not in self.VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")

        query = f"SELECT COUNT(*) FROM {table}{where_clause}"  # nosec B608
        result = self.fetchone(query, params)
        return result[0] if result else 0
