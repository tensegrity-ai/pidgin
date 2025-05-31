"""
Pidgin: AI Communication Protocol Research CLI
"""
import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional
from pathlib import Path

from pidgin.commands import create, run, meditate, compress, analyze, manage, models
from pidgin.config.settings import Settings

app = typer.Typer(
    name="pidgin",
    help="AI Communication Protocol Research CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit"),
):
    """
    Pidgin: Study emergent symbolic communication between AI systems.
    
    A sophisticated research tool for exploring AI-to-AI communication patterns,
    compression protocols, and symbol emergence.
    """
    # Handle version flag
    if version:
        from pidgin import __version__
        console.print(f"Pidgin v{__version__}")
        raise typer.Exit()
    
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["settings"] = Settings()





# Register subcommands
app.add_typer(create.app, name="create", help="Create experiments and templates")
app.add_typer(run.app, name="run", help="Run experiments")
app.add_typer(manage.app, name="manage", help="Manage experiments and resources")
app.add_typer(analyze.app, name="analyze", help="Analyze experiment results")
app.add_typer(models.app, name="models", help="Model information and shortcuts")

# Register special mode commands
app.command()(meditate.meditate)
app.command()(compress.compress)


if __name__ == "__main__":
    app()