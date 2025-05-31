"""Compression protocol testing."""
import asyncio
import typer
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.panel import Panel
from rich.table import Table
from typing import Optional, List

from pidgin.core.experiment import Experiment, ExperimentConfig
from pidgin.llm.factory import create_llm, parse_model_spec
from pidgin.storage.experiments import ExperimentStorage
from pidgin.commands.run import _run_experiment

console = Console()


def compress(
    ctx: typer.Context,
    models: List[str] = typer.Option([], "--model", "-m", help="Models to use (format: model:archetype)"),
    start_turn: Optional[int] = typer.Option(None, "--start", "-s", help="Turn to start compression"),
    rate: Optional[float] = typer.Option(None, "--rate", "-r", help="Compression rate increase per phase"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", "-t", help="Maximum turns"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Experiment name"),
    validation_phases: bool = typer.Option(True, "--validation/--no-validation", "-v/-V", help="Include validation phases"),
    run_immediately: bool = typer.Option(True, "--run/--no-run", "-R/-N", help="Run immediately after creation"),
):
    """
    Run compression protocol testing.
    
    Tests how LLMs develop compressed communication protocols over time.
    The system gradually encourages more compressed responses while
    tracking symbol emergence and semantic preservation.
    """
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    console.print(Panel.fit(
        "[bold cyan]🗜️  Compression Testing[/bold cyan]\n\n"
        "Explore how AI systems develop compressed symbolic communication\n"
        "while preserving semantic content and achieving mutual understanding.",
        border_style="cyan"
    ))
    
    # Interactive setup if parameters not provided
    if not models:
        console.print("\n[bold]Select at least 2 models for compression testing:[/bold]")
        console.print("[dim]Format: model:archetype (e.g., claude:analytical)[/dim]\n")
        
        models = []
        while True:
            model_spec = Prompt.ask("Add model", default="")
            if not model_spec:
                if len(models) >= 2:
                    break
                console.print("[yellow]Need at least 2 models for compression testing[/yellow]")
                continue
            models.append(model_spec)
            console.print(f"[green]✓ Added {model_spec}[/green]")
    
    if start_turn is None:
        console.print("\n[bold]Compression Protocol:[/bold]")
        console.print("1. Models communicate normally for N turns")
        console.print("2. Compression guidance begins at turn N")
        console.print("3. Compression increases gradually each phase")
        console.print("4. Validation phases test symbol stability\n")
        
        start_turn = IntPrompt.ask("Start compression at turn", default=20)
    
    if rate is None:
        rate = FloatPrompt.ask("Compression rate increase per phase", default=0.1)
    
    if max_turns is None:
        max_turns = IntPrompt.ask("Maximum turns", default=200)
    
    if not name:
        name = Prompt.ask("Experiment name", default="Compression Protocol Test")
    
    # Parse models and create LLMs
    llms = []
    for model_spec in models:
        try:
            model_name, archetype = parse_model_spec(model_spec)
            llm = create_llm(model_name, archetype)
            llms.append(llm)
            console.print(f"[green]✓[/green] Configured {llm.name}")
        except Exception as e:
            console.print(f"[red]Error configuring {model_spec}: {e}[/red]")
            raise typer.Exit(1)
    
    # Create experiment config
    config = ExperimentConfig(
        name=name,
        max_turns=max_turns,
        compression_enabled=True,
        compression_start_turn=start_turn,
        compression_rate=rate,
        mediation_level="observe",
    )
    
    # Add metadata for compression testing
    metadata = {
        "compression_test": True,
        "validation_phases": validation_phases,
        "initial_task": "Please work together to establish efficient communication protocols. "
                       "You may develop any symbols, abbreviations, or compressed formats that help "
                       "you communicate more efficiently while maintaining understanding."
    }
    
    # Create experiment
    try:
        experiment = Experiment(config=config, llms=llms)
        experiment.metadata.update(metadata)
        storage.save(experiment)
        
        console.print(f"\n[green]✓ Created compression experiment: {experiment.id}[/green]")
        
        # Show compression schedule
        _show_compression_schedule(config, max_turns)
        
        if run_immediately:
            console.print("\n[cyan]Starting compression test...[/cyan]\n")
            asyncio.run(_run_experiment(experiment, storage, watch=True))
        else:
            console.print(f"\n[dim]Run with: pidgin run {experiment.id}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error creating experiment: {e}[/red]")
        raise typer.Exit(1)


def _show_compression_schedule(config: ExperimentConfig, max_turns: int):
    """Show the compression schedule."""
    table = Table(title="Compression Schedule", show_header=True, header_style="bold")
    table.add_column("Phase", style="cyan")
    table.add_column("Turns", justify="center")
    table.add_column("Compression Target", justify="center")
    table.add_column("Description")
    
    # Calculate phases
    start = config.compression_start_turn
    rate = config.compression_rate
    phase_length = 20  # turns per phase
    
    table.add_row(
        "Baseline",
        f"1-{start-1}",
        "0%",
        "Normal communication"
    )
    
    phase = 1
    current_turn = start
    compression = 0.0
    
    while current_turn < max_turns:
        compression += rate
        end_turn = min(current_turn + phase_length - 1, max_turns)
        
        table.add_row(
            f"Phase {phase}",
            f"{current_turn}-{end_turn}",
            f"{compression*100:.0f}%",
            "Gradual compression encouragement"
        )
        
        current_turn = end_turn + 1
        phase += 1
        
        if current_turn >= max_turns:
            break
    
    console.print("\n")
    console.print(table)
    console.print("")