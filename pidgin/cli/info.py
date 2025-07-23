# pidgin/cli/info.py
"""Information commands for Pidgin."""

from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config.models import MODELS
from ..ui.display_utils import DisplayUtils
from .constants import MODEL_GLYPHS, PROVIDER_COLORS

console = Console()
display = DisplayUtils(console)


def _create_config_file(force):
    """Create a configuration file with example settings."""
    from ..config import Config

    config_path = Path.home() / ".config" / "pidgin" / "pidgin.yaml"

    if config_path.exists() and not force:
        display.warning(
            f"Config file already exists at: {config_path}", use_panel=False
        )
        display.info("Use --force to overwrite", use_panel=False)
        return

    # Create config instance to access the write method
    config = Config()

    # Create directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write example config
    config._write_example_config(config_path)

    display.success("◆ Created configuration file")
    display.info(f"Location: {config_path}", use_panel=False)

    profiles_info = [
        "Available convergence profiles:",
        "  • balanced   - Default, balanced weights",
        "  • structural - Emphasizes structural patterns (2x weight)",
        "  • semantic   - Emphasizes content/meaning",
        "  • strict     - Higher standards for all metrics",
    ]
    display.info("\n".join(profiles_info), use_panel=False)
    display.dim("\nEdit the file to customize settings")


@click.group()
@click.option(
    "--create-config",
    is_flag=True,
    help="Create a configuration file with example settings",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing config (use with --create-config)",
)
def info(create_config, force):
    """View information about models, dimensions, and configuration.

    Use --create-config to create ~/.config/pidgin/pidgin.yaml with example settings.
    """
    if create_config:
        _create_config_file(force)
    elif force:
        display.warning("--force flag only works with --create-config", use_panel=False)
        return

    # If no subcommand and no create-config flag, show help
    if not create_config:
        ctx = click.get_current_context()
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())


@info.command()
def models():
    """List all available AI models.

    Shows models grouped by provider with their configurations.
    """
    # No title panel needed

    # Group models by provider
    providers = {}
    for model_id, config in MODELS.items():
        if config.provider not in providers:
            providers[config.provider] = []
        providers[config.provider].append((model_id, config))

    # Display each provider's models
    for provider in ["openai", "anthropic", "google", "xai", "local"]:
        if provider not in providers:
            continue

        # Create table for this provider
        color = PROVIDER_COLORS.get(provider, "white")
        table = Table(
            box=None, padding=(0, 2), show_header=True, header_style=f"bold {color}"
        )
        table.add_column("Model ID", style=color)
        table.add_column("Alias", style=color)
        table.add_column("Context", justify="right", style="dim")

        for model_id, config in sorted(providers[provider], key=lambda x: x[0]):
            glyph = MODEL_GLYPHS.get(model_id, "●")

            # Format context window
            if config.context_window:
                if config.context_window >= 1_000_000:
                    context = f"{config.context_window // 1_000_000}M"
                elif config.context_window >= 1000:
                    context = f"{config.context_window // 1000}K"
                else:
                    context = str(config.context_window)
            else:
                context = "∞"

            # Get the primary alias (first one) or show "-"
            primary_alias = config.aliases[0] if config.aliases else "-"

            table.add_row(f"{glyph} {model_id}", primary_alias, context)

        # Wrap table in a panel with provider name
        provider_panel = Panel(
            table,
            title=f"[bold {color}]{provider.title()}[/bold {color}]",
            border_style=color,
            expand=False,
        )
        console.print(provider_panel)
        console.print()  # Blank line between providers

    # Add notes about using models
    notes = (
        "• Use the model names shown above when running (e.g., 'gpt', 'claude', 'gemini')\n"
        "• Local models require Ollama to be running\n"
        "• Custom local models can be used with format: local:model-name\n"
        "• Common usage: pidgin run -a gpt -b claude"
    )
    display.dim(notes)


@info.command()
def config():
    """Show current configuration."""
    from ..config import get_config

    config = get_config()

    console.print("\n[bold]Configuration[/bold]\n")

    # Check for config file
    config_paths = [
        Path.home() / ".config" / "pidgin" / "pidgin.yaml",
        Path.home() / ".pidgin.yaml",
        Path(".pidgin.yaml"),
        Path("pidgin.yaml"),
    ]

    found_config = None
    for path in config_paths:
        if path.exists():
            found_config = path
            break

    if found_config:
        console.print(f"[green]Config file:[/green] {found_config}")
    else:
        console.print("[yellow]No config file found[/yellow]")
        console.print("[dim]Run 'pidgin info --create-config' to create one[/dim]")

    console.print("\n[bold]Current Settings:[/bold]")

    # Convergence settings
    profile = config.get("convergence.profile", "balanced")
    console.print(f"  Convergence profile: {profile}")

    # Show weights if using custom profile
    if profile == "custom":
        weights = config.get("convergence.custom_weights", {})
        if weights:
            console.print("  Custom weights:")
            for metric, weight in weights.items():
                console.print(f"    {metric}: {weight}")

    console.print()


@info.command()
def dimensions():
    """Explain dimensional prompts and show available dimensions."""
    console.print("\n[bold]Dimensional Prompts[/bold]\n")

    console.print(
        "Dimensional prompts shape conversation dynamics using three components:"
    )
    console.print("  [cyan]relationship:topic:modifier[/cyan]\n")

    console.print("[bold]Components:[/bold]")
    console.print("  • [bold]Relationship[/bold]: How agents relate to each other")
    console.print("  • [bold]Topic[/bold]: Subject matter or domain")
    console.print("  • [bold]Modifier[/bold]: Style or approach (optional)\n")

    console.print("[bold]Examples:[/bold]")
    console.print(
        "  [dim]pidgin run -a claude -b gpt -d peers:philosophy:analytical[/dim]"
    )
    console.print("  [dim]pidgin run -a claude -b gpt -d mentor:code:patient[/dim]")
    console.print("  [dim]pidgin run -a claude -b gpt -d debate:ethics[/dim]\n")

    # Available relationships
    console.print("[bold cyan]Relationships:[/bold cyan]")
    relationships = {
        "peers": "Equal partners in exploration",
        "mentor": "One guides, one learns",
        "debate": "Opposing viewpoints",
        "socratic": "Through questioning and dialogue",
        "collaboration": "Working together",
        "interview": "Q&A format",
    }
    for rel, desc in relationships.items():
        console.print(f"  • [cyan]{rel}[/cyan]: {desc}")

    console.print("\n[bold green]Topics:[/bold green]")
    topics = {
        "philosophy": "Fundamental nature of reality",
        "language": "How we communicate and create meaning",
        "science": "How the universe works",
        "creativity": "Creative process and imagination",
        "ethics": "Moral reasoning and ethical questions",
        "meta": "Our own conversation and thinking",
    }
    for topic, desc in topics.items():
        console.print(f"  • [green]{topic}[/green]: {desc}")

    console.print("\n[bold yellow]Modifiers:[/bold yellow] (optional)")
    modifiers = {
        "analytical": "Systematic analysis",
        "intuitive": "Pattern-focused exploration",
        "exploratory": "Curiosity-driven",
        "critical": "Careful scrutiny and questioning",
        "playful": "Creative and fun",
        "supportive": "Constructive and encouraging",
    }
    for mod, desc in modifiers.items():
        console.print(f"  • [yellow]{mod}[/yellow]: {desc}")

    console.print("\n[dim]Note: You can also use custom prompts with -p/--prompt[/dim]")
