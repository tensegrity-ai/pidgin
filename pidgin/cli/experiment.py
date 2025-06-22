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

import click
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

# Store original working directory
ORIGINAL_CWD = os.getcwd()


@click.group()
def experiment():
    """Manage batch conversation experiments.
    
    Run multiple conversations in parallel with different configurations
    to study emergent patterns and behaviors.
    """
    pass


@experiment.command()
@click.option('--agent-a', '-a', required=True, help='First agent model')
@click.option('--agent-b', '-b', required=True, help='Second agent model') 
@click.option('--repetitions', '-r', default=10, help='Number of conversations to run')
@click.option('--turns', '-t', default=DEFAULT_TURNS, help=f'Max turns per conversation (default: {DEFAULT_TURNS})')
@click.option('--prompt', '-p', help='Initial prompt for conversations')
@click.option('--dimension', '-d', multiple=True, help='Conversation dimensions')
@click.option('--temperature', type=float, help='Temperature for both agents')
@click.option('--temperature-a', type=float, help='Temperature for agent A only')
@click.option('--temperature-b', type=float, help='Temperature for agent B only')
@click.option('--name', '-n', help='Experiment name')
@click.option('--parallel', type=int, default=DEFAULT_PARALLEL, help=f'Max parallel conversations (default: {DEFAULT_PARALLEL})')
@click.option('--convergence-threshold', type=float, help='Convergence threshold (0.0-1.0)')
@click.option('--convergence-action', type=click.Choice(['notify', 'pause', 'stop']), default='notify')
@click.option('--first-speaker', type=click.Choice(['a', 'b', 'random']), default='a')
@click.option('--dry-run', is_flag=True, help='Show configuration without running')
def start(agent_a, agent_b, repetitions, turns, prompt, dimension,
          temperature, temperature_a, temperature_b, name, parallel,
          convergence_threshold, convergence_action, first_speaker, dry_run):
    """Start a new experiment with multiple conversations.
    
    \b
    EXAMPLES:
        pidgin experiment start -a gpt-4 -b claude -r 10
        pidgin experiment start -a gemini -b gemini -r 20 -t 30 -n "gemini-self-talk"
        pidgin experiment start -a local:llama3.1 -b gpt-4 -r 5 --parallel 2
    
    The experiment runs in the background. Use 'pidgin experiment dashboard'
    to monitor progress in real-time.
    """
    # Validate models
    try:
        agent_a_id, agent_a_name = validate_model_id(agent_a)
        agent_b_id, agent_b_name = validate_model_id(agent_b)
    except ValueError as e:
        console.print(f"[{NORD_RED}]Error: {e}[/{NORD_RED}]")
        return
    
    # Handle temperature settings
    temp_a = temperature_a if temperature_a is not None else temperature
    temp_b = temperature_b if temperature_b is not None else temperature
    
    # Build initial prompt
    initial_prompt = build_initial_prompt(prompt, list(dimension))
    
    # Generate experiment name if not provided
    if not name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{agent_a}_{agent_b}_{timestamp}"
    
    # Create experiment configuration
    config = ExperimentConfig(
        name=name,
        agent_a_model=agent_a_id,
        agent_b_model=agent_b_id,
        repetitions=repetitions,
        max_turns=turns,
        temperature_a=temp_a,
        temperature_b=temp_b,
        custom_prompt=initial_prompt if prompt else None,
        dimensions=list(dimension) if dimension else None,
        parallel_count=parallel,
        convergence_threshold=convergence_threshold,
        convergence_action=convergence_action,
        first_speaker=first_speaker
    )
    
    # Show configuration
    console.print(f"\n[bold {NORD_BLUE}]◆ Experiment Configuration[/bold {NORD_BLUE}]")
    console.print(f"  Name: {name}")
    console.print(f"  Models: {format_model_display(agent_a_id)} ↔ {format_model_display(agent_b_id)}")
    console.print(f"  Conversations: {repetitions}")
    console.print(f"  Turns per conversation: {turns}")
    console.print(f"  Parallel execution: {parallel}")
    
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
    
    if dry_run:
        console.print(f"\n[{NORD_YELLOW}]Dry run - no experiment will be started[/{NORD_YELLOW}]")
        return
    
    # Start the experiment
    console.print(f"\n[{NORD_GREEN}]Starting experiment...[/{NORD_GREEN}]")
    
    manager = ExperimentManager(base_dir=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments")
    
    try:
        exp_id = manager.start_experiment(config, working_dir=ORIGINAL_CWD)
        
        console.print(f"\n[bold {NORD_GREEN}]✓ Experiment started successfully![/bold {NORD_GREEN}]")
        console.print(f"  ID: {exp_id}")
        console.print(f"  Name: {name}")
        console.print(f"\n[{NORD_BLUE}]Monitor progress:[/{NORD_BLUE}]")
        console.print(f"  pidgin experiment dashboard {exp_id}")
        console.print(f"\n[{NORD_BLUE}]View logs:[/{NORD_BLUE}]")
        console.print(f"  pidgin experiment logs {exp_id}")
        
    except Exception as e:
        console.print(f"\n[{NORD_RED}]Failed to start experiment: {e}[/{NORD_RED}]")
        if "startup error" in str(e).lower():
            console.print(f"[{NORD_YELLOW}]Check the logs for more details[/{NORD_YELLOW}]")


@experiment.command()
@click.option('--status', '-s', 
              type=click.Choice(['all', 'running', 'completed', 'failed']),
              default='all',
              help='Filter by status')
@click.option('--limit', '-n', default=20, help='Number of experiments to show')
def list(status, limit):
    """List experiments with their status.
    
    Shows recent experiments with their configuration and progress.
    """
    storage = ExperimentStore(
        db_path=Path(ORIGINAL_CWD) / "pidgin_output" / "experiments" / "experiments.db"
    )
    
    # Get experiments
    experiments = storage.list_experiments(
        status_filter=None if status == 'all' else status
    )
    
    if not experiments:
        console.print(f"[{NORD_YELLOW}]No experiments found[/{NORD_YELLOW}]")
        return
    
    # Create table
    table = Table(title=f"Experiments ({status})")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Models", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Progress", style="blue")
    table.add_column("Started", style="magenta")
    
    # Add experiments
    for exp in experiments[:limit]:
        exp_id = exp['experiment_id']
        config = json.loads(exp['config'])
        
        # Format models
        models = f"{config['agent_a_model']} ↔ {config['agent_b_model']}"
        
        # Format status with color
        status_color = {
            'running': NORD_GREEN,
            'completed': NORD_BLUE,
            'failed': NORD_RED,
            'created': NORD_YELLOW
        }.get(exp['status'], 'white')
        status_text = f"[{status_color}]{exp['status']}[/{status_color}]"
        
        # Format progress
        total = exp['total_conversations']
        completed = exp['completed_conversations']
        failed = exp['failed_conversations']
        progress = f"{completed}/{total}"
        if failed > 0:
            progress += f" [{NORD_RED}]{failed} failed[/{NORD_RED}]"
        
        # Format time
        created = datetime.fromisoformat(exp['created_at'])
        time_str = created.strftime("%Y-%m-%d %H:%M")
        
        table.add_row(
            exp_id,
            exp['name'],
            models,
            status_text,
            progress,
            time_str
        )
    
    console.print(table)
    
    if len(experiments) > limit:
        console.print(f"\n[{NORD_YELLOW}]Showing {limit} of {len(experiments)} experiments[/{NORD_YELLOW}]")


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
@click.argument('experiment_id', required=False)
def dashboard(experiment_id):
    """Attach to a running experiment and show real-time metrics.
    
    If EXPERIMENT_ID is not provided, will search for running experiments
    and let you choose one.
    
    \b
    EXAMPLES:
        pidgin experiment dashboard
        pidgin experiment dashboard exp_abc123
    
    The dashboard shows:
    - Conversation progress
    - Real-time convergence metrics with sparklines
    - Recent messages from both agents
    - Experiment status
    
    Press Ctrl+C to detach from the dashboard.
    """
    from ..dashboard.dashboard import run_dashboard as run_experiment_dashboard
    
    try:
        asyncio.run(run_experiment_dashboard(experiment_id))
    except KeyboardInterrupt:
        # Clean exit
        pass
    except Exception as e:
        console.print(f"[{NORD_RED}]Error: {e}[/{NORD_RED}]")
        if "No module named" in str(e):
            console.print(f"[{NORD_YELLOW}]Make sure all dependencies are installed[/{NORD_YELLOW}]")


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
