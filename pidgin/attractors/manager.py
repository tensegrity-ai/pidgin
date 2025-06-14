"""Attractor detection manager.

This module manages attractor detection for conversations.
ONLY uses structural detection because that's what actually works.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import json
from datetime import datetime

from .structural import StructuralPatternDetector

logger = logging.getLogger(__name__)


class AttractorManager:
    """
    Manages attractor detection for conversations.
    ONLY uses structural detection because that's what actually works.
    """

    def __init__(self, config: Dict):
        # Structural detection is THE ONLY reliable method
        self.structural_detector = StructuralPatternDetector(
            window_size=config.get("window_size", 10),
            threshold=config.get("threshold", 3),
        )
        self.enabled = config.get("enabled", True)
        self.action = config.get("on_detection", "stop")
        self.check_interval = config.get("check_interval", 5)
        self.detection_history: list[dict[str, Any]] = []

    def check(
        self, messages: List[str], turn_count: int, show_progress: bool = True
    ) -> Optional[Dict]:
        """
        Check if conversation has entered an attractor.
        Returns detection details if found, None otherwise.
        """
        if not self.enabled:
            return None

        # Only check at intervals to avoid excessive computation
        if turn_count % self.check_interval != 0:
            return None

        # ONLY check structural patterns - everything else is noise
        result = self.structural_detector.detect_attractor(messages)

        if result:
            # Enhance result with metadata
            result["turn_detected"] = turn_count
            result["timestamp"] = datetime.now().isoformat()
            result["action"] = self.action

            self.detection_history.append(result)

        return result

    def save_analysis(self, transcript_path: Path) -> Optional[Path]:
        """Save attractor analysis alongside transcript."""
        if not self.detection_history:
            return None

        analysis_path = transcript_path.with_suffix(".attractor")

        # Ensure parent directory exists
        analysis_path.parent.mkdir(parents=True, exist_ok=True)

        analysis = {
            "detection_count": len(self.detection_history),
            "first_detection": self.detection_history[0]
            if self.detection_history
            else None,
            "all_detections": self.detection_history,
            "summary": self._generate_summary(),
        }

        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2)

        return analysis_path

    def _generate_summary(self) -> Dict:
        """Generate a summary of attractor patterns."""
        if not self.detection_history:
            return {"status": "no_attractors_detected"}

        first = self.detection_history[0]

        return {
            "status": "attractor_detected",
            "first_detection_turn": first["turn_detected"],
            "primary_type": first["type"],
            "pattern_description": first["description"],
            "total_detections": len(self.detection_history),
            "confidence_range": {
                "min": min(d["confidence"] for d in self.detection_history),
                "max": max(d["confidence"] for d in self.detection_history),
                "avg": sum(d["confidence"] for d in self.detection_history)
                / len(self.detection_history),
            },
        }
