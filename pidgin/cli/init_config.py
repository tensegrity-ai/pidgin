# pidgin/cli/init_config.py
"""Initialize configuration file command."""

from pathlib import Path
import rich_click as click
from rich.console import Console

from ..config import Config
from .constants import NORD_GREEN, NORD_YELLOW, NORD_BLUE
from ..ui.display_utils import DisplayUtils

console = Console()
display = DisplayUtils(console)


@click.command()
@click.option('--force', '-f', is_flag=True, help='Overwrite existing config')
def init_config(force):
    """Create a configuration file with example settings.
    
    Creates ~/.config/pidgin/pidgin.yaml with convergence profiles
    and other customizable settings.
    """
    config_path = Path.home() / ".config" / "pidgin" / "pidgin.yaml"
    
    if config_path.exists() and not force:
        display.warning(f"Config file already exists at: {config_path}", use_panel=False)
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
        "  • strict     - Higher standards for all metrics"
    ]
    display.info("\n".join(profiles_info), use_panel=False)
    display.dim("\nEdit the file to customize settings")