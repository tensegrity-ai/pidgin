# Branch Command Refactoring Plan

## Problem Statement
The `branch()` function in `cli/branch.py` is 292 lines long (lines 50-342), violating our 200-line guideline and handling multiple responsibilities in a single monolithic function.

## Important Note
**No backwards compatibility required** - We can make clean breaks and optimal design choices without preserving old interfaces.

## Current Structure Analysis

### Responsibilities Breakdown
1. **Conversation Discovery** (lines 92-116, ~25 lines)
   - Find source conversation across experiments
   - Load conversation state

2. **Configuration Building** (lines 118-173, ~55 lines)
   - Extract original configuration
   - Apply model overrides
   - Apply temperature overrides
   - Apply awareness overrides
   - Apply other parameter overrides

3. **Spec File Generation** (lines 180-208, ~28 lines)
   - Build YAML spec data
   - Save to file

4. **Change Display** (lines 210-232, ~22 lines)
   - Compare original vs new config
   - Format changes for display

5. **Validation** (lines 254-280, ~26 lines)
   - Validate configuration
   - Validate API keys

6. **Execution** (lines 282-341, ~59 lines)
   - Start experiment
   - Handle quiet mode
   - Handle interactive display
   - Show completion info

## Proposed Refactoring

### New Module Structure
```
cli/
  branch.py (main command, ~100 lines)
  branch_handlers/
    __init__.py
    models.py (~20 lines)
    source_finder.py (~60 lines)
    config_builder.py (~80 lines)
    spec_writer.py (~40 lines)
    executor.py (~100 lines)
```

### Class Designs

#### 1. Data Models (`models.py`)
```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

@dataclass
class BranchSource:
    """Source conversation data for branching."""
    conversation_id: str
    experiment_dir: Path
    config: Dict[str, Any]
    messages: List[Any]
    metadata: Dict[str, Any]
    branch_point: int
    
    def get_info(self) -> str:
        """Format source info for display."""
        return "\n".join([
            f"Source: {self.experiment_dir.name}",
            f"Conversation: {self.conversation_id}",
            f"Branch point: Turn {self.branch_point} of {len(self.messages)}",
            f"Original models: {self.config['agent_a_model']} ↔ {self.config['agent_b_model']}"
        ])
```

#### 2. Source Finder (`source_finder.py`)
```python
from pathlib import Path
from typing import Optional
from ..experiments.state_builder import StateBuilder
from .models import BranchSource

class BranchSourceFinder:
    """Find and load source conversations for branching."""
    
    def __init__(self, experiments_dir: Path):
        self.experiments_dir = experiments_dir
        self.state_builder = StateBuilder()
    
    def find_conversation(
        self, 
        conversation_id: str, 
        turn: Optional[int] = None
    ) -> Optional[BranchSource]:
        """Find conversation and return source data.
        
        Args:
            conversation_id: ID of conversation to find
            turn: Optional turn number to branch from
            
        Returns:
            BranchSource if found, None otherwise
        """
        for exp_dir in self.experiments_dir.glob("exp_*"):
            if not exp_dir.is_dir():
                continue
            
            state = self.state_builder.get_conversation_state(
                exp_dir, conversation_id, turn
            )
            if state:
                return BranchSource(
                    conversation_id=conversation_id,
                    experiment_dir=exp_dir,
                    config=state["config"],
                    messages=state["messages"],
                    metadata=state["metadata"],
                    branch_point=state["branch_point"]
                )
        return None
```

#### 3. Config Builder (`config_builder.py`)
```python
from typing import Optional, List, Dict, Any
from ..providers.model_validator import validate_model_id
from ..experiments.config import ExperimentConfig

class BranchConfigBuilder:
    """Build configuration for branched experiments."""
    
    def __init__(self, original_config: Dict[str, Any]):
        self.original_config = original_config
        self.branch_config = original_config.copy()
    
    def apply_model_overrides(
        self, 
        agent_a: Optional[str], 
        agent_b: Optional[str]
    ) -> List[str]:
        """Apply model overrides and return any errors."""
        errors = []
        if agent_a:
            try:
                self.branch_config["agent_a_model"] = validate_model_id(agent_a)[0]
            except ValueError as e:
                errors.append(f"Invalid agent A model: {e}")
        
        if agent_b:
            try:
                self.branch_config["agent_b_model"] = validate_model_id(agent_b)[0]
            except ValueError as e:
                errors.append(f"Invalid agent B model: {e}")
        
        return errors
    
    def apply_temperature_overrides(
        self,
        temperature: Optional[float],
        temp_a: Optional[float],
        temp_b: Optional[float]
    ):
        """Apply temperature overrides."""
        if temperature is not None:
            self.branch_config["temperature_a"] = temperature
            self.branch_config["temperature_b"] = temperature
        if temp_a is not None:
            self.branch_config["temperature_a"] = temp_a
        if temp_b is not None:
            self.branch_config["temperature_b"] = temp_b
    
    def apply_awareness_overrides(
        self,
        awareness: Optional[str],
        awareness_a: Optional[str],
        awareness_b: Optional[str]
    ):
        """Apply awareness overrides."""
        if awareness:
            self.branch_config["awareness_a"] = awareness
            self.branch_config["awareness_b"] = awareness
        if awareness_a:
            self.branch_config["awareness_a"] = awareness_a
        if awareness_b:
            self.branch_config["awareness_b"] = awareness_b
    
    def apply_other_overrides(self, max_turns: Optional[int]):
        """Apply other parameter overrides."""
        if max_turns is not None:
            self.branch_config["max_turns"] = max_turns
    
    def get_changes(self) -> List[str]:
        """Get list of configuration changes."""
        changes = []
        
        if self.branch_config["agent_a_model"] != self.original_config["agent_a_model"]:
            changes.append(
                f"Agent A: {self.original_config['agent_a_model']} → "
                f"{self.branch_config['agent_a_model']}"
            )
        
        if self.branch_config["agent_b_model"] != self.original_config["agent_b_model"]:
            changes.append(
                f"Agent B: {self.original_config['agent_b_model']} → "
                f"{self.branch_config['agent_b_model']}"
            )
        
        # Add temperature and awareness changes...
        
        return changes
    
    def build_experiment_config(
        self,
        name: str,
        repetitions: int,
        messages: List[Any],
        conversation_id: str,
        branch_point: int
    ) -> ExperimentConfig:
        """Build ExperimentConfig for the branch."""
        return ExperimentConfig(
            name=name,
            agent_a_model=self.branch_config["agent_a_model"],
            agent_b_model=self.branch_config["agent_b_model"],
            repetitions=repetitions,
            max_turns=self.branch_config["max_turns"],
            temperature_a=self.branch_config.get("temperature_a"),
            temperature_b=self.branch_config.get("temperature_b"),
            awareness_a=self.branch_config.get("awareness_a", "basic"),
            awareness_b=self.branch_config.get("awareness_b", "basic"),
            branch_from_conversation=conversation_id,
            branch_from_turn=branch_point,
            branch_messages=messages
        )
```

#### 4. Spec Writer (`spec_writer.py`)
```python
import yaml
from typing import Dict, Any, List
from pathlib import Path

class BranchSpecWriter:
    """Handle branch specification file operations."""
    
    def save_spec(
        self,
        spec_path: str,
        branch_config: Dict[str, Any],
        metadata: Dict[str, Any],
        messages: List[Any],
        name: str,
        repetitions: int,
        conversation_id: str,
        branch_point: int
    ) -> Optional[str]:
        """Save branch specification to YAML file.
        
        Returns:
            Error message if failed, None if successful
        """
        spec_data = {
            "name": name,
            "agent_a_model": branch_config["agent_a_model"],
            "agent_b_model": branch_config["agent_b_model"],
            "repetitions": repetitions,
            "max_turns": branch_config["max_turns"],
            "temperature_a": branch_config.get("temperature_a"),
            "temperature_b": branch_config.get("temperature_b"),
            "awareness_a": branch_config.get("awareness_a", "basic"),
            "awareness_b": branch_config.get("awareness_b", "basic"),
            "branch_from": {
                "conversation_id": conversation_id,
                "turn": branch_point,
                "experiment_id": metadata.get("original_experiment_id"),
            },
            "initial_messages": [
                {"role": msg.role, "content": msg.content} 
                for msg in messages
            ],
        }
        
        try:
            with open(spec_path, "w") as f:
                yaml.dump(spec_data, f, default_flow_style=False)
            return None
        except Exception as e:
            return str(e)
```

#### 5. Executor (`executor.py`)
```python
import asyncio
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from ..ui.display_utils import DisplayUtils
from ..experiments.config import ExperimentConfig
from ..experiments.manager import ExperimentManager
from ..providers.api_key_manager import APIKeyManager

class BranchExecutor:
    """Execute branched experiments."""
    
    def __init__(self, display: DisplayUtils, console: Console):
        self.display = display
        self.console = console
    
    def validate_config(self, config: ExperimentConfig) -> Optional[str]:
        """Validate configuration.
        
        Returns:
            Error message if validation fails, None if valid
        """
        errors = config.validate()
        if errors:
            return "Configuration errors:\n\n" + "\n".join(
                f"  • {error}" for error in errors
            )
        return None
    
    def validate_api_keys(self, config: ExperimentConfig) -> Optional[str]:
        """Validate API keys for required providers.
        
        Returns:
            Error message if validation fails, None if valid
        """
        from ..config.models import get_model_config
        
        providers = set()
        agent_a_config = get_model_config(config.agent_a_model)
        agent_b_config = get_model_config(config.agent_b_model)
        
        if agent_a_config:
            providers.add(agent_a_config.provider)
        if agent_b_config:
            providers.add(agent_b_config.provider)
        
        try:
            APIKeyManager.validate_required_providers(list(providers))
            return None
        except Exception as e:
            return str(e)
    
    def execute(
        self, 
        config: ExperimentConfig, 
        quiet: bool,
        working_dir: str
    ) -> Optional[str]:
        """Execute the branch experiment.
        
        Returns:
            Experiment ID if successful, None if failed
        """
        # Validate
        if error := self.validate_config(config):
            self.display.error(error, use_panel=True)
            return None
        
        if error := self.validate_api_keys(config):
            self.display.error(error, title="Missing API Keys", use_panel=True)
            return None
        
        # Start experiment
        from ..io.paths import get_experiments_dir
        manager = ExperimentManager(base_dir=get_experiments_dir())
        
        try:
            exp_id = manager.start_experiment(config, working_dir=working_dir)
            self.console.print(f"\n[#a3be8c]✓ Started branch: {exp_id}[/#a3be8c]")
            
            if quiet:
                self._show_quiet_mode_info(exp_id, config.name)
            else:
                self._show_interactive_display(exp_id, config.name, config.repetitions)
            
            return exp_id
            
        except Exception as e:
            self.display.error(f"Failed to start branch: {str(e)}", use_panel=True)
            return None
    
    def _show_quiet_mode_info(self, exp_id: str, name: str):
        """Show commands for quiet mode."""
        self.console.print("\n[#4c566a]Running in background. Check progress:[/#4c566a]")
        cmd_lines = [
            "pidgin monitor              # Monitor all experiments",
            f"pidgin stop {name}    # Stop by name",
            f"pidgin stop {exp_id[:8]}  # Stop by ID",
        ]
        self.display.info("\n".join(cmd_lines), title="Commands", use_panel=True)
    
    def _show_interactive_display(self, exp_id: str, name: str, repetitions: int):
        """Show interactive display and handle completion."""
        self.console.print(
            "[#4c566a]Ctrl+C to exit display • experiment continues[/#4c566a]\n"
        )
        
        from ..experiments.display_runner import run_display
        
        try:
            asyncio.run(run_display(exp_id, "chat"))
            self._show_completion_info(exp_id, repetitions)
        except KeyboardInterrupt:
            self.console.print()
            self.display.info(
                "Display exited. Branch continues in background.", 
                use_panel=False
            )
    
    def _show_completion_info(self, exp_id: str, repetitions: int):
        """Show completion information if manifest exists."""
        from ..io.paths import get_experiments_dir
        
        exp_dir = get_experiments_dir() / exp_id
        manifest_path = exp_dir / "manifest.json"
        
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            
            completed = manifest.get("completed_conversations", 0)
            total = manifest.get("total_conversations", repetitions)
            
            self.display.info(
                f"Branch complete: {completed}/{total} conversations",
                context=f"Output: {exp_dir}",
                use_panel=True
            )
```

### Refactored Main Function
```python
def branch(
    conversation_id: str,
    turn: Optional[int],
    agent_a: Optional[str],
    agent_b: Optional[str],
    # ... other parameters ...
):
    """Branch a conversation from any point with parameter changes."""
    
    # 1. Find source conversation
    finder = BranchSourceFinder(get_experiments_dir())
    source = finder.find_conversation(conversation_id, turn)
    if not source:
        display.error(
            f"Conversation '{conversation_id}' not found",
            context="Check the conversation ID and try again"
        )
        return
    
    # 2. Display source info
    display.info(source.get_info(), title="◆ Branch Source", use_panel=True)
    
    # 3. Build configuration
    builder = BranchConfigBuilder(source.config)
    
    # Apply overrides
    if errors := builder.apply_model_overrides(agent_a, agent_b):
        for error in errors:
            display.error(error)
        return
    
    builder.apply_temperature_overrides(temperature, temp_a, temp_b)
    builder.apply_awareness_overrides(awareness, awareness_a, awareness_b)
    builder.apply_other_overrides(max_turns)
    
    # 4. Generate name if needed
    if not name:
        name = f"{generate_experiment_name()}_branch"
        display.dim(f"Generated branch name: {name}")
    
    # 5. Save spec if requested
    if spec:
        writer = BranchSpecWriter()
        if error := writer.save_spec(
            spec, builder.branch_config, source.metadata,
            source.messages, name, repetitions,
            conversation_id, source.branch_point
        ):
            display.error(f"Failed to save spec: {error}")
            return
        display.info(f"Saved branch spec to: {spec}")
    
    # 6. Show changes
    if changes := builder.get_changes():
        display.info("\n".join(changes), title="◆ Branch Changes", use_panel=True)
    else:
        display.info("No parameter changes (exact replay)", use_panel=False)
    
    # 7. Build experiment config
    config = builder.build_experiment_config(
        name, repetitions, source.messages,
        conversation_id, source.branch_point
    )
    
    # 8. Execute
    executor = BranchExecutor(display, console)
    executor.execute(config, quiet, ORIGINAL_CWD)
```

## Implementation Steps

1. **Create directory structure**
   ```bash
   mkdir -p cli/branch_handlers
   touch cli/branch_handlers/__init__.py
   ```

2. **Extract classes in order**
   - Start with models.py (data structures)
   - Extract BranchSourceFinder
   - Extract BranchConfigBuilder
   - Extract BranchSpecWriter
   - Extract BranchExecutor

3. **Update main function**
   - Replace monolithic code with orchestrator
   - Update imports

4. **Test each component**
   - Unit tests for each class
   - Integration test for full flow

5. **Clean up**
   - Remove old code
   - Update documentation

## Benefits

- **Reduced complexity**: 295-line function → ~50-line orchestrator
- **Single responsibility**: Each class has one clear purpose
- **Testability**: Each component can be tested independently
- **Reusability**: Components can be reused elsewhere
- **Maintainability**: Changes isolated to relevant components
- **All modules under 200 lines**: Meeting project guidelines
- **No backwards compatibility constraints**: Clean, optimal design

## Timeline

- **Hour 1**: Create structure and extract models + source finder
- **Hour 2**: Extract config builder and spec writer
- **Hour 3**: Extract executor and update main function
- **Hour 4**: Write tests and documentation

Total: ~4 hours of focused work