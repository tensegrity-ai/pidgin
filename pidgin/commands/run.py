"""Run experiments."""
import asyncio
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from typing import Optional, List

from pidgin.storage.experiments import ExperimentStorage
from pidgin.core.conversation import ConversationManager, ConversationEvent
from pidgin.ui.live import LiveConversationView

app = typer.Typer()
console = Console()


@app.command()
def experiment(
    ctx: typer.Context,
    experiment_id: str = typer.Argument(..., help="Experiment ID to run"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume paused experiment"),
    watch: bool = typer.Option(True, "--watch/--no-watch", "-w/-W", help="Watch live output"),
):
    """Run an experiment."""
    settings = ctx.obj["settings"]
    storage = ExperimentStorage(settings.experiments_dir)
    
    # Load experiment
    experiment = storage.load(experiment_id)
    if not experiment:
        console.print(f"[red]Error: Experiment {experiment_id} not found[/red]")
        raise typer.Exit(1)
    
    # Check if can run
    if resume and not experiment.can_resume:
        console.print(f"[red]Error: Cannot resume experiment in {experiment.status} status[/red]")
        raise typer.Exit(1)
    elif not resume and not experiment.can_start:
        console.print(f"[red]Error: Cannot start experiment in {experiment.status} status[/red]")
        raise typer.Exit(1)
    
    # Run the experiment
    try:
        asyncio.run(_run_experiment(experiment, storage, watch))
    except KeyboardInterrupt:
        console.print("\n[yellow]Experiment interrupted by user[/yellow]")
        experiment.pause()
        storage.save(experiment)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _run_experiment(experiment, storage, watch: bool):
    """Run the experiment asynchronously."""
    if watch:
        # Create live view
        live_view = LiveConversationView(experiment)
        
        # Event handler
        async def handle_event(event: ConversationEvent, data: dict):
            live_view.update_event(event, data)
            
            # Save periodically
            if event == ConversationEvent.TURN_COMPLETE:
                if experiment.current_turn % experiment.config.save_frequency == 0:
                    storage.save(experiment)
        
        # Create conversation manager
        manager = ConversationManager(experiment, event_handler=handle_event)
        
        # Run with live display
        with Live(live_view.get_display(), console=console, refresh_per_second=2) as live:
            live_view.live = live
            
            # Start conversation
            task = asyncio.create_task(manager.run())
            
            # Handle user input in background
            input_task = asyncio.create_task(_handle_user_input(manager, live_view))
            
            try:
                await task
            finally:
                input_task.cancel()
                
    else:
        # Run without display
        manager = ConversationManager(experiment)
        await manager.run()
    
    # Save final state
    storage.save(experiment)
    storage.save_transcript(experiment)
    
    console.print(f"\n[green]✓ Experiment completed: {experiment.id}[/green]")
    console.print(f"[dim]Transcript saved to: {storage.get_transcript_path(experiment.id)}[/dim]")


async def _handle_user_input(manager: ConversationManager, view: LiveConversationView):
    """Handle user input during experiment."""
    # This is a simplified version
    # In a real implementation, you'd handle keyboard input properly
    while manager.is_running:
        await asyncio.sleep(0.1)
        # Check for pause/resume/stop commands
        # Update view based on input


@app.command()
def batch(
    ctx: typer.Context,
    experiments: List[str] = typer.Argument(..., help="Experiment IDs to run"),
    parallel: bool = typer.Option(False, "--parallel", "-p", help="Run experiments in parallel"),
    max_parallel: int = typer.Option(3, "--max-parallel", help="Maximum parallel experiments"),
):
    """Run multiple experiments in batch."""
    console.print("[yellow]Batch execution not yet implemented[/yellow]")
    # TODO: Implement batch execution