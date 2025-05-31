"""Create experiments and templates."""
import typer
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from typing import List, Optional
from pathlib import Path

from pidgin.core.experiment import Experiment, ExperimentConfig
from pidgin.llm.factory import create_llm, parse_model_spec, get_available_models
from pidgin.config.archetypes import Archetype
from pidgin.storage.experiments import ExperimentStorage

app = typer.Typer(
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)
console = Console()


@app.command()
def experiment(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Experiment name"),
    models: List[str] = typer.Option([], "--model", "-m", help="Models to use (format: model:archetype)"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", "-t", help="Maximum conversation turns"),
    compression: bool = typer.Option(False, "--compression", "-c", help="Enable compression testing"),
    compression_start: Optional[int] = typer.Option(20, "--compression-start", "-s", help="Turn to start compression"),
    mediation: Optional[str] = typer.Option(None, "--mediation", "-M", help="Mediation level (full/light/observe/auto)"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i/-I", help="Interactive mode"),
):
    """Create a new experiment."""
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    if interactive and not name:
        console.print("[bold cyan]🧪 Create New Experiment[/bold cyan]\n")
        
        # Get experiment name
        name = Prompt.ask("Experiment name", default="Untitled Experiment")
        
        # Show available models
        if not models:
            console.print("\n[bold]Available Models:[/bold]")
            model_table = Table(show_header=True, header_style="bold magenta")
            model_table.add_column("Provider", style="dim")
            model_table.add_column("Model", style="cyan")
            model_table.add_column("Name")
            
            available = get_available_models()
            for provider, provider_models in available.items():
                for model_id, model_name in provider_models.items():
                    model_table.add_row(provider, model_id, model_name)
            
            console.print(model_table)
            
            # Get models interactively
            console.print("\n[dim]Enter models one at a time. Format: model:archetype (e.g., claude:creative)[/dim]")
            console.print("[dim]Available archetypes: analytical, creative, pragmatic, theoretical, collaborative[/dim]")
            console.print("[dim]Press Enter with empty input when done.[/dim]\n")
            
            models = []
            while True:
                model_spec = Prompt.ask("Add model", default="")
                if not model_spec:
                    if len(models) < 2 and not Confirm.ask("Create with fewer than 2 models?"):
                        continue
                    break
                models.append(model_spec)
                console.print(f"[green]✓ Added {model_spec}[/green]")
        
        # Get other parameters
        if max_turns is None:
            max_turns = IntPrompt.ask("Maximum turns", default=settings.defaults.max_turns)
        
        if compression:
            compression_start = IntPrompt.ask("Start compression at turn", default=20)
        
        if mediation is None:
            console.print("\n[bold]Mediation Levels:[/bold]")
            console.print("- [cyan]full[/cyan]: Human approves every message")
            console.print("- [cyan]light[/cyan]: Human can intervene anytime")
            console.print("- [cyan]observe[/cyan]: Watch only, no intervention")
            console.print("- [cyan]auto[/cyan]: Fully autonomous\n")
            
            mediation = Prompt.ask(
                "Mediation level",
                choices=["full", "light", "observe", "auto"],
                default=settings.defaults.mediation_level
            )
    
    # Validate inputs
    if not name:
        console.print("[red]Error: Experiment name is required[/red]")
        raise typer.Exit(1)
    
    if not models:
        console.print("[red]Error: At least one model is required[/red]")
        raise typer.Exit(1)
    
    # Parse models and create LLMs
    llms = []
    for model_spec in models:
        try:
            model, archetype = parse_model_spec(model_spec)
            llm = create_llm(model, archetype)
            llms.append(llm)
            console.print(f"[green]✓[/green] Configured {llm.name}")
        except Exception as e:
            console.print(f"[red]Error configuring {model_spec}: {e}[/red]")
            raise typer.Exit(1)
    
    # Create experiment config
    config = ExperimentConfig(
        name=name,
        max_turns=max_turns or settings.defaults.max_turns,
        mediation_level=mediation or settings.defaults.mediation_level,
        compression_enabled=compression,
        compression_start_turn=compression_start if compression else None,
    )
    
    # Create experiment
    try:
        experiment = Experiment(config=config, llms=llms)
        storage.save(experiment)
        
        console.print(f"\n[green]✓ Created experiment: {experiment.id}[/green]")
        console.print(f"[dim]Run with: pidgin run {experiment.id}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error creating experiment: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def template(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Template name"),
    from_experiment: Optional[str] = typer.Option(None, "--from", "-f", help="Create from existing experiment"),
):
    """Create a reusable experiment template."""
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    console.print(f"[yellow]Template creation not yet implemented[/yellow]")
    # TODO: Implement template creation