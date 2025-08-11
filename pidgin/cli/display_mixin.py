"""Mixin for common CLI display patterns."""

from typing import Optional, List, Dict, Any
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ..ui.display_utils import DisplayUtils


class CLIDisplayMixin:
    """Mixin providing common display patterns for CLI commands.
    
    This mixin should be used by CLI command handlers to ensure
    consistent display patterns across all commands.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the display mixin.
        
        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()
        self.display = DisplayUtils(self.console)
    
    def show_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Display a command header with optional subtitle.
        
        Args:
            title: Main title for the command
            subtitle: Optional subtitle with additional info
        """
        header_text = Text(title, style="bold cyan")
        if subtitle:
            header_text.append(f"\n{subtitle}", style="dim")
        
        panel = Panel(
            header_text,
            border_style="cyan",
            expand=False
        )
        self.console.print(panel)
        self.console.print()
    
    def show_config(self, config: Dict[str, Any], title: str = "Configuration") -> None:
        """Display configuration in a formatted table.
        
        Args:
            config: Configuration dictionary to display
            title: Title for the configuration section
        """
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Parameter", style="green")
        table.add_column("Value", style="white")
        
        for key, value in config.items():
            if value is not None:
                # Format value based on type
                if isinstance(value, bool):
                    display_value = "✓" if value else "✗"
                elif isinstance(value, (list, tuple)):
                    display_value = ", ".join(str(v) for v in value)
                elif isinstance(value, Path):
                    display_value = str(value)
                else:
                    display_value = str(value)
                
                table.add_row(key.replace("_", " ").title(), display_value)
        
        self.console.print(table)
        self.console.print()
    
    def show_progress(self, description: str) -> Progress:
        """Create and return a progress spinner for long operations.
        
        Args:
            description: Description of the operation
            
        Returns:
            Progress object to be used with context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        )
    
    def show_result(
        self, 
        success: bool, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Display operation result with optional details.
        
        Args:
            success: Whether the operation succeeded
            message: Result message
            details: Optional dictionary of result details
        """
        if success:
            self.display.success(message)
        else:
            self.display.error(message)
        
        if details:
            for key, value in details.items():
                self.console.print(f"  [dim]{key}:[/dim] {value}")
    
    def show_list(
        self,
        items: List[str],
        title: Optional[str] = None,
        numbered: bool = True
    ) -> None:
        """Display a list of items.
        
        Args:
            items: List of items to display
            title: Optional title for the list
            numbered: Whether to number the items
        """
        if title:
            self.console.print(f"[bold]{title}[/bold]")
        
        for i, item in enumerate(items, 1):
            if numbered:
                self.console.print(f"  {i}. {item}")
            else:
                self.console.print(f"  • {item}")
        
        self.console.print()
    
    def confirm_action(
        self,
        action: str,
        details: Optional[str] = None,
        default: bool = False
    ) -> bool:
        """Ask for user confirmation before proceeding.
        
        Args:
            action: Description of the action to confirm
            details: Optional additional details
            default: Default answer if user just presses Enter
            
        Returns:
            True if user confirms, False otherwise
        """
        prompt = f"[yellow]⚠ {action}[/yellow]"
        if details:
            prompt += f"\n  [dim]{details}[/dim]"
        
        prompt += f"\n  Continue? [{('Y' if default else 'y')}/{('n' if default else 'N')}]: "
        
        self.console.print(prompt, end="")
        response = input().strip().lower()
        
        if not response:
            return default
        
        return response in ["y", "yes"]
    
    def show_file_operation(
        self,
        operation: str,
        file_path: Path,
        success: bool = True
    ) -> None:
        """Display a file operation result.
        
        Args:
            operation: Type of operation (created, updated, deleted, etc.)
            file_path: Path to the file
            success: Whether the operation succeeded
        """
        icon = "✓" if success else "✗"
        style = "green" if success else "red"
        
        self.console.print(
            f"[{style}]{icon}[/{style}] {operation}: [cyan]{file_path}[/cyan]"
        )
    
    def show_summary(
        self,
        title: str,
        stats: Dict[str, Any],
        show_panel: bool = True
    ) -> None:
        """Display a summary of operation statistics.
        
        Args:
            title: Title for the summary
            stats: Dictionary of statistics to display
            show_panel: Whether to wrap in a panel
        """
        lines = []
        for key, value in stats.items():
            formatted_key = key.replace("_", " ").title()
            lines.append(f"[bold]{formatted_key}:[/bold] {value}")
        
        content = "\n".join(lines)
        
        if show_panel:
            panel = Panel(
                content,
                title=f"[bold]{title}[/bold]",
                border_style="green",
                expand=False
            )
            self.console.print(panel)
        else:
            self.console.print(f"[bold]{title}[/bold]")
            for line in lines:
                self.console.print(f"  {line}")
    
    def show_separator(self, char: str = "─", width: Optional[int] = None) -> None:
        """Display a visual separator line.
        
        Args:
            char: Character to use for the separator
            width: Width of separator (None for full width)
        """
        if width is None:
            width = self.console.width
        
        self.console.print(char * width, style="dim")