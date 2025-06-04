"""Conductor mode for manual control of AI conversations."""

from datetime import datetime
from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.table import Table

from .types import Message, MessageSource


class ConductorMiddleware:
    """Manual conductor mode - user approves each message before sending."""
    
    def __init__(self, console: Console):
        """Initialize the conductor middleware.
        
        Args:
            console: Rich console for terminal display
        """
        self.console = console
        self.intervention_history: List[Dict[str, Any]] = []
        self.turn_count = 0
        self.conversation_history = []  # For back functionality
        self.resume_requested = False  # Communication with dialogue engine
        
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
            "Enter", 
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
            
        # Create modified message, preserving source attribution
        modified_message = Message(
            role=original_message.role,
            content=new_content,
            agent_id=original_message.agent_id,
            source=original_message.source
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
        
    def inject_message(self, current_agent_id: str, target_agent_id: str) -> Optional[Message]:
        """Allow user to inject a custom message.
        
        Args:
            current_agent_id: ID of the agent currently speaking
            target_agent_id: ID of the agent that will receive the message
            
        Returns:
            Injected message or None if cancelled
        """
        self.console.print(f"\n[cyan]Inject message:[/cyan]")
        
        # Simplified injection sources
        source_options = Table(show_header=False, box=None, padding=(0, 1))
        source_options.add_column("Num", style="bold cyan")
        source_options.add_column("Source")
        source_options.add_column("Description", style="dim")
        
        source_options.add_row("1", "External", "Intervention message (visible to both agents)")
        source_options.add_row("2", "Agent A", "Message as Agent A")
        source_options.add_row("3", "Agent B", "Message as Agent B")
        
        self.console.print(source_options)
        self.console.print()
        
        while True:
            source_choice = Prompt.ask("From", choices=["1", "2", "3"], default="1")
            
            if source_choice == "1":
                source = MessageSource.HUMAN  # Use HUMAN for external interventions
                agent_id = "external"
                role = "user"
                break
            elif source_choice == "2":
                source = MessageSource.AGENT_A
                agent_id = "agent_a"
                role = "assistant"
                break
            elif source_choice == "3":
                source = MessageSource.AGENT_B
                agent_id = "agent_b"
                role = "assistant"
                break
        
        # Get content
        self.console.print(f"\n[cyan]Message content (Ctrl+D when done, empty to cancel):[/cyan]")
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
            role=role,
            content=content,
            agent_id=agent_id,
            source=source
        )
        
        # Record the injection
        self.intervention_history.append({
            'type': 'inject',
            'turn': self.turn_count,
            'timestamp': datetime.now().isoformat(),
            'content': content,
            'agent_id': agent_id,
            'source': source.value,
            'current_agent': current_agent_id,
            'target_agent': target_agent_id
        })
        
        self.console.print(f"\n[green]✓ Message injected as {source.value}[/green]\n")
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
            
            if command in ["", "enter"]:
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
        
        return {
            'total_interventions': len(self.intervention_history),
            'edits': edit_count,
            'injections': inject_count,
            'skips': 0,  # No skip functionality in manual mode
            'history': self.intervention_history
        }
    
    def request_resume(self):
        """Request dialogue engine to clear pause state and continue flowing."""
        self.resume_requested = True
    
    def cleanup(self):
        """Clean up resources when conversation ends."""
        # No special cleanup needed for manual mode
        pass


class FlowingConductorMiddleware:
    """Flowing conductor mode - conversation flows until Space is pressed to pause."""
    
    def __init__(self, console: Console):
        """Initialize the flowing conductor middleware.
        
        Args:
            console: Rich console for terminal display
        """
        self.console = console
        self.intervention_history: List[Dict[str, Any]] = []
        self.turn_count = 0
        self.is_paused = False
        self.is_flowing = True
        self.pending_message = None
        self.pending_agent_name = None
        self.pending_target_agent_id = None
        self.conversation_history = []  # For back functionality
        self.convergence_calculator = None  # Will be set by dialogue engine
        self.resume_requested = False  # Communication with dialogue engine
        
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
        if self.is_flowing:
            # In flowing mode, status is shown in dialogue engine turn counter
            return
        else:
            # Paused mode controls
            controls = Text()
            controls.append("[", style="dim")
            controls.append("Enter", style="bold green")
            controls.append(": continue | ", style="dim")
            controls.append("n", style="bold cyan")
            controls.append(": step | ", style="dim")
            controls.append("e", style="bold yellow")
            controls.append(": edit | ", style="dim")
            controls.append("i", style="bold cyan")
            controls.append(": inject | ", style="dim")
            controls.append("b", style="bold blue")
            controls.append(": back | ", style="dim")
            controls.append("q", style="bold red")
            controls.append(": quit | ", style="dim")
            controls.append("?", style="bold")
            controls.append(": help", style="dim")
            controls.append("]", style="dim")
            
            self.console.print(controls)
        
    def display_help(self):
        """Display detailed help information."""
        help_table = Table(title="Flowing Conductor Mode Commands", show_header=True)
        help_table.add_column("Command", style="bold")
        help_table.add_column("Action")
        help_table.add_column("Description")
        
        help_table.add_row(
            "Ctrl+Z", 
            "Pause", 
            "Pause the flowing conversation (while flowing)"
        )
        help_table.add_row(
            "Enter", 
            "Continue", 
            "Resume flowing mode (while paused)"
        )
        help_table.add_row(
            "n", 
            "Step", 
            "Process one message and pause again"
        )
        help_table.add_row(
            "e", 
            "Edit", 
            "Modify the current message before sending"
        )
        help_table.add_row(
            "i", 
            "Inject", 
            "Insert a custom message into the conversation"
        )
        help_table.add_row(
            "b", 
            "Back", 
            "Go back to previous message (not yet implemented)"
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
            
        # Create modified message, preserving source attribution
        modified_message = Message(
            role=original_message.role,
            content=new_content,
            agent_id=original_message.agent_id,
            source=original_message.source
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
        
    def inject_message(self, current_agent_id: str, target_agent_id: str) -> Optional[Message]:
        """Allow user to inject a custom message.
        
        Args:
            current_agent_id: ID of the agent currently speaking
            target_agent_id: ID of the agent that will receive the message
            
        Returns:
            Injected message or None if cancelled
        """
        self.console.print(f"\n[cyan]Inject message:[/cyan]")
        
        # Simplified injection sources
        source_options = Table(show_header=False, box=None, padding=(0, 1))
        source_options.add_column("Num", style="bold cyan")
        source_options.add_column("Source")
        source_options.add_column("Description", style="dim")
        
        source_options.add_row("1", "External", "Intervention message (visible to both agents)")
        source_options.add_row("2", "Agent A", "Message as Agent A")
        source_options.add_row("3", "Agent B", "Message as Agent B")
        
        self.console.print(source_options)
        self.console.print()
        
        while True:
            source_choice = Prompt.ask("From", choices=["1", "2", "3"], default="1")
            
            if source_choice == "1":
                source = MessageSource.HUMAN  # Use HUMAN for external interventions
                agent_id = "external"
                role = "user"
                break
            elif source_choice == "2":
                source = MessageSource.AGENT_A
                agent_id = "agent_a"
                role = "assistant"
                break
            elif source_choice == "3":
                source = MessageSource.AGENT_B
                agent_id = "agent_b"
                role = "assistant"
                break
        
        # Get content
        self.console.print(f"\n[cyan]Message content (Ctrl+D when done, empty to cancel):[/cyan]")
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
            role=role,
            content=content,
            agent_id=agent_id,
            source=source
        )
        
        # Record the injection
        self.intervention_history.append({
            'type': 'inject',
            'turn': self.turn_count,
            'timestamp': datetime.now().isoformat(),
            'content': content,
            'agent_id': agent_id,
            'source': source.value,
            'current_agent': current_agent_id,
            'target_agent': target_agent_id
        })
        
        self.console.print(f"\n[green]✓ Message injected as {source.value}[/green]\n")
        return injected_message
        

    async def process_message(self, message: Message, agent_name: str, 
                            target_agent_id: str, turn: int) -> Optional[Message]:
        """Process a message with flowing conductor controls.
        
        Args:
            message: The message to process
            agent_name: Name of the agent sending the message
            target_agent_id: ID of the agent that will receive the message
            turn: Current turn number
            
        Returns:
            Processed message, None to skip, or raises exception to quit
        """
        self.turn_count = turn
        
        # Store pending message details
        self.pending_message = message
        self.pending_agent_name = agent_name
        self.pending_target_agent_id = target_agent_id
        
        # Check if paused (either manually paused or pause was requested)
        if self.is_paused:
            return await self._handle_paused_mode(message, agent_name, target_agent_id, turn)
        
        # In flowing mode, just return the message - clean and simple
        return message
    
    def pause(self):
        """Pause the flowing conductor (called by dialogue engine on Ctrl+Z)."""
        if self.is_flowing:
            self.is_paused = True
            self.is_flowing = False
            self.console.print("\n[yellow]🎼 Conductor paused - will enter control mode at next message[/yellow]")
    
    def _is_external_message(self, message: Message) -> bool:
        """Check if a message is an external/system message."""
        return message.agent_id in ["external", "system", "human", "mediator"]
    
    def request_resume(self):
        """Request dialogue engine to clear pause state and continue flowing."""
        self.resume_requested = True
    
    async def _handle_paused_mode(self, message: Message, agent_name: str, 
                                target_agent_id: str, turn: int) -> Optional[Message]:
        """Handle interactions when paused."""
        while True:
            # Display the pending message
            self.display_pending_message(message, agent_name, turn)
            
            # Display convergence trend if available
            self.display_convergence_trend()
            
            # Display controls
            self.display_controls()
            
            # Get user input
            command = Prompt.ask(">", default="").strip().lower()
            
            if command in ["", "enter"]:
                # Continue - resume flowing mode
                self.console.print("[green]→ Resuming flowing mode...[/green]\n")
                self.is_paused = False
                self.is_flowing = True
                return message
                
            elif command == "n":
                # Step - process one message and pause again
                self.console.print("[cyan]→ Stepping (will pause after next message)...[/cyan]\n")
                self.is_paused = True
                self.is_flowing = False
                return message
                
            elif command == "e":
                # Edit the message
                message = self.edit_message(message)
                # Loop back to show edited message
                
            elif command == "i":
                # Inject a message
                injected = self.inject_message(message.agent_id, target_agent_id)
                if injected:
                    if self._is_external_message(injected):
                        # For external messages, auto-resume after injection
                        self.console.print("\n[cyan]ℹ️  External message sent to both agents, resuming conversation...[/cyan]")
                        self.is_paused = False
                        self.is_flowing = True
                        self.request_resume()  # Signal dialogue engine to clear pause
                        return injected
                    else:
                        # For agent messages, keep existing paused behavior
                        self.console.print("\n[cyan]Message injected. Press Enter to continue...[/cyan]")
                    return injected
                # Otherwise loop back
                
            elif command == "b":
                # Back - not yet implemented
                self.console.print("[yellow]Back functionality not yet implemented[/yellow]\n")
                
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
        
        return {
            'total_interventions': len(self.intervention_history),
            'edits': edit_count,
            'injections': inject_count,
            'skips': 0,  # No skip functionality in flowing mode
            'history': self.intervention_history
        }
    
    def cleanup(self):
        """Clean up resources when conversation ends."""
        # No cleanup needed for simplified flowing conductor
        pass
    
    def display_convergence_trend(self):
        """Display convergence trend when paused."""
        if not self.convergence_calculator:
            return
            
        recent_history = self.convergence_calculator.get_recent_history(5)
        if not recent_history:
            return
            
        # Create the trend panel
        from rich.table import Table
        from rich.panel import Panel
        
        trend_table = Table(show_header=False, box=None)
        trend_table.add_column("Turn", style="dim")
        trend_table.add_column("Score")
        trend_table.add_column("Visual")
        
        for turn, score in recent_history:
            # Create visual bar
            bar_length = int(score * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            # Add warning emoji if above threshold
            warning = " ⚠️" if score >= 0.75 else ""
            
            trend_table.add_row(
                f"Turn {turn}:",
                f"{score:.2f}{warning}",
                f"[cyan]{bar}[/cyan]"
            )
        
        # Add trend summary
        trend = self.convergence_calculator.get_trend()
        trend_color = {
            "increasing": "red",
            "decreasing": "green", 
            "stable": "yellow",
            "fluctuating": "blue",
            "insufficient data": "dim"
        }.get(trend, "white")
        
        self.console.print(Panel(
            trend_table,
            title="[bold]Convergence Trend[/bold]",
            subtitle=f"[{trend_color}]Trend: {trend}[/{trend_color}]",
            border_style="cyan"
        ))