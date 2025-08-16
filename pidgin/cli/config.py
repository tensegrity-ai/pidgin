"""Create and manage Pidgin configuration."""

import rich_click as click
from rich.console import Console

from ..config import Config
from ..io.directories import get_config_dir
from ..ui.display_utils import DisplayUtils

console = Console()
display = DisplayUtils(console)


@click.command()
@click.option(
    "--force", "-f", is_flag=True, help="Overwrite existing configuration file"
)
def config(force: bool):
    """Create a configuration file with example settings.

    Creates ~/.config/pidgin/pidgin.yaml with default settings
    and examples for customization.
    """
    config_path = get_config_dir() / "pidgin.yaml"

    if config_path.exists() and not force:
        display.warning(
            f"Config file already exists at: {config_path}", use_panel=False
        )
        display.info("Use --force to overwrite", use_panel=False)
        return

    config_instance = Config()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    config_instance._write_example_config(config_path)

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
