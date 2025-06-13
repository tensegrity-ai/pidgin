"""Display manager for all console output in dialogue engine."""

from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel

from ..types import Message, Agent
from .base import Component


class DisplayManager(Component):
    """Handles all console display and Rich rendering for conversations."""
    
    def __init__(self, console: Console):
        """Initialize display manager with Rich console."""
        self.console = console
        
    def reset(self):
        """Reset display state for new conversation."""
        # Display manager is stateless, nothing to reset
        pass
        
    def show_initial_setup(self, agent_a: Agent, agent_b: Agent, config: Dict[str, Any]):
        """Display conversation setup information."""
        self.console.print("[bold cyan]🎼 Conversation Setup[/bold cyan]")
        self.console.print(f"Agent A: {agent_a.id} ({agent_a.model})")
        self.console.print(f"Agent B: {agent_b.id} ({agent_b.model})")
        self.console.print()
        
    def display_message(self, message: Message, model_name: str = "", context_info: Optional[Dict[str, Any]] = None):
        """Display a message with proper formatting.
        
        Args:
            message: The message to display
            model_name: Model name to show in title
            context_info: Optional context usage information
        """
        # Handle different message types
        if message.agent_id == "agent_a":
            title = f"[bold green]Agent A ({model_name})[/bold green]"
            border_style = "green"
        elif message.agent_id == "agent_b":
            title = f"[bold magenta]Agent B ({model_name})[/bold magenta]"
            border_style = "magenta"
        elif message.agent_id == "system":
            # System messages are internal setup - don't display them
            return  # Skip display of system messages
        else:
            # Everything else is a human note
            title = "[bold cyan]Human Note[/bold cyan]"
            border_style = "cyan"
            
        self.console.print(
            Panel(
                message.content,
                title=title,
                border_style=border_style,
            )
        )
        self.console.print()
        
    def show_turn_progress(self, turn: int, max_turns: int, metrics: Optional[Dict[str, Any]] = None):
        """Display turn counter with optional metrics.
        
        Args:
            turn: Current turn number
            max_turns: Maximum number of turns
            metrics: Optional metrics to display (convergence, context usage, etc.)
        """
        if (turn + 1) % 5 == 0:  # Every 5 turns
            status_parts = [f"Turn {turn + 1}/{max_turns}"]
            
            # Add metrics if provided
            if metrics:
                if 'convergence' in metrics and metrics['convergence'] > 0:
                    emoji = " ⚠️" if metrics['convergence'] >= 0.75 else ""
                    status_parts.append(f"Conv: {metrics['convergence']:.2f}{emoji}")
                
                if 'context_usage' in metrics and metrics['context_usage'] > 50:
                    status_parts.append(f"Context: {metrics['context_usage']:.0f}%")
            
            self.console.print(f"\n[dim]{' | '.join(status_parts)} | Ctrl+C to pause[/dim]\n")
        else:
            # Minimal turn counter every turn
            self.console.print(f"\n[dim]Turn {turn + 1}/{max_turns}[/dim]\n")
            
    def show_attractor_detection(self, result: Dict[str, Any]):
        """Display attractor detection results.
        
        Args:
            result: Attractor detection result dictionary
        """
        self.console.print()
        max_turns = result.get('max_turns', '?')
        self.console.print(
            f"[red bold]🎯 ATTRACTOR DETECTED - Turn {result['turn_detected']}/{max_turns}[/red bold]"
        )
        self.console.print(f"[yellow]Type:[/yellow] {result['type']}")
        self.console.print(f"[yellow]Pattern:[/yellow] {result['description']}")
        self.console.print(f"[yellow]Confidence:[/yellow] {result['confidence']:.0%}")
        if 'typical_turns' in result:
            self.console.print(f"[yellow]Typical occurrence:[/yellow] Turn {result['typical_turns']}")
        self.console.print()
        
    def show_context_windows(self, agents: list[Agent], context_manager: Any):
        """Display context window limits for agents.
        
        Args:
            agents: List of agents
            context_manager: Context window manager instance
        """
        self.console.print("[bold cyan]Context Windows:[/bold cyan]")
        for agent in agents:
            if agent.model in context_manager.context_limits:
                limit = context_manager.context_limits[agent.model]
                effective_limit = limit - context_manager.reserved_tokens
                self.console.print(
                    f"  • {agent.id} ({agent.model}): "
                    f"{effective_limit:,} tokens (total: {limit:,})"
                )
        self.console.print()
        
    def show_context_warning(self, usage: float, turns_remaining: int, model: str):
        """Display context usage warning.
        
        Args:
            usage: Context usage percentage
            turns_remaining: Estimated turns remaining
            model: Model name that's constrained
        """
        self.console.print(
            f"\n[yellow bold]⚠️  Context Warning ({model}): "
            f"{usage:.1f}% used, ~{turns_remaining} turns remaining[/yellow bold]\n"
        )
        
    def show_context_pause(self, usage: float, model: str):
        """Display context auto-pause message.
        
        Args:
            usage: Context usage percentage
            model: Model name that triggered pause
        """
        self.console.print(
            f"[red bold]🛑 Auto-pausing: Context window {usage:.1f}% full "
            f"for {model}[/red bold]"
        )
        
    def show_intervention_controls(self):
        """Display intervention control options."""
        self.console.print("[yellow]🎼 Intervention mode activated[/yellow]")
        
    def show_checkpoint_saved(self, path: str):
        """Display checkpoint saved message.
        
        Args:
            path: Path where checkpoint was saved
        """
        self.console.print(f"\n[green]Checkpoint saved: {path}[/green]")
        self.console.print(f"[green]Resume with: pidgin resume {path}[/green]\n")
        
    def show_initial_prompt(self, prompt: str):
        """Display the initial conversation prompt.
        
        Args:
            prompt: Initial prompt text
        """
        self.console.print(
            Panel(
                prompt,
                title="[bold cyan]Human Note (Initial Prompt)[/bold cyan]",
                border_style="cyan",
            )
        )
        self.console.print()
        
    def show_mode_info(self, mode: str):
        """Display conductor mode information.
        
        Args:
            mode: Either 'manual' or 'flowing'
        """
        if mode == "manual":
            self.console.print("[bold cyan]🎼 Manual Mode Active[/bold cyan]")
            self.console.print("[dim]You will approve each message before it's sent.[/dim]\n")
        else:
            self.console.print("[bold cyan]🎼 Flowing Mode (Default)[/bold cyan]")
            self.console.print("[dim]Conversation flows automatically. Press Ctrl+C to pause.[/dim]\n")
            
    def show_resume_info(self, turn: int):
        """Display resume information.
        
        Args:
            turn: Turn number being resumed from
        """
        self.console.print(f"[green]Resuming conversation from turn {turn}[/green]\n")