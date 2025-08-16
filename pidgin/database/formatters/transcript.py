"""Transcript message formatting."""

from typing import Dict, List


class TranscriptMessageFormatter:
    """Handles formatting of conversation transcripts."""

    def format_token_usage(self, messages: List[Dict], token_data: Dict) -> str:
        """Format token usage breakdown.

        Args:
            messages: List of message dictionaries
            token_data: Token usage data dictionary

        Returns:
            Formatted token usage markdown
        """
        lines = [
            "## Token Usage Breakdown",
            "",
            "| Agent | Input Tokens | Output Tokens | Total | Cost |",
            "|-------|-------------|---------------|--------|------|",
        ]

        # Agent A stats
        a_input = token_data.get("agent_a_input_tokens", 0)
        a_output = token_data.get("agent_a_output_tokens", 0)
        a_total = token_data.get("agent_a_total_tokens", 0)
        a_cost = (token_data.get("agent_a_cost_cents", 0) or 0) / 100.0

        lines.append(
            f"| Agent A | {a_input:,} | {a_output:,} | {a_total:,} | ${a_cost:.2f} |"
        )

        # Agent B stats
        b_input = token_data.get("agent_b_input_tokens", 0)
        b_output = token_data.get("agent_b_output_tokens", 0)
        b_total = token_data.get("agent_b_total_tokens", 0)
        b_cost = (token_data.get("agent_b_cost_cents", 0) or 0) / 100.0

        lines.append(
            f"| Agent B | {b_input:,} | {b_output:,} | {b_total:,} | ${b_cost:.2f} |"
        )

        # Totals
        total_input = a_input + b_input
        total_output = a_output + b_output
        total_tokens = token_data.get("total_tokens", 0)
        total_cost = (token_data.get("total_cost_cents", 0) or 0) / 100.0

        lines.append(
            f"| **Total** | **{total_input:,}** | **{total_output:,}** | "
            f"**{total_tokens:,}** | **${total_cost:.2f}** |"
        )

        # Add per-turn breakdown if available
        turn_costs = []
        for msg in messages:
            if msg.get("input_tokens") or msg.get("output_tokens"):
                turn_costs.append(msg)

        if turn_costs:
            lines.extend(
                [
                    "",
                    "### Per-Turn Token Usage",
                    "",
                    "| Turn | Agent | Input | Output | Total |",
                    "|------|-------|-------|--------|--------|",
                ]
            )

            for msg in turn_costs[:10]:  # Limit to first 10 for readability
                turn = msg.get("turn_number", "?")
                agent = msg.get("agent_id", "?")
                inp = msg.get("input_tokens", 0)
                out = msg.get("output_tokens", 0)
                total = inp + out

                lines.append(f"| {turn} | {agent} | {inp:,} | {out:,} | {total:,} |")

            if len(turn_costs) > 10:
                lines.append(f"| ... | ({len(turn_costs) - 10} more turns) | | | |")

        return "\n".join(lines)

    def format_transcript(self, messages: List[Dict], conv_data: Dict) -> str:
        """Format conversation transcript.

        Args:
            messages: List of message dictionaries
            conv_data: Conversation data dictionary

        Returns:
            Formatted transcript markdown
        """
        lines = ["## Full Transcript", ""]

        for msg in messages:
            # Determine agent name
            if msg["agent_id"] == "agent_a":
                name = conv_data.get("agent_a_chosen_name") or conv_data.get(
                    "agent_a_model", "Agent A"
                )
            elif msg["agent_id"] == "agent_b":
                name = conv_data.get("agent_b_chosen_name") or conv_data.get(
                    "agent_b_model", "Agent B"
                )
            else:
                name = msg["agent_id"]

            lines.append(f"**{name}**: {msg['content']}")
            lines.append("")

        lines.append("---")

        return "\n".join(lines)
