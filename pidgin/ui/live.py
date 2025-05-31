"""Live conversation view using Rich."""
from datetime import datetime
from typing import Dict, Any, Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.syntax import Syntax

from pidgin.core.experiment import Experiment
from pidgin.core.conversation import ConversationEvent


class LiveConversationView:
    """Live view for ongoing conversations."""
    
    def __init__(self, experiment: Experiment):
        self.experiment = experiment
        self.console = Console()
        self.live: Optional[Live] = None
        
        # State
        self.current_speaker = None
        self.current_message = ""
        self.last_event: Optional[ConversationEvent] = None
        self.event_data: Dict[str, Any] = {}
        self.start_time = datetime.now()
        
        # UI Components
        self.layout = self._create_layout()
    
    def _create_layout(self) -> Layout:
        """Create the layout structure."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=5)
        )
        
        layout["main"].split_row(
            Layout(name="conversation", ratio=3),
            Layout(name="sidebar", ratio=1)
        )
        
        return layout
    
    def get_display(self) -> Layout:
        """Get the current display layout."""
        # Update all sections
        self.layout["header"].update(self._render_header())
        self.layout["conversation"].update(self._render_conversation())
        self.layout["sidebar"].update(self._render_sidebar())
        self.layout["footer"].update(self._render_footer())
        
        return self.layout
    
    def _render_header(self) -> Panel:
        """Render the header section."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
        
        header_text = Text()
        header_text.append("🧪 ", style="bold")
        header_text.append(self.experiment.config.name, style="bold cyan")
        header_text.append(f"  •  Turn {self.experiment.current_turn}/{self.experiment.config.max_turns}")
        header_text.append(f"  •  {elapsed_str}", style="dim")
        
        return Panel(header_text, box=None, style="on dark_blue")
    
    def _render_conversation(self) -> Panel:
        """Render the conversation section."""
        # Get recent conversation history
        recent_turns = self.experiment.conversation_history[-10:]  # Last 10 turns
        
        conversation_group = []
        
        for turn in recent_turns:
            speaker = turn.get("speaker", "Unknown")
            content = turn.get("content", "")
            turn_num = turn.get("turn", 0)
            
            # Determine speaker style
            if "Claude" in speaker:
                speaker_style = "bold blue"
                bubble_style = "blue"
            elif "GPT" in speaker:
                speaker_style = "bold green"
                bubble_style = "green"
            elif "Gemini" in speaker:
                speaker_style = "bold red"
                bubble_style = "red"
            else:
                speaker_style = "bold yellow"
                bubble_style = "yellow"
            
            # Create message panel
            message_text = Text()
            message_text.append(f"[{turn_num}] ", style="dim")
            message_text.append(speaker, style=speaker_style)
            message_text.append("\n")
            
            # Truncate long messages
            if len(content) > 300:
                message_text.append(content[:300] + "...", style="white")
            else:
                message_text.append(content, style="white")
            
            conversation_group.append(Panel(
                message_text,
                border_style=bubble_style,
                box=Panel.ROUNDED,
                padding=(0, 1)
            ))
        
        # Add current message if speaking
        if self.current_speaker and self.current_message:
            current_text = Text()
            current_text.append(self.current_speaker, style="bold cyan")
            current_text.append(" is typing...\n", style="dim")
            current_text.append(self.current_message, style="white dim")
            
            conversation_group.append(Panel(
                current_text,
                border_style="cyan",
                box=Panel.ROUNDED,
                padding=(0, 1)
            ))
        
        return Panel(
            Group(*conversation_group) if conversation_group else "[dim]Waiting for conversation to start...[/dim]",
            title="💬 Conversation",
            border_style="bright_blue"
        )
    
    def _render_sidebar(self) -> Panel:
        """Render the sidebar with experiment info."""
        # Participants table
        participants_table = Table(show_header=False, box=None, padding=(0, 1))
        participants_table.add_column("Role", style="cyan")
        participants_table.add_column("Model")
        
        for i, llm in enumerate(self.experiment.llms):
            role = f"Agent {i+1}" if not self.experiment.config.meditation_mode else "Meditator"
            participants_table.add_row(role, llm.name)
        
        # Metrics
        metrics_text = Text()
        metrics_text.append("Metrics\n", style="bold")
        metrics_text.append(f"Tokens: {self.experiment.metrics.total_tokens:,}\n")
        
        if self.experiment.config.compression_enabled:
            ratio = self.experiment.metrics.compression_ratio
            compression_pct = (1 - ratio) * 100
            metrics_text.append(f"Compression: {compression_pct:.1f}%\n")
        
        if self.experiment.metrics.symbols_emerged:
            metrics_text.append(f"Symbols: {len(self.experiment.metrics.symbols_emerged)}")
        
        # Status
        status_color = {
            "running": "green",
            "paused": "yellow",
            "completed": "blue",
            "failed": "red"
        }.get(str(self.experiment.status), "white")
        
        status_text = Text()
        status_text.append("Status: ", style="bold")
        status_text.append(str(self.experiment.status).upper(), style=f"bold {status_color}")
        
        sidebar_content = Group(
            Panel(participants_table, title="👥 Participants", border_style="dim"),
            Panel(metrics_text, title="📊 Metrics", border_style="dim"),
            Panel(status_text, title="🔄 Status", border_style="dim")
        )
        
        return Panel(sidebar_content, title="ℹ️ Info", border_style="bright_blue")
    
    def _render_footer(self) -> Panel:
        """Render the footer with controls and events."""
        # Controls
        controls = Text()
        controls.append("Controls: ", style="bold")
        controls.append("[P]ause  ", style="cyan")
        controls.append("[R]esume  ", style="green")
        controls.append("[S]top  ", style="red")
        controls.append("[I]ntervene", style="yellow")
        
        # Last event
        event_text = Text()
        if self.last_event:
            event_text.append("Last Event: ", style="bold")
            event_text.append(self.last_event, style="dim")
            
            if self.last_event == ConversationEvent.SYMBOL_DETECTED:
                symbol = self.event_data.get("symbol", "")
                event_text.append(f" - '{symbol}'", style="cyan")
        
        footer_content = Group(controls, event_text)
        
        return Panel(footer_content, title="🎮 Controls", border_style="dim")
    
    def update_event(self, event: ConversationEvent, data: Dict[str, Any]):
        """Update the view with a new event."""
        self.last_event = event
        self.event_data = data
        
        if event == ConversationEvent.TURN_START:
            self.current_speaker = data.get("speaker")
            self.current_message = ""
        
        elif event == ConversationEvent.MESSAGE_GENERATED:
            self.current_speaker = None
            self.current_message = ""
        
        # Force refresh if live
        if self.live:
            self.live.update(self.get_display())
    
    def update_streaming_message(self, token: str):
        """Update with a streaming token."""
        self.current_message += token
        
        if self.live:
            self.live.update(self.get_display())