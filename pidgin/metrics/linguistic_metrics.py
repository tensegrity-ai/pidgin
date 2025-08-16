"""Linguistic and stylistic metrics for conversation analysis."""

import math
from collections import Counter
from typing import Dict, List

from .constants import (
    AGREEMENT_MARKERS,
    DISAGREEMENT_MARKERS,
    FIRST_PERSON_PLURAL,
    FIRST_PERSON_SINGULAR,
    HEDGE_WORDS,
    POLITENESS_MARKERS,
    SECOND_PERSON,
)


class LinguisticAnalyzer:
    """Calculates linguistic and stylistic metrics."""

    @staticmethod
    def calculate_entropy(counter: Counter) -> float:
        """Calculate Shannon entropy of word distribution."""
        if not counter:
            return 0.0

        total = sum(counter.values())
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in counter.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log2(prob)

        return entropy

    @staticmethod
    def calculate_character_entropy(text: str) -> float:
        """Calculate Shannon entropy of character distribution."""
        if not text:
            return 0.0

        # Count character frequencies
        char_counter = Counter(text)
        total = len(text)

        entropy = 0.0
        for count in char_counter.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log2(prob)

        return entropy

    @staticmethod
    def calculate_self_repetition(words: List[str]) -> float:
        """Calculate repetition within a single message."""
        if len(words) < 2:
            return 0.0

        # Count consecutive repeated words
        repetitions = sum(1 for i in range(1, len(words)) if words[i] == words[i - 1])

        # Normalize by message length
        return repetitions / (len(words) - 1)

    @staticmethod
    def calculate_lexical_diversity_index(
        word_count: int, vocabulary_size: int
    ) -> float:
        """Calculate lexical diversity (TTR variant)."""
        if word_count == 0:
            return 0.0
        # Use root TTR for length-independent measure
        return vocabulary_size / math.sqrt(word_count)

    @staticmethod
    def count_linguistic_markers(words: List[str]) -> Dict[str, int]:
        """Count various linguistic markers in the message."""
        words_lower = [w.lower() for w in words]

        return {
            "hedge_words": sum(1 for w in words_lower if w in HEDGE_WORDS),
            "agreement_markers": sum(1 for w in words_lower if w in AGREEMENT_MARKERS),
            "disagreement_markers": sum(
                1 for w in words_lower if w in DISAGREEMENT_MARKERS
            ),
            "politeness_markers": sum(
                1 for w in words_lower if w in POLITENESS_MARKERS
            ),
            "first_person_singular": sum(
                1 for w in words_lower if w in FIRST_PERSON_SINGULAR
            ),
            "first_person_plural": sum(
                1 for w in words_lower if w in FIRST_PERSON_PLURAL
            ),
            "second_person": sum(1 for w in words_lower if w in SECOND_PERSON),
        }

    @staticmethod
    def calculate_formality_score(text: str, words: List[str]) -> float:
        """Estimate formality based on various indicators."""
        if not words:
            return 0.5  # Neutral

        # Positive indicators of formality
        formal_score = 0.0

        # Contractions indicate informality
        contraction_count = len([w for w in words if "'" in w])
        formal_score -= (contraction_count / len(words)) * 0.3

        # Exclamations indicate informality
        exclamation_count = text.count("!")
        formal_score -= (exclamation_count / len(words)) * 0.2

        # Question marks are neutral, but multiple indicate informality
        multi_question = len(
            [i for i in range(len(text) - 1) if text[i : i + 2] == "??"]
        )
        formal_score -= (multi_question / len(words)) * 0.1

        # Long words indicate formality
        long_words = [w for w in words if len(w) > 7]
        formal_score += (len(long_words) / len(words)) * 0.3

        # Normalize to 0-1 range
        return max(0.0, min(1.0, 0.5 + formal_score))

    @staticmethod
    def calculate_hapax_legomena_ratio(word_counter: Counter) -> float:
        """Calculate ratio of words appearing only once."""
        if not word_counter:
            return 0.0

        hapax_count = sum(1 for count in word_counter.values() if count == 1)
        total_unique = len(word_counter)

        if total_unique == 0:
            return 0.0

        return hapax_count / total_unique

    @staticmethod
    def calculate_lexical_diversity_index_ngrams(words: List[str]) -> float:
        """Calculate LDI using bigrams and trigrams."""
        if len(words) < 3:
            return 0.0

        # Generate bigrams
        bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
        unique_bigrams = len(set(bigrams))
        total_bigrams = len(bigrams)

        # Generate trigrams
        trigrams = [
            (words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)
        ]
        unique_trigrams = len(set(trigrams))
        total_trigrams = len(trigrams)

        total = total_bigrams + total_trigrams
        if total == 0:
            return 0.0

        return (unique_bigrams + unique_trigrams) / total

    @staticmethod
    def count_repeated_ngrams(words: List[str]) -> Dict[str, int]:
        """Count repeated bigrams and trigrams in the message."""
        result = {"repeated_bigrams": 0, "repeated_trigrams": 0}

        if len(words) < 2:
            return result

        # Count bigrams
        bigram_counter: Counter[tuple[str, str]] = Counter()
        for i in range(len(words) - 1):
            bigram = (words[i].lower(), words[i + 1].lower())
            bigram_counter[bigram] += 1

        # Count bigrams appearing 2+ times
        result["repeated_bigrams"] = sum(
            1 for count in bigram_counter.values() if count >= 2
        )

        # Count trigrams if enough words
        if len(words) >= 3:
            trigram_counter: Counter[tuple[str, str, str]] = Counter()
            for i in range(len(words) - 2):
                trigram = (words[i].lower(), words[i + 1].lower(), words[i + 2].lower())
                trigram_counter[trigram] += 1

            # Count trigrams appearing 2+ times
            result["repeated_trigrams"] = sum(
                1 for count in trigram_counter.values() if count >= 2
            )

        return result

    @staticmethod
    def calculate_densities(words: List[str], sentences: List[str]) -> Dict[str, float]:
        """Calculate various linguistic densities."""
        word_count = len(words)
        sentence_count = len(sentences)

        # Count questions (sentences ending with ?)
        question_sentences = sum(1 for s in sentences if s.strip().endswith("?"))
        question_density = question_sentences / max(sentence_count, 1)

        # Hedge word density
        words_lower = [w.lower() for w in words]
        hedge_count = sum(1 for w in words_lower if w in HEDGE_WORDS)
        hedge_density = hedge_count / max(word_count, 1)

        return {"question_density": question_density, "hedge_density": hedge_density}
