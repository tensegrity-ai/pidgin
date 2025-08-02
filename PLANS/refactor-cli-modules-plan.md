# CLI Module Refactoring Plan

## Problem Statement

Three modules significantly exceed the 200-line guideline:
- `pidgin/cli/run.py`: 862 lines (4.3x over limit!)
- `pidgin/experiments/runner.py`: 477 lines (2.4x over limit)
- `pidgin/core/conductor.py`: 372 lines (1.9x over limit)

The `run.py` module is particularly problematic with massive functions:
- `run()`: 255 lines
- `_run_conversations()`: 271 lines

## Analysis

### run.py Issues
1. **Mixed Responsibilities**: Handles YAML parsing, model selection, config building, daemon management, and display coordination
2. **Massive Functions**: Individual functions doing 5+ distinct tasks
3. **Poor Separation**: CLI concerns mixed with business logic

### runner.py Issues
1. **Setup Code Pollution**: Contains extensive setup methods that don't directly run experiments
2. **Mixed Abstractions**: Low-level provider creation mixed with high-level orchestration

### conductor.py Status
- Likely acceptable as-is (372 lines for a central orchestrator is reasonable)
- Should be reviewed but not priority

## Refactoring Plan

### Phase 1: Extract from run.py

Create these new modules in `pidgin/cli/`:

#### 1. `spec_loader.py` (~80 lines)
```python
class SpecLoader:
    """Handle YAML spec file loading and validation."""
    
    def load_spec(self, spec_file: Path) -> Dict
    def validate_spec(self, spec: Dict) -> None
    def spec_to_config(self, spec: Dict) -> ExperimentConfig
```

#### 2. `model_selector.py` (~150 lines)
```python
class ModelSelector:
    """Interactive model selection and validation."""
    
    def select_model(self, prompt: str) -> Optional[str]
    def validate_models(self, agent_a: str, agent_b: str) -> None
    def get_available_models() -> Dict[str, List[str]]
    def prompt_for_custom_model() -> Optional[str]
```

#### 3. `config_builder.py` (~100 lines)
```python
class ConfigBuilder:
    """Build ExperimentConfig from CLI arguments."""
    
    def build_config(self, **kwargs) -> ExperimentConfig
    def apply_temperature_settings(self, config: ExperimentConfig, ...) -> None
    def apply_convergence_settings(self, config: ExperimentConfig, ...) -> None
    def generate_experiment_name() -> str
```

#### 4. `display_manager.py` (~100 lines)
```python
class DisplayManager:
    """Manage display modes and live output."""
    
    def determine_display_mode(self, quiet: bool, tail: bool, ...) -> str
    def launch_display(self, exp_id: str, display_mode: str, ...) -> None
    def show_completion_info(self, exp_dir: Path) -> None
```

#### 5. `daemon_launcher.py` (~80 lines)
```python
class DaemonLauncher:
    """Start and manage experiment daemon."""
    
    def start_daemon(self, config: ExperimentConfig) -> str
    def validate_before_start(self, config: ExperimentConfig) -> None
    def show_startup_message(self, exp_id: str, name: str, ...) -> None
```

### Phase 2: Extract from runner.py

Create these new modules in `pidgin/experiments/`:

#### 1. `experiment_setup.py` (~120 lines)
```python
class ExperimentSetup:
    """Handle all experiment setup tasks."""
    
    def setup_event_bus(self, exp_dir: Path, ...) -> EventBus
    def create_agents_and_providers(self, config: ExperimentConfig, ...) -> Tuple
    def setup_output_and_console(self, exp_dir: Path, ...) -> Tuple
    def register_conversation(self, exp_dir: Path, conv_id: str) -> None
```

#### 2. `conversation_orchestrator.py` (~100 lines)
```python
class ConversationOrchestrator:
    """Orchestrate parallel and sequential conversation execution."""
    
    async def run_parallel(self, conversations: List, ...) -> None
    async def run_sequential(self, conversations: List, ...) -> None
    async def run_single_conversation(self, conv_id: str, ...) -> None
```

### Phase 3: Update run.py

The refactored `run.py` (~200 lines) will:
```python
def run(spec_file, agent_a, agent_b, ...):
    """Simplified run command."""
    
    # Handle spec file
    if spec_file:
        spec_loader = SpecLoader()
        config = spec_loader.load_and_convert(spec_file)
    else:
        # Handle CLI arguments
        model_selector = ModelSelector()
        if not agent_a:
            agent_a = model_selector.select_model("Select first agent")
        
        config_builder = ConfigBuilder()
        config = config_builder.build_config(
            agent_a=agent_a,
            agent_b=agent_b,
            ...
        )
    
    # Launch experiment
    daemon_launcher = DaemonLauncher()
    exp_id = daemon_launcher.start_daemon(config)
    
    # Handle display
    display_manager = DisplayManager()
    display_manager.launch_display(exp_id, display_mode, ...)
```

### Phase 4: Update runner.py

The refactored `runner.py` (~200 lines) will focus solely on experiment execution:
```python
class ExperimentRunner:
    def __init__(self, output_dir: Path, daemon: Optional[ExperimentDaemon] = None):
        self.setup = ExperimentSetup()
        self.orchestrator = ConversationOrchestrator()
    
    async def run_experiment_with_id(self, exp_id: str, config: ExperimentConfig):
        """Simplified experiment execution."""
        # Setup
        event_bus = self.setup.setup_event_bus(exp_dir, config)
        agents, providers = self.setup.create_agents_and_providers(config, event_bus)
        
        # Execute
        if config.max_parallel > 1:
            await self.orchestrator.run_parallel(conversations, ...)
        else:
            await self.orchestrator.run_sequential(conversations, ...)
```

## Testing Strategy

1. **Create test stubs first** for each new module
2. **Extract with tests** - ensure each extraction maintains functionality
3. **Integration tests** remain unchanged (they test the full flow)
4. **Unit tests** for each new module

## Implementation Order

1. Start with `model_selector.py` - self-contained and easy to test
2. Extract `spec_loader.py` - clear boundaries
3. Extract `config_builder.py` - depends on model validation
4. Extract `daemon_launcher.py` - straightforward extraction
5. Extract `display_manager.py` - complex but isolated
6. Refactor what remains in `run.py`
7. Move to `runner.py` refactoring

## Success Criteria

- [ ] run.py under 200 lines
- [ ] runner.py under 200 lines  
- [ ] All tests passing
- [ ] No functionality lost
- [ ] Each new module has clear single responsibility
- [ ] Each new module has unit tests

## Notes

- This is a large refactoring that should be done incrementally
- Each extraction should be a separate commit
- Consider using the test-first-developer agent for creating test stubs
- The existing integration tests will catch any regressions