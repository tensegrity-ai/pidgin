"""Model management commands."""
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from typing import Optional

from pidgin.llm.models import (
    get_model_shortcuts,
    PROVIDER_NAMES,
    DEFAULT_MODEL,
    resolve_model_name
)
from pidgin.config.settings import Settings

app = typer.Typer(
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]}
)
console = Console()


@app.command("list")
def list_models(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all model IDs"),
):
    """List available models and shortcuts."""
    settings = ctx.obj["settings"]
    
    console.print("\n[bold]Available Models:[/bold]\n")
    
    shortcuts_by_provider = get_model_shortcuts()
    
    for provider, provider_name in PROVIDER_NAMES.items():
        # Check if API key is configured
        has_key = settings.has_api_key(provider)
        key_status = "[green]✓ API key configured[/green]" if has_key else "[red]✗ No API key[/red]"
        
        # Provider header
        console.print(f"  [bold]{provider_name}[/bold]    {key_status}")
        
        # Get shortcuts for this provider
        shortcuts = shortcuts_by_provider.get(provider, {})
        
        if shortcuts:
            # Create table for shortcuts
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Shortcut", style="cyan", min_width=20)
            table.add_column("→", style="dim")
            table.add_column("Model ID", style="white")
            table.add_column("", style="yellow")  # For default marker
            
            # Sort shortcuts by name
            for shortcut in sorted(shortcuts.keys()):
                full_id = shortcuts[shortcut]
                
                # Check if this is the default
                is_default = full_id == DEFAULT_MODEL
                default_marker = "[DEFAULT]" if is_default else ""
                
                # Skip duplicates unless verbose
                if not verbose and full_id == shortcut:
                    continue
                
                table.add_row(
                    shortcut,
                    "→",
                    full_id,
                    default_marker
                )
            
            console.print(table)
        else:
            console.print("    [dim]No models available[/dim]")
        
        console.print()  # Empty line between providers
    
    console.print("[dim]You can also use full model identifiers directly.[/dim]")
    console.print("[dim]Use shortcuts with: pidgin create -m claude:creative[/dim]\n")


@app.command("info", no_args_is_help=True)
def model_info(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model name or shortcut"),
):
    """Show information about a specific model."""
    # Resolve model name
    resolved = resolve_model_name(model)
    
    if resolved == model:
        console.print(f"[cyan]{model}[/cyan] is a full model identifier")
    else:
        console.print(f"[cyan]{model}[/cyan] → [white]{resolved}[/white]")
    
    # Get provider
    from pidgin.llm.models import get_model_provider
    provider = get_model_provider(resolved)
    
    if provider:
        provider_name = PROVIDER_NAMES.get(provider, provider)
        console.print(f"Provider: [bold]{provider_name}[/bold]")
        
        # Check if API key is configured
        settings = ctx.obj["settings"]
        has_key = settings.has_api_key(provider)
        if has_key:
            console.print("[green]✓ API key configured[/green]")
        else:
            console.print("[red]✗ No API key configured[/red]")
            console.print(f"[dim]Set {provider.upper()}_API_KEY environment variable[/dim]")
    else:
        console.print("[yellow]Unknown model - may be a future model ID[/yellow]")