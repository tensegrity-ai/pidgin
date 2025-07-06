# pidgin/ui/progress_display.py
"""Progress display handler for centered panel view."""

import asyncio
from typing import Dict, Optional
from datetime import datetime

from rich.console import Console
from rich.live import Live

from ..core.event_bus import EventBus
from ..core.events import (
    Event,
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageCompleteEvent,
    APIErrorEvent,
    ErrorEvent,
    MessageRequestEvent,
)
from ..display.progress_panel import ProgressPanel


# Model pricing per 1k tokens (input, output)
MODEL_PRICING = {
    # OpenAI
    "gpt-4": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    
    # Anthropic
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-2.1": {"input": 0.008, "output": 0.024},
    
    # Google
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.00025, "output": 0.001},
    
    # Default for unknown models
    "default": {"input": 0.001, "output": 0.003}
}


class ProgressDisplay:
    """Handles progress panel display for conversations."""
    
    def __init__(self, bus: EventBus, console: Console, agents: Dict, 
                 experiment_name: str = None, total_conversations: int = 1):
        """Initialize progress display.
        
        Args:
            bus: Event bus to subscribe to
            console: Rich console for output
            agents: Dict mapping agent_id to Agent objects
            experiment_name: Name of the experiment
            total_conversations: Total conversations to run
        """
        self.bus = bus
        self.console = console
        self.agents = agents
        self.live = None
        self.panel = None
        
        # Extract agent names
        agent_a = agents.get("agent_a")
        agent_b = agents.get("agent_b")
        agent_a_name = agent_a.display_name if agent_a else "Agent A"
        agent_b_name = agent_b.display_name if agent_b else "Agent B"
        
        # Use experiment name or create default
        if not experiment_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"conversation_{timestamp}"
        
        # Initialize progress panel
        self.panel = ProgressPanel(
            experiment_name=experiment_name,
            agent_a=agent_a_name,
            agent_b=agent_b_name,
            conv_total=total_conversations
        )
        
        # Subscribe to events
        bus.subscribe(ConversationStartEvent, self.handle_conversation_start)
        bus.subscribe(TurnStartEvent, self.handle_turn_start)
        bus.subscribe(TurnCompleteEvent, self.handle_turn_complete)
        bus.subscribe(MessageCompleteEvent, self.handle_message_complete)
        bus.subscribe(MessageRequestEvent, self.handle_message_request)
        bus.subscribe(ConversationEndEvent, self.handle_conversation_end)
        bus.subscribe(ErrorEvent, self.handle_error)
        bus.subscribe(APIErrorEvent, self.handle_error)
        
        # Track current models for pricing
        self.current_models = {
            "agent_a": agent_a.model if agent_a else None,
            "agent_b": agent_b.model if agent_b else None
        }
        
        # Track tokens per conversation
        self.current_conv_tokens = 0
        
    async def start(self):
        """Start the live display."""
        self.live = Live(
            self.panel.render(),
            console=self.console,
            refresh_per_second=0.5,
            screen=True,  # Clear screen for centering
            vertical_overflow="visible"
        )
        self.live.start()
        
    def update(self):
        """Update the display."""
        if self.live:
            self.live.update(self.panel.render())
            
    def stop(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()
            self.live = None
    
    def handle_conversation_start(self, event: ConversationStartEvent):
        """Handle conversation start event."""
        self.panel.turn_total = event.max_turns
        self.panel.turn_current = 0
        self.current_conv_tokens = 0
        self.update()
        
    def handle_turn_start(self, event: TurnStartEvent):
        """Handle turn start event."""
        self.panel.update_turn(event.turn_number)
        self.update()
        
    def handle_turn_complete(self, event: TurnCompleteEvent):
        """Handle turn complete event."""
        if event.convergence_score is not None:
            self.panel.update_convergence(event.convergence_score)
        self.update()
        
    def handle_message_request(self, event: MessageRequestEvent):
        """Handle message request event."""
        # Show who we're waiting for
        agent_name = self.agents.get(event.agent_id, {}).display_name or event.agent_id
        self.panel.set_waiting(agent_name)
        self.update()
        
    def handle_message_complete(self, event: MessageCompleteEvent):
        """Handle message complete event."""
        # Clear waiting state
        self.panel.set_waiting(None)
        
        # Get tokens from event
        tokens = event.tokens_used
            
        # Get model for pricing
        model = self.current_models.get(event.agent_id)
        if model:
            cost = self.calculate_cost(tokens, model, is_output=True)
            self.panel.add_tokens(int(tokens), cost)
            self.current_conv_tokens += int(tokens)
            
        self.update()
        
    def handle_conversation_end(self, event: ConversationEndEvent):
        """Handle conversation end event."""
        # Update conversation completion
        if self.panel.conv_total > 1:
            self.panel.conv_completed += 1
            self.panel.conv_current = self.panel.conv_completed + 1
            
            # Add final convergence score
            if hasattr(event, 'final_convergence') and event.final_convergence:
                self.panel.complete_conversation(
                    self.current_conv_tokens, 
                    event.final_convergence
                )
        
        self.update()
        
    def handle_error(self, event):
        """Handle error events."""
        if self.panel.conv_total > 1:
            self.panel.conv_failed += 1
        self.panel.last_error = str(getattr(event, 'error', 'Unknown error'))
        self.update()
        
    def calculate_cost(self, tokens: int, model: str, is_output: bool = True) -> float:
        """Calculate cost for tokens.
        
        Args:
            tokens: Number of tokens
            model: Model name
            is_output: Whether these are output tokens (vs input)
            
        Returns:
            Cost in dollars
        """
        # Find pricing for model
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        
        # Calculate cost
        rate_key = "output" if is_output else "input"
        cost_per_1k = pricing[rate_key]
        cost = (tokens / 1000.0) * cost_per_1k
        
        return cost