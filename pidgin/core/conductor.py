"""Event-driven conversation orchestrator.

Future: Event replay will enable resume by replaying events.jsonl
No need for separate checkpoint files - events ARE the state.
"""

import time
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console

from ..analysis.convergence import ConvergenceCalculator
from ..config.config import get_config
from ..config.system_prompts import get_system_prompts
from ..io.logger import get_logger
from ..io.output_manager import OutputManager
from ..ui.display_utils import DisplayUtils, dim
from .conversation_lifecycle import ConversationLifecycle
from .event_bus import EventBus
from .events import MessageCompleteEvent
from .interrupt_handler import InterruptHandler
from .message_handler import MessageHandler
from .name_coordinator import NameCoordinator
from .rate_limiter import StreamingRateLimiter
from .turn_executor import TurnExecutor
from .types import Agent, Conversation

logger = get_logger("conductor")


class Conductor:
    """Event-driven conversation orchestrator."""

    def __init__(
        self,
        output_manager: OutputManager,
        user_interaction=None,
        console: Optional[Console] = None,
        bus: Optional[EventBus] = None,
        base_providers: Optional[Dict] = None,
        transcript_manager=None,
        convergence_threshold_override: Optional[float] = None,
        convergence_action_override: Optional[str] = None,
    ):
        """Initialize the Conductor.

        Args:
            output_manager: Manager for output files
            user_interaction: Optional user interaction handler
            console: Optional console for display output
            bus: Optional shared EventBus
            base_providers: Pre-configured providers
            transcript_manager: Optional transcript manager
            convergence_threshold_override: Override convergence threshold
            convergence_action_override: Override convergence action
        """
        # Core components
        self.output_manager = output_manager
        self.user_interaction = user_interaction
        self.console = console if console else Console()
        self.config = get_config()

        # Get convergence weights from config
        conv_config = self.config.get_convergence_config()
        convergence_weights = conv_config.get("weights", None)

        # Initialize specialized handlers
        self.interrupt_handler = InterruptHandler(bus or EventBus(), console)
        self.name_coordinator = NameCoordinator()
        self.rate_limiter = StreamingRateLimiter()
        self.convergence_calculator = ConvergenceCalculator(weights=convergence_weights)

        # Lifecycle manager needs to be set up
        self.lifecycle = ConversationLifecycle(console)

        # Message handler needs references
        self.message_handler = MessageHandler(
            bus or EventBus(), self.rate_limiter, self.name_coordinator, console
        )

        # Turn executor needs everything
        self.turn_executor = TurnExecutor(
            bus or EventBus(),
            self.message_handler,
            self.convergence_calculator,
            self.config,
            time.time(),  # Will be updated at conversation start
        )

        # Set convergence overrides
        self.turn_executor.set_convergence_overrides(
            convergence_threshold_override, convergence_action_override
        )

        # Store bus and providers
        self.bus = bus
        self.base_providers = base_providers or {}
        self.lifecycle.set_providers(self.base_providers)

        # State
        self.current_conv_dir = None
        self.start_time = None

        # Transcript manager (optional)
        self.transcript_manager = transcript_manager

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
        conversation_id: Optional[str] = None,
        prompt_tag: Optional[str] = None,
        branch_messages: Optional[list] = None,
    ) -> Conversation:
        """Run a complete conversation using events.

        Args:
            agent_a: First agent
            agent_b: Second agent
            initial_prompt: Starting prompt
            max_turns: Maximum number of turns
            display_mode: Display mode (normal, quiet, chat)
            show_timing: Whether to show timing information
            choose_names: Whether agents should choose their own names
            awareness_a: Awareness level for agent A (none, basic, firm, research)
            awareness_b: Awareness level for agent B (none, basic, firm, research)
            temperature_a: Temperature setting for agent A (0.0-2.0)
            temperature_b: Temperature setting for agent B (0.0-2.0)
            conversation_id: Optional pre-assigned conversation ID

        Returns:
            The completed conversation
        """
        # Setup phase
        conv_id, conv_dir = await self._setup_conversation(
            agent_a,
            agent_b,
            initial_prompt,
            display_mode,
            show_timing,
            choose_names,
            conversation_id,
            prompt_tag,
        )

        # Initialize conversation
        conversation = await self._initialize_conversation(
            conv_id,
            conv_dir,
            agent_a,
            agent_b,
            initial_prompt,
            awareness_a,
            awareness_b,
            choose_names,
            temperature_a,
            temperature_b,
            max_turns,
            prompt_tag,
            branch_messages,
        )

        # Run conversation turns
        final_turn, end_reason = await self._run_conversation_turns(
            conversation, agent_a, agent_b, max_turns
        )

        # Finalize conversation
        await self._finalize_conversation(
            conversation, conv_id, conv_dir, final_turn, max_turns, end_reason
        )

        return conversation

    async def _setup_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        display_mode: str,
        show_timing: bool,
        choose_names: bool,
        conversation_id: Optional[str],
        prompt_tag: Optional[str],
    ) -> tuple[str, Path]:
        """Setup conversation infrastructure."""
        # Initialize name mode
        self.name_coordinator.initialize_name_mode(choose_names)
        self.name_coordinator.assign_display_names(agent_a, agent_b)

        # Create output directory
        conv_id, conv_dir = self.output_manager.create_conversation_dir(conversation_id)
        self.current_conv_dir = conv_dir  # Store for transcript saving

        # Initialize event system
        await self.lifecycle.initialize_event_system(
            conv_dir,
            display_mode,
            show_timing,
            {"agent_a": agent_a, "agent_b": agent_b},
            self.bus,
            None,  # db_store
            prompt_tag,
        )

        # Update components with bus
        self._update_components_with_bus()

        return conv_id, conv_dir

    def _update_components_with_bus(self):
        """Update all components with the event bus."""
        # Get the bus from lifecycle (it may have created one)
        self.bus = self.lifecycle.bus

        # Update all components with the bus
        self.interrupt_handler.bus = self.bus
        self.message_handler.bus = self.bus
        self.turn_executor.bus = self.bus

        # Set display filter if created
        if self.lifecycle.display_filter:
            self.message_handler.set_display_filter(self.lifecycle.display_filter)

        # Subscribe to message completions
        self.bus.subscribe(
            MessageCompleteEvent, self.message_handler.handle_message_complete
        )
        
        # Subscribe to context limit events
        from .events import ContextLimitEvent
        self.bus.subscribe(
            ContextLimitEvent, self.message_handler.handle_context_limit
        )

    async def _initialize_conversation(
        self,
        conv_id: str,
        conv_dir: Path,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        awareness_a: str,
        awareness_b: str,
        choose_names: bool,
        temperature_a: Optional[float],
        temperature_b: Optional[float],
        max_turns: int,
        prompt_tag: Optional[str],
        branch_messages: Optional[list] = None,
    ) -> Conversation:
        """Initialize conversation and emit start events."""
        # Create conversation
        conversation = self.lifecycle.create_conversation(
            conv_id, agent_a, agent_b, initial_prompt, branch_messages
        )

        # Get system prompts and add initial messages
        system_prompts, custom_awareness = get_system_prompts(
            awareness_a=awareness_a,
            awareness_b=awareness_b,
            choose_names=choose_names,
            model_a_name=agent_a.model,
            model_b_name=agent_b.model,
        )
        # Only add initial messages if not branching
        if not branch_messages:
            await self.lifecycle.add_initial_messages(
                conversation, system_prompts, initial_prompt, prompt_tag
            )

        # Store custom awareness for turn injection
        self.turn_executor.set_custom_awareness(custom_awareness)

        # Set up interrupt handling
        self.interrupt_handler.setup_interrupt_handler()
        self.interrupt_handler.interrupt_requested = False  # Reset flag

        # Emit start events
        self.start_time = time.time()
        self.turn_executor.start_time = self.start_time
        await self.lifecycle.emit_start_events(
            conversation,
            agent_a,
            agent_b,
            initial_prompt,
            max_turns,
            system_prompts,
            temperature_a,
            temperature_b,
            prompt_tag,
        )

        return conversation

    async def _run_conversation_turns(
        self, conversation: Conversation, agent_a: Agent, agent_b: Agent, max_turns: int
    ) -> tuple[int, Optional[str]]:
        """Run all conversation turns."""
        final_turn = 0
        end_reason = None

        try:
            for turn_num in range(max_turns):
                self.interrupt_handler.current_turn = turn_num

                # Check for interrupt before starting turn
                if self.interrupt_handler.interrupt_requested:
                    await self.interrupt_handler.handle_pause(conversation)
                    if not await self.interrupt_handler.should_continue(conversation):
                        end_reason = "interrupted"
                        break

                turn = await self.turn_executor.run_single_turn(
                    conversation, turn_num, agent_a, agent_b, self.interrupt_handler
                )
                if turn is None:
                    # Turn executor signaled to stop
                    final_turn = (
                        turn_num  # Use current turn_num since this turn was attempted
                    )
                    end_reason = self.turn_executor.stop_reason or "interrupted"
                    if self.console:
                        display = DisplayUtils(self.console)
                        display.dim(
                            f"Turn returned None, stopping due to: {end_reason}"
                        )
                    break
                final_turn = turn_num

        finally:
            # Always restore original handler
            self.interrupt_handler.restore_interrupt_handler()

        return final_turn, end_reason

    async def _finalize_conversation(
        self,
        conversation: Conversation,
        conv_id: str,
        conv_dir: Path,
        final_turn: int,
        max_turns: int,
        end_reason: Optional[str],
    ):
        """Finalize conversation with end events and cleanup."""
        # Always emit end event with appropriate reason
        await self.lifecycle.emit_end_event_with_reason(
            conversation, final_turn, max_turns, self.start_time, end_reason
        )

        # Note: We no longer load single chats to a database
        # JSONL files are the single source of truth


    def check_interrupt(self) -> bool:
        """Check if interrupt was requested during message.

        Returns:
            True if interrupt was requested
        """
        return self.interrupt_handler.check_interrupt()
