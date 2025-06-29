# pidgin/cli/experiment.py
"""Experiment-related CLI commands."""

import os
import sys
import json
import asyncio
import signal
import subprocess
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
from .constants import (
    NORD_GREEN, NORD_RED, NORD_BLUE, NORD_YELLOW, NORD_CYAN,
    DEFAULT_TURNS, DEFAULT_TEMPERATURE, DEFAULT_PARALLEL
)
from ..experiments import ExperimentManager, ExperimentConfig, ExperimentStore

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
@click.option("--daemon", is_flag=True, help="Start in background (detached)")
@click.option("--debug", is_flag=True, help="Run in debug mode (no daemonization)")
def start(model_a, model_b, repetitions, max_turns, prompt, dimensions, name,
          temperature, temp_a, temp_b, awareness, awareness_a, awareness_b,
          convergence_threshold, choose_names, max_parallel, daemon, debug):
    """Start a new experiment session.

    By default, runs conversations sequentially (one at a time) for reliability.
    Sequential execution avoids rate limits (API models) and memory issues (local models).

    [bold]EXAMPLES:[/bold]

    [#4c566a]Sequential execution (default and recommended):[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 20 --name "test"

    [#4c566a]Background execution:[/#4c566a] 
        pidgin experiment start -a opus -b gpt-4 -r 100 --name "prod" --daemon

    [#4c566a]Parallel execution (use with caution):[/#4c566a]
        pidgin experiment start -a claude -b gpt -r 10 --name "parallel" --max-parallel 3

    [bold]WARNING:[/bold] Parallel execution can cause rate limits or memory issues.
    Most users should stick with sequential execution.
    """
    # Validate models
    try:
        agent_a_id, agent_a_name = validate_model_id(model_a)
        agent_b_id, agent_b_name = validate_model_id(model_b)
    except ValueError as e:
        console.print(f"[{NORD_RED}]Error: {e}[/{NORD_RED}]")
        return
    
    # Handle temperature settings
    temp_a = temp_a if temp_a is not None else temperature
    temp_b = temp_b if temp_b is not None else temperature
    
    # Build initial prompt
    initial_prompt = build_initial_prompt(prompt, dimensions.split(',') if dimensions else [])
    
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
    
    # Check if experiment already exists
    storage = ExperimentStore()

    # Check if experiment name already exists
    existing = next((exp for exp in storage.list_experiments() if exp.get('name') == name), None)

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
        from ..experiments.parallel_runner import ParallelExperimentRunner
        
        runner = ParallelExperimentRunner(storage)
        
        try:
            # Create experiment and run it
            exp_id = asyncio.run(runner.run_experiment(config))
            console.print(f"\n[#a3be8c]✓ Experiment '{name}' completed[/#a3be8c]")
        except KeyboardInterrupt:
            console.print(f"\n[#ebcb8b]Experiment interrupted by user[/#ebcb8b]")
        except Exception as e:
            console.print(f"\n[#bf616a]✗ Experiment failed: {e}[/#bf616a]")
            import traceback
            traceback.print_exc()
        return
        
    # Always start as daemon for non-debug mode
    base_dir = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
    manager = ExperimentManager(base_dir=base_dir)
    
    console.print(f"[#8fbcbb]◆ Starting experiment '{name}'[/#8fbcbb]")
    console.print(f"[#4c566a]  Models: {model_a} vs {model_b}[/#4c566a]")
    console.print(f"[#4c566a]  Conversations: {repetitions}[/#4c566a]")
    console.print(f"[#4c566a]  Max turns: {max_turns}[/#4c566a]")
    
    try:
        # Use the original working directory captured at module import
        exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)
        
        # Show completion message
        if not daemon:
            console.print(f"\n[#8fbcbb]◆ Experiment started successfully[/#8fbcbb]")
            console.print(f"[#4c566a]Use 'pidgin experiment status {exp_id[:8]}' to check progress[/#4c566a]")
        else:
            console.print(f"\n[#a3be8c]✓ Experiment '{name}' started in background[/#a3be8c]")
            console.print(f"[#4c566a]Use 'pidgin experiment status' to check progress[/#4c566a]")
            
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
    storage = ExperimentStore(
        db_path=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "experiments.db"
    )
    
    # Get experiments - filter by status if not showing all
    if all:
        experiments = storage.list_experiments()
    else:
        # Only show running experiments by default
        experiments = storage.list_experiments(status_filter='running')
    
    if not experiments:
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
    
    for exp in experiments:
        config = json.loads(exp.get('config', '{}'))
        
        # Format progress
        total = exp.get('total_conversations', 0)
        completed = exp.get('completed_conversations', 0)
        progress = f"{completed}/{total}"
        
        # Format status with color
        status = exp.get('status', 'unknown')
        status_color = {
            'running': NORD_GREEN,
            'completed': NORD_BLUE,
            'failed': NORD_RED,
            'interrupted': NORD_YELLOW
        }.get(status, 'white')
        status_display = f"[{status_color}]{status}[/{status_color}]"
        
        # Format models
        models = f"{config.get('agent_a_model', '?')} ↔ {config.get('agent_b_model', '?')}"
        
        # Format time
        started = exp.get('started_at', exp.get('created_at', ''))
        if started:
            try:
                dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = started
        else:
            time_str = "-"
        
        table.add_row(
            exp['experiment_id'],
            exp.get('name', 'Unnamed'),
            status_display,
            progress,
            models,
            time_str
        )
    
    console.print(table)

@experiment.command()
@click.argument('experiment_id')
def stop(experiment_id):
    """Stop a running experiment gracefully."""
    manager = ExperimentManager(
        base_dir=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
    )
    
    console.print(f"[{NORD_YELLOW}]→ Stopping experiment {experiment_id}...[/{NORD_YELLOW}]")
    
    if manager.stop_experiment(experiment_id):
        console.print(f"[{NORD_GREEN}]✓ Stopped experiment {experiment_id}[/{NORD_GREEN}]")
    else:
        console.print(f"[{NORD_RED}]✗ Failed to stop experiment {experiment_id}[/{NORD_RED}]")
        console.print(f"[{NORD_YELLOW}]  (It may not be running)[/{NORD_YELLOW}]")


@experiment.command(name='stop-all')
@click.option('--force', is_flag=True, help='Force kill all experiment processes')
def stop_all(force):
    """KILLSWITCH: Stop ALL running experiments immediately.
    
    This command will:
    - Find all running experiment daemons
    - Gracefully stop them (or force kill with --force)
    - Update database to mark experiments as failed
    - Clean up any orphaned processes
    
    WARNING: This will terminate all experiments without saving state!
    """
    console.print(f"[bold {NORD_RED}]⚠️  EXPERIMENT KILLSWITCH ⚠️[/bold {NORD_RED}]")
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
            if force:
                os.kill(pid, signal.SIGKILL)
                console.print(f"[{NORD_RED}]  ✗ Force killed {exp_id} (PID: {pid})[/{NORD_RED}]")
            else:
                os.kill(pid, signal.SIGTERM)
                console.print(f"[{NORD_YELLOW}]  → Stopped {exp_id} (PID: {pid})[/{NORD_YELLOW}]")
        except ProcessLookupError:
            console.print(f"[{NORD_YELLOW}]  ! {exp_id} already dead (PID: {pid})[/{NORD_YELLOW}]")
        except Exception as e:
            console.print(f"[{NORD_RED}]  ✗ Failed to stop {exp_id}: {e}[/{NORD_RED}]")
    
    # Clean up database
    console.print(f"\n[{NORD_CYAN}]Updating database...[/{NORD_CYAN}]")
    
    storage = ExperimentStore(
        db_path=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "experiments.db"
    )
    
    # Mark all running experiments as failed
    experiments = storage.list_experiments(status_filter='running')
    for exp in experiments:
        storage.update_experiment_status(exp['experiment_id'], 'failed')
        console.print(f"[{NORD_GREEN}]  ✓ Marked '{exp['name']}' as failed[/{NORD_GREEN}]")
    
    console.print(f"\n[bold {NORD_GREEN}]✓ KILLSWITCH COMPLETE[/bold {NORD_GREEN}]")
    console.print(f"[{NORD_YELLOW}]All experiments have been stopped.[/{NORD_YELLOW}]")


@experiment.command()
@click.argument('experiment_id')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
def logs(experiment_id, lines, follow):
    """Show logs from an experiment.
    
    By default shows the last 50 lines. Use -f to follow the log
    in real-time (press Ctrl+C to stop).
    """
    manager = ExperimentManager(
        base_dir=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments"
    )
    
    if follow:
        console.print(f"[{NORD_CYAN}]Following logs for {experiment_id} (Ctrl+C to stop)...[/{NORD_CYAN}]\n")
        try:
            manager.tail_logs(experiment_id, follow=True)
        except KeyboardInterrupt:
            console.print(f"\n[{NORD_YELLOW}]Stopped following logs.[/{NORD_YELLOW}]")
    else:
        logs = manager.get_logs(experiment_id, lines=lines)
        if logs:
            console.print(logs)
        else:
            console.print(f"[{NORD_RED}]No logs found for experiment {experiment_id}[/{NORD_RED}]")




@experiment.command()
def monitor():
    """System-wide monitor for experiments and API usage.
    
    Shows a real-time overview of:
    - API usage and rate limits for all providers
    - Active experiments with live metrics
    - System statistics and health
    - Estimated costs
    
    This gives you a bird's eye view of your Pidgin system,
    helping you manage rate limits and track experiment progress.
    
    [bold]FEATURES:[/bold]
    • Live updates from database
    • Rate limit warnings with visual bars
    • Convergence alerts
    • Cost tracking (coming soon)
    
    Press 'q' to quit, 'r' to refresh, 'e' to export stats.
    """
    from ..monitor.system_monitor import SystemMonitor
    
    console.print("[#8fbcbb]◆ Starting system monitor...[/#8fbcbb]")
    console.print("[#4c566a]Press 'q' to exit[/#4c566a]\n")
    
    monitor = SystemMonitor()
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        console.print("\n[#4c566a]Monitor stopped[/#4c566a]")


@experiment.command()
@click.argument('experiment_id')
def analyze(experiment_id):
    """Analyze completed experiment results.
    
    Generates statistical analysis and visualizations for the experiment.
    """
    storage = ExperimentStore(
        db_path=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "experiments.db"
    )
    
    # Get experiment
    exp = storage.get_experiment(experiment_id)
    if not exp:
        console.print(f"[{NORD_RED}]Experiment {experiment_id} not found[/{NORD_RED}]")
        return
    
    if exp['status'] not in ['completed', 'failed']:
        console.print(f"[{NORD_YELLOW}]Experiment is still {exp['status']}[/{NORD_YELLOW}]")
        return
    
    console.print(f"\n[bold {NORD_BLUE}]◆ Analyzing: {exp['name']}[/bold {NORD_BLUE}]")
    
    # Get metrics
    metrics = storage.get_experiment_metrics(experiment_id)
    
    # Display convergence stats
    conv_stats = metrics.get('convergence_stats', {})
    console.print(f"\n[{NORD_CYAN}]Convergence Statistics:[/{NORD_CYAN}]")
    console.print(f"  Average: {conv_stats.get('avg', 0):.3f}")
    console.print(f"  Min: {conv_stats.get('min', 0):.3f}")
    console.print(f"  Max: {conv_stats.get('max', 0):.3f}")
    console.print(f"  Conversations: {conv_stats.get('conversation_count', 0)}")
    
    # Display vocabulary trends
    console.print(f"\n[{NORD_CYAN}]Vocabulary Overlap by Turn:[/{NORD_CYAN}]")
    overlap = metrics.get('overlap_by_turn', {})
    if overlap:
        for turn in sorted(overlap.keys())[:10]:
            bar_width = int(overlap[turn] * 20)
            bar = "█" * bar_width + "░" * (20 - bar_width)
            console.print(f"  Turn {turn:2d}: {bar} {overlap[turn]:.3f}")
    
    # Display emergent words
    emergent = metrics.get('emergent_words', [])
    if emergent:
        console.print(f"\n[{NORD_CYAN}]Emergent Words (first appeared after turn 5):[/{NORD_CYAN}]")
        for word, turn in emergent[:10]:
            console.print(f"  '{word}' - first seen in turn {turn}")
    
    # Save full analysis
    output_file = Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / f"{experiment_id}_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    console.print(f"\n[{NORD_GREEN}]Full analysis saved to:[/{NORD_GREEN}]")
    console.print(f"  {output_file}")
