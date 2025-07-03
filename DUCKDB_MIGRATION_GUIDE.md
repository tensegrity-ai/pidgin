# DuckDB Migration Guide

## Overview

This guide covers the migration from the basic DuckDB implementation to a fully-featured, event-sourced architecture that leverages DuckDB's advanced capabilities.

## What's Changing

### 1. **Async Everything**
- All database operations are now async
- Non-blocking I/O in event handlers
- Better performance for concurrent experiments

### 2. **Event Sourcing Architecture**
- Events are stored in DuckDB instead of JSONL files
- Complete audit trail with time-travel queries
- Rebuild any state from events

### 3. **Native DuckDB Types**
- `MAP` type for word frequencies (massive space savings)
- `STRUCT` for grouped metrics (cleaner schema)
- Native JSON handling
- Better query performance

### 4. **Real-time Analytics**
- Pre-computed views for dashboards
- Window functions for trend analysis
- Direct querying of external files

## Migration Steps

### 1. Check Current Status

```bash
pidgin db status
```

This shows your current schema version and features.

### 2. Run Migration

```bash
# Migrate existing database
pidgin db migrate

# Or create fresh database
pidgin db migrate --fresh
```

### 3. Verify Migration

```bash
pidgin db status
```

You should see:
- ✓ Event sourcing enabled
- ✓ Native DuckDB types (STRUCT, MAP)
- ✓ Analytics views

## New Features

### Event Sourcing

All events are now persisted to the database:

```python
# Query events
SELECT * FROM events
WHERE event_type = 'TurnCompleteEvent'
AND conversation_id = ?
ORDER BY timestamp;
```

### Advanced Analytics

Query convergence trends with window functions:

```sql
SELECT 
    turn_number,
    convergence.score,
    AVG(convergence.score) OVER (
        ORDER BY turn_number 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) as rolling_avg_5
FROM turn_metrics;
```

### Word Frequency Analysis

Word frequencies are now stored as MAP types:

```sql
-- Get top shared words
SELECT 
    turn_number,
    map_top_n(vocabulary.shared, 10) as top_words,
    cardinality(vocabulary.shared) as shared_vocab_size
FROM turn_metrics;
```

### Direct File Queries

Query archived data without importing:

```sql
-- Query old JSONL files
SELECT * FROM read_json_auto('pidgin_output/*/events.jsonl')
WHERE event_type = 'ConversationEndEvent';

-- Query Parquet archives
SELECT * FROM read_parquet('archive/*.parquet');
```

## API Changes

### Storage Layer

The storage layer is now fully async:

```python
# Old (blocking)
storage.create_experiment(name, config)

# New (async)
await storage.create_experiment(name, config)
```

### Event Bus

Events are persisted to database:

```python
# Create database-backed event bus
from pidgin.database.event_bus import DatabaseEventBus

bus = DatabaseEventBus(db_path)
await bus.start()
```

### Event Handler

The event handler is now async:

```python
from pidgin.database.event_handler import AsyncExperimentEventHandler

handler = AsyncExperimentEventHandler(storage, experiment_id)
await handler.handle_turn_complete(event)
```

## Performance Benefits

1. **10-100x faster analytical queries** - Columnar storage and optimized indexes
2. **50-80% storage reduction** - MAP types and compression
3. **Non-blocking operations** - Async throughout
4. **Real-time dashboards** - Pre-computed views

## Compatibility

- Existing experiments are preserved during migration
- Old JSONL files can still be queried directly
- Gradual migration path available

## Troubleshooting

### Migration Fails

If migration fails:

1. Check disk space
2. Ensure DuckDB version >= 0.9.0
3. Run `pidgin db reset --force` for fresh start (WARNING: deletes data)

### Performance Issues

1. Run `ANALYZE` to update statistics
2. Check view refresh settings
3. Consider partitioning large tables

### Query Errors

DuckDB SQL differs slightly from SQLite:
- Use `STRUCT` access: `config.max_turns` not `json_extract(config, '$.max_turns')`
- Use `MAP` functions: `map_keys()`, `map_values()`, `cardinality()`
- Window functions have more options

## Examples

See `/examples/duckdb_demo.py` for comprehensive examples of:
- Async operations
- Analytics queries
- Event sourcing
- MAP/STRUCT usage

## Resources

- [DuckDB Documentation](https://duckdb.org/docs/)
- [DuckDB Data Types](https://duckdb.org/docs/sql/data_types/overview)
- [Window Functions](https://duckdb.org/docs/sql/window_functions)