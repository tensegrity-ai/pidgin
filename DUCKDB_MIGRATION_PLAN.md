# DuckDB Migration Plan for Pidgin

## Overview
This document outlines the comprehensive plan to migrate Pidgin from SQLite to DuckDB, including architectural improvements that leverage DuckDB's advanced features.

## Current Architecture Pain Points

1. **Blocking I/O**: Sync database calls in async event handlers block the event loop
2. **Redundant Storage**: Metrics stored both as individual columns AND JSON blobs
3. **Inefficient Word Storage**: Word frequencies as individual rows (N rows per turn)
4. **Limited Analytics**: No time series analysis, rolling averages, or trend detection
5. **Disconnected Events**: events.jsonl files separate from database
6. **No Real-time Views**: All queries compute from scratch

## DuckDB Architectural Opportunities

### 1. Event Sourcing Architecture
Instead of storing derived state, store events as the source of truth:

```sql
-- Raw events table (replaces events.jsonl)
CREATE TABLE events (
    event_id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP DEFAULT now(),
    conversation_id TEXT,
    event_type TEXT,
    event_data JSON,
    -- Partitioned by date for efficient queries
    event_date DATE DEFAULT CAST(now() AS DATE)
) PARTITION BY (event_date);

-- Create materialized views for common queries
CREATE MATERIALIZED VIEW conversation_state AS
SELECT 
    conversation_id,
    MAX(CASE WHEN event_type = 'ConversationStartEvent' THEN event_data->>'status' END) as status,
    COUNT(CASE WHEN event_type = 'TurnCompleteEvent' THEN 1 END) as turn_count,
    -- ... other derived fields
FROM events
GROUP BY conversation_id;
```

### 2. Time Series Metrics Design
Leverage DuckDB's columnar storage and window functions:

```sql
-- Metrics as time series with native types
CREATE TABLE turn_metrics (
    conversation_id TEXT,
    turn_number INTEGER,
    timestamp TIMESTAMP,
    -- Core metrics as columns for fast queries
    convergence_score DOUBLE,
    vocabulary_overlap DOUBLE,
    -- Rich metrics as STRUCT for organization
    lexical_metrics STRUCT(
        vocabulary_size INTEGER,
        unique_words INTEGER,
        type_token_ratio DOUBLE
    ),
    -- Word frequencies as MAP instead of separate table
    word_frequencies MAP(VARCHAR, INTEGER),
    -- All other metrics as JSON for flexibility
    extended_metrics JSON
);

-- Efficient rolling averages
CREATE VIEW rolling_convergence AS
SELECT 
    conversation_id,
    turn_number,
    convergence_score,
    AVG(convergence_score) OVER (
        PARTITION BY conversation_id 
        ORDER BY turn_number 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) as rolling_avg_5
FROM turn_metrics;
```

### 3. Async Database Layer
Non-blocking operations with connection pooling:

```python
import asyncio
import duckdb
from concurrent.futures import ThreadPoolExecutor

class AsyncDuckDB:
    def __init__(self, db_path: str, max_workers: int = 4):
        self.db_path = db_path
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def execute(self, query: str, params=None):
        """Execute query asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_execute,
            query,
            params
        )
    
    def _sync_execute(self, query: str, params):
        """Synchronous execution in thread pool."""
        with duckdb.connect(self.db_path) as conn:
            if params:
                return conn.execute(query, params).fetchdf()
            return conn.execute(query).fetchdf()
```

### 4. Smart Storage Schema

```sql
-- Experiments table with better types
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    -- Use INTERVAL for duration tracking
    duration INTERVAL,
    -- Native JSON for config
    config JSON NOT NULL,
    -- Pre-computed stats
    stats STRUCT(
        total_conversations INTEGER,
        completed_conversations INTEGER,
        avg_convergence DOUBLE,
        total_turns INTEGER
    )
);

-- Message storage with full text search
CREATE TABLE messages (
    conversation_id TEXT,
    turn_number INTEGER,
    agent_id TEXT,
    content TEXT,
    -- Pre-computed embeddings for similarity
    embedding DOUBLE[],
    -- Full text search
    FULLTEXT INDEX (content)
);
```

### 5. External Data Integration

```sql
-- Query events.jsonl directly without import
CREATE VIEW event_files AS
SELECT * FROM read_json_auto('pidgin_output/*/events.jsonl');

-- Archive old experiments to Parquet
COPY (SELECT * FROM experiments WHERE created_at < now() - INTERVAL '30 days')
TO 'archive/old_experiments.parquet' (FORMAT PARQUET);

-- Query archived data seamlessly
CREATE VIEW all_experiments AS
SELECT * FROM experiments
UNION ALL
SELECT * FROM read_parquet('archive/*.parquet');
```

### 6. Real-time Analytics Views

```sql
-- Live experiment dashboard
CREATE MATERIALIZED VIEW experiment_dashboard AS
SELECT 
    e.experiment_id,
    e.name,
    e.created_at,
    COUNT(DISTINCT c.conversation_id) as conversations,
    AVG(tm.convergence_score) as avg_convergence,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tm.convergence_score) as median_convergence,
    -- Convergence trend
    regr_slope(tm.convergence_score, tm.turn_number) as convergence_trend
FROM experiments e
JOIN conversations c ON e.experiment_id = c.experiment_id
JOIN turn_metrics tm ON c.conversation_id = tm.conversation_id
GROUP BY e.experiment_id, e.name, e.created_at;

-- Refresh periodically
CREATE TASK refresh_dashboard
SCHEDULE EVERY 1 MINUTE
AS REFRESH MATERIALIZED VIEW experiment_dashboard;
```

## Implementation Strategy

### Phase 1: Core Migration (Minimal Changes)
1. **Replace imports**: sqlite3 → duckdb
2. **Update schema**: 
   - AUTOINCREMENT → SEQUENCE
   - Keep existing structure
3. **Connection handling**:
   ```python
   def _get_connection(self):
       return duckdb.connect(str(self.db_path))
   ```
4. **Result handling**:
   ```python
   # DuckDB returns tuples, need to convert
   df = result.fetchdf()  # Get as DataFrame
   return df.to_dict('records')  # Convert to list of dicts
   ```

### Phase 2: Async Wrapper (Non-blocking)
1. Create AsyncDuckDB class with ThreadPoolExecutor
2. Update event handlers to use async database calls
3. Prevent event loop blocking

### Phase 3: Schema Optimization
1. Combine word_frequencies into MAP column
2. Use STRUCT for grouped metrics
3. Native JSON handling
4. Add materialized views for common queries

### Phase 4: Event Sourcing (Optional)
1. Store events in database instead of JSONL
2. Build state from events
3. Enable time-travel queries

## Benefits

1. **Performance**: 10-100x faster analytical queries
2. **Concurrency**: Non-blocking database operations
3. **Storage**: 50-80% less space with columnar compression
4. **Analytics**: Built-in time series and statistical functions
5. **Flexibility**: Query external files without import
6. **Real-time**: Materialized views update automatically

## Breaking Changes

1. Database file: `experiments.db` → `experiments.duckdb`
2. Word frequencies: Separate table → MAP column (Phase 3)
3. Events: JSONL files → Database table (Phase 4, optional)

## Minimal Migration Path (Phase 1 Only)

If we want to keep changes minimal:

1. **Update imports**:
   ```python
   import duckdb  # instead of sqlite3
   ```

2. **Update connection**:
   ```python
   conn = duckdb.connect(str(self.db_path))
   ```

3. **Update schema creation**:
   - Remove AUTOINCREMENT
   - Add sequences for ID generation
   - Keep rest the same

4. **Update result handling**:
   ```python
   # Option 1: Use fetchdf() and convert
   df = conn.execute(query).fetchdf()
   if df.empty:
       return None
   return df.to_dict('records')
   
   # Option 2: Use fetchall() with manual dict conversion
   results = conn.execute(query).fetchall()
   columns = [desc[0] for desc in conn.description]
   return [dict(zip(columns, row)) for row in results]
   ```

5. **Handle JSON fields**:
   ```python
   # DuckDB can parse JSON automatically
   # No need for json.loads() on retrieval
   ```

This minimal approach gets us DuckDB's performance benefits without major architectural changes. We can implement the advanced features later as needed.