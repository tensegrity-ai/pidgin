"""Summary formatting for experiments."""

import json
from typing import Dict


class SummaryFormatter:
    """Handles formatting of experiment summaries."""

    def generate_experiment_summary(self, exp_data: Dict) -> str:
        """Generate experiment summary markdown.

        Args:
            exp_data: Experiment data dictionary

        Returns:
            Formatted experiment summary markdown
        """
        lines = [
            f"# Experiment: {exp_data['name']}",
            "",
            f"**ID**: {exp_data['experiment_id']}",
            f"**Status**: {exp_data['status']}",
            f"**Created**: {exp_data['created_at']}",
            "",
            "## Progress",
            "",
            f"- Total Conversations: {exp_data['total_conversations']}",
            f"- Completed: {exp_data['completed_conversations']}",
            f"- Failed: {exp_data['failed_conversations']}",
            "",
        ]

        # Parse config if available
        if exp_data.get("config"):
            config = (
                json.loads(exp_data["config"])
                if isinstance(exp_data["config"], str)
                else exp_data["config"]
            )

            lines.extend(
                [
                    "## Configuration",
                    "",
                    f"- Agent A: {config.get('agent_a_model', 'Unknown')}",
                    f"- Agent B: {config.get('agent_b_model', 'Unknown')}",
                    f"- Max Turns: {config.get('max_turns', 'Unknown')}",
                    f"- Convergence Threshold: {config.get('convergence_threshold', 'None')}",
                    "",
                ]
            )

        return "\n".join(lines)
