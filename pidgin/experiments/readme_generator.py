"""Generate README files for experiment directories."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..io.logger import get_logger

logger = get_logger("readme_generator")


class ExperimentReadmeGenerator:
    """Generates README.md files for experiment directories."""

    def __init__(self, experiment_dir: Path):
        """Initialize with experiment directory.

        Args:
            experiment_dir: Path to experiment directory
        """
        self.experiment_dir = experiment_dir
        self.manifest_path = experiment_dir / "manifest.json"
        self.readme_path = experiment_dir / "README.md"

    def generate(self) -> bool:
        """Generate README.md from experiment data.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load manifest
            if not self.manifest_path.exists():
                logger.warning(f"No manifest.json found in {self.experiment_dir}")
                return False

            with open(self.manifest_path) as f:
                manifest = json.load(f)

            # Generate README content
            content = self._generate_content(manifest)

            # Write README
            with open(self.readme_path, "w") as f:
                f.write(content)

            logger.debug(
                f"Generated README.md for experiment {manifest.get('name', 'unknown')}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to generate README: {e}")
            return False

    def _generate_content(self, manifest: Dict[str, Any]) -> str:
        """Generate README content from manifest data.

        Args:
            manifest: Experiment manifest data

        Returns:
            Formatted README content
        """
        # Extract basic info
        exp_id = manifest.get("experiment_id", "unknown")
        name = manifest.get("name", "Unnamed Experiment")
        status = manifest.get("status", "unknown")
        created_at = manifest.get("created_at", "")
        completed_at = manifest.get("completed_at", "")

        # Format timestamps
        start_time = self._format_timestamp(created_at)
        end_time = (
            self._format_timestamp(completed_at) if completed_at else "In progress"
        )
        duration = self._calculate_duration(created_at, completed_at)

        # Get configuration
        config = manifest.get("configuration", {})
        agent_a = config.get("model_a", "unknown")
        agent_b = config.get("model_b", "unknown")
        max_turns = config.get("max_turns", 0)
        temperature_a = config.get("temperature_a", "default")
        temperature_b = config.get("temperature_b", "default")
        initial_prompt = config.get("initial_prompt", "Not specified")

        # Get results
        total_convs = manifest.get("total_conversations", 0)
        completed_convs = manifest.get("completed_conversations", 0)
        conversations = manifest.get("conversations", {})

        # Calculate statistics
        total_turns = sum(conv.get("turns", 0) for conv in conversations.values())
        avg_turns = total_turns / len(conversations) if conversations else 0

        # Build README
        lines = [
            f"# Experiment: {name}",
            "",
            f"**ID**: `{exp_id}`  ",
            f"**Started**: {start_time}  ",
            f"**Completed**: {end_time}  ",
        ]

        if duration:
            lines.append(f"**Duration**: {duration}  ")

        lines.extend(
            [
                f"**Status**: {self._format_status(status)}",
                "",
                "## Configuration",
                "",
                "**Agents**:",
                f"- Agent A: `{agent_a}`",
                f"- Agent B: `{agent_b}`",
                "",
                "**Parameters**:",
                f"- Max turns: {max_turns}",
                f"- Temperature A: {temperature_a}",
                f"- Temperature B: {temperature_b}",
                f'- Initial prompt: "{initial_prompt}"',
                "",
            ]
        )

        # Add convergence settings if present
        convergence_threshold = config.get("convergence_threshold")
        if convergence_threshold is not None:
            convergence_action = config.get("convergence_action", "stop")
            lines.extend(
                [
                    f"- Convergence threshold: {convergence_threshold} (action: {convergence_action})",
                    "",
                ]
            )

        # Results section
        lines.extend(
            [
                "## Results Summary",
                "",
                f"**Conversations**: {completed_convs} of {total_convs} completed  ",
            ]
        )

        if conversations:
            lines.append(
                f"**Total turns**: {total_turns} (avg: {avg_turns:.1f} per conversation)  "
            )

        # Add conversation details
        if conversations:
            lines.extend(["", "## Conversations", ""])

            for i, (conv_id, conv_data) in enumerate(conversations.items(), 1):
                turns = conv_data.get("turns", 0)
                status = conv_data.get("status", "unknown")
                end_reason = conv_data.get("end_reason", "")

                status_icon = (
                    "✓"
                    if status == "completed"
                    else "⚠️"
                    if status == "failed"
                    else "⏳"
                )
                line = f"{i}. `{conv_id}` - {turns} turns {status_icon}"

                if end_reason:
                    line += f" ({end_reason})"

                lines.append(line)

        # Files section
        lines.extend(
            [
                "",
                "## Files",
                "",
                "- `manifest.json` - Complete experiment metadata",
                "- `conv_*.jsonl` - Raw event streams for each conversation",
                "- `.imported` - Indicates data has been imported to DuckDB (if present)",
                "",
                "## Quick Analysis",
                "",
                "```bash",
                "# View manifest",
                "cat manifest.json | jq .",
                "",
                "# Search for specific events",
                'grep "MessageCompleteEvent" conv_*.jsonl | jq .content',
                "",
                "# Import to database (if not already done)",
                f"pidgin import {exp_id}",
                "```",
            ]
        )

        return "\n".join(lines)

    def _format_timestamp(self, timestamp: str) -> str:
        """Format ISO timestamp to readable format."""
        if not timestamp:
            return "Unknown"
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, AttributeError):
            return timestamp

    def _calculate_duration(self, start: str, end: str) -> Optional[str]:
        """Calculate duration between timestamps."""
        if not start or not end:
            return None
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            duration = end_dt - start_dt

            # Format duration nicely
            total_seconds = int(duration.total_seconds())
            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                return f"{minutes}m {seconds}s"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        except (ValueError, AttributeError):
            return None

    def _format_status(self, status: str) -> str:
        """Format status with emoji."""
        status_map = {
            "completed": "Completed ✓",
            "failed": "Failed ✗",
            "running": "Running ⏳",
            "cancelled": "Cancelled ⚠️",
        }
        return status_map.get(status, status.title())
