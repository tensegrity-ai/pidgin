# pidgin/cli/info.py
"""Information commands for Pidgin."""

import rich_click as click
from rich.console import Console
from rich.table import Table

from ..config.models import MODELS
from .constants import PROVIDER_COLORS, MODEL_GLYPHS

console = Console()


@click.group()
def info():
    """View information about models, dimensions, and configuration."""
    pass


@info.command()
def models():
    """List all available AI models.
    
    Shows models grouped by provider with their configurations.
    """
    console.print("\n[bold]Available Models[/bold]\n")
    
    # Group models by provider
    providers = {}
    for model_id, config in MODELS.items():
        if config.provider not in providers:
            providers[config.provider] = []
        providers[config.provider].append((model_id, config))
    
    # Display each provider's models
    for provider in ['openai', 'anthropic', 'google', 'xai', 'local']:
        if provider not in providers:
            continue
            
        # Provider header
        color = PROVIDER_COLORS.get(provider, "white")
        console.print(f"[bold {color}]{provider.title()}[/bold {color}]")
        
        # Create table for this provider
        table = Table(box=None, padding=(0, 2))
        table.add_column("Model", style=color)
        table.add_column("ID", style="dim")
        table.add_column("Context", justify="right", style="dim")
        table.add_column("Tier", style="dim")
        
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
            
            # Show pricing tier
            tier_display = {
                "economy": "economy",
                "standard": "standard",
                "premium": "premium",
                "free": "free"
            }.get(config.pricing_tier, config.pricing_tier)
            
            table.add_row(
                f"{glyph} {config.shortname}",
                model_id,
                context,
                tier_display
            )
        
        console.print(table)
        console.print()  # Blank line between providers
    
    # Add note about local models
    console.print("[dim]Note: Local models require Ollama to be running[/dim]")
    console.print("[dim]Custom local models can be used with format: local:model-name[/dim]\n")



@info.command()
def config():
    """Show current configuration."""
    from ..config import get_config
    from pathlib import Path
    
    config = get_config()
    
    console.print("\n[bold]Configuration[/bold]\n")
    
    # Check for config file
    config_paths = [
        Path.home() / ".config" / "pidgin" / "pidgin.yaml",
        Path.home() / ".pidgin.yaml",
        Path(".pidgin.yaml"),
        Path("pidgin.yaml")
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
        console.print("[dim]Run 'pidgin init-config' to create one[/dim]")
    
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
    
    console.print("Dimensional prompts shape conversation dynamics using three components:")
    console.print("  [cyan]relationship:topic:modifier[/cyan]\n")
    
    console.print("[bold]Components:[/bold]")
    console.print("  • [bold]Relationship[/bold]: How agents relate to each other")
    console.print("  • [bold]Topic[/bold]: Subject matter or domain")
    console.print("  • [bold]Modifier[/bold]: Style or approach (optional)\n")
    
    console.print("[bold]Examples:[/bold]")
    console.print("  [dim]pidgin run -a claude -b gpt -d peers:philosophy:analytical[/dim]")
    console.print("  [dim]pidgin run -a claude -b gpt -d mentor:code:patient[/dim]")
    console.print("  [dim]pidgin run -a claude -b gpt -d debate:ethics[/dim]\n")
    
    # Available relationships
    console.print("[bold cyan]Relationships:[/bold cyan]")
    relationships = {
        "peers": "Equal partners in exploration",
        "mentor": "One guides, one learns",
        "debate": "Opposing viewpoints",
        "socratic": "Through questioning",
        "collaborative": "Working together",
        "interview": "Q&A format"
    }
    for rel, desc in relationships.items():
        console.print(f"  • [cyan]{rel}[/cyan]: {desc}")
    
    console.print("\n[bold green]Topics:[/bold green]")
    topics = {
        "philosophy": "Fundamental questions",
        "science": "Natural phenomena",
        "ethics": "Moral reasoning",
        "creativity": "Artistic expression",
        "mathematics": "Abstract patterns",
        "psychology": "Mind and behavior",
        "technology": "Tools and systems",
        "history": "Past events",
        "language": "Communication itself",
        "consciousness": "Awareness and experience"
    }
    for topic, desc in topics.items():
        console.print(f"  • [green]{topic}[/green]: {desc}")
    
    console.print("\n[bold yellow]Modifiers:[/bold yellow] (optional)")
    modifiers = {
        "analytical": "Logic-focused",
        "creative": "Imaginative",
        "critical": "Questioning",
        "supportive": "Encouraging",
        "challenging": "Provocative",
        "playful": "Light-hearted",
        "formal": "Professional",
        "casual": "Relaxed",
        "patient": "Thoughtful",
        "rapid": "Quick exchange"
    }
    for mod, desc in modifiers.items():
        console.print(f"  • [yellow]{mod}[/yellow]: {desc}")
    
    console.print("\n[dim]Note: You can also use custom prompts with -p/--prompt[/dim]")