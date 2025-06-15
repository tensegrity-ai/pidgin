"""User interaction handler for managing all user interactions during conversations."""

from enum import Enum
from typing import Optional
from rich.console import Console


class TimeoutDecision(Enum):
    """Possible user decisions when an agent times out."""
    WAIT = "wait"
    SKIP = "skip"
    END = "end"


class UserInteractionHandler:
    """Handles all user interactions in a consistent way."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize with optional console for display.
        
        Args:
            console: Rich console for output, or None for headless operation
        """
        self.console = console
        
    def get_timeout_decision(self, agent_display_name: str) -> TimeoutDecision:
        """Get user decision when an agent times out.
        
        Args:
            agent_display_name: Display name of the agent that timed out
            
        Returns:
            TimeoutDecision enum value
        """
        if not self.console:
            # No console = headless operation, default to skip
            return TimeoutDecision.SKIP
            
        self.show_timeout_warning(agent_display_name)
        
        try:
            user_input = input("\nYour choice: ").strip().lower()
            if user_input == "skip":
                return TimeoutDecision.SKIP
            elif user_input == "end":
                return TimeoutDecision.END
            else:
                # Default to wait (including empty input/Enter)
                return TimeoutDecision.WAIT
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+C or EOF as END
            return TimeoutDecision.END
        
    def show_timeout_warning(self, agent_display_name: str):
        """Display timeout warning to user.
        
        Args:
            agent_display_name: Display name of the agent that timed out
        """
        if not self.console:
            return
            
        self.console.print(
            f"\n[yellow]⚠ {agent_display_name} is taking longer than expected.[/yellow]"
        )
        self.console.print("[yellow]Options:[/yellow]")
        self.console.print("  1. Wait longer (press Enter)")
        self.console.print("  2. Skip this turn (type 'skip')")
        self.console.print("  3. End conversation (type 'end')")
    
    def show_pause_notification(self):
        """Show that conversation is pausing."""
        if self.console:
            self.console.print("\n[yellow]⏸ Pausing conversation...[/yellow]\n")
    
    def get_pause_decision(self) -> str:
        """Get user decision while paused."""
        if not self.console:
            return "continue"
            
        self.console.print("[bold cyan]Conversation Paused[/bold cyan]")
        self.console.print("\nOptions:")
        self.console.print("  1. [green]Continue[/green] - Resume the conversation")
        self.console.print("  2. [red]Exit[/red] - End the conversation")
        self.console.print()
        
        while True:
            try:
                choice = input("Your choice (1/2): ").strip()
                if choice == "1" or choice.lower() == "continue":
                    return "continue"
                elif choice == "2" or choice.lower() == "exit":
                    return "exit"
                else:
                    self.console.print("[red]Invalid choice. Please enter 1 or 2.[/red]")
            except (EOFError, KeyboardInterrupt):
                # Handle Ctrl+C during pause menu as exit
                return "exit"