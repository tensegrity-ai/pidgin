"""Text analysis utilities for metrics calculation."""

import re
from collections import Counter
from typing import List, Set, Tuple

from .constants import (
    ACKNOWLEDGMENT_REGEX,
    ALL_SPECIAL_SYMBOLS,
    ARROW_PATTERN,
    EMOJI_PATTERN,
    EXCLAMATION_PATTERN,
    MATH_PATTERN,
    QUESTION_PATTERN,
    SENTENCE_ENDINGS,
)


class TextAnalyzer:
    """Handles text analysis operations for metrics."""

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple word tokenization (handles contractions too)."""
        return re.findall(r"\b[\w']+\b", text.lower())

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Split text into sentences using regex."""
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def count_sentences(text: str) -> int:
        """Count sentences based on punctuation."""
        return len(re.findall(SENTENCE_ENDINGS, text))

    @staticmethod
    def count_questions(text: str) -> int:
        return len(re.findall(QUESTION_PATTERN, text))

    @staticmethod
    def count_exclamations(text: str) -> int:
        return len(re.findall(EXCLAMATION_PATTERN, text))

    @staticmethod
    def count_paragraphs(text: str) -> int:
        """Count paragraphs (separated by double newlines)."""
        paragraphs = text.strip().split("\n\n")
        return len([p for p in paragraphs if p.strip()])

    @staticmethod
    def count_proper_nouns(words: List[str]) -> int:
        """Estimate proper nouns by counting capitalized words not at sentence start."""
        if not words:
            return 0

        # Reconstruct approximate positions
        proper_count = 0
        for i, word in enumerate(words):
            # Skip first word and words after punctuation
            if i > 0 and word[0].isupper() and len(word) > 1:
                proper_count += 1

        return proper_count

    @staticmethod
    def count_numbers(text: str) -> int:
        """Count numeric tokens in text."""
        # Match integers, decimals, and formatted numbers
        number_pattern = r"\b\d+(?:[.,]\d+)*\b"
        return len(re.findall(number_pattern, text))

    @staticmethod
    def starts_with_acknowledgment(message: str) -> bool:
        """Check if message starts with acknowledgment phrase."""
        return bool(ACKNOWLEDGMENT_REGEX.match(message.strip().lower()))

    @staticmethod
    def count_special_symbols(message: str) -> int:
        """Count emojis, arrows, math symbols, and other special characters."""
        emoji_count = len(EMOJI_PATTERN.findall(message))
        arrow_count = len(ARROW_PATTERN.findall(message))
        math_count = len(MATH_PATTERN.findall(message))

        # Count other special symbols not covered above
        other_count = 0
        for char in message:
            if char in ALL_SPECIAL_SYMBOLS and char not in "→←↑↓⟶⟵+-*/=≈≠≤≥<>":
                other_count += 1

        return emoji_count + arrow_count + math_count + other_count

    @staticmethod
    def calculate_punctuation_diversity(text: str) -> int:
        """Count unique punctuation marks used."""
        punctuation = set(re.findall(r"[^\w\s]", text))
        return len(punctuation)

    @staticmethod
    def get_word_frequencies(message: str) -> Tuple[Counter, Set[str]]:
        """Get word frequency counter and vocabulary set."""
        words = TextAnalyzer.tokenize(message)
        return Counter(words), set(words)

    @staticmethod
    def calculate_symbol_density(text: str) -> float:
        """Calculate non-alphabetic character density."""
        if not text:
            return 0.0

        # Count non-alphabetic characters (excluding spaces)
        non_alpha = sum(1 for char in text if not char.isalpha() and not char.isspace())
        return non_alpha / len(text)

    @staticmethod
    def count_emojis(text: str) -> int:
        """Count Unicode emoji characters."""
        return len(EMOJI_PATTERN.findall(text))

    @staticmethod
    def count_arrows(text: str) -> int:
        """Count arrow symbols (both ASCII and Unicode)."""
        return len(ARROW_PATTERN.findall(text))
