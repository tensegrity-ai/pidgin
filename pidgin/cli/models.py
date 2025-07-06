# pidgin/cli/models.py
"""Models command for listing available AI models."""

import rich_click as click
from rich.console import Console
from rich.table import Table

from ..config.models import MODELS
from .constants import NORD_BLUE, MODEL_EMOJIS, PROVIDER_COLORS

console = Console()


@click.command()
@click.option('--provider', '-p', 
              type=click.Choice(['all', 'openai', 'anthropic', 'google', 'xai', 'local']),
              default='all',
              help='Filter models by provider')
@click.option('--format', '-f',
              type=click.Choice(['table', 'list', 'json']),
              default='table',
              help='Output format')
def models(provider, format):
    """Display available AI models organized by provider.

    Shows all supported models with their aliases, context windows,
    and key characteristics.
    """
    # Filter models by provider
    models_to_show = {}
    for model_id, config in MODELS.items():
        if provider == 'all' or config.provider == provider:
            models_to_show[model_id] = config
    
    if format == 'json':
        import json
        output = {}
        for model_id, config in models_to_show.items():
            output[model_id] = {
                'provider': config.provider,
                'model': config.model,
                'display_name': config.display_name,
                'temperature': config.temperature,
                'emoji': MODEL_EMOJIS.get(model_id, '🤖')
            }
        console.print_json(data=output)
        return
    
    if format == 'list':
        for model_id, config in models_to_show.items():
            emoji = MODEL_EMOJIS.get(model_id, '🤖')
            color = PROVIDER_COLORS.get(config.provider, 'white')
            console.print(f"{emoji} [{color}]{model_id}[/{color}] - {config.display_name}")
        return
    
    # Table format
    table = Table(title="Available Models" if provider == 'all' else f"{provider.title()} Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Display Name", style="white")
    table.add_column("Provider", style="yellow")
    table.add_column("Temperature", style="green")
    
    # Group by provider for better display
    by_provider = {}
    for model_id, config in models_to_show.items():
        if config.provider not in by_provider:
            by_provider[config.provider] = []
        by_provider[config.provider].append((model_id, config))
    
    # Sort providers
    for prov in ['openai', 'anthropic', 'google', 'xai', 'local']:
        if prov not in by_provider:
            continue
            
        # Add provider separator
        if len(by_provider) > 1 and provider == 'all':
            table.add_row("", f"[bold {PROVIDER_COLORS.get(prov, 'white')}]── {prov.title()} ──[/bold {PROVIDER_COLORS.get(prov, 'white')}]", "", "")
        
        # Add models
        for model_id, config in sorted(by_provider[prov], key=lambda x: x[0]):
            emoji = MODEL_EMOJIS.get(model_id, '🤖')
            table.add_row(
                f"{emoji} {model_id}",
                config.display_name,
                config.provider,
                f"{config.temperature:.1f}" if config.temperature else "-"
            )
    
    console.print(table)
    
    # Show additional info
    console.print(f"\n[{NORD_BLUE}]To use a model:[/{NORD_BLUE}]")
    console.print(f"  pidgin run -a <model-id> -b <model-id>")
    console.print(f"\n[{NORD_BLUE}]For local models with Ollama:[/{NORD_BLUE}]")
    console.print(f"  pidgin run -a local:llama3.1 -b local:mistral")