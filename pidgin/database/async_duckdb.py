"""Async wrapper for DuckDB operations."""

import asyncio
import duckdb
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import threading
from dataclasses import dataclass
import queue
import time


@dataclass
class QueryResult:
    """Result of a database query."""
    rows: List[Dict[str, Any]]
    columns: List[str]
    row_count: int


class AsyncDuckDB:
    """Async wrapper for DuckDB with connection pooling and batch operations."""
    
    def __init__(self, db_path: Union[str, Path], max_workers: int = 4, 
                 batch_size: int = 1000, batch_timeout: float = 0.1,
                 read_only: bool = False):
        """Initialize async DuckDB wrapper.
        
        Args:
            db_path: Path to DuckDB database file
            max_workers: Maximum number of worker threads
            batch_size: Maximum number of events to batch before flushing
            batch_timeout: Maximum time in seconds to wait before flushing batch
            read_only: If True, open database in read-only mode
        """
        self.db_path = str(Path(db_path).resolve())
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.read_only = read_only
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Batch insert queue and processing
        self._batch_queue = queue.Queue()
        self._batch_lock = threading.Lock()
        self._running = False
        self._batch_thread = None
        
        # Database will be initialized on first connection
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # Note: Can't use read_only=True when other connections exist
            # DuckDB error: "Can't open a connection to same database file with different configuration"
            self._local.conn = duckdb.connect(self.db_path)
            
            # Configure for better concurrency
            # DuckDB uses MVCC and handles locking internally
            # Multiple readers are allowed, but only one writer at a time
            
            # Enable JSON extension (skip in read-only mode as it requires writes)
            if not self.read_only:
                try:
                    self._local.conn.execute("INSTALL json")
                    self._local.conn.execute("LOAD json")
                except:
                    # Extension might already be installed
                    pass
        return self._local.conn
    
    def _init_database(self):
        """Initialize database with any required setup."""
        conn = duckdb.connect(self.db_path)
        try:
            # Enable useful extensions
            conn.execute("INSTALL json")
            conn.execute("LOAD json")
        finally:
            conn.close()
    
    async def execute(self, query: str, params: Optional[tuple] = None) -> QueryResult:
        """Execute a query asynchronously.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            QueryResult with rows, columns, and count
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_execute,
            query,
            params
        )
    
    def _sync_execute(self, query: str, params: Optional[tuple]) -> QueryResult:
        """Synchronous execution in thread pool."""
        conn = self._get_connection()
        
        if params:
            result = conn.execute(query, params)
        else:
            result = conn.execute(query)
        
        # Check if this is a SELECT query
        if result.description:
            # Get column names
            columns = [desc[0] for desc in result.description]
            
            # Fetch all rows and convert to dicts
            rows = []
            for row in result.fetchall():
                rows.append(dict(zip(columns, row)))
            
            return QueryResult(rows=rows, columns=columns, row_count=len(rows))
        else:
            # For INSERT/UPDATE/DELETE, return affected rows
            return QueryResult(rows=[], columns=[], row_count=result.fetchone()[0] if result.fetchone() else 0)
    
    async def executemany(self, query: str, params_list: List[tuple]) -> int:
        """Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
            
        Returns:
            Total number of affected rows
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_executemany,
            query,
            params_list
        )
    
    def _sync_executemany(self, query: str, params_list: List[tuple]) -> int:
        """Synchronous batch execution."""
        conn = self._get_connection()
        
        # DuckDB doesn't have executemany, so we use a transaction
        conn.begin()
        try:
            affected = 0
            for params in params_list:
                result = conn.execute(query, params)
                row = result.fetchone()
                if row:
                    affected += row[0]
            conn.commit()
            return affected
        except Exception:
            conn.rollback()
            raise
    
    async def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row.
        
        Args:
            query: SQL query to execute
            params: Optional parameters
            
        Returns:
            Dict representing the row, or None if no results
        """
        result = await self.execute(query, params)
        return result.rows[0] if result.rows else None
    
    async def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows.
        
        Args:
            query: SQL query to execute
            params: Optional parameters
            
        Returns:
            List of dicts representing rows
        """
        result = await self.execute(query, params)
        return result.rows
    
    async def fetch_df(self, query: str, params: Optional[tuple] = None):
        """Fetch results as a pandas DataFrame.
        
        Args:
            query: SQL query to execute
            params: Optional parameters
            
        Returns:
            pandas DataFrame with results
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_fetch_df,
            query,
            params
        )
    
    def _sync_fetch_df(self, query: str, params: Optional[tuple]):
        """Synchronously fetch as DataFrame."""
        conn = self._get_connection()
        
        if params:
            return conn.execute(query, params).fetchdf()
        else:
            return conn.execute(query).fetchdf()
    
    @asynccontextmanager
    async def transaction(self):
        """Async context manager for transactions.
        
        Usage:
            async with db.transaction():
                await db.execute("INSERT ...")
                await db.execute("UPDATE ...")
        """
        # Start transaction
        await self.execute("BEGIN")
        try:
            yield
            # Commit on success
            await self.execute("COMMIT")
        except Exception:
            # Rollback on error
            await self.execute("ROLLBACK")
            raise
    
    async def batch_insert(self, table: str, records: List[Dict[str, Any]]):
        """Batch insert records into a table.
        
        Args:
            table: Table name
            records: List of dicts to insert
        """
        if not records:
            return
        
        # Get columns from first record
        columns = list(records[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)
        
        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
        
        # Convert records to tuples
        params_list = []
        for record in records:
            params_list.append(tuple(record.get(col) for col in columns))
        
        await self.executemany(query, params_list)
    
    def start_batch_processor(self):
        """Start the batch processing thread."""
        if self._running or self.read_only:
            return
        
        self._running = True
        self._batch_thread = threading.Thread(target=self._process_batches, daemon=True)
        self._batch_thread.start()
    
    def stop_batch_processor(self):
        """Stop the batch processing thread."""
        self._running = False
        if self._batch_thread:
            self._batch_thread.join(timeout=1.0)
    
    def queue_batch_insert(self, table: str, record: Dict[str, Any]):
        """Queue a record for batch insertion.
        
        Args:
            table: Table name
            record: Record to insert
        """
        self._batch_queue.put((table, record))
    
    def _process_batches(self):
        """Process batched inserts in background thread."""
        batches = {}
        last_flush = time.time()
        
        while self._running:
            try:
                # Try to get items with timeout
                deadline = last_flush + self.batch_timeout
                timeout = max(0.01, deadline - time.time())
                
                try:
                    table, record = self._batch_queue.get(timeout=timeout)
                    
                    # Add to batch
                    if table not in batches:
                        batches[table] = []
                    batches[table].append(record)
                    
                except queue.Empty:
                    pass
                
                # Check if we should flush
                current_time = time.time()
                should_flush = (
                    current_time - last_flush >= self.batch_timeout or
                    any(len(records) >= self.batch_size for records in batches.values())
                )
                
                if should_flush and batches:
                    # Flush all batches
                    conn = self._get_connection()
                    conn.begin()
                    
                    try:
                        for table, records in batches.items():
                            if records:
                                # Batch insert
                                columns = list(records[0].keys())
                                placeholders = ", ".join(["?" for _ in columns])
                                column_names = ", ".join(columns)
                                
                                query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
                                
                                for record in records:
                                    params = tuple(record.get(col) for col in columns)
                                    conn.execute(query, params)
                        
                        conn.commit()
                        batches.clear()
                        last_flush = current_time
                        
                    except Exception as e:
                        conn.rollback()
                        print(f"Batch insert error: {e}")
                        batches.clear()
                        
            except Exception as e:
                print(f"Batch processor error: {e}")
    
    async def close(self):
        """Close all connections and stop batch processor."""
        self.stop_batch_processor()
        
        # Close connections in all worker threads
        futures = []
        for _ in range(self.executor._max_workers):
            future = self.executor.submit(self._close_thread_connection)
            futures.append(future)
        
        # Wait for all to complete
        for future in futures:
            try:
                future.result(timeout=1.0)
            except Exception as e:
                print(f"Error closing connection: {e}")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
    
    def _close_thread_connection(self):
        """Close connection in current thread."""
        if hasattr(self._local, 'conn') and self._local.conn:
            try:
                self._local.conn.close()
            except Exception as e:
                print(f"Error closing DuckDB connection: {e}")
            finally:
                self._local.conn = None