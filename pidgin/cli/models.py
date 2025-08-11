"""List available AI models."""

import rich_click as click
from rich.console import Console
from rich.table import Table

from ..config.models import MODELS
from ..ui.display_utils import DisplayUtils
from .constants import MODEL_GLYPHS, PROVIDER_COLORS

console = Console()
display = DisplayUtils(console)


@click.command()
def models():
    """List all available AI models.
    
    Shows models grouped by provider with their configurations.
    """
    # Group models by provider
    providers = {}
    for model_id, config in MODELS.items():
        if config.provider not in providers:
            providers[config.provider] = []
        providers[config.provider].append((model_id, config))

    # Sort providers
    provider_order = ["anthropic", "openai", "google", "xai", "local"]
    sorted_providers = sorted(
        providers.keys(), key=lambda p: provider_order.index(p) if p in provider_order else 99
    )

    # Create table
    table = Table(show_header=True, header_style="bold cyan", title="Available Models")
    table.add_column("Provider", style="dim", width=12)
    table.add_column("Model ID", style="green", width=20)
    table.add_column("Display Name", width=30)
    table.add_column("Context", justify="right", width=12)

    for provider in sorted_providers:
        models = sorted(providers[provider], key=lambda x: x[0])
        
        for i, (model_id, config) in enumerate(models):
            # Provider column (only show for first model of each provider)
            provider_display = ""
            if i == 0:
                glyph = MODEL_GLYPHS.get(provider, "●")
                color = PROVIDER_COLORS.get(provider, "white")
                provider_display = f"[{color}]{glyph}[/{color}] {provider.title()}"
            
            # Format context window
            context = f"{config.context_window:,}" if config.context_window else "?"
            
            table.add_row(
                provider_display,
                model_id,
                config.display_name,
                context
            )

    console.print(table)
    console.print()
    console.print("[dim]Use model ID (green column) with -a/-b flags[/dim]")
    console.print("[dim]Example: pidgin run -a claude -b gpt-4[/dim]")