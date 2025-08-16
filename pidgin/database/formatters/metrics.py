"""Metrics formatting for transcripts."""

from typing import Dict, List


class MetricsFormatter:
    """Handles formatting of various metrics tables."""

    def format_summary_metrics(
        self, conv_data: Dict, token_data: Dict, num_turns: int
    ) -> str:
        """Format summary metrics table.

        Args:
            conv_data: Conversation data dictionary
            token_data: Token usage data dictionary
            num_turns: Number of turns in conversation

        Returns:
            Formatted summary metrics markdown
        """
        total_cost = (token_data.get("total_cost_cents") or 0) / 100.0
        final_convergence = conv_data.get("final_convergence_score")
        if final_convergence is None:
            final_convergence = 0

        lines = [
            "## Summary Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Turns | {conv_data.get('total_turns', num_turns)} |",
            f"| Final Convergence | {final_convergence:.3f} |",
            f"| Total Messages | {conv_data.get('total_turns', num_turns) * 2} |",
            f"| Total Tokens | {token_data.get('total_tokens', 0):,} |",
            f"| Total Cost | ${total_cost:.2f} |",
            f"| Ended Due To | {conv_data.get('convergence_reason') or 'max_turns'} |",
        ]

        return "\n".join(lines)

    def format_convergence_progression(self, turn_metrics: List[Dict]) -> str:
        """Format convergence progression table.

        Args:
            turn_metrics: List of turn metric dictionaries

        Returns:
            Formatted convergence progression markdown
        """
        if not turn_metrics:
            return "## Convergence Progression\n\nNo data available"

        lines = [
            "## Convergence Progression",
            "",
            "| Turn | Vocabulary Overlap | Avg Length Diff | Turn Score | Cumulative |",
            "|------|-------------------|-----------------|------------|------------|",
        ]

        for tm in turn_metrics:
            turn_num = tm.get("turn_number", 0)
            vocab_overlap = tm.get("vocabulary_overlap", 0)
            length_diff = tm.get("avg_message_length_difference", 0)
            turn_score = tm.get("turn_convergence_score", 0)
            cumulative = tm.get("cumulative_convergence_score", 0)

            lines.append(
                f"| {turn_num} | {vocab_overlap:.3f} | {length_diff:.1f} | "
                f"{turn_score:.3f} | {cumulative:.3f} |"
            )

        # Add milestone markers
        lines.append("")
        lines.append("### Convergence Milestones")
        lines.append("")

        milestones = [0.1, 0.25, 0.5, 0.75, 0.9]
        reached = []

        for milestone in milestones:
            for tm in turn_metrics:
                if tm.get("cumulative_convergence_score", 0) >= milestone:
                    reached.append(
                        f"- **{milestone:.0%}**: Turn {tm.get('turn_number', 0)}"
                    )
                    break

        if reached:
            lines.extend(reached)
        else:
            lines.append("- No significant milestones reached")

        return "\n".join(lines)

    def format_message_length_evolution(self, turn_metrics: List[Dict]) -> str:
        """Format message length evolution table.

        Args:
            turn_metrics: List of turn metric dictionaries

        Returns:
            Formatted message length evolution markdown
        """
        if not turn_metrics:
            return "## Message Length Evolution\n\nNo data available"

        lines = [
            "## Message Length Evolution",
            "",
            "| Turn | Agent A Length | Agent B Length | Difference | Avg Diff |",
            "|------|---------------|---------------|------------|----------|",
        ]

        for tm in turn_metrics:
            turn_num = tm.get("turn_number", 0)
            a_len = tm.get("agent_a_message_length", 0)
            b_len = tm.get("agent_b_message_length", 0)
            diff = abs(a_len - b_len)
            avg_diff = tm.get("avg_message_length_difference", 0)

            lines.append(
                f"| {turn_num} | {a_len} | {b_len} | {diff} | {avg_diff:.1f} |"
            )

        # Add summary statistics
        if turn_metrics:
            total_a = sum(tm.get("agent_a_message_length", 0) for tm in turn_metrics)
            total_b = sum(tm.get("agent_b_message_length", 0) for tm in turn_metrics)
            avg_a = total_a / len(turn_metrics)
            avg_b = total_b / len(turn_metrics)

            lines.extend(
                [
                    "",
                    "### Length Statistics",
                    "",
                    f"- **Agent A Average**: {avg_a:.1f} characters",
                    f"- **Agent B Average**: {avg_b:.1f} characters",
                    f"- **Total Characters**: {total_a + total_b:,}",
                    f"- **Balance Ratio**: {min(avg_a, avg_b) / max(avg_a, avg_b, 1):.2%}",
                ]
            )

        return "\n".join(lines)

    def format_vocabulary_metrics(self, turn_metrics: List[Dict]) -> str:
        """Format vocabulary metrics table.

        Args:
            turn_metrics: List of turn metric dictionaries

        Returns:
            Formatted vocabulary metrics markdown
        """
        if not turn_metrics:
            return "## Vocabulary Metrics\n\nNo data available"

        lines = [
            "## Vocabulary Metrics",
            "",
            "| Turn | Unique Words A | Unique Words B | Shared | Overlap % |",
            "|------|---------------|---------------|--------|-----------|",
        ]

        for tm in turn_metrics:
            turn_num = tm.get("turn_number", 0)
            unique_a = tm.get("unique_words_agent_a", 0)
            unique_b = tm.get("unique_words_agent_b", 0)
            shared = tm.get("shared_vocabulary_size", 0)
            overlap = tm.get("vocabulary_overlap", 0)

            lines.append(
                f"| {turn_num} | {unique_a} | {unique_b} | {shared} | {overlap:.1%} |"
            )

        # Add vocabulary growth analysis
        if turn_metrics:
            first_overlap = turn_metrics[0].get("vocabulary_overlap", 0)
            last_overlap = turn_metrics[-1].get("vocabulary_overlap", 0)
            max_overlap = max(tm.get("vocabulary_overlap", 0) for tm in turn_metrics)

            lines.extend(
                [
                    "",
                    "### Vocabulary Convergence",
                    "",
                    f"- **Initial Overlap**: {first_overlap:.1%}",
                    f"- **Final Overlap**: {last_overlap:.1%}",
                    f"- **Peak Overlap**: {max_overlap:.1%}",
                    f"- **Change**: {'+' if last_overlap > first_overlap else ''}"
                    f"{last_overlap - first_overlap:.1%}",
                ]
            )

        return "\n".join(lines)

    def format_response_times(self, turn_metrics: List[Dict]) -> str:
        """Format response times table.

        Args:
            turn_metrics: List of turn metric dictionaries

        Returns:
            Formatted response times markdown
        """
        if not turn_metrics:
            return "## Response Times\n\nNo data available"

        lines = [
            "## Response Times",
            "",
            "| Turn | Agent A (ms) | Agent B (ms) | Total (ms) |",
            "|------|-------------|-------------|------------|",
        ]

        total_a_time = 0
        total_b_time = 0

        for tm in turn_metrics:
            turn_num = tm.get("turn_number", 0)
            a_time = tm.get("agent_a_response_time_ms", 0)
            b_time = tm.get("agent_b_response_time_ms", 0)
            total_time = a_time + b_time

            total_a_time += a_time
            total_b_time += b_time

            lines.append(f"| {turn_num} | {a_time:,} | {b_time:,} | {total_time:,} |")

        # Add timing statistics
        if turn_metrics:
            num_turns = len(turn_metrics)
            lines.extend(
                [
                    "",
                    "### Timing Statistics",
                    "",
                    f"- **Total Time**: {(total_a_time + total_b_time) / 1000:.1f}s",
                    f"- **Agent A Average**: {total_a_time / num_turns:.0f}ms",
                    f"- **Agent B Average**: {total_b_time / num_turns:.0f}ms",
                    f"- **Avg Turn Time**: {(total_a_time + total_b_time) / num_turns:.0f}ms",
                ]
            )

        return "\n".join(lines)
