"""Conversation lifecycle management."""

import time
from pathlib import Path
from typing import Dict, Optional

from .event_bus import EventBus
from .types import Agent, Conversation, Message
from .events import (
    Event,
    ConversationStartEvent,
    ConversationEndEvent,
    SystemPromptEvent,
    MessageCompleteEvent,
)
from ..ui.tail_display import TailDisplay
from ..ui.display_filter import DisplayFilter
from ..providers.event_wrapper import EventAwareProvider
from ..database.event_store import EventStore


class ConversationLifecycle:
    """Manages conversation initialization, start/end events, and cleanup."""
    
    def __init__(self, console=None):
        """Initialize lifecycle manager.
        
        Args:
            console: Optional console for output
        """
        self.console = console
        self.bus = None
        self._owns_bus = False
        self.db_store = None
        self._owns_db_store = False
        self.event_logger = None
        self.display_filter = None
        self.base_providers = {}
        self.wrapped_providers = {}
        self._end_event_emitted = False
    
    def set_providers(self, base_providers):
        """Set base providers for wrapping.
        
        Args:
            base_providers: Dict of agent_id -> provider
        """
        self.base_providers = base_providers
    
    async def initialize_event_system(
        self,
        conv_dir: Path,
        display_mode: str,
        show_timing: bool,
        agents: Dict[str, Agent],
        existing_bus=None,
        db_store=None,
    ):
        """Initialize EventBus and display components.
        
        Args:
            conv_dir: Conversation directory
            display_mode: Display mode (normal, quiet, verbose)
            show_timing: Whether to show timing
            agents: Dict of agent_id -> Agent
            existing_bus: Optional existing EventBus to use
            db_store: Optional existing EventStore to use
        """
        # Handle database store
        if db_store is None:
            # Create database connection first
            # Use in-memory database for tests
            db_path = conv_dir / "conversation.db" if conv_dir else ":memory:"
            self.db_store = EventStore(db_path)
            self._owns_db_store = True
        else:
            self.db_store = db_store
            self._owns_db_store = False
        
        if existing_bus is None:
            # We don't have a bus yet, create one with db_store and event logging
            # Create events directory next to conversation directory
            event_log_dir = conv_dir.parent / "events"
            self.bus = EventBus(self.db_store, event_log_dir=event_log_dir)
            self._owns_bus = True
            await self.bus.start()
        else:
            # Using shared bus
            self.bus = existing_bus
        
        # Create event logger and display filter based on mode
        if display_mode == "tail":
            # Use tail display for showing raw events
            self.tail_display = TailDisplay(self.bus, self.console)
            self.progress_display = None
        elif display_mode == "verbose":
            # Use verbose display for minimal message viewing
            from ..ui.verbose_display import VerboseDisplay
            self.verbose_display = VerboseDisplay(self.bus, self.console, agents)
            self.progress_display = None
        elif display_mode == "progress":
            # Use progress panel display
            from ..ui.progress_display import ProgressDisplay
            self.progress_display = ProgressDisplay(
                self.bus, self.console, agents,
                experiment_name=conv_dir.parent.name
            )
            # Start the live display
            import asyncio
            asyncio.create_task(self.progress_display.start())
            # Still create event logger for file logging
            self.tail_display = TailDisplay(self.bus, None)
            self.display_filter = None
        else:
            # Use display filter for normal/quiet modes
            if self.console is not None and display_mode != 'none':
                self.display_filter = DisplayFilter(
                    self.console, display_mode, show_timing, agents
                )
                self.bus.subscribe(Event, self.display_filter.handle_event)
            else:
                self.display_filter = None
            # Still create event logger but without console output (for file logging)
            self.tail_display = TailDisplay(self.bus, None)
            self.progress_display = None
        
        # Wrap providers with event awareness now that bus exists
        # Create wrapped providers for agent_a and agent_b
        self.wrapped_providers = {}
        
        if "agent_a" in self.base_providers:
            self.wrapped_providers["agent_a"] = EventAwareProvider(
                self.base_providers["agent_a"], self.bus, "agent_a"
            )
        
        if "agent_b" in self.base_providers:
            self.wrapped_providers["agent_b"] = EventAwareProvider(
                self.base_providers["agent_b"], self.bus, "agent_b"
            )
    
    def create_conversation(
        self, conv_id: str, agent_a: Agent, agent_b: Agent, initial_prompt: str
    ) -> Conversation:
        """Create and initialize conversation object.
        
        Args:
            conv_id: Conversation ID
            agent_a: First agent
            agent_b: Second agent
            initial_prompt: Initial prompt
            
        Returns:
            New conversation object
        """
        conversation = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt=initial_prompt,
        )
        conversation.id = conv_id  # Use our generated ID
        return conversation
    
    async def add_initial_messages(
        self,
        conversation: Conversation,
        system_prompts: Dict[str, str],
        initial_prompt: str,
    ):
        """Add system prompts and initial message to conversation.
        
        Args:
            conversation: Conversation to add messages to
            system_prompts: Dict of agent_id -> system prompt
            initial_prompt: Initial user prompt
        """
        system_prompt_a = system_prompts["agent_a"]
        system_prompt_b = system_prompts["agent_b"]
        
        # Add system prompt and initial message
        messages_to_add = []
        if system_prompt_a:  # Only add if non-empty (chaos mode has empty prompts)
            messages_to_add.append(
                Message(role="system", content=system_prompt_a, agent_id="system")
            )
        messages_to_add.append(
            Message(
                role="user", content=f"[HUMAN]: {initial_prompt}", agent_id="researcher"
            )
        )
        
        conversation.messages.extend(messages_to_add)
    
    async def emit_start_events(
        self,
        conversation: Conversation,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        max_turns: int,
        system_prompts: Dict[str, str],
        temperature_a: Optional[float],
        temperature_b: Optional[float],
    ):
        """Emit all start-of-conversation events.
        
        Args:
            conversation: Conversation object
            agent_a: First agent
            agent_b: Second agent
            initial_prompt: Initial prompt
            max_turns: Maximum turns
            system_prompts: System prompts dict
            temperature_a: Temperature for agent A
            temperature_b: Temperature for agent B
        """
        # Emit conversation start event
        await self.bus.emit(
            ConversationStartEvent(
                conversation_id=conversation.id,
                agent_a_model=agent_a.model,
                agent_b_model=agent_b.model,
                initial_prompt=initial_prompt,
                max_turns=max_turns,
                agent_a_display_name=agent_a.display_name,
                agent_b_display_name=agent_b.display_name,
                temperature_a=temperature_a,
                temperature_b=temperature_b,
            )
        )
        
        # Emit system prompt events for both agents
        system_prompt_a = system_prompts["agent_a"]
        system_prompt_b = system_prompts["agent_b"]
        
        if system_prompt_a:  # Only emit if non-empty
            await self.bus.emit(
                SystemPromptEvent(
                    conversation_id=conversation.id,
                    agent_id="agent_a",
                    prompt=system_prompt_a,
                    agent_display_name=agent_a.display_name,
                )
            )
        
        if system_prompt_b:  # Only emit if non-empty
            await self.bus.emit(
                SystemPromptEvent(
                    conversation_id=conversation.id,
                    agent_id="agent_b",
                    prompt=system_prompt_b,
                    agent_display_name=agent_b.display_name,
                )
            )
    
    async def emit_end_event_with_reason(
        self,
        conversation: Conversation,
        final_turn: int,
        max_turns: int,
        start_time: float,
        reason: Optional[str] = None,
    ):
        """Emit conversation end event with specific reason and cleanup.
        
        Args:
            conversation: Conversation object
            final_turn: Last turn number completed
            max_turns: Maximum turns allowed
            start_time: Conversation start time
            reason: Optional specific reason for ending
        """
        # Check if we already emitted an end event
        if self._end_event_emitted:
            if self.console:
                self.console.print("[dim]Warning: Attempted to emit ConversationEndEvent twice[/dim]")
            # Still run cleanup
            await self.cleanup()
            return
        
        # Mark that we've emitted the end event
        self._end_event_emitted = True
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Determine end reason if not provided
        if not reason:
            if final_turn + 1 >= max_turns:
                reason = "max_turns_reached"
            else:
                reason = "interrupted"
        
        # Emit end event
        await self.bus.emit(
            ConversationEndEvent(
                conversation_id=conversation.id,
                reason=reason,
                total_turns=final_turn + 1,
                duration_ms=duration_ms,
            )
        )
        
        await self.cleanup()
    
    async def emit_end_event(
        self,
        conversation: Conversation,
        final_turn: int,
        max_turns: int,
        start_time: float,
    ):
        """Emit conversation end event and cleanup.
        
        Args:
            conversation: Conversation object
            final_turn: Last turn number completed
            max_turns: Maximum turns allowed
            start_time: Conversation start time
        """
        await self.emit_end_event_with_reason(
            conversation, final_turn, max_turns, start_time, None
        )
    
    async def cleanup(self):
        """Clean up resources without emitting end event."""
        # Stop progress display if active
        if hasattr(self, 'progress_display') and self.progress_display:
            self.progress_display.stop()
        
        # Stop event bus if we own it
        if self._owns_bus and self.bus:
            await self.bus.stop()
        
        # Close db store if we own it
        if self._owns_db_store and self.db_store:
            # Close the database connection
            if hasattr(self.db_store, 'db') and self.db_store.db:
                await self.db_store.db.close()
    
    async def save_transcripts(self, conversation: Conversation, output_manager, conv_dir: Path):
        """Save conversation transcripts.
        
        Args:
            conversation: Conversation to save
            output_manager: Output manager for saving
            conv_dir: Conversation directory
        """
        if output_manager and conv_dir:
            # The output manager saves files, not transcripts directly
            # Transcripts are saved via the event log which has already been written
            # TODO: Gather metrics if needed
            pass