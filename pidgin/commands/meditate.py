"""Meditation mode - single LLM self-dialogue."""
import asyncio
import typer
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from typing import Optional

from pidgin.core.experiment import Experiment, ExperimentConfig
from pidgin.llm.factory import create_llm, parse_model_spec
from pidgin.storage.experiments import ExperimentStorage
from pidgin.commands.run import _run_experiment

console = Console()


def meditate(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use (format: model:archetype)"),
    style: Optional[str] = typer.Option(None, "--style", "-s", help="Meditation style (wandering/focused/recursive/deep)"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", "-t", help="Maximum turns"),
    basin_detection: bool = typer.Option(False, "--basin-detection", "-b", help="Stop when attractor state reached"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Experiment name"),
    run_immediately: bool = typer.Option(True, "--run/--no-run", "-r/-R", help="Run immediately after creation"),
):
    """
    Start a meditation session - single LLM self-dialogue.
    
    In meditation mode, a single LLM converses with itself, starting with the prompt:
    "Please respond to this task. You may be collaborating with another AI system on this."
    
    This can lead to interesting emergent behaviors and self-organizing patterns.
    """
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    console.print(Panel.fit(
        "[bold magenta]🧘 Meditation Mode[/bold magenta]\n\n"
        "A single LLM will converse with itself, potentially discovering\n"
        "interesting patterns and attractors in its thought space.",
        border_style="magenta"
    ))
    
    # Interactive setup if parameters not provided
    if not model:
        model = Prompt.ask(
            "Select model",
            default=f"{settings.defaults.model}:{settings.defaults.archetype}"
        )
    
    if not style:
        console.print("\n[bold]Meditation Styles:[/bold]")
        console.print("- [cyan]wandering[/cyan]: Free-form exploration")
        console.print("- [cyan]focused[/cyan]: Goal-directed thinking")
        console.print("- [cyan]recursive[/cyan]: Meta-cognitive loops")
        console.print("- [cyan]deep[/cyan]: Philosophical contemplation\n")
        
        style = Prompt.ask(
            "Meditation style",
            choices=["wandering", "focused", "recursive", "deep"],
            default="wandering"
        )
    
    if max_turns is None:
        max_turns = IntPrompt.ask("Maximum turns", default=200)
    
    if not basin_detection:
        basin_detection = Confirm.ask(
            "Enable basin detection (stop when conversation reaches attractor)?",
            default=False
        )
    
    if not name:
        name = Prompt.ask("Experiment name", default=f"Meditation - {style}")
    
    # Parse model and create LLM
    try:
        model_name, archetype = parse_model_spec(model)
        llm = create_llm(model_name, archetype)
        console.print(f"[green]✓[/green] Configured {llm.name}")
    except Exception as e:
        console.print(f"[red]Error configuring model: {e}[/red]")
        raise typer.Exit(1)
    
    # Add style-specific system prompts
    style_prompts = {
        "wandering": "Explore ideas freely, following interesting threads wherever they lead.",
        "focused": "Work systematically toward understanding or solving the implicit task.",
        "recursive": "Reflect on your own thinking process and engage in meta-cognitive exploration.",
        "deep": "Contemplate fundamental questions and explore philosophical depths."
    }
    
    if style in style_prompts:
        original_prompt = llm.config.system_prompt
        llm.config.system_prompt = f"{original_prompt}\n\nMeditation guidance: {style_prompts[style]}"
    
    # Create experiment config
    config = ExperimentConfig(
        name=name,
        max_turns=max_turns,
        meditation_mode=True,
        meditation_style=style,
        basin_detection=basin_detection,
        mediation_level="observe",  # Always observe-only for meditation
    )
    
    # Create experiment
    try:
        experiment = Experiment(config=config, llms=[llm])
        storage.save(experiment)
        
        console.print(f"\n[green]✓ Created meditation experiment: {experiment.id}[/green]")
        
        if run_immediately:
            console.print("\n[cyan]Starting meditation...[/cyan]\n")
            asyncio.run(_run_experiment(experiment, storage, watch=True))
        else:
            console.print(f"[dim]Run with: pidgin run {experiment.id}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error creating experiment: {e}[/red]")
        raise typer.Exit(1)