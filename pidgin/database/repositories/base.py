"""Base repository class for database operations."""

from abc import ABC, abstractmethod
from typing import Optional
import asyncio
import random
from ..async_duckdb import AsyncDuckDB
from ...core.exceptions import DatabaseError, DatabaseLockError, DatabaseConnectionError
from ...io.logger import get_logger

logger = get_logger("repository")


class BaseRepository(ABC):
    """Base class for all repository implementations."""
    
    def __init__(self, db: AsyncDuckDB):
        """Initialize repository with database connection.
        
        Args:
            db: AsyncDuckDB instance for database operations
        """
        self.db = db
        self._lock = asyncio.Lock()
    
    async def _retry_with_backoff(self, func, max_retries: Optional[int] = None):
        """Retry a database operation with exponential backoff.
        
        Args:
            func: Async function to retry
            max_retries: Maximum number of retries (default from constants)
            
        Returns:
            Result from the function
            
        Raises:
            DatabaseError: If all retries are exhausted
        """
        if max_retries is None:
            from ...core.constants import SystemDefaults
            max_retries = SystemDefaults.MAX_RETRIES
        
        last_error = None
        for attempt in range(max_retries):
            try:
                return await func()
            except DatabaseLockError as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"Database locked, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Database lock persisted after {max_retries} attempts")
                    raise
            except Exception as e:
                # Convert other exceptions to DatabaseError
                logger.error(f"Database operation failed: {e}")
                raise DatabaseError(f"Database operation failed: {e}") from e
        
        # This should never be reached, but just in case
        if last_error:
            raise last_error
        raise DatabaseError("Unexpected error in retry logic")
    
    async def execute_query(self, query: str, params: Optional[tuple] = None):
        """Execute a query with retry logic.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query result
        """
        async def _execute():
            if params:
                return await self.db.execute(query, params)
            else:
                return await self.db.execute(query)
        
        return await self._retry_with_backoff(_execute)
    
    async def fetch_one(self, query: str, params: Optional[tuple] = None):
        """Fetch one row with retry logic.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Single row as dict or None
        """
        async def _fetch():
            await self.execute_query(query, params)
            return await self.db.fetchone()
        
        return await self._retry_with_backoff(_fetch)
    
    async def fetch_all(self, query: str, params: Optional[tuple] = None):
        """Fetch all rows with retry logic.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of rows as dicts
        """
        async def _fetch():
            await self.execute_query(query, params)
            return await self.db.fetchall()
        
        return await self._retry_with_backoff(_fetch)