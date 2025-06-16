"""Progress tracker for conversation turn management."""

from typing import Optional
from .base import Component


class ProgressTracker(Component):
    """Tracks conversation progress and turn state."""

    def __init__(self, max_turns: int, start_turn: int = 0):
        """Initialize progress tracker.

        Args:
            max_turns: Maximum number of turns allowed
            start_turn: Starting turn number (for resumed conversations)
        """
        self.max_turns = max_turns
        self.current_turn = start_turn
        self.completed = False
        self.completion_reason: Optional[str] = None

    def reset(self):
        """Reset progress state for new conversation."""
        self.current_turn = 0
        self.completed = False
        self.completion_reason = None

    def should_continue(self) -> bool:
        """Check if conversation should continue.

        Returns:
            True if should continue, False if completed or reached max turns
        """
        return self.current_turn < self.max_turns and not self.completed

    def complete_turn(self):
        """Mark current turn as completed and increment counter."""
        self.current_turn += 1

        # Check if we've reached max turns
        if self.current_turn >= self.max_turns:
            self.mark_stopped("max_turns_reached")

    def mark_stopped(self, reason: str = "manual"):
        """Mark conversation as stopped.

        Args:
            reason: Reason for stopping (e.g., "high_convergence", "error", "intervention")
        """
        self.completed = True
        self.completion_reason = reason

    def get_progress_info(self) -> dict:
        """Get current progress information.

        Returns:
            Dictionary with progress details
        """
        return {
            "current_turn": self.current_turn,
            "max_turns": self.max_turns,
            "completed": self.completed,
            "completion_reason": self.completion_reason,
            "turns_remaining": self.max_turns - self.current_turn,
            "progress_percentage": (self.current_turn / self.max_turns * 100)
            if self.max_turns > 0
            else 0,
        }
