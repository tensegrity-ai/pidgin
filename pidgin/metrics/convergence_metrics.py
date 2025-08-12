"""Convergence and similarity metrics for conversation analysis."""

import math
import zlib
from collections import Counter
from typing import Dict, List, Set

from .text_analysis import TextAnalyzer


class ConvergenceCalculator:
    """Calculates convergence-related metrics between messages."""

    @staticmethod
    def calculate_vocabulary_overlap(vocab_a: Set[str], vocab_b: Set[str]) -> float:
        """Calculate Jaccard similarity between vocabularies."""
        if not vocab_a or not vocab_b:
            return 0.0
        union = vocab_a | vocab_b
        if not union:
            return 0.0
        return len(vocab_a & vocab_b) / len(union)

    @staticmethod
    def calculate_mimicry_score(message_a: str, message_b: str) -> float:
        """Calculate how much message_b mimics phrases from message_a."""
        words_a = TextAnalyzer.tokenize(message_a.lower())
        words_b = TextAnalyzer.tokenize(message_b.lower())

        if not words_a or not words_b:
            return 0.0

        mimicry_score = 0.0

        # Check for copied phrases of different lengths
        for n in range(2, min(6, len(words_a), len(words_b)) + 1):
            ngrams_a = set(zip(*[words_a[i:] for i in range(n)]))
            ngrams_b = set(zip(*[words_b[i:] for i in range(n)]))

            if ngrams_a:
                overlap = len(ngrams_a & ngrams_b) / len(ngrams_a)
                # Weight longer phrases more heavily
                mimicry_score += overlap * (n - 1)

        # Normalize by maximum possible score
        max_n = min(6, len(words_a), len(words_b))
        if max_n > 1:
            max_score = sum(range(1, max_n))
            if max_score > 0:
                mimicry_score /= max_score

        return mimicry_score

    @staticmethod
    def calculate_cross_repetition(message_a: str, message_b: str) -> float:
        """Calculate word repetition between messages."""
        words_a = TextAnalyzer.tokenize(message_a.lower())
        words_b = TextAnalyzer.tokenize(message_b.lower())

        if not words_a or not words_b:
            return 0.0

        # Count shared words
        counter_a = Counter(words_a)
        counter_b = Counter(words_b)

        shared_count = 0
        for word in set(words_a) & set(words_b):
            shared_count += min(counter_a[word], counter_b[word])

        # Normalize by total words
        total_words = len(words_a) + len(words_b)
        return (2 * shared_count) / total_words if total_words > 0 else 0.0

    @staticmethod
    def calculate_structural_similarity(message_a: str, message_b: str) -> float:
        """Calculate structural similarity between messages."""
        sentences_a = TextAnalyzer.split_sentences(message_a)
        sentences_b = TextAnalyzer.split_sentences(message_b)

        # Compare sentence counts
        len_similarity = 1 - abs(len(sentences_a) - len(sentences_b)) / max(
            len(sentences_a), len(sentences_b), 1
        )

        # Compare average sentence lengths
        avg_len_a = sum(len(s.split()) for s in sentences_a) / max(len(sentences_a), 1)
        avg_len_b = sum(len(s.split()) for s in sentences_b) / max(len(sentences_b), 1)

        length_similarity = 1 - abs(avg_len_a - avg_len_b) / max(
            avg_len_a, avg_len_b, 1
        )

        # Weight both factors
        return 0.5 * len_similarity + 0.5 * length_similarity

    @staticmethod
    def calculate_compression_ratio(text: str) -> float:
        """Calculate compression ratio as a complexity metric."""
        if not text:
            return 0.0

        original_size = len(text.encode("utf-8"))
        compressed_size = len(zlib.compress(text.encode("utf-8")))

        ratio = compressed_size / original_size if original_size > 0 else 0.0
        # Cap the ratio at 2.0 to handle very short texts where overhead is high
        return min(ratio, 2.0)

    @staticmethod
    def calculate_overall_convergence_score(
        metrics: Dict[str, float], weights: Dict[str, float] = None
    ) -> float:
        """Calculate weighted average of multiple convergence metrics."""
        if not weights:
            # Default equal weights
            weights = {
                "vocabulary_overlap": 0.25,
                "cross_repetition": 0.25,
                "structural_similarity": 0.25,
                "mutual_mimicry": 0.25,
            }

        score = 0.0
        total_weight = 0.0

        for metric, weight in weights.items():
            if metric in metrics and metrics[metric] is not None:
                score += metrics[metric] * weight
                total_weight += weight

        return score / total_weight if total_weight > 0 else 0.0

    @staticmethod
    def calculate_message_length_ratio(len_a: int, len_b: int) -> float:
        """Calculate length ratio between messages."""
        if len_a == 0 and len_b == 0:
            return 1.0

        max_len = max(len_a, len_b)
        if max_len == 0:
            return 1.0

        return min(len_a, len_b) / max_len

    @staticmethod
    def calculate_sentence_pattern_similarity(
        sentences_a: List[str], sentences_b: List[str]
    ) -> float:
        """Calculate similarity of sentence count distributions."""
        if not sentences_a and not sentences_b:
            return 1.0

        # Get sentence length distributions
        lengths_a = [len(s.split()) for s in sentences_a]
        lengths_b = [len(s.split()) for s in sentences_b]

        # Create frequency distributions
        max_len = max(lengths_a + lengths_b) if (lengths_a or lengths_b) else 0
        if max_len == 0:
            return 1.0

        dist_a_int = [0] * (max_len + 1)
        dist_b_int = [0] * (max_len + 1)

        for length in lengths_a:
            dist_a_int[length] += 1
        for length in lengths_b:
            dist_b_int[length] += 1

        # Normalize
        total_a = sum(dist_a_int)
        total_b = sum(dist_b_int)

        if total_a > 0:
            dist_a = [x / total_a for x in dist_a_int]
        else:
            dist_a = [0.0] * len(dist_a_int)
        if total_b > 0:
            dist_b = [x / total_b for x in dist_b_int]
        else:
            dist_b = [0.0] * len(dist_b_int)

        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(dist_a, dist_b))
        norm_a = math.sqrt(sum(a * a for a in dist_a))
        norm_b = math.sqrt(sum(b * b for b in dist_b))

        if norm_a * norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @staticmethod
    def calculate_repetition_ratio(
        messages: List[str], min_phrase_length: int = 3
    ) -> float:
        """Calculate ratio of repeated phrases across messages."""
        if len(messages) < 2:
            return 0.0

        # Collect all n-grams of specified length or longer
        all_phrases = []

        for message in messages:
            words = TextAnalyzer.tokenize(message.lower())
            if len(words) >= min_phrase_length:
                # Extract phrases of minimum length
                for i in range(len(words) - min_phrase_length + 1):
                    phrase = tuple(words[i : i + min_phrase_length])
                    all_phrases.append(phrase)

        if not all_phrases:
            return 0.0

        # Count repeated phrases
        phrase_counter = Counter(all_phrases)
        repeated_phrases = sum(1 for count in phrase_counter.values() if count > 1)

        return repeated_phrases / len(all_phrases)
