"""Convergence metrics for tracking when AI agents start sounding alike."""

import re
from typing import Any, List, Tuple


class ConvergenceCalculator:
    """Calculate structural similarity between agent responses."""

    def __init__(self, window_size: int = 10, weights: dict = None):
        """Initialize convergence calculator.

        Args:
            window_size: Number of recent messages to consider
            weights: Optional weight dictionary for convergence calculation
        """
        self.window_size = window_size
        self.history: List[float] = []

        # Default weights if none provided
        self.weights = weights or {
            "content": 0.4,
            "length": 0.15,
            "sentences": 0.2,
            "structure": 0.15,
            "punctuation": 0.1,
        }

        # Validate weights
        self._validate_weights()

    def calculate(self, messages: List[Any]) -> float:
        """Calculate structural similarity between recent A and B messages.

        Returns 0.0 (completely different) to 1.0 (identical).

        Args:
            messages: Full conversation history

        Returns:
            Convergence score between 0.0 and 1.0
        """
        # Get recent messages from each agent, ensuring balance
        # Only use messages from agent turns (not system/external)
        agent_messages = [m for m in messages if m.agent_id in ["agent_a", "agent_b"]]
        recent_messages = (
            agent_messages[-self.window_size :]
            if len(agent_messages) > self.window_size
            else agent_messages
        )

        recent_a = [m for m in recent_messages if m.agent_id == "agent_a"]
        recent_b = [m for m in recent_messages if m.agent_id == "agent_b"]

        if not recent_a or not recent_b:
            return 0.0

        # Balance the comparison by taking equal numbers of recent messages
        min_count = min(len(recent_a), len(recent_b))
        recent_a = recent_a[-min_count:] if min_count > 0 else recent_a
        recent_b = recent_b[-min_count:] if min_count > 0 else recent_b

        # Clean the message content before analysis
        recent_a = [self._clean_message_content(m) for m in recent_a]
        recent_b = [self._clean_message_content(m) for m in recent_b]

        # First check for exact content matches
        content_sim = self._content_similarity(recent_a, recent_b)

        # If content is very similar, weight it heavily
        if content_sim > 0.9:
            similarity = (
                content_sim * 0.7 + content_sim * 0.3
            )  # Heavily weight exact matches
        else:
            # Calculate multiple structural similarity metrics
            length_sim = self._length_similarity(recent_a, recent_b)
            sentence_sim = self._sentence_pattern_similarity(recent_a, recent_b)
            structure_sim = self._structure_similarity(recent_a, recent_b)
            punctuation_sim = self._punctuation_similarity(recent_a, recent_b)

            # Weighted average including content similarity
            similarity = (
                content_sim * self.weights["content"]
                + length_sim * self.weights["length"]
                + sentence_sim * self.weights["sentences"]
                + structure_sim * self.weights["structure"]
                + punctuation_sim * self.weights["punctuation"]
            )

        # Track history
        self.history.append(similarity)

        return round(similarity, 2)

    def _clean_message_content(self, message: Any) -> Any:
        """Clean message content by removing embedded agent labels and formatting."""
        content = message.content

        # Remove embedded agent labels like "**Agent A**:" and "**Agent B**:"
        content = re.sub(r"\*\*Agent [AB]\*\*:\s*", "", content)

        # Remove markdown formatting artifacts from collaborative responses
        content = re.sub(r"\*\*Agent [AB]\*\*", "", content)

        # Remove excessive newlines and clean up spacing
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = content.strip()

        # Create a new message object with cleaned content
        from types import SimpleNamespace

        cleaned_message = SimpleNamespace()
        cleaned_message.content = content
        cleaned_message.agent_id = message.agent_id
        cleaned_message.role = message.role
        cleaned_message.timestamp = getattr(message, "timestamp", None)

        return cleaned_message

    def _content_similarity(self, messages_a: List, messages_b: List) -> float:
        """Calculate direct content similarity between messages."""
        if not messages_a or not messages_b:
            return 0.0

        # Get the most recent message from each agent for comparison
        content_a = messages_a[-1].content.strip().lower()
        content_b = messages_b[-1].content.strip().lower()

        # Handle exact matches
        if content_a == content_b:
            return 1.0

        # Handle cases where one message contains the other
        if content_a in content_b or content_b in content_a:
            shorter = min(len(content_a), len(content_b))
            longer = max(len(content_a), len(content_b))
            return shorter / longer if longer > 0 else 0.0

        # Basic character-level similarity for very short messages
        if len(content_a) < 50 and len(content_b) < 50:
            # Simple character overlap for short messages
            chars_a = set(content_a)
            chars_b = set(content_b)
            intersection = len(chars_a.intersection(chars_b))
            union = len(chars_a.union(chars_b))
            return intersection / union if union > 0 else 0.0

        # For longer messages, use word-level comparison
        words_a = set(content_a.split())
        words_b = set(content_b.split())
        intersection = len(words_a.intersection(words_b))
        union = len(words_a.union(words_b))
        return intersection / union if union > 0 else 0.0

    def _length_similarity(self, messages_a: List, messages_b: List) -> float:
        """Calculate similarity based on message lengths."""
        if not messages_a or not messages_b:
            return 0.0

        # Compare average message lengths
        avg_len_a = sum(len(m.content) for m in messages_a) / len(messages_a)
        avg_len_b = sum(len(m.content) for m in messages_b) / len(messages_b)

        if avg_len_a == 0 or avg_len_b == 0:
            return 0.0

        # Ratio similarity (closer to 1.0 means more similar)
        ratio = min(avg_len_a, avg_len_b) / max(avg_len_a, avg_len_b)
        return ratio

    def _sentence_pattern_similarity(self, messages_a: List, messages_b: List) -> float:
        """Calculate similarity based on sentence patterns."""
        # Extract sentences using simple regex
        sentence_pattern = r"[.!?]+[\s]"

        def avg_sentences(messages):
            total_sentences = 0
            for m in messages:
                # Count sentences (add 1 for last sentence if no trailing punctuation)
                count = len(re.findall(sentence_pattern, m.content))
                if m.content and not m.content.strip().endswith((".", "!", "?")):
                    count += 1
                total_sentences += count
            return total_sentences / len(messages) if messages else 0

        avg_sent_a = avg_sentences(messages_a)
        avg_sent_b = avg_sentences(messages_b)

        if avg_sent_a == 0 or avg_sent_b == 0:
            return 0.0

        ratio = min(avg_sent_a, avg_sent_b) / max(avg_sent_a, avg_sent_b)
        return ratio

    def _structure_similarity(self, messages_a: List, messages_b: List) -> float:
        """Calculate similarity based on structural patterns.

        Includes paragraphs, lists, questions.
        """

        def extract_features(messages):
            features = {"paragraphs": 0, "lists": 0, "questions": 0, "code_blocks": 0}

            for m in messages:
                content = m.content
                # Count paragraphs (double newlines)
                features["paragraphs"] += len(re.findall(r"\n\n", content)) + 1
                # Count list items (lines starting with -, *, or numbers)
                features["lists"] += len(
                    re.findall(r"^[\s]*[-*•]|\d+\.", content, re.MULTILINE)
                )
                # Count questions
                features["questions"] += content.count("?")
                # Count code blocks (triple backticks)
                features["code_blocks"] += content.count("```")

            # Normalize by message count
            for key in features:
                features[key] = features[key] / len(messages) if messages else 0

            return features

        features_a = extract_features(messages_a)
        features_b = extract_features(messages_b)

        # Calculate similarity for each feature
        similarities = []
        for key in features_a:
            if features_a[key] == 0 and features_b[key] == 0:
                similarities.append(1.0)  # Both have none, that's similar
            elif features_a[key] == 0 or features_b[key] == 0:
                similarities.append(0.0)  # One has none, that's different
            else:
                ratio = min(features_a[key], features_b[key]) / max(
                    features_a[key], features_b[key]
                )
                similarities.append(ratio)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _punctuation_similarity(self, messages_a: List, messages_b: List) -> float:
        """Calculate similarity based on punctuation patterns."""

        def punctuation_profile(messages):
            profile = {
                "exclamations": 0,
                "commas": 0,
                "semicolons": 0,
                "colons": 0,
                "dashes": 0,
            }

            total_chars = 0
            for m in messages:
                content = m.content
                total_chars += len(content)
                profile["exclamations"] += content.count("!")
                profile["commas"] += content.count(",")
                profile["semicolons"] += content.count(";")
                profile["colons"] += content.count(":")
                profile["dashes"] += content.count("-") + content.count("—")

            # Normalize by total characters
            for key in profile:
                profile[key] = profile[key] / total_chars if total_chars > 0 else 0

            return profile

        profile_a = punctuation_profile(messages_a)
        profile_b = punctuation_profile(messages_b)

        # Calculate similarity
        similarities = []
        for key in profile_a:
            if profile_a[key] == 0 and profile_b[key] == 0:
                similarities.append(1.0)
            elif profile_a[key] == 0 or profile_b[key] == 0:
                similarities.append(0.0)
            else:
                ratio = min(profile_a[key], profile_b[key]) / max(
                    profile_a[key], profile_b[key]
                )
                similarities.append(ratio)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def get_trend(self) -> str:
        """Get the trend of convergence (increasing, decreasing, stable)."""
        if len(self.history) < 3:
            return "insufficient data"

        recent = self.history[-3:]

        # Check if increasing
        if recent[-1] > recent[-2] > recent[-3]:
            return "increasing"
        # Check if decreasing
        elif recent[-1] < recent[-2] < recent[-3]:
            return "decreasing"
        # Check if relatively stable (within 0.1)
        elif all(abs(recent[i] - recent[i - 1]) < 0.1 for i in range(1, len(recent))):
            return "stable"
        else:
            return "fluctuating"

    def _validate_weights(self):
        """Validate that weights are properly configured.

        Raises:
            ValueError: If weights don't sum to 1.0 or have invalid values
        """
        # Check all required keys are present
        required_keys = {"content", "length", "sentences", "structure", "punctuation"}
        provided_keys = set(self.weights.keys())

        if provided_keys != required_keys:
            missing = required_keys - provided_keys
            extra = provided_keys - required_keys
            msg_parts = []
            if missing:
                msg_parts.append(f"missing keys: {missing}")
            if extra:
                msg_parts.append(f"extra keys: {extra}")
            raise ValueError(f"Invalid weight keys - {', '.join(msg_parts)}")

        # Check all weights are non-negative
        for key, value in self.weights.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(
                    f"Weight '{key}' must be a non-negative number, got {value}"
                )

        # Check weights sum to 1.0 (with small tolerance for floating point)
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    def get_recent_history(self, n: int = 5) -> List[Tuple[int, float]]:
        """Get recent convergence history with turn numbers.

        Args:
            n: Number of recent turns to return

        Returns:
            List of (turn_number, convergence_score) tuples
        """
        if not self.history:
            return []

        start_idx = max(0, len(self.history) - n)
        return [
            (i + 1, score)
            for i, score in enumerate(self.history[start_idx:], start=start_idx)
        ]
