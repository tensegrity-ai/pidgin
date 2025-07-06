# EventStore Refactoring Plan

## Current State
The EventStore class is a god object with 856 lines and 22 methods handling:
- Event storage and retrieval
- Experiment management
- Conversation management
- Metrics logging
- Message logging
- Token usage tracking
- Agent name logging

## Proposed Architecture

### 1. Core EventStore (Base Layer)
Keep EventStore as a thin coordinator that delegates to specialized repositories.

```python
class EventStore:
    """Coordinator for all storage operations."""
    def __init__(self, db_path: Optional[Path] = None):
        self.db = AsyncDuckDB(db_path)
        self.events = EventRepository(self.db)
        self.experiments = ExperimentRepository(self.db)
        self.conversations = ConversationRepository(self.db)
        self.metrics = MetricsRepository(self.db)
        self.messages = MessageRepository(self.db)
```

### 2. Repository Classes

#### EventRepository
Handles core event operations:
- `emit_event()` - Store events in JSONL and database
- `get_events()` - Retrieve events with filtering
- `search_events()` - Full-text search capabilities

#### ExperimentRepository
Manages experiment lifecycle:
- `create_experiment()`
- `get_experiment()`
- `update_experiment_status()`
- `list_experiments()`
- `mark_running_conversations_failed()`

#### ConversationRepository  
Manages conversations:
- `create_conversation()`
- `update_conversation_status()`
- `get_conversation_history()`
- `log_agent_name()`

#### MetricsRepository
Handles all metrics logging:
- `log_turn_metrics()`
- `log_message_metrics()`
- `log_word_frequencies()`
- `get_experiment_metrics()`

#### MessageRepository
Message and token management:
- `log_message()`
- `search_messages()`
- `log_token_usage()`

### 3. Shared Components

#### RetryHandler
Extract retry logic into a reusable component:
```python
class RetryHandler:
    async def retry_with_backoff(self, func, max_retries=3):
        """Retry with exponential backoff."""
```

#### DatabaseConnection
Manage database lifecycle:
```python
class DatabaseConnection:
    """Manages AsyncDuckDB connection and initialization."""
```

## Implementation Strategy

### Phase 1: Create Repository Interfaces (TDD)
1. Define repository abstract base classes
2. Write comprehensive tests for each repository
3. Tests should cover all existing EventStore functionality

### Phase 2: Implement Repositories
1. Start with EventRepository (simplest)
2. Move to ExperimentRepository
3. Continue with others
4. Each implementation should pass all tests

### Phase 3: Refactor EventStore
1. Replace direct database calls with repository calls
2. Maintain backward compatibility
3. Ensure all existing tests still pass

### Phase 4: Cleanup
1. Remove duplicated code
2. Add thread safety where needed
3. Update documentation

## Benefits
1. **Single Responsibility**: Each repository has one clear purpose
2. **Testability**: Easier to mock and test individual components
3. **Maintainability**: Changes to one domain don't affect others
4. **Extensibility**: Easy to add new repositories or features
5. **Thread Safety**: Can add proper locking per repository

## Backward Compatibility
The refactored EventStore will maintain the same public API, so existing code continues to work:
```python
# This still works
store = EventStore()
await store.create_experiment(...)
await store.log_turn_metrics(...)
```

## Testing Strategy
1. Write integration tests for current EventStore behavior
2. Write unit tests for each new repository
3. Ensure all tests pass during each refactoring step
4. Add thread safety tests for concurrent operations