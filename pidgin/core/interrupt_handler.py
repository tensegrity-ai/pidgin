"""Interrupt handling for conversations."""

import signal
from typing import Optional

from rich.console import Console

from .events import (
    ConversationPausedEvent,
    ConversationResumedEvent,
    InterruptRequestEvent,
)
from .types import Conversation


class InterruptHandler:
    """Handles interrupt signals and conversation pausing."""

    def __init__(self, bus, console: Optional[Console] = None):
        """Initialize interrupt handler.

        Args:
            bus: Event bus for emitting interrupt events
            console: Optional console for user feedback
        """
        self.bus = bus
        self.console = console
        self.interrupt_requested = False
        self.paused = False
        self.current_turn = 0
        self._original_sigint_handler = None

    def setup_interrupt_handler(self):
        """Set up Ctrl+C as interrupt trigger."""

        def handle_interrupt(signum, frame):
            if not self.interrupt_requested:  # Prevent multiple interrupts
                self.interrupt_requested = True
                # Show immediate feedback
                if self.console:
                    from ..ui.display_utils import DisplayUtils

                    display = DisplayUtils(self.console)
                    self.console.print()  # Add spacing
                    display.warning(
                        "⏸ Interrupt received, pausing after current message...",
                        use_panel=False,
                    )

        # Save original handler and set our own
        self._original_sigint_handler = signal.signal(signal.SIGINT, handle_interrupt)

    def restore_interrupt_handler(self):
        """Restore original interrupt handler."""
        if self._original_sigint_handler:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
            self._original_sigint_handler = None

    async def handle_interrupt_request(self, conversation_id: str):
        """Handle interrupt request."""
        await self.bus.emit(
            InterruptRequestEvent(
                conversation_id=conversation_id,
                turn_number=self.current_turn,
                interrupt_source="user",
            )
        )

    async def handle_pause(self, conversation: Conversation):
        """Handle conversation pause."""
        # Emit interrupt request event
        await self.handle_interrupt_request(conversation.id)

        # Show pause notification
        # Pause notification removed

        # Emit paused event
        await self.bus.emit(
            ConversationPausedEvent(
                conversation_id=conversation.id,
                turn_number=self.current_turn,
                paused_during="between_turns",
            )
        )

        self.paused = True

    async def should_continue(self, conversation: Conversation) -> bool:
        """Check if conversation should continue after pause."""
        # Get user decision
        decision = "exit"  # Always exit on pause

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

    def check_interrupt(self) -> bool:
        """Check if interrupt was requested during message.

        Returns:
            True if interrupt was requested
        """
        return self.interrupt_requested
