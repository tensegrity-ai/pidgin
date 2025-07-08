# DuckDB Atomic Sequence Generation Research

## Problem Statement
The current event sequence generation has a race condition:
```sql
-- Step 1: Get next sequence (not atomic)
SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE conversation_id = ?

-- Step 2: Insert with that sequence (separate operation)
INSERT INTO events (..., sequence) VALUES (..., ?)
```

## DuckDB Capabilities

### 1. INSERT with RETURNING Clause
DuckDB supports the RETURNING clause for INSERT statements:
```sql
INSERT INTO table_name (col1, col2) 
VALUES (val1, val2) 
RETURNING col1, col2, calculated_expression;
```

### 2. Sequences Support
DuckDB has full sequence support:
```sql
CREATE SEQUENCE seq_name START 1;
SELECT nextval('seq_name');
```

### 3. ACID Transaction Support
DuckDB provides full ACID compliance with proper transaction isolation.

## Solution Options

### Option 1: INSERT with Subquery (Recommended)
**Atomic sequence generation using a single INSERT statement:**

```sql
INSERT INTO events (
    timestamp, event_type, conversation_id, 
    experiment_id, event_data, sequence
) 
SELECT ?, ?, ?, ?, ?, 
       COALESCE(MAX(sequence), 0) + 1
FROM events 
WHERE conversation_id = ?
RETURNING sequence;
```

**Pros:**
- Fully atomic - no race condition possible
- No additional database objects needed
- Works with any DuckDB version
- Single round-trip to database

**Cons:**
- Slightly more complex SQL syntax

### Option 2: DuckDB Sequences
**Use native sequences per conversation:**

```sql
-- Create sequence for each conversation
CREATE SEQUENCE IF NOT EXISTS seq_conversation_123 START 1;

-- Use in INSERT
INSERT INTO events (..., sequence) 
VALUES (..., nextval('seq_conversation_123'))
RETURNING sequence;
```

**Pros:**
- Clean, standard SQL syntax
- Guaranteed unique sequences
- Good performance

**Cons:**
- Requires creating a sequence per conversation
- Sequence management overhead
- Potential for many sequence objects in database

### Option 3: Explicit Transaction
**Wrap operations in a transaction:**

```sql
BEGIN TRANSACTION;
SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE conversation_id = ?;
INSERT INTO events (..., sequence) VALUES (..., ?);
COMMIT;
```

**Pros:**
- Traditional approach
- Clear transaction boundaries

**Cons:**
- Requires proper connection/transaction management
- More complex error handling
- Multiple round-trips to database

## Known Issues in DuckDB

1. **INSERT OR IGNORE with RETURNING**: Returns incorrect values when row already exists (Issue #12540)
2. **ON CONFLICT with RETURNING**: Returns sequence value even when no insert occurs (Issues #12552, #14126, #17143)
3. **Sequences increment on conflict**: Sequence increments even when INSERT fails due to conflict

## Implementation Recommendation

Use **Option 1 (INSERT with Subquery)** because:
1. It's fully atomic with no race conditions
2. Requires no additional database objects
3. Works reliably with current DuckDB versions
4. Avoids known issues with sequences and RETURNING on conflicts
5. Single database round-trip for better performance

## Code Example

```python
def save_event_atomic(self, event: Event, experiment_id: str, conversation_id: str):
    """Save event with atomic sequence generation."""
    query = """
        INSERT INTO events (
            timestamp, event_type, conversation_id, 
            experiment_id, event_data, sequence
        ) 
        SELECT ?, ?, ?, ?, ?, 
               COALESCE(MAX(sequence), 0) + 1
        FROM events 
        WHERE conversation_id = ?
        RETURNING sequence
    """
    
    result = self.fetchone(query, [
        event.timestamp,
        event.__class__.__name__,
        conversation_id,
        experiment_id,
        json.dumps(event_dict),
        conversation_id  # For WHERE clause in subquery
    ])
    
    if result:
        sequence = result[0]
        logger.debug(f"Saved event with sequence {sequence}")
```

## References

- [DuckDB INSERT Statement Documentation](https://duckdb.org/docs/stable/sql/statements/insert.html)
- [DuckDB CREATE SEQUENCE Documentation](https://duckdb.org/docs/stable/sql/statements/create_sequence.html)
- [DuckDB ACID Transactions](https://duckdb.org/2024/09/25/changing-data-with-confidence-and-acid.html)
- GitHub Issues: #12540, #12552, #14126, #17143 (INSERT RETURNING with conflicts)