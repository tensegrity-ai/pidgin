"""Event-driven conversation orchestrator.

Future: Event replay will enable resume by replaying events.jsonl
No need for separate checkpoint files - events ARE the state.
"""

import asyncio
import re
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from .event_bus import EventBus
from ..ui.event_logger import EventLogger
from ..ui.display_filter import DisplayFilter
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
    InterruptRequestEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    RateLimitPaceEvent,
    TokenUsageEvent,
)
from ..config.models import get_model_config
from ..io.output_manager import OutputManager
from ..providers.event_wrapper import EventAwareProvider
from ..config.system_prompts import get_system_prompts
from ..io.transcripts import TranscriptManager
from .types import Agent, Conversation, Message
from ..ui.user_interaction import UserInteractionHandler, TimeoutDecision
from ..analysis.convergence import ConvergenceCalculator
from ..config.config import get_config
from .rate_limiter import StreamingRateLimiter


class Conductor:
    """Event-driven conversation orchestrator."""

    # Nord colors for consistency
    NORD_YELLOW = "#ebcb8b"  # nord13
    NORD_RED = "#bf616a"  # nord11

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

        # Interrupt handling
        self.interrupt_requested = False
        self.paused = False
        self._original_sigint_handler = None

        # Convergence tracking
        self.convergence_calculator = ConvergenceCalculator()
        self.config = get_config()
        self.current_turn = 0

        # Rate limiting
        self.rate_limiter = StreamingRateLimiter()

    def _setup_interrupt_handler(self, conversation_id: str):
        """Set up Ctrl+C as interrupt trigger."""

        def handle_interrupt(signum, frame):
            if not self.interrupt_requested:  # Prevent multiple interrupts
                self.interrupt_requested = True
                # Show immediate feedback
                if self.console:
                    self.console.print(
                        f"\n[{self.NORD_YELLOW}]⏸ Interrupt received, pausing after current message...[/{self.NORD_YELLOW}]"
                    )

        # Save original handler and set our own
        self._original_sigint_handler = signal.signal(signal.SIGINT, handle_interrupt)

    def _restore_interrupt_handler(self):
        """Restore original interrupt handler."""
        if self._original_sigint_handler:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
            self._original_sigint_handler = None

    async def _handle_interrupt_request(self, conversation_id: str):
        """Handle interrupt request."""
        await self.bus.emit(
            InterruptRequestEvent(
                conversation_id=conversation_id,
                turn_number=self.current_turn,
                interrupt_source="user",
            )
        )

    async def _handle_pause(self, conversation: Conversation):
        """Handle conversation pause."""
        # Emit interrupt request event
        await self._handle_interrupt_request(conversation.id)

        # Show pause notification
        self.user_interaction.show_pause_notification()

        # Emit paused event
        await self.bus.emit(
            ConversationPausedEvent(
                conversation_id=conversation.id,
                turn_number=self.current_turn,
                paused_during="between_turns",
            )
        )

        self.paused = True

    async def _should_continue(self, conversation: Conversation) -> bool:
        """Check if conversation should continue after pause."""
        # Get user decision
        decision = self.user_interaction.get_pause_decision()

        if decision == "continue":
            # Emit resumed event
            await self.bus.emit(
                ConversationResumedEvent(
                    conversation_id=conversation.id, turn_number=self.current_turn
                )
            )
            self.interrupt_requested = False
            self.paused = False
            return True
        elif decision == "exit":
            return False
        else:
            # For now, just handle continue/exit
            return False

    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        max_turns: int = 10,
        display_mode: str = "normal",
        show_timing: bool = False,
        choose_names: bool = False,
        awareness_a: str = "basic",
        awareness_b: str = "basic",
        temperature_a: Optional[float] = None,
        temperature_b: Optional[float] = None,
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
            awareness_a: Awareness level for agent A (none, basic, firm, research)
            awareness_b: Awareness level for agent B (none, basic, firm, research)
            temperature_a: Temperature setting for agent A (0.0-2.0)
            temperature_b: Temperature setting for agent B (0.0-2.0)

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
        await self._initialize_event_system(
            conv_dir,
            display_mode,
            show_timing,
            {"agent_a": agent_a, "agent_b": agent_b},
        )

        # Create conversation
        conversation = self._create_conversation(
            conv_id, agent_a, agent_b, initial_prompt
        )

        # Get system prompts and add initial messages
        system_prompts = get_system_prompts(
            awareness_a=awareness_a,
            awareness_b=awareness_b,
            choose_names=choose_names,
            model_a_name=agent_a.model,
            model_b_name=agent_b.model,
        )
        await self._add_initial_messages(conversation, system_prompts, initial_prompt)

        # Set up interrupt handling
        self._setup_interrupt_handler(conversation.id)
        self.interrupt_requested = False  # Reset flag

        try:
            # Emit start events
            self.start_time = time.time()
            await self._emit_start_events(
                conversation,
                agent_a,
                agent_b,
                initial_prompt,
                max_turns,
                system_prompts,
                temperature_a,
                temperature_b,
            )

            # Run turns
            final_turn = 0
            for turn_num in range(max_turns):
                self.current_turn = turn_num

                # Check for interrupt before starting turn
                if self.interrupt_requested:
                    await self._handle_pause(conversation)
                    if not await self._should_continue(conversation):
                        break

                turn = await self.run_single_turn(
                    conversation, turn_num, agent_a, agent_b
                )
                if turn is None:
                    break
                final_turn = turn_num

            # Emit end event and cleanup
            await self._emit_end_event(
                conversation, final_turn, max_turns, self.start_time
            )

        finally:
            # Always restore original handler
            self._restore_interrupt_handler()

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
            conversation.id, agent_a, turn_number, conversation.messages
        )
        if agent_a_message is None:
            return None

        conversation.messages.append(agent_a_message)

        # Get Agent B message
        agent_b_message = await self._get_agent_message(
            conversation.id, agent_b, turn_number, conversation.messages
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

        # Calculate convergence
        convergence_score = self.convergence_calculator.calculate(conversation.messages)

        # Emit turn complete with convergence
        await self.bus.emit(
            TurnCompleteEvent(
                conversation_id=conversation.id,
                turn_number=turn_number,
                turn=turn,
                convergence_score=convergence_score,
            )
        )

        # Check convergence threshold
        conv_config = self.config.get_convergence_config()
        threshold = conv_config.get("convergence_threshold", 0.85)
        action = conv_config.get("convergence_action", "stop")

        if convergence_score >= threshold:
            if action == "stop":
                # Stop the conversation
                await self.bus.emit(
                    ConversationEndEvent(
                        conversation_id=conversation.id,
                        reason="high_convergence",
                        total_turns=turn_number + 1,
                        duration_ms=int((time.time() - self.start_time) * 1000),
                    )
                )
                return None  # Signal to stop
            elif action == "warn":
                # Just log a warning (display already shows it)
                pass

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
        timeout: float = 60.0,
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
        # Estimate payload size for rate limiting
        payload_tokens = self._estimate_payload_tokens(
            conversation_history, agent.model
        )
        avg_response_tokens = 500  # Conservative estimate
        total_estimated = payload_tokens + avg_response_tokens

        # Determine provider for rate limiting
        provider = self._get_provider_name(agent.model)

        # Acquire rate limit slot (may wait)
        wait_time = await self.rate_limiter.acquire(provider, total_estimated)

        # Emit rate limit event if we waited
        if wait_time > 0.1:
            await self.bus.emit(
                RateLimitPaceEvent(
                    conversation_id=conversation_id,
                    provider=provider,
                    wait_time=wait_time,
                    reason="mixed",  # Could be either request or token rate
                )
            )

            # Show pacing indicator if we have display
            if hasattr(self, "display_filter") and self.display_filter:
                self.display_filter.show_pacing_indicator(provider, wait_time)

        # Track request timing
        request_start = time.time()

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
                temperature=agent.temperature,
            )
        )

        # Create interrupt check task
        async def check_interrupt():
            """Check for interrupt flag."""
            while not self.interrupt_requested:
                await asyncio.sleep(0.1)  # Check every 100ms
            return True

        interrupt_task = asyncio.create_task(check_interrupt())
        message_task = asyncio.create_task(asyncio.wait_for(future, timeout=timeout))

        # Wait for response with timeout OR interrupt
        try:
            # Wait for EITHER message completion OR interrupt
            done, pending = await asyncio.wait(
                [message_task, interrupt_task], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            if interrupt_task in done and interrupt_task.result():
                # Interrupted! Handle pause
                await self.bus.emit(
                    ConversationPausedEvent(
                        conversation_id=conversation_id,
                        turn_number=turn_number,
                        paused_during=f"waiting_for_{agent.id}",
                    )
                )

                # Wait for the message to complete anyway
                try:
                    message = await future
                    return message
                except:
                    return None
            else:
                # Message completed normally
                message = await message_task

                # Record request completion for rate limiting
                request_duration = time.time() - request_start
                if message:
                    # Estimate actual tokens (rough)
                    actual_tokens = len(message.content) // 4 + payload_tokens
                    self.rate_limiter.record_request_complete(
                        provider, actual_tokens, request_duration
                    )

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
                            f"[{self.NORD_RED}]{agent.display_name} still not responding. Skipping turn.[/{self.NORD_RED}]"
                        )
                    return None

    def _estimate_payload_tokens(self, messages: List[Message], model: str) -> int:
        """Estimate tokens in conversation history.

        Args:
            messages: Conversation messages
            model: Model name for provider-specific estimation

        Returns:
            Estimated token count
        """
        total = 0
        for msg in messages:
            # Rough estimates by model type
            if "gpt" in model.lower():
                total += len(msg.content) // 3.5  # GPT tokenization
            else:
                total += len(msg.content) // 3.8  # Claude/others
        return int(total)

    def _get_provider_name(self, model: str) -> str:
        """Get provider name from model.

        Args:
            model: Model name or alias

        Returns:
            Provider name (anthropic, openai, etc)
        """
        config = get_model_config(model)
        if config:
            return config.provider

        # Fallback pattern matching
        model_lower = model.lower()
        if "claude" in model_lower:
            return "anthropic"
        elif model_lower.startswith("gpt") or model_lower.startswith("o"):
            return "openai"
        elif "gemini" in model_lower:
            return "google"
        elif "grok" in model_lower:
            return "xai"
        else:
            return "openai"  # Default

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
        bracket_match = re.search(r"\[(\w{2,8})\]", message_content)
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

    async def _initialize_event_system(
        self,
        conv_dir: Path,
        display_mode: str,
        show_timing: bool,
        agents: Dict[str, Agent],
    ):
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
        # Create wrapped providers for agent_a and agent_b
        self.wrapped_providers = {}

        # Map providers to agents based on model
        agent_a = agents["agent_a"]
        agent_b = agents["agent_b"]

        # Find provider for agent_a
        for model_id, provider in self.base_providers.items():
            if model_id == agent_a.model:
                self.wrapped_providers["agent_a"] = EventAwareProvider(
                    provider, self.bus, "agent_a"
                )
                break

        # Find provider for agent_b
        for model_id, provider in self.base_providers.items():
            if model_id == agent_b.model:
                self.wrapped_providers["agent_b"] = EventAwareProvider(
                    provider, self.bus, "agent_b"
                )
                break

        # Subscribe to message completions
        self.bus.subscribe(MessageCompleteEvent, self._handle_message_complete)

    def _create_conversation(
        self, conv_id: str, agent_a: Agent, agent_b: Agent, initial_prompt: str
    ) -> Conversation:
        """Create and initialize conversation object."""
        conversation = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt=initial_prompt,
        )
        conversation.id = conv_id  # Use our generated ID
        return conversation

    async def _add_initial_messages(
        self,
        conversation: Conversation,
        system_prompts: Dict[str, str],
        initial_prompt: str,
    ):
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
            Message(
                role="user", content=f"[HUMAN]: {initial_prompt}", agent_id="researcher"
            )
        )

        conversation.messages.extend(messages_to_add)

    async def _emit_start_events(
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

    async def _emit_end_event(
        self,
        conversation: Conversation,
        final_turn: int,
        max_turns: int,
        start_time: float,
    ):
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
