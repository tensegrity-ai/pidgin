# pidgin/cli/init_config.py
"""Initialize configuration file command."""

from pathlib import Path
import rich_click as click
from rich.console import Console

from ..config import Config
from .constants import NORD_GREEN, NORD_YELLOW, NORD_BLUE

console = Console()


@click.command()
@click.option('--force', '-f', is_flag=True, help='Overwrite existing config')
def init_config(force):
    """Create a configuration file with example settings.
    
    Creates ~/.config/pidgin/pidgin.yaml with convergence profiles
    and other customizable settings.
    """
    config_path = Path.home() / ".config" / "pidgin" / "pidgin.yaml"
    
    if config_path.exists() and not force:
        console.print(f"[{NORD_YELLOW}]Config file already exists at: {config_path}[/{NORD_YELLOW}]")
        console.print(f"Use --force to overwrite")
        return
    
    # Create config instance to access the write method
    config = Config()
    
    # Create directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write example config
    config._write_example_config(config_path)
    
    console.print(f"\n[{NORD_GREEN}]◆ Created configuration file[/{NORD_GREEN}]")
    console.print(f"Location: {config_path}")
    console.print(f"\n[{NORD_BLUE}]Available convergence profiles:[/{NORD_BLUE}]")
    console.print("  • balanced   - Default, balanced weights")
    console.print("  • structural - Emphasizes structural patterns (2x weight)")
    console.print("  • semantic   - Emphasizes content/meaning")
    console.print("  • strict     - Higher standards for all metrics")
    console.print(f"\n[dim]Edit the file to customize settings[/dim]")