"""Simplified metrics interface for live UI display."""

import re
import unicodedata
from collections import Counter
from typing import Any, Dict

from .constants import EMOJI_PATTERN, SENTENCE_ENDINGS


def calculate_turn_metrics(content: str) -> Dict[str, Any]:
    """Calculate basic metrics for UI display.

    This is a simplified version for real-time display during conversations.
    For comprehensive analysis, use MetricsCalculator.

    Args:
        content: The message content

    Returns:
        Dictionary containing display-friendly metrics
    """
    # Basic metrics
    length = len(content)

    # Sentence count (simple approximation)
    sentences = len(SENTENCE_ENDINGS.findall(content)) or 1

    # Word diversity
    words = re.findall(r"\b\w+\b", content.lower())
    word_diversity = len(set(words)) / len(words) if words else 0

    # Emoji density
    emoji_count = count_emojis(content)
    emoji_density = emoji_count / length if length > 0 else 0

    return {
        "length": length,
        "sentences": sentences,
        "word_diversity": round(word_diversity, 3),
        "emoji_density": round(emoji_density, 4),
        "emoji_count": emoji_count,
    }


def count_emojis(text: str) -> int:
    """Count emojis in text using Unicode categories."""
    emoji_matches = EMOJI_PATTERN.findall(text)
    emoji_count = len(emoji_matches)

    # Also check for other symbol categories
    for char in text:
        # Check for Symbol, Other category (catches more emojis)
        if unicodedata.category(char) == "So" and char not in emoji_matches:
            emoji_count += 1

    return emoji_count


def calculate_structural_similarity(
    messages_a: list[str], messages_b: list[str]
) -> Dict[str, float]:
    """Calculate basic structural similarity between two agents' messages.

    Args:
        messages_a: List of Agent A's message contents
        messages_b: List of Agent B's message contents

    Returns:
        Dictionary of similarity metrics
    """
    if not messages_a or not messages_b:
        return {
            "avg_length_ratio": 0.0,
            "sentence_pattern_similarity": 0.0,
            "punctuation_similarity": 0.0,
        }

    # Average length ratio
    avg_len_a = sum(len(m) for m in messages_a) / max(len(messages_a), 1)
    avg_len_b = sum(len(m) for m in messages_b) / max(len(messages_b), 1)
    length_ratio = (
        min(avg_len_a, avg_len_b) / max(avg_len_a, avg_len_b)
        if max(avg_len_a, avg_len_b) > 0
        else 0
    )

    # Sentence pattern similarity
    avg_sent_a = sum(len(SENTENCE_ENDINGS.findall(m)) or 1 for m in messages_a) / max(
        len(messages_a), 1
    )
    avg_sent_b = sum(len(SENTENCE_ENDINGS.findall(m)) or 1 for m in messages_b) / max(
        len(messages_b), 1
    )
    sentence_similarity = (
        min(avg_sent_a, avg_sent_b) / max(avg_sent_a, avg_sent_b)
        if max(avg_sent_a, avg_sent_b) > 0
        else 0
    )

    # Punctuation similarity
    punct_a: Counter[str] = Counter()
    punct_b: Counter[str] = Counter()

    for m in messages_a:
        for p in ".!?,;:-—":
            punct_a[p] += m.count(p)

    for m in messages_b:
        for p in ".!?,;:-—":
            punct_b[p] += m.count(p)

    # Normalize by total characters
    total_a = sum(len(m) for m in messages_a)
    total_b = sum(len(m) for m in messages_b)

    punct_sim = 0.0
    punct_marks = ".!?,;:-—"
    for p in punct_marks:
        freq_a = punct_a[p] / total_a if total_a > 0 else 0
        freq_b = punct_b[p] / total_b if total_b > 0 else 0
        if freq_a > 0 or freq_b > 0:
            punct_sim += min(freq_a, freq_b) / max(freq_a, freq_b)
    punct_sim /= len(punct_marks)

    return {
        "avg_length_ratio": round(length_ratio, 3),
        "sentence_pattern_similarity": round(sentence_similarity, 3),
        "punctuation_similarity": round(punct_sim, 3),
    }


def update_phase_detection(
    phase_detection: Dict[str, Any], metrics: Dict[str, Any], turn: int
) -> None:
    """Update phase detection based on current metrics.

    Args:
        phase_detection: Phase detection dictionary to update
        metrics: Current turn metrics
        turn: Current turn number
    """
    # High convergence phase
    if (
        phase_detection["high_convergence_start"] is None
        and "convergence" in metrics
        and metrics["convergence"] > 0.75
    ):
        phase_detection["high_convergence_start"] = turn

    # Emoji phase (> 1% of characters)
    if (
        phase_detection["emoji_phase_start"] is None
        and "emoji_density" in metrics
        and metrics["emoji_density"] > 0.01
    ):
        phase_detection["emoji_phase_start"] = turn

    # Symbolic phase (> 10% of characters)
    if (
        phase_detection["symbolic_phase_start"] is None
        and "emoji_density" in metrics
        and metrics["emoji_density"] > 0.10
    ):
        phase_detection["symbolic_phase_start"] = turn
