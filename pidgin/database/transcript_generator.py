"""Generate markdown transcripts from database data."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import duckdb

from ..io.logger import get_logger

logger = get_logger("transcript_generator")


class TranscriptGenerator:
    """Generate rich markdown transcripts from database data."""

    def __init__(self, db_path: Path):
        """Initialize with database connection.

        Args:
            db_path: Path to DuckDB database
        """
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path), read_only=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def generate_experiment_transcripts(self, experiment_id: str, output_dir: Path):
        """Generate all transcripts for an experiment.

        Args:
            experiment_id: Experiment ID
            output_dir: Directory to write transcripts
        """
        # Create transcripts directory
        transcripts_dir = output_dir / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)

        # Get experiment data
        exp_data = self._get_experiment_data(experiment_id)
        if not exp_data:
            logger.error(f"Experiment {experiment_id} not found in database")
            return

        # Generate experiment summary
        summary_path = transcripts_dir / "summary.md"
        with open(summary_path, "w") as f:
            f.write(self._generate_experiment_summary(exp_data))
        logger.debug(f"Generated experiment summary: {summary_path}")

        # Get all conversations
        conversations = self._get_conversations(experiment_id)

        # Generate transcript for each conversation
        for conv in conversations:
            conv_id = conv["conversation_id"]
            transcript = self.generate_conversation_transcript(conv_id)

            # Write transcript
            transcript_path = transcripts_dir / f"{conv_id}.md"
            with open(transcript_path, "w") as f:
                f.write(transcript)
            logger.debug(f"Generated transcript: {transcript_path}")

    def generate_conversation_transcript(self, conversation_id: str) -> str:
        """Generate markdown transcript for a single conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Markdown formatted transcript
        """
        # Get all data from database
        conv_data = self._get_conversation_data(conversation_id)
        turn_metrics = self._get_turn_metrics(conversation_id)
        messages = self._get_messages(conversation_id)
        token_data = self._get_token_usage(conversation_id)

        if not conv_data:
            return f"# Conversation {conversation_id} not found"

        # Build transcript sections
        sections = []

        # Header
        sections.append(self._format_header(conv_data, token_data))

        # Summary metrics table
        sections.append(
            self._format_summary_metrics(conv_data, token_data, len(turn_metrics))
        )

        # Convergence progression
        sections.append(self._format_convergence_progression(turn_metrics))

        # Message length evolution
        sections.append(self._format_message_length_evolution(turn_metrics))

        # Vocabulary metrics
        sections.append(self._format_vocabulary_metrics(turn_metrics))

        # Response time analysis
        sections.append(self._format_response_times(turn_metrics))

        # Token usage by turn
        sections.append(self._format_token_usage(messages, token_data))

        # Full transcript
        sections.append(self._format_transcript(messages, conv_data))

        # Join all sections
        return "\n\n".join(sections)

    def _get_experiment_data(self, experiment_id: str) -> Optional[Dict]:
        """Get experiment data from database."""
        result = self.conn.execute(
            "SELECT * FROM experiments WHERE experiment_id = ?", [experiment_id]
        ).fetchone()

        if result:
            cols = [desc[0] for desc in self.conn.description]
            return dict(zip(cols, result))
        return None

    def _get_conversations(self, experiment_id: str) -> List[Dict]:
        """Get all conversations for an experiment."""
        results = self.conn.execute(
            """
            SELECT * FROM conversations
            WHERE experiment_id = ?
            ORDER BY created_at
            """,
            [experiment_id],
        ).fetchall()

        cols = [desc[0] for desc in self.conn.description]
        return [dict(zip(cols, row)) for row in results]

    def _get_conversation_data(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation data from database."""
        result = self.conn.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?", [conversation_id]
        ).fetchone()

        if result:
            cols = [desc[0] for desc in self.conn.description]
            return dict(zip(cols, result))
        return None

    def _get_turn_metrics(self, conversation_id: str) -> List[Dict]:
        """Get turn metrics from database."""
        results = self.conn.execute(
            """
            SELECT * FROM turn_metrics
            WHERE conversation_id = ?
            ORDER BY turn_number
            """,
            [conversation_id],
        ).fetchall()

        cols = [desc[0] for desc in self.conn.description]
        return [dict(zip(cols, row)) for row in results]

    def _get_messages(self, conversation_id: str) -> List[Dict]:
        """Get messages from database."""
        results = self.conn.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY turn_number, agent_id
            """,
            [conversation_id],
        ).fetchall()

        cols = [desc[0] for desc in self.conn.description]
        return [dict(zip(cols, row)) for row in results]

    def _get_token_usage(self, conversation_id: str) -> Dict:
        """Get token usage summary."""
        result = self.conn.execute(
            """
            SELECT
                SUM(total_tokens) as total_tokens,
                SUM(total_cost) as total_cost_cents
            FROM token_usage
            WHERE conversation_id = ?
            """,
            [conversation_id],
        ).fetchone()

        if result and result[0]:
            return {
                "total_tokens": int(result[0]),
                "total_cost_cents": float(result[1]) if result[1] else 0,
            }
        return {"total_tokens": 0, "total_cost_cents": 0}

    def _format_header(self, conv_data: Dict, token_data: Dict) -> str:
        """Format transcript header."""
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
            f"# Conversation: {conv_data.get('agent_a_model', 'Unknown')} ↔ {conv_data.get('agent_b_model', 'Unknown')}",
            "",
            f"**Experiment**: {conv_data.get('experiment_id', 'N/A')}",
            f"**Date**: {date_str}",
            f"**Duration**: {duration_str}",
            f"**Agents**: {agent_a} ↔ {agent_b}",
        ]

        return "\n".join(lines)

    def _format_summary_metrics(
        self, conv_data: Dict, token_data: Dict, num_turns: int
    ) -> str:
        """Format summary metrics table."""
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
            f"| Total Tokens | {token_data['total_tokens']:,} |",
            f"| Total Cost | ${total_cost:.2f} |",
            f"| Ended Due To | {conv_data.get('convergence_reason', 'max_turns')} |",
        ]

        return "\n".join(lines)

    def _format_convergence_progression(self, turn_metrics: List[Dict]) -> str:
        """Format convergence progression table."""
        if not turn_metrics:
            return "## Convergence Progression\n\nNo data available"

        # Sample turns for the table
        sample_turns = [1, 5, 10, 15, 20, 25]

        lines = [
            "## Convergence Progression",
            "",
            "| Turn | " + " | ".join(str(t) for t in sample_turns) + " |",
            "|------|" + "|".join("---" for _ in sample_turns) + "|",
        ]

        scores = []
        trends = []

        for target_turn in sample_turns:
            # Find closest turn
            closest = None
            for tm in turn_metrics:
                if tm["turn_number"] <= target_turn:
                    closest = tm
                else:
                    break

            if closest and closest["convergence_score"] is not None:
                score = closest["convergence_score"]
                scores.append(f"{score:.3f}")

                # Calculate trend
                if len(scores) > 1:
                    prev_idx = max(0, len(scores) - 2)
                    # Check if previous score is not "-"
                    if scores[prev_idx] != "-":
                        prev_score = float(scores[prev_idx])
                        if score > prev_score + 0.1:
                            trends.append("↑↑")
                        elif score > prev_score:
                            trends.append("↑")
                        elif score < prev_score:
                            trends.append("↓")
                        else:
                            trends.append("→")
                    else:
                        trends.append("-")  # Can't calculate trend from missing data
                else:
                    trends.append("-")
            else:
                scores.append("-")
                trends.append("-")

        lines.append("| Score | " + " | ".join(scores) + " |")
        lines.append("| Trend | " + " | ".join(trends) + " |")

        return "\n".join(lines)

    def _format_message_length_evolution(self, turn_metrics: List[Dict]) -> str:
        """Format message length evolution table."""
        if not turn_metrics:
            return "## Message Length Evolution\n\nNo data available"

        lines = [
            "## Message Length Evolution",
            "",
            "| Metric | Turns 1-5 | Turns 6-10 | Turns 11-15 | Turns 16-20 | Turns 21-25 |",
            "|--------|-----------|------------|-------------|-------------|-------------|",
        ]

        # Group metrics by turn ranges
        ranges = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25)]

        avg_chars_a = []
        avg_chars_b = []
        avg_words_a = []
        avg_words_b = []

        for start, end in ranges:
            metrics_in_range = [
                tm for tm in turn_metrics if start <= tm["turn_number"] <= end
            ]

            if metrics_in_range:
                chars_a = [
                    tm["message_a_length"]
                    for tm in metrics_in_range
                    if tm["message_a_length"] is not None
                ]
                chars_b = [
                    tm["message_b_length"]
                    for tm in metrics_in_range
                    if tm["message_b_length"] is not None
                ]
                words_a = [
                    tm["message_a_word_count"]
                    for tm in metrics_in_range
                    if tm["message_a_word_count"] is not None
                ]
                words_b = [
                    tm["message_b_word_count"]
                    for tm in metrics_in_range
                    if tm["message_b_word_count"] is not None
                ]

                avg_chars_a.append(
                    str(int(sum(chars_a) / len(chars_a))) if chars_a else "-"
                )
                avg_chars_b.append(
                    str(int(sum(chars_b) / len(chars_b))) if chars_b else "-"
                )
                avg_words_a.append(
                    str(int(sum(words_a) / len(words_a))) if words_a else "-"
                )
                avg_words_b.append(
                    str(int(sum(words_b) / len(words_b))) if words_b else "-"
                )
            else:
                avg_chars_a.append("-")
                avg_chars_b.append("-")
                avg_words_a.append("-")
                avg_words_b.append("-")

        lines.append("| Avg Chars (A) | " + " | ".join(avg_chars_a) + " |")
        lines.append("| Avg Chars (B) | " + " | ".join(avg_chars_b) + " |")
        lines.append("| Avg Words (A) | " + " | ".join(avg_words_a) + " |")
        lines.append("| Avg Words (B) | " + " | ".join(avg_words_b) + " |")

        return "\n".join(lines)

    def _format_vocabulary_metrics(self, turn_metrics: List[Dict]) -> str:
        """Format vocabulary metrics table."""
        if not turn_metrics:
            return "## Vocabulary Metrics\n\nNo data available"

        lines = [
            "## Vocabulary Metrics",
            "",
            "| Turn Range | Unique Words (A) | Unique Words (B) | Shared Vocabulary | Overlap % |",
            "|------------|------------------|------------------|-------------------|-----------|",
        ]

        # Group by turn ranges
        ranges = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25)]

        for start, end in ranges:
            metrics_in_range = [
                tm for tm in turn_metrics if start <= tm["turn_number"] <= end
            ]

            if metrics_in_range:
                # Get the last turn in range for cumulative vocabulary
                last_metric = metrics_in_range[-1]

                unique_a = last_metric.get("message_a_unique_words", 0)
                unique_b = last_metric.get("message_b_unique_words", 0)

                # Parse shared vocabulary from JSON
                shared_vocab_json = last_metric.get("shared_vocabulary")
                if shared_vocab_json:
                    try:
                        if isinstance(shared_vocab_json, str):
                            shared_vocab = json.loads(shared_vocab_json)
                        else:
                            shared_vocab = shared_vocab_json
                        shared_count = (
                            len(shared_vocab) if isinstance(shared_vocab, list) else 0
                        )
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse shared_vocabulary JSON: {shared_vocab_json}"
                        )
                        shared_count = 0
                else:
                    shared_count = 0

                # Calculate overlap percentage (handle None values)
                unique_a = unique_a or 0
                unique_b = unique_b or 0
                total_unique = unique_a + unique_b - shared_count
                overlap_pct = (
                    (shared_count / total_unique * 100) if total_unique > 0 else 0
                )

                lines.append(
                    f"| {start}-{end} | {unique_a} | {unique_b} | {shared_count} | {overlap_pct:.1f}% |"
                )
            else:
                lines.append(f"| {start}-{end} | - | - | - | - |")

        return "\n".join(lines)

    def _format_response_times(self, turn_metrics: List[Dict]) -> str:
        """Format response time analysis table."""
        if not turn_metrics:
            return "## Response Time Analysis\n\nNo data available"

        lines = [
            "## Response Time Analysis",
            "",
            "| Turn Range | Avg Response Time (A) | Avg Response Time (B) |",
            "|------------|----------------------|----------------------|",
        ]

        # Group by turn ranges
        ranges = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25)]

        for start, end in ranges:
            metrics_in_range = [
                tm for tm in turn_metrics if start <= tm["turn_number"] <= end
            ]

            if metrics_in_range:
                times_a = [
                    tm["message_a_response_time_ms"]
                    for tm in metrics_in_range
                    if tm.get("message_a_response_time_ms") is not None
                ]
                times_b = [
                    tm["message_b_response_time_ms"]
                    for tm in metrics_in_range
                    if tm.get("message_b_response_time_ms") is not None
                ]

                avg_a = f"{int(sum(times_a) / len(times_a)):,} ms" if times_a else "-"
                avg_b = f"{int(sum(times_b) / len(times_b)):,} ms" if times_b else "-"

                lines.append(f"| {start}-{end} | {avg_a} | {avg_b} |")
            else:
                lines.append(f"| {start}-{end} | - | - |")

        return "\n".join(lines)

    def _format_token_usage(self, messages: List[Dict], token_data: Dict) -> str:
        """Format token usage by turn table."""
        if not messages:
            return "## Token Usage by Turn\n\nNo data available"

        lines = [
            "## Token Usage by Turn",
            "",
            "| Turn | Tokens (A) | Tokens (B) | Cumulative | Cost |",
            "|------|------------|------------|------------|------|",
        ]

        # Sample turns
        sample_turns = [1, 5, 10, 15, 20, 25]
        cumulative = 0

        for turn in sample_turns:
            # Get messages for this turn
            turn_messages = [m for m in messages if m["turn_number"] == turn]

            if turn_messages:
                tokens_a = (
                    next(
                        (
                            m["token_count"]
                            for m in turn_messages
                            if m["agent_id"] == "agent_a"
                        ),
                        0,
                    )
                    or 0
                )
                tokens_b = (
                    next(
                        (
                            m["token_count"]
                            for m in turn_messages
                            if m["agent_id"] == "agent_b"
                        ),
                        0,
                    )
                    or 0
                )

                # Calculate cumulative up to this turn
                cumulative = sum(
                    m["token_count"] or 0 for m in messages if m["turn_number"] <= turn
                )

                # Estimate cost (simplified)
                cost = (
                    cumulative
                    * (token_data["total_cost_cents"] / token_data["total_tokens"])
                    / 100
                    if token_data["total_tokens"] > 0
                    else 0
                )

                lines.append(
                    f"| {turn} | {tokens_a} | {tokens_b} | {cumulative:,} | ${cost:.3f} |"
                )
            else:
                if turn <= len(messages) // 2:
                    lines.append(f"| {turn} | - | - | - | - |")

        return "\n".join(lines)

    def _format_transcript(self, messages: List[Dict], conv_data: Dict) -> str:
        """Format the full conversation transcript."""
        if not messages:
            return "## Transcript\n\nNo messages found"

        lines = ["## Transcript", ""]

        # Get agent names
        agent_a_name = conv_data.get("agent_a_chosen_name") or conv_data.get(
            "agent_a_model", "Agent A"
        )
        agent_b_name = conv_data.get("agent_b_chosen_name") or conv_data.get(
            "agent_b_model", "Agent B"
        )

        # Group messages by turn
        current_turn = None

        for msg in messages:
            turn = msg["turn_number"]

            if turn != current_turn:
                if current_turn is not None:
                    lines.append("")  # Add spacing between turns
                lines.append(f"### Turn {turn}")
                lines.append("")
                current_turn = turn

            # Determine agent name
            if msg["agent_id"] == "agent_a":
                name = agent_a_name
            elif msg["agent_id"] == "agent_b":
                name = agent_b_name
            else:
                name = msg["agent_id"]

            lines.append(f"**{name}**: {msg['content']}")
            lines.append("")

        lines.append("---")

        return "\n".join(lines)

    def _generate_experiment_summary(self, exp_data: Dict) -> str:
        """Generate experiment summary markdown."""
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
