"""Metrics tracker for conversation analysis and convergence."""

from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

from ...core.types import Message
from ...analysis.convergence import ConvergenceCalculator
from ...metrics import calculate_turn_metrics, update_phase_detection
from .base import Component


class MetricsTracker(Component):
    """Tracks conversation metrics and convergence."""

    def __init__(self):
        """Initialize metrics tracking components."""
        self.convergence_calculator = ConvergenceCalculator()
        self.turn_metrics: Dict[str, List[Any]] = defaultdict(list)
        self.phase_detection: Dict[str, Optional[int]] = {
            "high_convergence_start": None,
            "emoji_phase_start": None,
            "symbolic_phase_start": None,
        }
        self.convergence_history: List[Dict[str, Any]] = []
        self.current_convergence = 0.0
        self.convergence_threshold = 0.75
        self.auto_paused_at_convergence = False

    def reset(self):
        """Reset all metrics for new conversation."""
        self.turn_metrics.clear()
        self.phase_detection = {
            "high_convergence_start": None,
            "emoji_phase_start": None,
            "symbolic_phase_start": None,
        }
        self.convergence_history.clear()
        self.current_convergence = 0.0
        self.auto_paused_at_convergence = False

    def update_metrics(self, message: Message, turn: int):
        """Update all metrics for a new message.

        Args:
            message: The new message
            turn: Current turn number
        """
        # Skip system messages
        if message.agent_id == "system":
            return

        # Calculate turn metrics
        metrics = calculate_turn_metrics(message.content)
        self.turn_metrics["message_lengths"].append(metrics["length"])
        self.turn_metrics["sentence_counts"].append(metrics["sentences"])
        self.turn_metrics["word_diversity"].append(metrics["word_diversity"])
        self.turn_metrics["emoji_density"].append(metrics["emoji_density"])

        # Update phase detection
        update_phase_detection(
            self.phase_detection,
            {
                "convergence": self.current_convergence,
                "emoji_density": metrics["emoji_density"],
            },
            turn + 1,
        )

    def calculate_convergence(self, messages: List[Message]) -> float:
        """Calculate current convergence score.

        Args:
            messages: All conversation messages

        Returns:
            Convergence score between 0 and 1
        """
        self.current_convergence = self.convergence_calculator.calculate(messages)
        return self.current_convergence

    def update_convergence_history(self, turn: int):
        """Add current convergence to history.

        Args:
            turn: Current turn number
        """
        self.convergence_history.append(
            {
                "turn": turn + 1,
                "score": self.current_convergence,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def check_convergence_pause(self) -> bool:
        """Check if should auto-pause due to high convergence.

        Returns:
            True if should pause, False otherwise
        """
        if self.current_convergence >= 0.90 and not self.auto_paused_at_convergence:
            self.auto_paused_at_convergence = True
            return True
        elif self.current_convergence < 0.85:
            # Reset flag if convergence drops (hysteresis)
            self.auto_paused_at_convergence = False
        return False

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get all current metrics for saving.

        Returns:
            Dictionary containing all metrics
        """
        return {
            "convergence_history": self.convergence_history,
            "turn_metrics": self.turn_metrics,
            "structural_patterns": {
                "current_convergence": self.current_convergence,
                "convergence_threshold": self.convergence_threshold,
                "auto_paused_at_convergence": self.auto_paused_at_convergence,
            },
            "phase_detection": self.phase_detection,
        }

    def get_display_metrics(self) -> Dict[str, Any]:
        """Get metrics formatted for display.

        Returns:
            Dictionary with display-ready metrics
        """
        return {
            "convergence": self.current_convergence,
            # Add other display metrics as needed
        }

    def set_convergence_threshold(self, threshold: float):
        """Update convergence threshold.

        Args:
            threshold: New threshold value (0-1)
        """
        self.convergence_threshold = threshold
