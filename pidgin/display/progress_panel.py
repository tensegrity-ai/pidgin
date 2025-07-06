# pidgin/display/progress_panel.py
"""Centered progress panel for experiment monitoring."""

from typing import Optional, Tuple, List
from rich.panel import Panel
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.columns import Columns

from ..cli.constants import NORD_GREEN, NORD_YELLOW, NORD_RED, NORD_CYAN, NORD_BLUE


class ProgressPanel:
    """Manages the centered progress display for experiments."""
    
    def __init__(self, experiment_name: str, agent_a: str, agent_b: str, 
                 conv_total: int = 1, turn_total: int = 50):
        """Initialize progress panel.
        
        Args:
            experiment_name: Name of the experiment
            agent_a: First agent name/model
            agent_b: Second agent name/model
            conv_total: Total conversations to run
            turn_total: Total turns per conversation
        """
        self.experiment_name = experiment_name
        self.agent_a = agent_a
        self.agent_b = agent_b
        
        # Progress tracking
        self.conv_current = 1
        self.conv_total = conv_total
        self.conv_completed = 0
        self.conv_failed = 0
        
        self.turn_current = 0
        self.turn_total = turn_total
        
        # Convergence tracking
        self.convergence_score = 0.0
        self.convergence_history: List[float] = []
        self.completed_convergences: List[float] = []
        
        # Token/cost tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        self.tokens_per_conv: List[int] = []
        
        # Display state
        self.waiting_for = None
        self.last_error = None
        
    def update_conversation(self, current: int, completed: int, failed: int):
        """Update conversation progress."""
        self.conv_current = current
        self.conv_completed = completed
        self.conv_failed = failed
        
    def update_turn(self, current: int):
        """Update turn progress."""
        self.turn_current = current
        
    def update_convergence(self, score: float):
        """Update convergence score."""
        self.convergence_history.append(score)
        self.convergence_score = score
        
    def add_tokens(self, tokens: int, cost: float):
        """Add token usage."""
        self.total_tokens += tokens
        self.total_cost += cost
        
    def complete_conversation(self, tokens: int, final_convergence: float):
        """Mark a conversation as complete."""
        self.tokens_per_conv.append(tokens)
        self.completed_convergences.append(final_convergence)
        
    def set_waiting(self, agent: Optional[str] = None):
        """Set waiting state."""
        self.waiting_for = agent
        
    def get_convergence_trend(self) -> str:
        """Calculate convergence trend indicator."""
        if len(self.convergence_history) < 2:
            return ""
            
        current = self.convergence_score
        previous = self.convergence_history[-2]
        delta = current - previous
        
        if abs(delta) < 0.01:
            return "→"
        elif delta > 0.05:
            return "↑↑"
        elif delta > 0:
            return "↑"
        elif delta < -0.05:
            return "↓↓"
        else:
            return "↓"
    
    def get_convergence_color(self) -> str:
        """Get color for convergence score."""
        if self.convergence_score > 0.7:
            return NORD_RED
        elif self.convergence_score > 0.5:
            return NORD_YELLOW
        else:
            return NORD_GREEN
            
    def format_tokens(self) -> str:
        """Format token count nicely."""
        if self.total_tokens < 1000:
            return f"{self.total_tokens} tokens"
        elif self.total_tokens < 10000:
            return f"{self.total_tokens/1000:.1f}k tokens"
        else:
            return f"{self.total_tokens/1000:.0f}k tokens"
            
    def make_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Create a progress bar string."""
        if total == 0:
            return "░" * width
            
        filled = int(width * current / total)
        bar = "█" * filled + "░" * (width - filled)
        percent = int(100 * current / total)
        return f"{bar} {percent:3d}%"
        
    def render(self) -> Panel:
        """Render the progress panel."""
        # Header
        header = Text(f"{self.agent_a} ↔ {self.agent_b}: {self.experiment_name}", 
                     style="bold", justify="center")
        
        lines = [header, Text()]  # Empty line after header
        
        # Single vs multiple conversation display
        if self.conv_total == 1:
            # Single conversation - just show turn progress
            turn_bar = self.make_progress_bar(self.turn_current, self.turn_total)
            
            # Build turn line with convergence
            turn_line = Text()
            turn_line.append(f"Turn  {self.turn_current:2d}/{self.turn_total:2d}  ")
            turn_line.append(turn_bar)
            
            if self.convergence_score > 0:
                trend = self.get_convergence_trend()
                conv_color = self.get_convergence_color()
                turn_line.append(f"  Conv: {self.convergence_score:.2f} {trend}", 
                               style=conv_color)
            
            turn_line.justify = "center"
            lines.append(turn_line)
            
        else:
            # Multiple conversations - show both progress bars
            conv_bar = self.make_progress_bar(self.conv_completed, self.conv_total)
            conv_line = Text(f"Conv  {self.conv_completed:2d}/{self.conv_total:2d}  {conv_bar}")
            conv_line.justify = "center"
            lines.append(conv_line)
            
            turn_bar = self.make_progress_bar(self.turn_current, self.turn_total)
            turn_line = Text()
            turn_line.append(f"Turn  {self.turn_current:2d}/{self.turn_total:2d}  ")
            turn_line.append(turn_bar)
            
            if self.convergence_score > 0:
                trend = self.get_convergence_trend()
                conv_color = self.get_convergence_color()
                turn_line.append(f"  Conv: {self.convergence_score:.2f} {trend}", 
                               style=conv_color)
            
            turn_line.justify = "center"
            lines.append(turn_line)
        
        lines.append(Text())  # Empty line
        
        # Token/cost display
        tokens_str = self.format_tokens()
        cost_str = f"${self.total_cost:.2f}"
        
        if self.conv_total > 1 and self.tokens_per_conv:
            # Show per-conversation average
            avg_tokens = sum(self.tokens_per_conv) / len(self.tokens_per_conv)
            token_line = Text(f"{tokens_str} ({cost_str}) • ~{int(avg_tokens)} tok/conv", 
                            justify="center")
        else:
            token_line = Text(f"{tokens_str} ({cost_str})", justify="center")
        
        lines.append(token_line)
        
        # Completion summary for multiple conversations
        if self.conv_total > 1 and (self.conv_completed > 0 or self.conv_failed > 0):
            lines.append(Text())
            
            summary_parts = []
            if self.conv_completed > 0 and self.completed_convergences:
                avg_conv = sum(self.completed_convergences) / len(self.completed_convergences)
                summary_parts.append(f"[{NORD_GREEN}]{self.conv_completed} complete: avg {avg_conv:.2f}[/{NORD_GREEN}]")
            if self.conv_failed > 0:
                summary_parts.append(f"[{NORD_RED}]{self.conv_failed} failed[/{NORD_RED}]")
                
            summary = Text.from_markup(" ".join(summary_parts), justify="center")
            lines.append(summary)
        
        # Create panel
        content = Text("\n").join(lines) if lines else Text()
        
        panel = Panel(
            content,
            width=65,
            padding=(1, 2),
            border_style=NORD_CYAN,
            style="on grey15"
        )
        
        # Add waiting indicator below panel if needed
        if self.waiting_for:
            from rich.console import Group
            status = Text(f"⠋ Waiting for {self.waiting_for}'s response...", 
                         style="dim", justify="center")
            # Add blank lines for spacing
            return Align.center(Group(Text(), Text(), panel, Text(), status), vertical="middle")
        
        # Add blank lines for spacing
        from rich.console import Group
        return Align.center(Group(Text(), Text(), panel), vertical="middle")