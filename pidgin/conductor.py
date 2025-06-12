"""Conductor mode for manual control of AI conversations."""

from datetime import datetime
from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.table import Table

from .types import Message, MessageSource, ConversationTurn, InterventionSource


class Conductor:
    """Clean conductor: end-of-turn interventions only."""

    def __init__(self, console: Console, mode: str = "flowing"):
        """Initialize the conductor.

        Args:
            console: Rich console for terminal display
            mode: "manual" (pause after each turn) or "flowing" (auto-run until paused)
        """
        self.console = console
        self.mode = mode
        self.intervention_history: List[Dict[str, Any]] = []
        self.is_paused = False if mode == "flowing" else True

    def should_intervene_after_turn(self, turn: ConversationTurn) -> bool:
        """Check if intervention is needed after complete turn."""
        if self.mode == "manual":
            return True  # Always ask in manual mode
        elif self.mode == "flowing":
            return self.is_paused  # Only if pause requested
        return False

    def _display_turn_summary(self, turn: ConversationTurn):
        """Display completed turn summary."""
        title = f"Turn {turn.turn_number} Complete"

        # Agent A message
        self.console.print(
            Panel(
                turn.agent_a_message.content,
                title=f"[bold blue]Agent A[/bold blue]",
                border_style="blue",
                padding=(1, 2),
            )
        )

        # Agent B message
        self.console.print(
            Panel(
                turn.agent_b_message.content,
                title=f"[bold green]Agent B[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

        if turn.post_turn_interventions:
            for intervention in turn.post_turn_interventions:
                self.console.print(
                    Panel(
                        intervention.content,
                        title=f"[bold yellow]{intervention.display_source}[/bold yellow]",
                        border_style="yellow",
                        padding=(1, 2),
                    )
                )

    def _display_intervention_controls(self):
        """Display intervention controls."""
        controls = Text()
        controls.append("[", style="dim")
        controls.append("Enter", style="bold green")
        controls.append(": continue | ", style="dim")
        controls.append("i", style="bold cyan")
        controls.append(": inject | ", style="dim")
        controls.append("q", style="bold red")
        controls.append(": quit | ", style="dim")
        controls.append("?", style="bold")
        controls.append(": help", style="dim")
        controls.append("]", style="dim")

        self.console.print(controls)

    def _display_help(self):
        """Display simplified help information."""
        help_table = Table(title="End-of-Turn Intervention Commands", show_header=True)
        help_table.add_column("Command", style="bold")
        help_table.add_column("Action")
        help_table.add_column("Description")

        help_table.add_row(
            "Enter", "Continue", "Continue conversation without intervention"
        )
        help_table.add_row("i", "Inject", "Add intervention message after this turn")
        help_table.add_row("q", "Quit", "Save conversation state and exit")
        help_table.add_row("?/h", "Help", "Show this help message")

        self.console.print("\n")
        self.console.print(help_table)
        self.console.print("\n")

    def _get_intervention_choice(self) -> str:
        """Get user's intervention choice."""
        self._display_intervention_controls()
        command = Prompt.ask(">", default="").strip().lower()

        if command in ["", "enter"]:
            return "continue"
        elif command == "i":
            return "inject"
        elif command == "q":
            return "quit"
        elif command in ["?", "h"]:
            self._display_help()
            return self._get_intervention_choice()  # Recursive call for retry
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("[dim]Press ? for help[/dim]\n")
            return self._get_intervention_choice()  # Recursive call for retry

    def _create_intervention(self) -> Optional[Message]:
        """Create intervention message (human/system/mediator)."""
        # Simplified options - no agent impersonation
        source_options = {
            "1": InterventionSource.HUMAN,
            "2": InterventionSource.SYSTEM,
            "3": InterventionSource.MEDIATOR,
        }

        source_table = Table(show_header=False, box=None, padding=(0, 1))
        source_table.add_column("Num", style="bold cyan")
        source_table.add_column("Source")
        source_table.add_column("Description", style="dim")

        source_table.add_row("1", "Human", "Researcher intervention")
        source_table.add_row("2", "System", "Technical/infrastructure message")
        source_table.add_row("3", "Mediator", "Neutral facilitation")

        self.console.print(source_table)
        self.console.print()

        source_choice = Prompt.ask(
            "Intervention source", choices=["1", "2", "3"], default="1"
        )
        source = source_options[source_choice]

        # Get content with improved UX
        content = self._get_multiline_input("Intervention content")

        if not content:
            self.console.print("[dim]Intervention cancelled (empty content)[/dim]")
            return None

        intervention = Message(
            role="user",  # All interventions are "user" role to agents
            content=content,
            agent_id=source.value,
            source=source,
        )

        # Track intervention
        self.intervention_history.append(
            {
                "type": "intervention",
                "source": source.value,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return intervention

    def get_intervention(self, turn: ConversationTurn) -> Optional[Message]:
        """Get intervention message for end of turn."""
        if not self.should_intervene_after_turn(turn):
            return None

        # Show completed turn
        self._display_turn_summary(turn)

        # Get intervention options
        action = self._get_intervention_choice()

        if action == "inject":
            return self._create_intervention()
        elif action == "continue":
            if self.mode == "flowing" and self.is_paused:
                self.is_paused = False  # Resume flowing
                self.console.print("[green]→ Resuming flowing mode...[/green]\n")
            return None
        elif action == "quit":
            raise KeyboardInterrupt("User quit from conductor")

        return None

    def _get_multiline_input(self, prompt: str) -> str:
        """Clean multiline input with double-enter submit."""

        # Display input prompt with clear instructions
        self.console.print(
            Panel(
                f"{prompt}\n\n[dim]• Type your message\n• Press Enter twice when done\n• Ctrl+D also works[/dim]",
                title="[bold cyan]Input Required[/bold cyan]",
                border_style="cyan",
            )
        )

        lines = []
        empty_line_count = 0

        try:
            while True:
                line = input()

                if line.strip() == "":
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        # Two consecutive empty lines = submit
                        break
                    else:
                        # First empty line, add it and continue
                        lines.append(line)
                else:
                    # Non-empty line, reset counter and add line
                    empty_line_count = 0
                    lines.append(line)

        except (EOFError, KeyboardInterrupt):
            # Still support Ctrl+D/Ctrl+C as backup
            self.console.print("\n[dim]Input cancelled[/dim]")
            return ""

        # Remove trailing empty lines and return
        while lines and lines[-1].strip() == "":
            lines.pop()

        result = "\n".join(lines).strip()
        if result:
            self.console.print(
                f"[green]✓ Input received ({len(result)} chars)[/green]\n"
            )

        return result

    def pause(self):
        """Pause the flowing conductor (called on Ctrl+Z)."""
        if self.mode == "flowing":
            self.is_paused = True
            self.console.print(
                "\n[yellow]🎼 Conductor paused - will pause at next turn[/yellow]"
            )

    def get_intervention_summary(self) -> Dict[str, Any]:
        """Get a summary of all interventions made during the conversation."""
        intervention_count = sum(
            1 for i in self.intervention_history if i["type"] == "intervention"
        )

        return {
            "total_interventions": len(self.intervention_history),
            "interventions": intervention_count,
            "history": self.intervention_history,
        }
