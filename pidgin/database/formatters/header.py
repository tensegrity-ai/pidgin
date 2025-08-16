"""Header formatting for transcripts."""

from typing import Dict


class HeaderFormatter:
    """Handles formatting of transcript headers."""

    def format_header(self, conv_data: Dict, token_data: Dict) -> str:
        """Format transcript header.

        Args:
            conv_data: Conversation data dictionary
            token_data: Token usage data dictionary

        Returns:
            Formatted header markdown
        """
        agent_a = conv_data.get("agent_a_chosen_name") or conv_data.get(
            "agent_a_model", "Agent A"
        )
        agent_b = conv_data.get("agent_b_chosen_name") or conv_data.get(
            "agent_b_model", "Agent B"
        )

        duration_ms = conv_data.get("duration_ms") or 0
        if duration_ms:
            duration_str = f"{duration_ms // 60000}m {(duration_ms % 60000) // 1000}s"
        else:
            duration_str = "N/A"

        started = conv_data.get("started_at", "")
        if isinstance(started, str):
            date_str = started
        elif started:
            date_str = started.strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            date_str = "N/A"

        lines = [
            f"# Conversation: {conv_data.get('agent_a_model') or 'Unknown'} ↔ {conv_data.get('agent_b_model') or 'Unknown'}",
            "",
            f"**Experiment**: {conv_data.get('experiment_id', 'N/A')}",
            f"**Date**: {date_str}",
            f"**Duration**: {duration_str}",
            f"**Agents**: {agent_a} ↔ {agent_b}",
        ]

        return "\n".join(lines)
