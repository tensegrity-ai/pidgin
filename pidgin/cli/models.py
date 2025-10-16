"""List available AI models."""

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config.model_types import ModelConfig
from ..config.models import MODELS
from ..ui.display_utils import DisplayUtils
from .constants import MODEL_GLYPHS, PROVIDER_COLORS

console = Console()
display = DisplayUtils(console)


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
                    display_name=f"{name.title()} ({size_gb}GB)"
                    if size_gb
                    else name.title(),
                    aliases=[name],
                    provider="local",
                    context_window=32768,  # Default context window for most Ollama models
                    notes="Local Ollama model",
                )
                ollama_models.append((model_id, config))
    except Exception:
        # If Ollama is not running or accessible, return empty list
        pass
    return ollama_models


@click.command()
@click.option(
    "--all", is_flag=True, help="Show all stable production models (curated + stable)"
)
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

    # Display title
    console.print()
    console.print("[bold cyan]Available Models[/bold cyan]")
    console.print()

    # Display each provider's models in separate panels
    for provider in sorted_providers:
        models_list = sorted(providers[provider], key=lambda x: x[0])

        # Provider header with glyph and color
        glyph = MODEL_GLYPHS.get(provider, "●")
        color = PROVIDER_COLORS.get(provider, "white")

        # Create compact table for this provider
        table = Table(box=None, padding=(0, 2), show_header=False)
        table.add_column("Model", style=color)
        table.add_column("Aliases", style="dim")
        table.add_column("Context", justify="right", style="dim")
        table.add_column("Cost", justify="right", style="dim")

        for model_id, config in models_list:
            # Strip provider prefix from model_id for cleaner display
            if ":" in model_id and model_id.startswith(f"{provider}:"):
                display_model_id = model_id[len(provider) + 1 :]
            else:
                display_model_id = model_id

            # Format aliases (show first 2-3 aliases)
            aliases = ", ".join(config.aliases[:3]) if config.aliases else "—"
            if len(config.aliases) > 3:
                aliases += f" +{len(config.aliases) - 3}"

            # Format context window
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
            if (
                config.input_cost_per_million is not None
                and config.output_cost_per_million is not None
            ):
                if (
                    config.input_cost_per_million == 0
                    and config.output_cost_per_million == 0
                ):
                    cost = "free"
                else:
                    in_cost = config.input_cost_per_million
                    out_cost = config.output_cost_per_million
                    # Use minimal decimal places
                    if in_cost >= 1:
                        in_str = (
                            f"{in_cost:.0f}"
                            if in_cost == int(in_cost)
                            else f"{in_cost:.1f}"
                        )
                    else:
                        in_str = f"{in_cost:.2f}".rstrip("0").rstrip(".")
                    if out_cost >= 1:
                        out_str = (
                            f"{out_cost:.0f}"
                            if out_cost == int(out_cost)
                            else f"{out_cost:.1f}"
                        )
                    else:
                        out_str = f"{out_cost:.2f}".rstrip("0").rstrip(".")
                    cost = f"${in_str}/${out_str}"
            else:
                cost = "—"

            table.add_row(display_model_id, aliases, context, cost)

        # Wrap table in a panel with provider name as title
        panel = Panel(
            table,
            title=f"[{color}]{glyph}[/{color}] [{color}]{provider.title()}[/{color}]",
            title_align="left",
            border_style=color,
            padding=(0, 1),
            expand=False,
        )
        console.print(panel)
    # Show usage instructions
    console.print("[dim]Use model ID or alias with -a/-b flags[/dim]")
    console.print("[dim]Example: [/dim][cyan]pidgin run -a sonnet-4 -b gpt-4o[/cyan]")
    console.print()

    # Show filtering status with better messaging
    if all:
        console.print("[dim]Showing all stable production models.[/dim]")
    else:
        console.print(
            "[dim]Showing essential models. Use [/dim][cyan]--all[/cyan][dim] for all stable releases.[/dim]"
        )

    # Check if Ollama is available and show helpful message
    if not ollama_models:
        try:
            import httpx

            response = httpx.get("http://localhost:11434/api/tags", timeout=0.5)
            if response.status_code != 200:
                console.print()
                console.print(
                    "[dim]For local models, install Ollama: [/dim][cyan]https://ollama.ai[/cyan]"
                )
        except Exception:
            console.print()
            console.print(
                "[dim]For local models, start Ollama or install: [/dim][cyan]https://ollama.ai[/cyan]"
            )
