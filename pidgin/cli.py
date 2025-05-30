"""
Pidgin: AI Communication Protocol Research CLI
"""
import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional
from pathlib import Path

from pidgin.commands import create, run, meditate, compress, analyze, manage
from pidgin.config.settings import Settings

app = typer.Typer(
    name="pidgin",
    help="AI Communication Protocol Research CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)

console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """
    Pidgin: Study emergent symbolic communication between AI systems.
    
    A sophisticated research tool for exploring AI-to-AI communication patterns,
    compression protocols, and symbol emergence.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config
    ctx.obj["settings"] = Settings(config_path=config)


@app.command()
def init(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite existing config"),
):
    """Interactive setup and configuration."""
    settings = ctx.obj["settings"]
    
    console.print(Panel.fit(
        "[bold blue]Welcome to Pidgin![/bold blue]\n\n"
        "Let's set up your AI communication research environment.",
        title="🦜 Initialization",
        border_style="blue"
    ))
    
    # Interactive configuration setup
    if settings.config_exists() and not force:
        if not typer.confirm("Configuration already exists. Overwrite?"):
            raise typer.Abort()
    
    # API Keys
    console.print("\n[bold]API Configuration[/bold]")
    anthropic_key = typer.prompt("Anthropic API Key", hide_input=True, default="")
    openai_key = typer.prompt("OpenAI API Key", hide_input=True, default="")
    google_key = typer.prompt("Google API Key", hide_input=True, default="")
    
    # Default settings
    console.print("\n[bold]Default Settings[/bold]")
    default_model = typer.prompt("Default model", default="claude-3-opus-20240229")
    max_turns = typer.prompt("Default max turns", default=100, type=int)
    
    # Save configuration
    settings.save_config({
        "api_keys": {
            "anthropic": anthropic_key,
            "openai": openai_key,
            "google": google_key,
        },
        "defaults": {
            "model": default_model,
            "max_turns": max_turns,
        }
    })
    
    console.print("\n[green]✓ Configuration saved successfully![/green]")


@app.command()
def version():
    """Show Pidgin version."""
    from pidgin import __version__
    console.print(f"Pidgin v{__version__}")


# Register subcommands
app.add_typer(create.app, name="create", help="Create experiments and templates")
app.add_typer(run.app, name="run", help="Run experiments")
app.add_typer(manage.app, name="manage", help="Manage experiments and resources")
app.add_typer(analyze.app, name="analyze", help="Analyze experiment results")

# Register special mode commands
app.command()(meditate.meditate)
app.command()(compress.compress)


if __name__ == "__main__":
    app()