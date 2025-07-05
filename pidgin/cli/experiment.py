# pidgin/cli/experiment.py
"""Experiment-related CLI commands."""

__all__ = ['experiment']

import os
import sys
import json
import asyncio
import signal
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .helpers import (
    get_provider_for_model,
    build_initial_prompt,
    validate_model_id,
    format_model_display,
    parse_temperature,
    parse_dimensions,
    get_experiment_dir
)
from ..config.resolution import resolve_temperatures
from ..config.defaults import get_smart_convergence_defaults
from ..io.paths import get_experiments_dir
from ..config.models import get_model_config
from .constants import (
    NORD_GREEN, NORD_RED, NORD_BLUE, NORD_YELLOW, NORD_CYAN,
    DEFAULT_TURNS, DEFAULT_TEMPERATURE, DEFAULT_PARALLEL
)
from ..experiments import ExperimentManager, ExperimentConfig
from .jsonl_reader import JSONLExperimentReader

console = Console()

# Import ORIGINAL_CWD from main module
from . import ORIGINAL_CWD


@click.group()
def experiment():
    """Run and manage experimental AI conversation sessions.

    Experiments run as daemons in the background for reliability.
    Use the status command to check progress.

    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Start experiment:[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 20 --name "test"
    
    [#4c566a]Check experiment status:[/#4c566a]
        pidgin experiment status
    
    [#4c566a]List experiment sessions:[/#4c566a]
        pidgin experiment list
    
    [#4c566a]Start in background (daemon):[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 100 --name "bg" --daemon
    """
    pass


@experiment.command()
@click.option("-a", "--agent-a", "model_a", required=True, help="First model")
@click.option("-b", "--agent-b", "model_b", required=True, help="Second model")
@click.option("-r", "--repetitions", default=10, help="Number of conversations to run")
@click.option("-t", "--max-turns", default=50, help="Maximum turns per conversation")
@click.option("-p", "--prompt", help="Custom prompt for conversations")
@click.option("-d", "--dimensions", help="Dimensional prompt (e.g., peers:philosophy)")
@click.option("--name", required=True, help="Experiment session name")
@click.option("--temperature", type=click.FloatRange(0.0, 2.0), help="Temperature for both models")
@click.option("--temp-a", type=click.FloatRange(0.0, 2.0), help="Temperature for model A only")
@click.option("--temp-b", type=click.FloatRange(0.0, 2.0), help="Temperature for model B only")
@click.option("--awareness", type=click.Choice(['none', 'basic', 'firm', 'research']), default='basic', help="Awareness level for both agents")
@click.option("--awareness-a", type=click.Choice(['none', 'basic', 'firm', 'research']), help="Awareness level for agent A only")
@click.option("--awareness-b", type=click.Choice(['none', 'basic', 'firm', 'research']), help="Awareness level for agent B only")
@click.option("--convergence-threshold", type=click.FloatRange(0.0, 1.0), help="Stop at convergence threshold")
@click.option("--choose-names", is_flag=True, help="Allow agents to choose names")
@click.option("--max-parallel", type=int, default=1, help="Max parallel conversations (default: 1, sequential)")
@click.option("--detach", is_flag=True, help="Start in background without attaching")
@click.option("--debug", is_flag=True, help="Run in debug mode (no daemonization)")
def start(model_a, model_b, repetitions, max_turns, prompt, dimensions, name,
          temperature, temp_a, temp_b, awareness, awareness_a, awareness_b,
          convergence_threshold, choose_names, max_parallel, detach, debug):
    """Start a new experiment session.

    By default, starts the experiment and automatically attaches to show live progress.
    Use Ctrl+C to detach while keeping the experiment running.

    [bold]EXAMPLES:[/bold]

    [#4c566a]Start and watch (default):[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 20 --name "test"

    [#4c566a]Start detached (background only):[/#4c566a] 
        pidgin experiment start -a opus -b gpt-4 -r 100 --name "prod" --detach

    [#4c566a]Parallel execution (use with caution):[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 10 --name "parallel" --max-parallel 3

    [bold]TIP:[/bold] You can always re-attach later with 'pidgin experiment attach <name>'
    """
    # Validate models
    try:
        agent_a_id, agent_a_name = validate_model_id(model_a)
        agent_b_id, agent_b_name = validate_model_id(model_b)
    except ValueError as e:
        console.print(f"[{NORD_RED}]Error: {e}[/{NORD_RED}]")
        return
    
    # Handle temperature settings
    temp_a, temp_b = resolve_temperatures(temperature, temp_a, temp_b)
    
    # Build initial prompt
    initial_prompt = build_initial_prompt(prompt, dimensions.split(',') if dimensions else [])
    
    # Add smart convergence defaults for API models
    convergence_action = 'stop'  # Default action for experiments
    if convergence_threshold is None:
        default_threshold, default_action = get_smart_convergence_defaults(agent_a_id, agent_b_id)
        if default_threshold is not None:
            convergence_threshold = default_threshold
            convergence_action = default_action
            console.print(f"[dim]Using default convergence threshold: {convergence_threshold} → {convergence_action}[/dim]")
    
    # Generate experiment name if not provided
    if not name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{model_a}_{model_b}_{timestamp}"
    
    # Create experiment configuration
    config = ExperimentConfig(
        name=name,
        agent_a_model=agent_a_id,
        agent_b_model=agent_b_id,
        repetitions=repetitions,
        max_turns=max_turns,
        temperature_a=temp_a,
        temperature_b=temp_b,
        custom_prompt=initial_prompt if prompt else None,
        dimensions=dimensions.split(',') if dimensions else None,
        max_parallel=max_parallel,
        convergence_threshold=convergence_threshold,
        convergence_action=convergence_action,
        awareness=awareness,
        awareness_a=awareness_a,
        awareness_b=awareness_b,
        choose_names=choose_names
    )
    
    # Show configuration
    console.print(f"\n[bold {NORD_BLUE}]◆ Experiment Configuration[/bold {NORD_BLUE}]")
    console.print(f"  Name: {name}")
    console.print(f"  Models: {format_model_display(agent_a_id)} ↔ {format_model_display(agent_b_id)}")
    console.print(f"  Conversations: {repetitions}")
    console.print(f"  Turns per conversation: {max_turns}")
    console.print(f"  Parallel execution: {max_parallel}")
    
    if initial_prompt != "Hello":
        console.print(f"  Initial prompt: {initial_prompt[:50]}...")
    
    if temp_a is not None or temp_b is not None:
        temp_parts = []
        if temp_a is not None:
            temp_parts.append(f"A: {temp_a}")
        if temp_b is not None:
            temp_parts.append(f"B: {temp_b}")
        console.print(f"  Temperature: {', '.join(temp_parts)}")
    
    if convergence_threshold:
        console.print(f"  Convergence: {convergence_threshold} → {convergence_action}")
    
    # Check if experiment already exists using JSONL
    jsonl_reader = JSONLExperimentReader(get_experiments_dir())
    experiments = jsonl_reader.list_experiments()
    existing = next((exp for exp in experiments if exp.get('name') == name), None)

    if existing:
        console.print(f"[#bf616a]Experiment session '{name}' already exists[/#bf616a]")
        console.print(f"Use 'pidgin experiment resume {name}' to reattach")
        return
    
    # Validate configuration
    errors = config.validate()
    if errors:
        console.print(f"[#bf616a]Configuration errors:[/#bf616a]")
        for error in errors:
            console.print(f"  • {error}")
        return
    
    if debug:
        # Debug mode - run directly without daemonization
        console.print(f"[#ebcb8b]◆ Starting experiment '{name}' in DEBUG mode[/#ebcb8b]")
        console.print(f"[#4c566a]  Models: {model_a} vs {model_b}[/#4c566a]")
        console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
        console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
        console.print(f"\n[#bf616a]Running in foreground - press Ctrl+C to stop[/#bf616a]\n")
        
        # Run directly without daemon
        from ..experiments import ExperimentRunner
        
        # Generate experiment ID
        exp_id = f"exp_{uuid.uuid4().hex[:8]}"
        
        # In debug mode, pass output directory
        runner = ExperimentRunner(get_experiments_dir(), daemon=None)
        
        async def run_debug_experiment():
            try:
                # Run the experiment
                await runner.run_experiment_with_id(exp_id, config)
                return True
            except Exception:
                raise
        
        try:
            success = asyncio.run(run_debug_experiment())
            console.print(f"\n[#a3be8c]✓ Experiment '{name}' completed[/#a3be8c]")
            # Terminal bell notification
            print('\a', end='', flush=True)
        except KeyboardInterrupt:
            console.print(f"\n[#ebcb8b]Experiment interrupted by user[/#ebcb8b]")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Experiment failed: {e}[/#bf616a]")
            import traceback
            traceback.print_exc()
            # Terminal bell for failure too
            print('\a', end='', flush=True)
        return
        
    # Always start as daemon for non-debug mode
    base_dir = get_experiments_dir()
    manager = ExperimentManager(base_dir=base_dir)
    
    console.print(f"[#8fbcbb]◆ Starting experiment '{name}'[/#8fbcbb]")
    console.print(f"[#4c566a]  Models: {model_a} vs {model_b}[/#4c566a]")
    console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
    console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
    
    try:
        # Use the original working directory captured at module import
        exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)
        
        # Show start message
        console.print(f"\n[#a3be8c]✓ Experiment '{name}' started successfully[/#a3be8c]")
        
        if detach:
            # User wants to detach - just show info
            console.print(f"[#4c566a]Running in background. Use 'pidgin experiment attach {exp_id[:8]}' to monitor[/#4c566a]")
        else:
            # Default behavior: automatically attach to show progress
            console.print(f"[#4c566a]Attaching to experiment...[/#4c566a]\n")
            
            # Give the daemon a moment to start
            import time
            time.sleep(2)
            
            # Get the experiment directory
            exp_dir = get_experiments_dir() / exp_id
            
            # Attach to the experiment
            try:
                asyncio.run(attach_to_experiment(exp_id, tail=False, exp_dir=exp_dir))
            except KeyboardInterrupt:
                # Already handled in attach_to_experiment
                pass
            
    except Exception as e:
        console.print(f"\n[#bf616a]✗ Failed to start experiment: {str(e)}[/#bf616a]")
        raise


# In pidgin/cli/experiment.py, update the list command around line 268:

@experiment.command()
@click.option("--all", is_flag=True, help="Show completed experiments too")
def list(all):
    """List experiment sessions (like screen -list).
    
    Shows active experiment sessions with their status and progress.
    """
    from ..experiments.state_builder import StateBuilder
    
    # Build states from JSONL files
    exp_base = get_experiments_dir()
    experiment_states = []
    
    # Find all experiment directories
    for exp_dir in exp_base.glob("exp_*"):
        if exp_dir.is_dir():
            state = StateBuilder.from_experiment_dir(exp_dir)
            if state:
                # Filter based on --all flag
                if all or state.status in ['running', 'created']:
                    experiment_states.append(state)
    
    if not experiment_states:
        if all:
            console.print(f"[{NORD_YELLOW}]No experiments found.[/{NORD_YELLOW}]")
        else:
            console.print(f"[{NORD_YELLOW}]No running experiments.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_CYAN}]Use --all to see completed experiments.[/{NORD_CYAN}]")
        return
    
    # Create table
    table = Table(title="Experiment Sessions")
    table.add_column("ID", style=NORD_CYAN)
    table.add_column("Name", style=NORD_GREEN)
    table.add_column("Status", style=NORD_YELLOW)
    table.add_column("Progress")
    table.add_column("Models")
    table.add_column("Started")
    
    # Sort by started time, most recent first
    experiment_states.sort(key=lambda s: s.started_at or s.created_at, reverse=True)
    
    for state in experiment_states:
        # Format progress
        completed, total = state.progress
        progress = f"{completed}/{total}"
        
        # Format status with color
        status_color = {
            'running': NORD_GREEN,
            'completed': NORD_BLUE,
            'failed': NORD_RED,
            'interrupted': NORD_YELLOW,
            'created': NORD_CYAN
        }.get(state.status, 'white')
        status_display = f"[{status_color}]{state.status}[/{status_color}]"
        
        # Format models from first conversation (they're all the same in an experiment)
        if state.conversations:
            first_conv = next(iter(state.conversations.values()))
            models = f"{first_conv.agent_a_model} ↔ {first_conv.agent_b_model}"
        else:
            models = "? ↔ ?"
        
        # Format time
        time_str = "-"
        if state.started_at:
            time_str = state.started_at.strftime("%Y-%m-%d %H:%M")
        elif state.created_at:
            time_str = state.created_at.strftime("%Y-%m-%d %H:%M")
        
        table.add_row(
            state.experiment_id[:8],  # Show shortened ID
            state.name,
            status_display,
            progress,
            models,
            time_str
        )
    
    console.print(table)
    
    if not all:
        console.print(f"\n[{NORD_CYAN}]Tip: Use 'pidgin experiment attach <id>' to monitor a running experiment[/{NORD_CYAN}]")

@experiment.command()
@click.argument('experiment_id', required=False)
@click.option('--watch', '-w', is_flag=True, help='Watch experiment until completion')
@click.option('--notify', '-n', is_flag=True, help='Terminal bell when complete')
def status(experiment_id, watch, notify):
    """Check status of an experiment.
    
    Shows detailed status of a specific experiment or all running experiments.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Check all running experiments:[/#4c566a]
        pidgin experiment status
    
    [#4c566a]Check specific experiment:[/#4c566a]
        pidgin experiment status abc123
    
    [#4c566a]Watch experiment until completion:[/#4c566a]
        pidgin experiment status abc123 --watch --notify
    """
    if experiment_id:
        # Show specific experiment - always use JSONL to avoid locks
        jsonl_reader = JSONLExperimentReader(get_experiments_dir())
        exp = jsonl_reader.get_experiment_status(experiment_id)
        
        if not exp:
            # Try partial match
            all_exps = jsonl_reader.list_experiments()
            matches = [e for e in all_exps if e['experiment_id'].startswith(experiment_id)]
            if len(matches) == 1:
                exp = matches[0]
            elif len(matches) > 1:
                console.print(f"[{NORD_RED}]Multiple experiments match '{experiment_id}'[/{NORD_RED}]")
                return
        
        if not exp:
            console.print(f"[{NORD_RED}]No experiment found with ID '{experiment_id}'[/{NORD_RED}]")
            return
        
        # Display experiment details
        # Handle config - might be dict (from JSONL) or string (from DB)
        config = exp.get('config', {})
        if isinstance(config, str):
            config = json.loads(config) if config else {}
        elif config is None:
            config = {}
        
        console.print(f"\n[bold {NORD_BLUE}]◆ Experiment: {exp['name']}[/bold {NORD_BLUE}]")
        console.print(f"  ID: {exp['experiment_id']}")
        console.print(f"  Status: {exp['status']}")
        console.print(f"  Progress: {exp['completed_conversations']}/{exp['total_conversations']}")
        console.print(f"  Models: {config.get('agent_a_model')} ↔ {config.get('agent_b_model')}")
        
        if exp['status'] == 'running':
            # Calculate estimated time
            if exp['completed_conversations'] > 0:
                started = datetime.fromisoformat(exp['started_at'].replace('Z', '+00:00'))
                elapsed = datetime.now(started.tzinfo) - started
                avg_time = elapsed / exp['completed_conversations']
                remaining = (exp['total_conversations'] - exp['completed_conversations']) * avg_time
                console.print(f"  Estimated time remaining: {str(remaining).split('.')[0]}")
        
        if watch and exp['status'] == 'running':
            console.print(f"\n[{NORD_YELLOW}]Watching experiment... Press Ctrl+C to stop[/{NORD_YELLOW}]")
            
            # Watch loop
            try:
                while True:
                    import time
                    time.sleep(5)  # Check every 5 seconds
                    
                    # Refresh experiment data from JSONL
                    jsonl_reader = JSONLExperimentReader(get_experiments_dir())
                    exp = jsonl_reader.get_experiment_status(exp['experiment_id'])
                    
                    if exp['status'] != 'running':
                        console.print(f"\n[{NORD_GREEN}]✓ Experiment completed with status: {exp['status']}[/{NORD_GREEN}]")
                        if notify:
                            # Try desktop notification
                            try:
                                from .notify import notify_experiment_complete
                                notify_experiment_complete(exp['name'], exp['status'])
                            except:
                                # Fallback to terminal bell
                                print('\a', end='', flush=True)
                        break
                    
                    # Update progress
                    console.print(f"\r  Progress: {exp['completed_conversations']}/{exp['total_conversations']}", end='')
                    
            except KeyboardInterrupt:
                console.print(f"\n[{NORD_YELLOW}]Stopped watching[/{NORD_YELLOW}]")
        
    else:
        # Show all running experiments - always use JSONL
        jsonl_reader = JSONLExperimentReader(get_experiments_dir())
        experiments = jsonl_reader.list_experiments(status_filter='running')
        
        if not experiments:
            console.print(f"[{NORD_YELLOW}]No running experiments.[/{NORD_YELLOW}]")
            console.print(f"[{NORD_CYAN}]Use 'pidgin experiment list --all' to see all experiments.[/{NORD_CYAN}]")
            return
        
        # Create summary table
        table = Table(title="Running Experiments")
        table.add_column("ID", style=NORD_CYAN)
        table.add_column("Name", style=NORD_GREEN)
        table.add_column("Progress")
        table.add_column("Models")
        table.add_column("Time Running")
        
        for exp in experiments:
            config = json.loads(exp.get('config', '{}'))
            
            # Format progress with percentage
            total = exp.get('total_conversations', 0)
            completed = exp.get('completed_conversations', 0)
            percentage = (completed / total * 100) if total > 0 else 0
            progress = f"{completed}/{total} ({percentage:.0f}%)"
            
            # Format models
            models = f"{config.get('agent_a_model', '?')} ↔ {config.get('agent_b_model', '?')}"
            
            # Calculate time running
            started = exp.get('started_at', exp.get('created_at', ''))
            if started:
                try:
                    dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                    elapsed = datetime.now(dt.tzinfo) - dt
                    time_str = str(elapsed).split('.')[0]
                except:
                    time_str = "-"
            else:
                time_str = "-"
            
            table.add_row(
                exp['experiment_id'][:8],
                exp.get('name', 'Unnamed'),
                progress,
                models,
                time_str
            )
        
        console.print(table)
        console.print(f"\n[{NORD_CYAN}]Use 'pidgin experiment status <id>' for details[/{NORD_CYAN}]")


async def attach_to_experiment(experiment_id: str, tail: bool = False, exp_dir: Path = None):
    """Attach to a running experiment - simplified version.
    
    Args:
        experiment_id: Experiment ID (can be partial)
        tail: Whether to show event stream (ignored for now)
        exp_dir: Optional pre-resolved experiment directory
        
    Returns:
        True if successfully attached and detached, False if error
    """
    import time
    import json
    
    # Find experiment directory if not provided
    if not exp_dir:
        exp_base = get_experiments_dir()
        
        # Handle partial ID match
        matching_dirs = list(exp_base.glob(f"{experiment_id}*"))
        if not matching_dirs:
            console.print(f"[{NORD_RED}]No experiment found matching '{experiment_id}'[/{NORD_RED}]")
            return False
        
        if len(matching_dirs) > 1:
            console.print(f"[{NORD_RED}]Multiple experiments match '{experiment_id}':[/{NORD_RED}]")
            for d in matching_dirs:
                console.print(f"  • {d.name}")
            return False
        
        exp_dir = matching_dirs[0]
    
    # Read metadata
    metadata_path = exp_dir / 'metadata.json'
    if not metadata_path.exists():
        console.print(f"[{NORD_RED}]No metadata found for experiment[/{NORD_RED}]")
        return False
        
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    if metadata.get('status') not in ['running', 'created']:
        console.print(f"[{NORD_YELLOW}]Experiment is {metadata.get('status', 'unknown')}[/{NORD_YELLOW}]")
        return False
    
    console.print(f"[bold {NORD_CYAN}]◆ Monitoring: {metadata.get('name', experiment_id)}[/bold {NORD_CYAN}]")
    console.print(f"[{NORD_YELLOW}][Ctrl+C to stop monitoring][/{NORD_YELLOW}]\n")
    
    # Simple status monitoring
    try:
        while True:
            # Reload metadata
            with open(metadata_path) as f:
                metadata = json.load(f)
            
            status = metadata.get('status', 'unknown')
            if status not in ['running', 'created']:
                console.print(f"\n[{NORD_GREEN}]Experiment {status}[/{NORD_GREEN}]")
                break
            
            # Show simple status
            completed = metadata.get('completed_conversations', 0)
            failed = metadata.get('failed_conversations', 0) 
            total = metadata.get('total_conversations', 0)
            
            console.print(f"Status: {completed}/{total} complete, {failed} failed", end='\r')
            
            # Wait before refresh
            time.sleep(2)
            
    except KeyboardInterrupt:
        console.print(f"\n[{NORD_YELLOW}]Stopped monitoring[/{NORD_YELLOW}]")
        return True
    
    return True


@experiment.command()
@click.argument('experiment_id')
@click.option('--tail', is_flag=True, help='Show event stream (like tail -f)')
def attach(experiment_id, tail):
    """Attach to a running experiment (like screen -r).
    
    Shows live progress of a running experiment. Ctrl+C to detach.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Attach with progress bar (default):[/#4c566a]
        pidgin experiment attach exp_abc123
    
    [#4c566a]Attach with event stream:[/#4c566a]
        pidgin experiment attach exp_abc123 --tail
    """
    # Run the async attach function
    try:
        asyncio.run(attach_to_experiment(experiment_id, tail))
    except KeyboardInterrupt:
        # Already handled in attach_to_experiment
        pass


@experiment.command()
@click.argument('experiment_id', required=False)
@click.option('--all', is_flag=True, help='Stop all running experiments')
def stop(experiment_id, all):
    """Stop a running experiment gracefully.
    
    Use --all to stop all running experiments at once.
    """
    if all:
        # Stop all logic from stop_all command
        console.print(f"[bold {NORD_RED}]⚠️  Stopping ALL experiments ⚠️[/bold {NORD_RED}]")
        console.print(f"[{NORD_YELLOW}]This will stop ALL running experiments![/{NORD_YELLOW}]\n")
        
        # Find all daemon PIDs
        active_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "active"
        daemon_pids = []
        
        if active_dir.exists():
            for pid_file in active_dir.glob("*.pid"):
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                        daemon_pids.append((pid, pid_file.stem))
                except:
                    pass
        
        console.print(f"[{NORD_CYAN}]Found {len(daemon_pids)} running daemons[/{NORD_CYAN}]")
        
        # Kill each daemon
        for pid, exp_id in daemon_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                console.print(f"[{NORD_YELLOW}]  → Stopped {exp_id} (PID: {pid})[/{NORD_YELLOW}]")
            except ProcessLookupError:
                console.print(f"[{NORD_YELLOW}]  ! {exp_id} already dead (PID: {pid})[/{NORD_YELLOW}]")
            except Exception as e:
                console.print(f"[{NORD_RED}]  ✗ Failed to stop {exp_id}: {e}[/{NORD_RED}]")
        
        # Clean up database
        console.print(f"\n[{NORD_CYAN}]Updating database...[/{NORD_CYAN}]")
        
        # Mark all running experiments as failed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            storage = EventStore(
                db_path=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "experiments.duckdb"
            )
            experiments = loop.run_until_complete(storage.list_experiments(status_filter='running'))
            for exp in experiments:
                loop.run_until_complete(storage.update_experiment_status(exp['experiment_id'], 'failed'))
            loop.run_until_complete(storage.close())
        finally:
            loop.close()
            console.print(f"[{NORD_GREEN}]  ✓ Marked '{exp['name']}' as failed[/{NORD_GREEN}]")
        
        console.print(f"\n[bold {NORD_GREEN}]✓ All experiments stopped[/bold {NORD_GREEN}]")
    else:
        if not experiment_id:
            console.print(f"[{NORD_RED}]Error: Either provide an experiment ID or use --all[/{NORD_RED}]")
            return
            
        manager = ExperimentManager(
            base_dir=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
        )
        
        console.print(f"[{NORD_YELLOW}]→ Stopping experiment {experiment_id}...[/{NORD_YELLOW}]")
        
        if manager.stop_experiment(experiment_id):
            console.print(f"[{NORD_GREEN}]✓ Stopped experiment {experiment_id}[/{NORD_GREEN}]")
        else:
            console.print(f"[{NORD_RED}]✗ Failed to stop experiment {experiment_id}[/{NORD_RED}]")
            console.print(f"[{NORD_YELLOW}]  (It may not be running)[/{NORD_YELLOW}]")




