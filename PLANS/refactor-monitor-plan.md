# Monitor Module Refactoring Plan

## Current State
- **File**: `pidgin/monitor/monitor.py`
- **Lines**: 845 (322% over 200-line target)
- **Responsibilities**: Mixed display, state reading, error tracking, metrics calculation

## Identified Responsibilities

1. **Display/UI Components** (~300 lines)
   - Panel building (header, experiments, conversations, errors)
   - Table formatting
   - Text truncation and formatting
   - Terminal width management

2. **State Management** (~200 lines)
   - Reading experiment states
   - Tracking conversation status
   - Building state from JSONL files

3. **Error Tracking** (~150 lines)
   - Collecting errors from logs
   - Categorizing errors
   - Checking error resolution
   - Error formatting

4. **Metrics Calculation** (~100 lines)
   - Token estimation
   - Cost calculation
   - Rate calculations
   - Statistics aggregation

5. **File Operations** (~95 lines)
   - Tailing log files
   - Reading JSONL files
   - Directory watching

## Proposed Extraction

### 1. `monitor_display.py` (~200 lines)
```python
class MonitorDisplay:
    """Handle all display and UI components for the monitor."""
    
    def build_header(self, stats) -> Panel
    def build_experiments_panel(self, experiments) -> Panel
    def build_conversations_panel(self, experiments) -> Panel
    def build_errors_panel(self, errors) -> Panel
    def format_table_row(self, data) -> str
    def truncate_text(self, text, max_length) -> str
    def get_panel_width(self) -> int
```

### 2. `monitor_state.py` (~180 lines)
```python
class MonitorState:
    """Manage experiment and conversation state."""
    
    def get_experiment_states(self) -> List[ExperimentState]
    def get_conversation_status(self, exp_id) -> Dict
    def is_recent(self, timestamp, minutes=5) -> bool
    def get_active_experiments(self) -> List
    def get_completed_experiments(self) -> List
```

### 3. `error_tracker.py` (~150 lines)
```python
class ErrorTracker:
    """Track and categorize errors from logs."""
    
    def get_recent_errors(self, minutes=10) -> List[Dict]
    def categorize_error(self, error) -> str
    def check_error_resolved(self, error) -> bool
    def format_error_message(self, error) -> str
    def get_error_statistics(self) -> Dict
```

### 4. `metrics_calculator.py` (~100 lines)
```python
class MetricsCalculator:
    """Calculate metrics for experiments."""
    
    def estimate_tokens(self, experiment) -> int
    def estimate_cost(self, experiment, tokens) -> float
    def calculate_rate(self, count, duration) -> float
    def aggregate_statistics(self, experiments) -> Dict
```

### 5. `monitor.py` (main, ~115 lines)
```python
class Monitor:
    """Main monitor orchestrating display components."""
    
    def __init__(self):
        self.display = MonitorDisplay()
        self.state = MonitorState()
        self.errors = ErrorTracker()
        self.metrics = MetricsCalculator()
    
    async def run(self)
    def build_display(self) -> Group
```

## Implementation Steps

1. **Create `monitor_display.py`**
   - Extract all panel building methods
   - Extract formatting utilities
   - Keep Rich dependencies isolated here

2. **Create `monitor_state.py`**
   - Extract state reading logic
   - Extract status tracking
   - Use StateBuilder internally

3. **Create `error_tracker.py`**
   - Extract error collection logic
   - Extract error categorization
   - Extract resolution checking

4. **Create `metrics_calculator.py`**
   - Extract token estimation
   - Extract cost calculation
   - Extract rate calculations

5. **Update `monitor.py`**
   - Keep only orchestration logic
   - Use extracted components
   - Maintain main run loop

## Testing Strategy
- Create tests for each extracted module
- Mock dependencies appropriately
- Test display formatting separately from logic
- Ensure monitor still works end-to-end

## Benefits
- Each module under 200 lines
- Clear separation of concerns
- Easier to test individual components
- Display logic isolated from business logic
- Metrics calculation reusable elsewhere