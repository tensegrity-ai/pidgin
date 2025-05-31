"""Manage experiments and resources."""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from typing import Optional
import json
from datetime import datetime

from pidgin.storage.experiments import ExperimentStorage
from pidgin.core.experiment import ExperimentStatus

app = typer.Typer(
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)
console = Console()


@app.command("list")
def list_experiments(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (created/running/paused/completed/failed)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of experiments to show"),
    all: bool = typer.Option(False, "--all", "-a", help="Show all experiments"),
):
    """List experiments."""
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    # Get experiments
    if all:
        limit = 1000
    
    status_filter = ExperimentStatus(status) if status else None
    experiments = storage.list(status=status_filter, limit=limit)
    
    if not experiments:
        console.print("[yellow]No experiments found[/yellow]")
        return
    
    # Create table
    table = Table(
        title=f"Experiments ({len(experiments)} shown)",
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Models", style="dim")
    table.add_column("Turns", justify="right")
    table.add_column("Compression", justify="right")
    table.add_column("Created", style="dim")
    
    # Status colors
    status_colors = {
        "created": "blue",
        "running": "green",
        "paused": "yellow",
        "completed": "cyan",
        "failed": "red",
        "cancelled": "magenta"
    }
    
    for exp in experiments:
        # Parse data
        exp_id = exp["id"][:8]  # Short ID
        name = exp["name"][:30] + "..." if len(exp["name"]) > 30 else exp["name"]
        status = exp["status"]
        status_color = status_colors.get(status, "white")
        
        # Get config and metrics
        config = json.loads(exp["config"])
        metrics = json.loads(exp["metrics"])
        
        # Models info (simplified for display)
        models = "N/A"  # Would need to store this better
        
        turns = f"{metrics['total_turns']}/{config['max_turns']}"
        
        compression = ""
        if config.get("compression_enabled"):
            ratio = metrics.get("compression_ratio", 1.0)
            compression = f"{(1 - ratio) * 100:.1f}%"
        
        created = datetime.fromisoformat(exp["created_at"])
        created_str = created.strftime("%Y-%m-%d %H:%M")
        
        table.add_row(
            exp_id,
            name,
            f"[{status_color}]{status}[/{status_color}]",
            models,
            turns,
            compression,
            created_str
        )
    
    console.print(table)


@app.command("show", no_args_is_help=True)
def show_experiment(
    ctx: typer.Context,
    experiment_id: str = typer.Argument(..., help="Experiment ID"),
    transcript: bool = typer.Option(False, "--transcript", "-t", help="Show full transcript"),
    metrics: bool = typer.Option(False, "--metrics", "-m", help="Show detailed metrics"),
):
    """Show detailed experiment information."""
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    # Load experiment
    experiment = storage.load(experiment_id)
    if not experiment:
        console.print(f"[red]Error: Experiment {experiment_id} not found[/red]")
        raise typer.Exit(1)
    
    # Basic info panel
    info_lines = [
        f"[bold]Name:[/bold] {experiment.config.name}",
        f"[bold]ID:[/bold] {experiment.id}",
        f"[bold]Status:[/bold] {experiment.status}",
        f"[bold]Created:[/bold] {experiment.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"[bold]Turns:[/bold] {experiment.current_turn}/{experiment.config.max_turns}",
    ]
    
    if experiment.config.meditation_mode:
        info_lines.append(f"[bold]Mode:[/bold] Meditation ({experiment.config.meditation_style})")
    else:
        info_lines.append(f"[bold]Mediation:[/bold] {experiment.config.mediation_level}")
    
    if experiment.config.compression_enabled:
        info_lines.append(f"[bold]Compression:[/bold] Enabled (start: {experiment.config.compression_start_turn})")
    
    console.print(Panel("\n".join(info_lines), title="🧪 Experiment Details", border_style="cyan"))
    
    # Models
    console.print("\n[bold]Participants:[/bold]")
    for i, llm in enumerate(experiment.llms, 1):
        console.print(f"  {i}. {llm.name} [{llm.provider}]")
    
    # Metrics
    if metrics or experiment.metrics.total_turns > 0:
        console.print("\n[bold]Metrics:[/bold]")
        console.print(f"  Total tokens: {experiment.metrics.total_tokens:,}")
        if experiment.config.compression_enabled:
            console.print(f"  Compression ratio: {experiment.metrics.compression_ratio:.3f}")
            if experiment.metrics.symbols_emerged:
                console.print(f"  Symbols emerged: {', '.join(experiment.metrics.symbols_emerged)}")
        if experiment.metrics.duration:
            console.print(f"  Duration: {experiment.metrics.duration:.1f}s")
    
    # Transcript preview or full
    if transcript and experiment.conversation_history:
        console.print("\n[bold]Transcript:[/bold]\n")
        for turn in experiment.conversation_history[-10:]:  # Last 10 turns
            speaker = turn.get("speaker", "Unknown")
            content = turn.get("content", "")
            console.print(f"[cyan]{speaker}:[/cyan] {content[:200]}...")
            console.print("")
    elif experiment.conversation_history:
        console.print(f"\n[dim]Use --transcript to see conversation history ({len(experiment.conversation_history)} turns)[/dim]")


@app.command("remove", no_args_is_help=True)
def remove_experiment(
    ctx: typer.Context,
    experiment_id: str = typer.Argument(..., help="Experiment ID to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove an experiment."""
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    # Load experiment to show info
    experiment = storage.load(experiment_id)
    if not experiment:
        console.print(f"[red]Error: Experiment {experiment_id} not found[/red]")
        raise typer.Exit(1)
    
    # Confirm
    if not force:
        console.print(f"[yellow]About to remove:[/yellow] {experiment.config.name} ({experiment.id})")
        if not typer.confirm("Are you sure?"):
            console.print("[cyan]Cancelled[/cyan]")
            return
    
    # Remove
    if storage.delete(experiment_id):
        console.print(f"[green]✓ Removed experiment {experiment_id}[/green]")
    else:
        console.print(f"[red]Error removing experiment[/red]")


@app.command("clean")
def clean_experiments(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Remove by status"),
    older_than: Optional[int] = typer.Option(None, "--older-than", "-o", help="Remove experiments older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show what would be removed"),
):
    """Clean up old or failed experiments."""
    console.print("[yellow]Clean command not yet implemented[/yellow]")
    # TODO: Implement cleanup