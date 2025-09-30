"""List available AI models."""

import rich_click as click
from rich.console import Console
from rich.table import Table

from ..config.models import MODELS
from ..config.model_types import ModelConfig
from ..ui.display_utils import DisplayUtils
from .constants import MODEL_GLYPHS, PROVIDER_COLORS

console = Console()
display = DisplayUtils(console)


def _get_table_width() -> int:
    """Calculate table width based on terminal size."""
    terminal_width = console.size.width
    # Leave some margin for borders and scrollbars
    # Minimum width of 80, maximum of 150 for readability
    return max(80, min(terminal_width - 4, 150))


def _get_ollama_models():
    """Fetch installed Ollama models dynamically."""
    ollama_models = []
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            for model in data.get("models", []):
                # Extract model name and size info
                name = model["name"].split(":")[0]  # Remove tag if present
                size_bytes = model.get("size", 0)
                size_gb = round(size_bytes / (1024**3), 1) if size_bytes else 0

                # Create a ModelConfig for each Ollama model
                model_id = f"local:{name}"
                config = ModelConfig(
                    model_id=model_id,
                    display_name=f"{name.title()} ({size_gb}GB)" if size_gb else name.title(),
                    aliases=[name],
                    provider="local",
                    context_window=32768,  # Default context window for most Ollama models
                    notes=f"Local Ollama model"
                )
                ollama_models.append((model_id, config))
    except Exception:
        # If Ollama is not running or accessible, return empty list
        pass
    return ollama_models


@click.command()
@click.option('--all', is_flag=True, help='Show all stable production models (curated + stable)')
def models(all):
    """List available AI models.

    Shows models grouped by provider with their configurations.
    By default shows only curated/essential models. Use --all to see all stable releases.
    """
    # Group models by provider with filtering
    providers = {}
    for model_id, config in MODELS.items():
        # Determine if model should be shown based on flags
        if all:
            # Show curated + stable models
            include = config.curated or config.stable
        else:
            # Default: show only curated models (and local models)
            include = config.curated or config.provider == "local"

        if not include:
            continue

        if config.provider not in providers:
            providers[config.provider] = []
        providers[config.provider].append((model_id, config))

    # Add dynamically fetched Ollama models
    ollama_models = _get_ollama_models()
    if ollama_models:
        if "local" not in providers:
            providers["local"] = []
        # Add Ollama models but avoid duplicates with the test model
        existing_ids = {model_id for model_id, _ in providers["local"]}
        for model_id, config in ollama_models:
            if model_id not in existing_ids:
                providers["local"].append((model_id, config))

    # Sort providers
    provider_order = ["anthropic", "openai", "google", "xai", "local"]
    sorted_providers = sorted(
        providers.keys(),
        key=lambda p: provider_order.index(p) if p in provider_order else 99,
    )

    # Calculate column widths based on terminal size
    table_width = _get_table_width()

    # Distribute widths proportionally
    # Total parts: 8% + 18% + 15% + 28% + 8% + 13% = 90% (10% for padding)
    provider_width = max(8, int(table_width * 0.08))
    model_id_width = max(15, int(table_width * 0.18))
    aliases_width = max(12, int(table_width * 0.15))
    display_name_width = max(20, int(table_width * 0.28))
    context_width = max(6, int(table_width * 0.08))
    cost_width = max(11, int(table_width * 0.13))

    table = Table(show_header=True, header_style="bold cyan", title="Available Models", width=table_width)
    table.add_column("Provider", style="dim", width=provider_width)
    table.add_column("Model ID", style="green", width=model_id_width)
    table.add_column("Aliases", style="yellow", width=aliases_width)
    table.add_column("Display Name", width=display_name_width)
    table.add_column("Context", justify="right", width=context_width)
    table.add_column("Cost", justify="right", width=cost_width)

    for provider in sorted_providers:
        models = sorted(providers[provider], key=lambda x: x[0])

        for i, (model_id, config) in enumerate(models):
            # Provider column (only show for first model of each provider)
            provider_display = ""
            if i == 0:
                glyph = MODEL_GLYPHS.get(provider, "●")
                color = PROVIDER_COLORS.get(provider, "white")
                provider_display = f"[{color}]{glyph}[/{color}] {provider.title()}"

            # Format aliases (show first 2-3 aliases)
            aliases = ", ".join(config.aliases[:3]) if config.aliases else ""
            if len(config.aliases) > 3:
                aliases += f" +{len(config.aliases) - 3}"

            # Format context window in a more compact way
            if config.context_window:
                if config.context_window >= 1_000_000:
                    context = f"{config.context_window // 1_000_000}M"
                elif config.context_window >= 1000:
                    context = f"{config.context_window // 1000}K"
                else:
                    context = str(config.context_window)
            else:
                context = "?"

            # Format cost (input/output per million tokens)
            if config.input_cost_per_million is not None and config.output_cost_per_million is not None:
                if config.input_cost_per_million == 0 and config.output_cost_per_million == 0:
                    cost = "free"
                else:
                    # Show in format: $3/$15 or $0.15/$1
                    in_cost = config.input_cost_per_million
                    out_cost = config.output_cost_per_million
                    # Use minimal decimal places
                    if in_cost >= 1:
                        in_str = f"{in_cost:.0f}" if in_cost == int(in_cost) else f"{in_cost:.1f}"
                    else:
                        in_str = f"{in_cost:.2f}".rstrip('0').rstrip('.')
                    if out_cost >= 1:
                        out_str = f"{out_cost:.0f}" if out_cost == int(out_cost) else f"{out_cost:.1f}"
                    else:
                        out_str = f"{out_cost:.2f}".rstrip('0').rstrip('.')
                    cost = f"${in_str}/${out_str}"
            else:
                cost = "—"

            # Strip provider prefix from model_id for cleaner display
            # Only remove the initial provider prefix, preserve other colons
            if ":" in model_id and model_id.startswith(f"{provider}:"):
                display_model_id = model_id[len(provider)+1:]
            else:
                display_model_id = model_id

            table.add_row(provider_display, display_model_id, aliases, config.display_name, context, cost)

    console.print(table)
    console.print()
    console.print("[dim]Use model ID (green) or aliases (yellow) with -a/-b flags[/dim]")
    console.print("[dim]Example: pidgin run -a claude -b gpt[/dim]")

    # Show filtering status with better messaging
    if all:
        console.print()
        console.print("[dim]Showing all stable production models.[/dim]")
    else:
        console.print()
        console.print("[dim]Showing essential models only. Use --all to see all stable releases.[/dim]")

    # Check if Ollama is available and show helpful message
    if not ollama_models:
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=0.5)
            if response.status_code != 200:
                console.print()
                console.print("[dim]◆ For local models: Install Ollama from https://ollama.ai[/dim]")
        except Exception:
            console.print()
            console.print("[dim]◆ For local models: Start Ollama with 'ollama serve' or install from https://ollama.ai[/dim]")
