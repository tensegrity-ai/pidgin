"""Command to load completed experiments into DuckDB for analytics."""

import asyncio
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..database.batch_loader import BatchLoader
from ..io.paths import get_experiments_dir
from .constants import NORD_GREEN, NORD_YELLOW, NORD_RED, NORD_CYAN

console = Console()


@click.command(hidden=True)  # Hidden command for advanced users
@click.argument('experiment_id', required=False)
@click.option('--all', is_flag=True, help='Load all completed experiments')
@click.option('--force', is_flag=True, help='Force reload even if already loaded')
def load_db(experiment_id, all, force):
    """Load completed experiments into DuckDB for analytics.
    
    After experiments complete, their JSONL data can be loaded into DuckDB
    for powerful analytics queries. This command handles the batch loading.
    
    [bold]EXAMPLES:[/bold]
    
    [#4c566a]Load a specific experiment:[/#4c566a]
        pidgin load-db exp_abc123
    
    [#4c566a]Load all completed experiments:[/#4c566a]
        pidgin load-db --all
    
    [#4c566a]Force reload (overwrites existing data):[/#4c566a]
        pidgin load-db exp_abc123 --force
    """
    if not experiment_id and not all:
        console.print(f"[{NORD_RED}]Error: Specify an experiment ID or use --all[/{NORD_RED}]")
        return
    
    async def run_loading():
        """Run the loading process."""
        loader = BatchLoader()
        
        try:
            if experiment_id:
                # Load specific experiment
                exp_base = get_experiments_dir()
                
                # Find matching experiment directory
                matching_dirs = list(exp_base.glob(f"{experiment_id}*"))
                if not matching_dirs:
                    console.print(f"[{NORD_RED}]No experiment found matching '{experiment_id}'[/{NORD_RED}]")
                    return
                
                if len(matching_dirs) > 1:
                    console.print(f"[{NORD_RED}]Multiple experiments match '{experiment_id}':[/{NORD_RED}]")
                    for d in matching_dirs:
                        console.print(f"  • {d.name}")
                    return
                
                exp_dir = matching_dirs[0]
                
                # Check if already loaded
                marker_file = exp_dir / ".loaded_to_db"
                if marker_file.exists() and not force:
                    console.print(f"[{NORD_YELLOW}]Experiment already loaded. Use --force to reload.[/{NORD_YELLOW}]")
                    return
                
                # Remove marker if forcing
                if force and marker_file.exists():
                    marker_file.unlink()
                
                console.print(f"[{NORD_CYAN}]Loading experiment {exp_dir.name}...[/{NORD_CYAN}]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Loading JSONL data...", total=None)
                    
                    success = await loader.load_experiment(exp_dir)
                    
                    if success:
                        # Create marker
                        marker_file.touch()
                        console.print(f"[{NORD_GREEN}][OK] Successfully loaded {exp_dir.name}[/{NORD_GREEN}]")
                    else:
                        console.print(f"[{NORD_RED}][FAIL] Failed to load {exp_dir.name}[/{NORD_RED}]")
            
            else:
                # Load all completed experiments
                console.print(f"[{NORD_CYAN}]Scanning for completed experiments...[/{NORD_CYAN}]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console
                ) as progress:
                    task = progress.add_task("Loading experiments...", total=None)
                    
                    stats = await loader.load_completed_experiments(get_experiments_dir())
                    
                    console.print(f"\n[bold {NORD_CYAN}]Batch Loading Complete[/bold {NORD_CYAN}]")
                    console.print(f"  Total experiments: {stats['total_experiments']}")
                    console.print(f"  [{NORD_GREEN}]Newly loaded: {stats['loaded']}[/{NORD_GREEN}]")
                    console.print(f"  [{NORD_RED}]Failed: {stats['failed']}[/{NORD_RED}]")
                    console.print(f"  [{NORD_YELLOW}]Already loaded: {stats['already_loaded']}[/{NORD_YELLOW}]")
                    
        finally:
            await loader.close()
    
    # Run the async function
    try:
        asyncio.run(run_loading())
    except KeyboardInterrupt:
        console.print(f"\n[{NORD_YELLOW}]Loading cancelled[/{NORD_YELLOW}]")
    except Exception as e:
        console.print(f"\n[{NORD_RED}]Error: {e}[/{NORD_RED}]")
        raise