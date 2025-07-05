# Database Layer Issues Analysis

## Critical Issues

### 1. Connection Leak in AsyncDuckDB
**Location**: `async_duckdb.py:350-360`
**Problem**: The `close()` method only closes the connection in the current thread, leaving connections open in worker threads.
**Impact**: Connection leak, potential "too many connections" errors
**Severity**: HIGH

### 2. Race Condition in Event Sequence Numbers  
**Location**: `event_store.py:138-145`
**Problem**: Sequence number generation and database insert aren't atomic, allowing duplicate sequences.
**Impact**: Event ordering could be corrupted
**Severity**: HIGH

### 3. Double-Fetch Bug in executemany
**Location**: `async_duckdb.py:156-157`
**Problem**: `result.fetchone()` called twice, causing incorrect affected row count
**Impact**: Incorrect metrics, potential null pointer
**Severity**: MEDIUM

## Performance Issues

### 4. Schema Check on Every Insert
**Location**: `event_store.py:346-352`  
**Problem**: Database schema queried on every conversation creation
**Impact**: Unnecessary database roundtrips
**Severity**: MEDIUM

### 5. Missing Indexes
**Locations**: Multiple
- `turn_metrics(conversation_id)` for COUNT queries
- Composite indexes for complex joins in analytics
- `word_frequencies` table needs better indexing
**Impact**: Slow queries as data grows
**Severity**: MEDIUM

### 6. No Connection Pooling
**Location**: `async_duckdb.py:55-74`
**Problem**: Connections live forever with no recycling or limits
**Impact**: Resource exhaustion possible
**Severity**: MEDIUM

## Reliability Issues

### 7. Missing Transaction Boundaries
**Location**: `event_store.py:402-478` and others
**Problem**: Multi-table updates aren't wrapped in transactions
**Impact**: Partial updates possible on failure
**Severity**: HIGH

### 8. Batch Processor Error Handling
**Location**: `async_duckdb.py:285-343`
**Problem**: 
- Batches lost on error (line 340)
- No connection failure recovery
- No graceful shutdown
**Impact**: Data loss possible
**Severity**: HIGH

### 9. Migration Transaction Safety
**Location**: `migrations.py:51-59`
**Problem**: Individual migrations not wrapped in transactions
**Impact**: Partial schema changes possible
**Severity**: MEDIUM

### 10. EventStore Initialization Cleanup
**Location**: `event_store.py:__init__`
**Problem**: AsyncDuckDB created but not cleaned up on initialization failure
**Impact**: Resource leak
**Severity**: LOW

## Maintenance Issues

### 11. Poor Error Context
**Location**: `event_store.py:120`
**Problem**: Retry logic only logs error message, not full context
**Impact**: Hard to debug production issues
**Severity**: LOW

### 12. Read-Only Mode Inconsistencies
**Location**: `event_store.py:58-59`
**Problem**: Batch processor starts even in read-only mode
**Impact**: Unnecessary resource usage
**Severity**: LOW

## Recommended Fixes Priority

1. **Fix connection leak** - Add proper cleanup for all thread connections
2. **Fix sequence race condition** - Use database sequences or atomic operations  
3. **Add transaction boundaries** - Wrap multi-table operations
4. **Fix batch processor** - Add proper error handling and graceful shutdown
5. **Fix double-fetch bug** - Simple one-line fix
6. **Add missing indexes** - Based on query patterns
7. **Cache schema info** - Check once during initialization
8. **Improve error handling** - Better context preservation

## Quick Wins
- Fix double-fetch bug (1 line change)
- Cache schema info (small refactor)
- Add missing indexes (SQL only)
- Fix read-only mode batch processor (1 line change)