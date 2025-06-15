"""Event-driven conversation orchestrator.

Future: Event replay will enable resume by replaying events.jsonl
No need for separate checkpoint files - events ARE the state.
"""

import asyncio
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from .event_bus import EventBus
from .event_logger import EventLogger
from .display_filter import DisplayFilter
from .events import (
    Event,
    Turn,
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    MessageRequestEvent,
    MessageCompleteEvent,
    SystemPromptEvent,
    ErrorEvent,
    ProviderTimeoutEvent,
)
from .models import get_model_config
from .output_manager import OutputManager
from .providers.event_wrapper import EventAwareProvider
from .system_prompts import get_system_prompts
from .transcripts import TranscriptManager
from .types import Agent, Conversation, Message
from .user_interaction import UserInteractionHandler, TimeoutDecision


class Conductor:
    """Event-driven conversation orchestrator."""

    def __init__(
        self,
        providers: Dict[str, any],
        output_manager: Optional[OutputManager] = None,
        console: Optional[Console] = None,
    ):
        """Initialize conductor with providers and output manager.

        Args:
            providers: Dict mapping agent_id to provider instances (not wrapped)
            output_manager: Optional output manager for saving conversations
            console: Optional console for output (used by event logger)
        """
        self.base_providers = providers  # Store unwrapped providers
        self.output_manager = output_manager or OutputManager()
        self.console = console or Console()
        self.bus = None  # Will be created per conversation
        self.wrapped_providers = None  # Will be created when bus is available
        self.event_logger = None  # Will be created with bus
        
        # User interaction handler
        self.user_interaction = UserInteractionHandler(console)

        # Track message completion
        self.pending_messages: Dict[str, asyncio.Future] = {}

        # Name choosing mode
        self.choose_names_mode = False
        self.agent_chosen_names: Dict[str, str] = {}
        
        # Track conversation directory for transcript saving
        self.current_conv_dir: Optional[Path] = None

    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        max_turns: int = 10,
        display_mode: str = "normal",
        show_timing: bool = False,
        choose_names: bool = False,
        stability_level: int = 2,
    ) -> Conversation:
        """Run a complete conversation using events.

        Args:
            agent_a: First agent
            agent_b: Second agent
            initial_prompt: Starting prompt
            max_turns: Maximum number of turns
            display_mode: Display mode (normal, quiet, verbose)
            show_timing: Whether to show timing information
            choose_names: Whether agents should choose their own names
            stability_level: System prompt stability level (0-4)

        Returns:
            The completed conversation
        """
        # Initialize name mode
        self._initialize_name_mode(choose_names)
        self._assign_display_names(agent_a, agent_b)
        
        # Create output directory
        conv_id, conv_dir = self.output_manager.create_conversation_dir()
        self.current_conv_dir = conv_dir  # Store for transcript saving
        
        # Initialize event system
        await self._initialize_event_system(conv_dir, display_mode, show_timing, 
                                           {"agent_a": agent_a, "agent_b": agent_b})
        
        # Create conversation
        conversation = self._create_conversation(conv_id, agent_a, agent_b, initial_prompt)
        
        # Get system prompts and add initial messages
        system_prompts = get_system_prompts(stability_level, choose_names)
        await self._add_initial_messages(conversation, system_prompts, initial_prompt)
        
        # Emit start events
        start_time = time.time()
        await self._emit_start_events(conversation, agent_a, agent_b, 
                                     initial_prompt, max_turns, system_prompts)
        
        # Run turns
        final_turn = 0
        for turn_num in range(max_turns):
            turn = await self.run_single_turn(conversation, turn_num, agent_a, agent_b)
            if turn is None:
                break
            final_turn = turn_num
        
        # Emit end event and cleanup
        await self._emit_end_event(conversation, final_turn, max_turns, start_time)
        
        # Save transcripts
        await self._save_transcripts(conversation)
        
        return conversation

    async def run_single_turn(
        self,
        conversation: Conversation,
        turn_number: int,
        agent_a: Agent,
        agent_b: Agent,
    ) -> Optional[Turn]:
        """Run a single conversation turn.

        Args:
            conversation: The conversation object
            turn_number: Current turn number
            agent_a: First agent
            agent_b: Second agent

        Returns:
            The completed turn or None if interrupted
        """
        # Emit turn start
        await self.bus.emit(
            TurnStartEvent(
                conversation_id=conversation.id,
                turn_number=turn_number,
            )
        )

        # Get Agent A message
        agent_a_message = await self._get_agent_message(
            conversation.id, 
            agent_a, 
            turn_number, 
            conversation.messages
        )
        if agent_a_message is None:
            return None
            
        conversation.messages.append(agent_a_message)

        # Get Agent B message
        agent_b_message = await self._get_agent_message(
            conversation.id, 
            agent_b, 
            turn_number, 
            conversation.messages
        )
        if agent_b_message is None:
            return None
            
        conversation.messages.append(agent_b_message)

        # Build turn
        turn = Turn(
            agent_a_message=agent_a_message,
            agent_b_message=agent_b_message,
            intervention=None,  # Not handling interventions yet
        )

        # Emit turn complete
        await self.bus.emit(
            TurnCompleteEvent(
                conversation_id=conversation.id,
                turn_number=turn_number,
                turn=turn,
            )
        )

        return turn

    def _handle_message_complete(self, event: MessageCompleteEvent) -> None:
        """Handle message completion events.

        Args:
            event: The message complete event
        """
        # Extract self-chosen name if in choose_names mode
        if self.choose_names_mode and event.agent_id not in self.agent_chosen_names:
            chosen_name = self._extract_chosen_name(event.message.content)
            if chosen_name:
                self.agent_chosen_names[event.agent_id] = chosen_name
                # Update agent display name
                if hasattr(self, "display_filter"):
                    if event.agent_id == "agent_a":
                        self.display_filter.agents["agent_a"].display_name = chosen_name
                    elif event.agent_id == "agent_b":
                        self.display_filter.agents["agent_b"].display_name = chosen_name

        # Check if we're waiting for this message
        if event.agent_id in self.pending_messages:
            future = self.pending_messages.pop(event.agent_id)
            if not future.done():
                future.set_result(event.message)

    async def _get_agent_message(
        self, 
        conversation_id: str,
        agent: Agent, 
        turn_number: int,
        conversation_history: List[Message],
        timeout: float = 60.0
    ) -> Optional[Message]:
        """Get a single agent's message with timeout handling.
        
        Args:
            conversation_id: ID of the current conversation
            agent: The agent to get a message from
            turn_number: Current turn number
            conversation_history: Full conversation history
            timeout: Initial timeout in seconds
            
        Returns:
            The agent's message or None if skipped
        """
        # Create future for this agent's response
        future = asyncio.Future()
        self.pending_messages[agent.id] = future
        
        # Request message
        await self.bus.emit(
            MessageRequestEvent(
                conversation_id=conversation_id,
                agent_id=agent.id,
                turn_number=turn_number,
                conversation_history=conversation_history.copy(),
            )
        )
        
        # Wait for response with timeout
        try:
            message = await asyncio.wait_for(future, timeout=timeout)
            return message
        except asyncio.TimeoutError:
            # Emit timeout event
            await self.bus.emit(
                ProviderTimeoutEvent(
                    conversation_id=conversation_id,
                    error_type="timeout",
                    error_message=f"{agent.display_name} did not respond within {timeout} seconds",
                    context=f"Turn {turn_number}",
                    agent_id=agent.id,
                    timeout_seconds=timeout,
                )
            )
            
            # Get user decision
            decision = self.user_interaction.get_timeout_decision(agent.display_name)
            
            if decision == TimeoutDecision.SKIP:
                return None
            elif decision == TimeoutDecision.END:
                raise KeyboardInterrupt("User requested end")
            else:  # WAIT
                try:
                    # Wait longer (double the timeout)
                    message = await asyncio.wait_for(future, timeout=timeout * 2)
                    return message
                except asyncio.TimeoutError:
                    if self.user_interaction.console:
                        self.user_interaction.console.print(
                            f"[red]{agent.display_name} still not responding. Skipping turn.[/red]"
                        )
                    return None

    def _extract_chosen_name(self, message_content: str) -> Optional[str]:
        """Extract self-chosen name from first response"""
        # Look for patterns like:
        # "I'll go by X" or "I'll go by [X]"
        # "Call me X" or "Call me [X]"
        # "I'll be X" or "I'll be [X]"
        # "My name is X" or "My name is [X]"
        # "I choose X" or "I choose [X]"
        # Also handle: "I am [X]", "[X] here", etc.

        # First try specific patterns
        patterns = [
            r"I'll (?:go by|be|choose) \[?(\w{2,8})\]?",
            r"Call me \[?(\w{2,8})\]?",
            r"My name is \[?(\w{2,8})\]?",
            r"I (?:choose|select) \[?(\w{2,8})\]?",
            r"I am \[?(\w{2,8})\]?",
            r"^\[?(\w{2,8})\]? here",  # "[Name] here" at start of message
        ]

        for pattern in patterns:
            match = re.search(pattern, message_content, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1)
                # Clean up the name - remove any remaining brackets
                name = name.strip("[]")
                return name

        # Fallback - look for any quoted short name (with or without brackets)
        quote_match = re.search(r'["\']\[?(\w{2,8})\]?["\']', message_content)
        if quote_match:
            name = quote_match.group(1)
            # Clean up the name - remove any remaining brackets
            name = name.strip("[]")
            return name

        # Additional fallback - look for standalone bracketed names
        bracket_match = re.search(r'\[(\w{2,8})\]', message_content)
        if bracket_match:
            return bracket_match.group(1)

        return None
    
    def _initialize_name_mode(self, choose_names: bool):
        """Set up name choosing mode."""
        self.choose_names_mode = choose_names
        self.agent_chosen_names = {}
        
    def _assign_display_names(self, agent_a: Agent, agent_b: Agent):
        """Assign display names to agents based on their models."""
        config_a = get_model_config(agent_a.model)
        config_b = get_model_config(agent_b.model)

        if config_a and config_b:
            # Store the model shortnames
            agent_a.model_shortname = config_a.shortname
            agent_b.model_shortname = config_b.shortname
            
            if config_a.shortname == config_b.shortname:
                # Same model - add numbers
                agent_a.display_name = f"{config_a.shortname}-1"
                agent_b.display_name = f"{config_b.shortname}-2"
            else:
                # Different models - use shortnames directly
                agent_a.display_name = config_a.shortname
                agent_b.display_name = config_b.shortname
        else:
            # Fallback to agent IDs
            agent_a.display_name = "Agent A"
            agent_b.display_name = "Agent B"
            agent_a.model_shortname = None
            agent_b.model_shortname = None
            
    async def _initialize_event_system(self, conv_dir: Path, display_mode: str, 
                                      show_timing: bool, agents: Dict[str, Agent]):
        """Initialize EventBus and display components."""
        # Create event bus with logging
        event_log_path = conv_dir / "events.jsonl"
        self.bus = EventBus(event_log_path)
        await self.bus.start()

        # Create event logger and display filter based on mode
        if display_mode == "verbose":
            # Use original event logger for verbose mode
            self.event_logger = EventLogger(self.bus, self.console)
        else:
            # Use display filter for normal/quiet modes
            self.display_filter = DisplayFilter(
                self.console, display_mode, show_timing, agents
            )
            self.bus.subscribe(Event, self.display_filter.handle_event)
            # Still create event logger but without console output (for file logging)
            self.event_logger = EventLogger(self.bus, None)

        # Wrap providers with event awareness now that bus exists
        self.wrapped_providers = {
            agent_id: EventAwareProvider(provider, self.bus, agent_id)
            for agent_id, provider in self.base_providers.items()
        }

        # Subscribe to message completions
        self.bus.subscribe(MessageCompleteEvent, self._handle_message_complete)
        
    def _create_conversation(self, conv_id: str, agent_a: Agent, agent_b: Agent, 
                            initial_prompt: str) -> Conversation:
        """Create and initialize conversation object."""
        conversation = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt=initial_prompt,
        )
        conversation.id = conv_id  # Use our generated ID
        return conversation
        
    async def _add_initial_messages(self, conversation: Conversation, 
                                   system_prompts: Dict[str, str], 
                                   initial_prompt: str):
        """Add system prompts and initial message to conversation."""
        system_prompt_a = system_prompts["agent_a"]
        system_prompt_b = system_prompts["agent_b"]

        # Add system prompt and initial message
        messages_to_add = []
        if system_prompt_a:  # Only add if non-empty (chaos mode has empty prompts)
            messages_to_add.append(
                Message(role="system", content=system_prompt_a, agent_id="system")
            )
        messages_to_add.append(
            Message(role="user", content=f"[HUMAN]: {initial_prompt}", agent_id="researcher")
        )
        
        conversation.messages.extend(messages_to_add)
        
    async def _emit_start_events(self, conversation: Conversation, agent_a: Agent, 
                                agent_b: Agent, initial_prompt: str, max_turns: int,
                                system_prompts: Dict[str, str]):
        """Emit all start-of-conversation events."""
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
            
    async def _emit_end_event(self, conversation: Conversation, final_turn: int, 
                             max_turns: int, start_time: float):
        """Emit conversation end event and cleanup."""
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit end event
        await self.bus.emit(
            ConversationEndEvent(
                conversation_id=conversation.id,
                reason="max_turns" if final_turn == max_turns - 1 else "completed",
                total_turns=final_turn + 1,
                duration_ms=duration_ms,
            )
        )

        # Stop the event bus to ensure all events are written
        await self.bus.stop()
        
    async def _save_transcripts(self, conversation: Conversation):
        """Save conversation transcripts to output directory.
        
        Args:
            conversation: The completed conversation
        """
        if self.current_conv_dir:
            transcript_manager = TranscriptManager(self.current_conv_dir)
            # TODO: Gather metrics if needed
            await transcript_manager.save(conversation)