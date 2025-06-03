"""Conductor mode for manual control of AI conversations."""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.table import Table
import click

from .types import Message


class ConductorMiddleware:
    """Middleware for manual approval and modification of messages in conversations."""
    
    def __init__(self, console: Console):
        """Initialize the conductor middleware.
        
        Args:
            console: Rich console for terminal display
        """
        self.console = console
        self.intervention_history: List[Dict[str, Any]] = []
        self.turn_count = 0
        
    def display_pending_message(self, message: Message, agent_name: str, turn: int):
        """Display the pending message in a nice panel.
        
        Args:
            message: The message to display
            agent_name: Name of the agent sending the message
            turn: Current turn number
        """
        # Create title with agent and turn info
        title = f"Turn {turn} - {agent_name}"
        
        # Display the message
        self.console.print(Panel(
            message.content,
            title=f"[bold blue]{title}[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        ))
        
    def display_controls(self):
        """Display available controls."""
        controls = Text()
        controls.append("[", style="dim")
        controls.append("Enter", style="bold green")
        controls.append(": continue | ", style="dim")
        controls.append("e", style="bold yellow")
        controls.append(": edit | ", style="dim")
        controls.append("i", style="bold cyan")
        controls.append(": inject | ", style="dim")
        controls.append("s", style="bold magenta")
        controls.append(": skip | ", style="dim")
        controls.append("q", style="bold red")
        controls.append(": quit | ", style="dim")
        controls.append("?", style="bold")
        controls.append(": help", style="dim")
        controls.append("]", style="dim")
        
        self.console.print(controls)
        
    def display_help(self):
        """Display detailed help information."""
        help_table = Table(title="Conductor Mode Commands", show_header=True)
        help_table.add_column("Command", style="bold")
        help_table.add_column("Action")
        help_table.add_column("Description")
        
        help_table.add_row(
            "Enter/n", 
            "Continue", 
            "Send the message as-is to the next agent"
        )
        help_table.add_row(
            "e", 
            "Edit", 
            "Modify the message before sending"
        )
        help_table.add_row(
            "i", 
            "Inject", 
            "Insert a custom message into the conversation"
        )
        help_table.add_row(
            "s", 
            "Skip", 
            "Skip this message (don't send it)"
        )
        help_table.add_row(
            "q", 
            "Quit", 
            "Save conversation state and exit"
        )
        help_table.add_row(
            "?/h", 
            "Help", 
            "Show this help message"
        )
        
        self.console.print("\n")
        self.console.print(help_table)
        self.console.print("\n")
        
    def edit_message(self, original_message: Message) -> Message:
        """Allow user to edit a message.
        
        Args:
            original_message: The original message to edit
            
        Returns:
            Modified message
        """
        self.console.print("\n[yellow]Enter edited message (Ctrl+D when done):[/yellow]")
        
        # Show current content
        self.console.print(Panel(
            original_message.content,
            title="[dim]Current Message[/dim]",
            border_style="dim"
        ))
        
        # Get new content
        lines = []
        self.console.print("[dim]New content:[/dim]")
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        new_content = "\n".join(lines).strip()
        
        # If empty, keep original
        if not new_content:
            self.console.print("[dim]No changes made.[/dim]")
            return original_message
            
        # Create modified message
        modified_message = Message(
            role=original_message.role,
            content=new_content,
            agent_id=original_message.agent_id
        )
        
        # Record the edit
        self.intervention_history.append({
            'type': 'edit',
            'turn': self.turn_count,
            'timestamp': datetime.now().isoformat(),
            'original': original_message.content,
            'modified': new_content,
            'agent_id': original_message.agent_id
        })
        
        self.console.print("\n[green]✓ Message edited[/green]\n")
        return modified_message
        
    def inject_message(self, agent_id: str, target_agent_id: str) -> Optional[Message]:
        """Allow user to inject a custom message.
        
        Args:
            agent_id: ID of the agent that would be "sending" the message
            target_agent_id: ID of the agent that will receive the message
            
        Returns:
            Injected message or None if cancelled
        """
        self.console.print(f"\n[cyan]Inject message as {agent_id} to {target_agent_id}:[/cyan]")
        self.console.print("[dim]Enter message (Ctrl+D when done, empty to cancel):[/dim]")
        
        # Get content
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        content = "\n".join(lines).strip()
        
        if not content:
            self.console.print("[dim]Injection cancelled.[/dim]")
            return None
            
        # Create injected message
        injected_message = Message(
            role="assistant",
            content=content,
            agent_id=agent_id
        )
        
        # Record the injection
        self.intervention_history.append({
            'type': 'inject',
            'turn': self.turn_count,
            'timestamp': datetime.now().isoformat(),
            'content': content,
            'agent_id': agent_id,
            'target_agent_id': target_agent_id
        })
        
        self.console.print("\n[green]✓ Message injected[/green]\n")
        return injected_message
        
    async def process_message(self, message: Message, agent_name: str, 
                            target_agent_id: str, turn: int) -> Optional[Message]:
        """Process a message with conductor controls.
        
        Args:
            message: The message to process
            agent_name: Name of the agent sending the message
            target_agent_id: ID of the agent that will receive the message
            turn: Current turn number
            
        Returns:
            Processed message, None to skip, or raises exception to quit
        """
        self.turn_count = turn
        
        while True:
            # Display the pending message
            self.display_pending_message(message, agent_name, turn)
            
            # Display controls
            self.display_controls()
            
            # Get user input
            command = Prompt.ask(">", default="").strip().lower()
            
            if command in ["", "n", "enter"]:
                # Continue with message as-is
                self.console.print("[green]→ Continuing...[/green]\n")
                return message
                
            elif command == "e":
                # Edit the message
                message = self.edit_message(message)
                # Loop back to show edited message
                
            elif command == "i":
                # Inject a message
                injected = self.inject_message(message.agent_id, target_agent_id)
                if injected:
                    # Return the injected message instead
                    return injected
                # Otherwise loop back
                
            elif command == "s":
                # Skip this message
                self.console.print("[yellow]⏭️  Message skipped[/yellow]\n")
                self.intervention_history.append({
                    'type': 'skip',
                    'turn': self.turn_count,
                    'timestamp': datetime.now().isoformat(),
                    'skipped_content': message.content,
                    'agent_id': message.agent_id
                })
                return None
                
            elif command == "q":
                # Quit
                self.console.print("[red]🛑 Quitting conductor mode...[/red]")
                raise KeyboardInterrupt("User quit from conductor mode")
                
            elif command in ["?", "h"]:
                # Show help
                self.display_help()
                
            else:
                # Unknown command
                self.console.print(f"[red]Unknown command: {command}[/red]")
                self.console.print("[dim]Press ? for help[/dim]\n")
                
    def get_intervention_summary(self) -> Dict[str, Any]:
        """Get a summary of all interventions made during the conversation.
        
        Returns:
            Dictionary containing intervention history and statistics
        """
        edit_count = sum(1 for i in self.intervention_history if i['type'] == 'edit')
        inject_count = sum(1 for i in self.intervention_history if i['type'] == 'inject')
        skip_count = sum(1 for i in self.intervention_history if i['type'] == 'skip')
        
        return {
            'total_interventions': len(self.intervention_history),
            'edits': edit_count,
            'injections': inject_count,
            'skips': skip_count,
            'history': self.intervention_history
        }