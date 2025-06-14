# Refactor DialogueEngine into Focused Components

## Analysis Summary
- DialogueEngine is currently 1032 lines (way too large!)
- It handles 10+ different responsibilities
- Tightly coupled with display, metrics, state, streaming, etc.
- Two config files exist (config.py and config_manager.py) causing confusion

## Step 0: Quick Fixes First

### 0.1 Fix Config Redundancy
1. Delete the simple `config.py` (only 5 lines, just imports)
2. Rename `config_manager.py` → `config.py`
3. Update imports in:
   - `dialogue.py`: Change `from .config_manager import get_config`
   - `cli.py`: Update config_manager imports

### 0.2 Rename Conductor → InterventionHandler
1. Rename `conductor.py` → `intervention_handler.py`
2. Rename `tests/test_conductor.py` → `tests/test_intervention_handler.py`
3. Update class name: `Conductor` → `InterventionHandler`
4. Update imports in:
   - `dialogue.py`: Change import and all references
   - Test file: Update imports and references
5. Keep method names the same for compatibility

## Step 1: Create Component Structure

```
pidgin/dialogue_components/
├── __init__.py
├── display_manager.py      # ~150 lines - All UI/console output
├── metrics_tracker.py      # ~120 lines - Metrics & convergence
├── progress_tracker.py     # ~80 lines - Turn management
├── response_handler.py     # ~150 lines - Streaming responses
└── state_manager.py        # ~100 lines - State & checkpoints
```

## Step 2: Component Extraction Details

### 2.1 DisplayManager (~150 lines)
**Responsibilities:**
- All Rich console output
- Message formatting and panels
- Turn progress display
- Context window display
- Attractor detection display

**Methods to extract:**
- `_display_message()` → `display_message()`
- Context window setup display (lines 243-262)
- Turn counter display (lines 659-707)
- Attractor display logic

### 2.2 MetricsTracker (~120 lines)
**Responsibilities:**
- Convergence calculation
- Turn metrics (message lengths, diversity, etc.)
- Phase detection
- Metrics aggregation for saving

**Methods/attributes to extract:**
- `convergence_calculator`
- `turn_metrics` dict
- `phase_detection` dict
- `convergence_history`
- `_get_current_metrics()` → `get_current_metrics()`
- Convergence calculation logic (lines 516-530)
- Metrics update logic (lines 532-558)

### 2.3 ProgressTracker (~80 lines)
**Responsibilities:**
- Track current turn
- Check if should continue
- Handle turn completion
- Mark conversation as stopped

**New simple implementation:**
```python
class ProgressTracker:
    def __init__(self, max_turns: int, start_turn: int = 0):
        self.max_turns = max_turns
        self.current_turn = start_turn
        self.completed = False
    
    def should_continue(self) -> bool:
        return self.current_turn < self.max_turns and not self.completed
    
    def complete_turn(self):
        self.current_turn += 1
    
    def mark_stopped(self):
        """Mark conversation as stopped (for attractors, errors, etc)"""
        self.completed = True
```

### 2.4 ResponseHandler (~150 lines)
**Responsibilities:**
- Get streaming responses from agents
- Handle interrupts during streaming
- Display streaming status
- Handle rate limits
- Check intervention handler for pauses

**Dependencies:**
```python
def __init__(self, router, display_manager, intervention_handler=None):
    self.router = router
    self.display_manager = display_manager
    self.intervention_handler = intervention_handler
```

**Methods to extract:**
- `_get_agent_response_streaming()` → `get_response_streaming()`
- `_get_agent_response()` → `get_response()`
- Rate limit handling logic

### 2.5 StateManager (~100 lines)
**Responsibilities:**
- Initialize conversation state
- Handle checkpoints
- Resume from checkpoints
- Save/load state

**Integrates with:**
- Existing `ConversationState` class
- Existing `CheckpointManager`

## Step 3: Refactored DialogueEngine (~250 lines)

The new DialogueEngine will only orchestrate:

```python
class DialogueEngine:
    def __init__(self, router, transcript_manager, config=None):
        self.router = router
        self.transcript_manager = transcript_manager
        self.config = config or get_config()
        
        # Initialize components
        self.display = DisplayManager(Console())
        self.metrics = MetricsTracker()
        self.state_manager = StateManager()
        self.response_handler = ResponseHandler(router, self.display)
        
        # Optional components
        if self.config.get('conversation.attractor_detection.enabled'):
            self.attractor_manager = AttractorManager(...)
        if self.config.get('context_management.enabled'):
            self.context_manager = ContextWindowManager()
        
    async def run_conversation(self, agent_a, agent_b, initial_prompt, max_turns, **options):
        # Setup
        if not options.get('resume_from_state'):
            self._setup_new_conversation(agent_a, agent_b, initial_prompt, max_turns)
        else:
            self._resume_conversation(options['resume_from_state'])
        
        # Main loop (simplified)
        progress = ProgressTracker(max_turns, self.state_manager.state.turn_count)
        
        while progress.should_continue():
            turn_result = await self._run_single_turn(progress.current_turn)
            
            if turn_result == 'pause':
                await self._handle_pause()
                break
            elif turn_result == 'stop':
                break
                
            progress.complete_turn()
        
        # Finalize
        await self._finalize_conversation()
```

## Step 4: Testing Strategy

1. **Create component tests first:**
   - `test_display_manager.py`
   - `test_metrics_tracker.py`
   - `test_progress_tracker.py`
   - `test_response_handler.py`
   - `test_state_manager.py`

2. **Update existing tests:**
   - Update imports for renamed modules
   - Mock components where needed

3. **Integration test:**
   - Test full conversation flow
   - Verify no behavior changes

## Step 5: Implementation Order

1. **Day 1: Quick fixes**
   - Fix config redundancy (15 min)
   - Rename Conductor → InterventionHandler (30 min)

2. **Day 2: Extract display components**
   - Create DisplayManager
   - Move all console/UI code
   - Test display functionality

3. **Day 3: Extract metrics & progress**
   - Create MetricsTracker
   - Create ProgressTracker
   - Test metrics collection

4. **Day 4: Extract response & state**
   - Create ResponseHandler
   - Create StateManager
   - Test streaming & state

5. **Day 5: Refactor DialogueEngine**
   - Update to use components
   - Clean up orchestration logic
   - Full integration testing

## Key Design Principles

### Component Interfaces
All components should implement a base interface for lifecycle management:

```python
class Component:
    """Base class for dialogue components"""
    def reset(self):
        """Reset component state for new conversation"""
        pass
```

### Dependency Flow
To avoid circular dependencies:
- DisplayManager: No dependencies on other components
- MetricsTracker: No dependencies on other components
- ProgressTracker: No dependencies on other components
- ResponseHandler: Depends on router, display, intervention handler
- StateManager: Depends on checkpoint manager
- DialogueEngine: Orchestrates all components

### Key Rules:
1. Components should not import each other (except through constructor dependencies)
2. Data flows through the DialogueEngine orchestrator
3. Components communicate through return values, not direct calls

## Benefits

1. **Maintainability**: Each component ~100-150 lines vs 1000+
2. **Testability**: Components can be unit tested in isolation
3. **Reusability**: Components can be used in other contexts
4. **Clarity**: Single responsibility for each component
5. **Extensibility**: Easy to add new features to specific components
6. **Future-Ready**: Component pattern aligns with future event architecture

## Success Metrics

- [ ] DialogueEngine under 300 lines
- [ ] Each component under 200 lines
- [ ] All existing tests pass
- [ ] New component tests added
- [ ] No behavior changes in conversations
- [ ] Clear separation of concerns