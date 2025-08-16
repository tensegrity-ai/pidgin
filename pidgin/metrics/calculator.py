"""Comprehensive metrics calculator for conversation analysis."""

from collections import Counter
from typing import Any, Dict, List, Set

from .convergence_metrics import ConvergenceCalculator
from .linguistic_metrics import LinguisticAnalyzer
from .text_analysis import TextAnalyzer


class MetricsCalculator:
    """Calculates comprehensive metrics for conversation turns with caching."""

    def __init__(self) -> None:
        """Initialize calculator with tracking structures for efficient computation."""
        # Cumulative vocabulary tracking (incrementally updated)
        self.cumulative_vocab: Dict[str, set] = {"agent_a": set(), "agent_b": set()}

        # All words seen by each agent (for repetition calculation)
        self.all_agent_words: Dict[str, set] = {"agent_a": set(), "agent_b": set()}

        # Token cache to avoid re-tokenizing
        self._token_cache: Dict[str, List[str]] = {}
        self._cache_size_limit = 1000  # Limit cache size

        # Previous messages for context
        self.previous_messages: Dict[str, List[str]] = {"agent_a": [], "agent_b": []}

        # Track turn vocabularies for other analyses
        self.turn_vocabularies: List[Dict[str, Set[str]]] = []

        # Initialize helper classes
        self.text_analyzer = TextAnalyzer()
        self.convergence_calc = ConvergenceCalculator()
        self.linguistic_analyzer = LinguisticAnalyzer()

    def _tokenize_cached(self, text: str) -> List[str]:
        """Tokenize with caching to avoid redundant processing."""
        # Check cache
        if text in self._token_cache:
            return self._token_cache[text]

        # Tokenize
        tokens = self.text_analyzer.tokenize(text.lower())

        # Add to cache if within size limit
        if len(self._token_cache) < self._cache_size_limit:
            self._token_cache[text] = tokens

        return tokens

    def calculate_turn_metrics(
        self, turn_number: int, agent_a_message: str, agent_b_message: str
    ) -> Dict[str, Any]:
        """Calculate all metrics for a turn.

        Args:
            turn_number: 0-indexed turn number
            agent_a_message: Message from agent A
            agent_b_message: Message from agent B

        Returns:
            Dictionary with all calculated metrics
        """
        # Calculate metrics for each agent
        metrics_a = self._calculate_message_metrics(
            agent_a_message, "agent_a", turn_number
        )
        metrics_b = self._calculate_message_metrics(
            agent_b_message, "agent_b", turn_number
        )

        # Calculate convergence metrics with optimization
        convergence = self._calculate_convergence(
            agent_a_message, agent_b_message, turn_number
        )

        # Update tracking structures for next turn
        self.previous_messages["agent_a"].append(agent_a_message)
        self.previous_messages["agent_b"].append(agent_b_message)

        # Combine all metrics
        return {
            "turn_number": turn_number,
            "agent_a": metrics_a,
            "agent_b": metrics_b,
            "convergence": convergence,
        }

    def _calculate_message_metrics(
        self, message: str, agent: str, turn_number: int
    ) -> Dict[str, Any]:
        """Calculate metrics for a single message."""
        # Use cached tokenization
        words = self._tokenize_cached(message)
        sentences = self.text_analyzer.split_sentences(message)

        # Basic metrics
        word_count = len(words)
        sentence_count = len(sentences)
        char_count = len(message)

        # Vocabulary analysis
        unique_words = set(words)
        vocab_size = len(unique_words)

        # Safe division with guards
        avg_word_length = sum(len(w) for w in words) / max(word_count, 1)
        avg_sentence_length = word_count / max(sentence_count, 1)

        # Linguistic analysis
        word_counter = Counter(words)
        linguistic_markers = self.linguistic_analyzer.count_linguistic_markers(words)
        entropy = self.linguistic_analyzer.calculate_entropy(word_counter)
        char_entropy = self.linguistic_analyzer.calculate_character_entropy(message)
        lexical_diversity = self.linguistic_analyzer.calculate_lexical_diversity_index(
            word_count, vocab_size
        )
        self_repetition = self.linguistic_analyzer.calculate_self_repetition(words)
        formality_score = self.linguistic_analyzer.calculate_formality_score(
            message, words
        )

        # New linguistic metrics
        hapax_ratio = self.linguistic_analyzer.calculate_hapax_legomena_ratio(
            word_counter
        )
        ldi_ngrams = self.linguistic_analyzer.calculate_lexical_diversity_index_ngrams(
            words
        )
        repeated_ngrams = self.linguistic_analyzer.count_repeated_ngrams(words)
        densities = self.linguistic_analyzer.calculate_densities(words, sentences)

        # Text analysis metrics
        question_count = self.text_analyzer.count_questions(message)
        exclamation_count = self.text_analyzer.count_exclamations(message)
        paragraph_count = self.text_analyzer.count_paragraphs(message)
        punctuation_diversity = self.text_analyzer.calculate_punctuation_diversity(
            message
        )
        starts_with_ack = self.text_analyzer.starts_with_acknowledgment(message)
        compression_ratio = self.convergence_calc.calculate_compression_ratio(message)

        # Special elements
        special_symbol_count = self.text_analyzer.count_special_symbols(message)
        number_count = self.text_analyzer.count_numbers(message)
        proper_noun_count = self.text_analyzer.count_proper_nouns(words)

        # New symbol metrics
        symbol_density = self.text_analyzer.calculate_symbol_density(message)
        emoji_count = self.text_analyzer.count_emojis(message)
        arrow_count = self.text_analyzer.count_arrows(message)

        # Repetition calculation
        repetition = self._calculate_repetition(words, agent, turn_number)

        # Calculate new words (words not seen before by this agent)
        new_words_set = unique_words - self.all_agent_words[agent]
        new_words_count = len(new_words_set)

        # Update agent's cumulative vocabulary
        self.cumulative_vocab[agent].update(unique_words)
        self.all_agent_words[agent].update(unique_words)

        return {
            # Basic counts
            "message_length": char_count,
            "word_count": word_count,
            "vocabulary_size": vocab_size,
            "vocabulary": unique_words,
            # Structure
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "avg_word_length": avg_word_length,
            "avg_sentence_length": avg_sentence_length,
            # Content types
            "question_count": question_count,
            "exclamation_count": exclamation_count,
            "special_symbol_count": special_symbol_count,
            "number_count": number_count,
            "proper_noun_count": proper_noun_count,
            "emoji_count": emoji_count,
            "arrow_count": arrow_count,
            "symbol_density": symbol_density,
            **densities,  # question_density, hedge_density
            # Linguistic markers
            **linguistic_markers,
            # Complexity
            "entropy": entropy,
            "char_entropy": char_entropy,
            "compression_ratio": compression_ratio,
            "lexical_diversity": lexical_diversity,
            "lexical_diversity_index": ldi_ngrams,
            "punctuation_diversity": punctuation_diversity,
            "hapax_ratio": hapax_ratio,
            # Repetition
            "self_repetition": self_repetition,
            "turn_repetition": repetition,  # This is what import_service expects
            **repeated_ngrams,  # repeated_bigrams, repeated_trigrams
            # Style
            "formality_score": formality_score,
            "starts_with_acknowledgment": starts_with_ack,
            "unique_word_ratio": vocab_size / max(word_count, 1),
            # New words
            "new_words": new_words_count,
        }

    def _calculate_convergence(
        self, message_a: str, message_b: str, turn_number: int
    ) -> Dict[str, float]:
        """Calculate convergence metrics between messages."""
        # Get vocabularies for this turn
        words_a = set(self._tokenize_cached(message_a))
        words_b = set(self._tokenize_cached(message_b))

        # Store turn vocabulary
        turn_vocab = {"agent_a": words_a, "agent_b": words_b}
        self.turn_vocabularies.append(turn_vocab)

        # Current turn overlap
        current_overlap = self.convergence_calc.calculate_vocabulary_overlap(
            words_a, words_b
        )

        # Cumulative overlap (using already updated cumulative sets)
        cumulative_overlap = self.convergence_calc.calculate_vocabulary_overlap(
            self.cumulative_vocab["agent_a"], self.cumulative_vocab["agent_b"]
        )

        # Other convergence metrics
        cross_repetition = self.convergence_calc.calculate_cross_repetition(
            message_a, message_b
        )
        structural_similarity = self.convergence_calc.calculate_structural_similarity(
            message_a, message_b
        )

        # Mimicry (check both directions)
        mimicry_a_to_b = self.convergence_calc.calculate_mimicry_score(
            message_a, message_b
        )
        mimicry_b_to_a = self.convergence_calc.calculate_mimicry_score(
            message_b, message_a
        )

        # Safe division for mutual mimicry
        mutual_mimicry = (
            (mimicry_a_to_b + mimicry_b_to_a) / 2
            if mimicry_a_to_b is not None and mimicry_b_to_a is not None
            else 0.0
        )

        # New convergence metrics
        length_ratio = self.convergence_calc.calculate_message_length_ratio(
            len(message_a), len(message_b)
        )

        sentences_a = self.text_analyzer.split_sentences(message_a)
        sentences_b = self.text_analyzer.split_sentences(message_b)
        sentence_pattern_similarity = (
            self.convergence_calc.calculate_sentence_pattern_similarity(
                sentences_a, sentences_b
            )
        )

        # Calculate overall convergence score
        convergence_metrics = {
            "vocabulary_overlap": current_overlap,
            "cross_repetition": cross_repetition,
            "structural_similarity": structural_similarity,
            "mutual_mimicry": mutual_mimicry,
        }
        overall_convergence = self.convergence_calc.calculate_overall_convergence_score(
            convergence_metrics
        )

        # Track messages for repetition ratio calculation
        if not hasattr(self, "all_messages"):
            self.all_messages = []
        self.all_messages.extend([message_a, message_b])

        # Calculate repetition ratio if we have enough messages
        repetition_ratio = 0.0
        if len(self.all_messages) >= 4:  # At least 2 turns
            repetition_ratio = self.convergence_calc.calculate_repetition_ratio(
                self.all_messages[-10:]  # Use last 5 turns (10 messages)
            )

        return {
            "vocabulary_overlap": current_overlap,
            "cumulative_overlap": cumulative_overlap,
            "cross_repetition": cross_repetition,
            "structural_similarity": structural_similarity,
            "mimicry_a_to_b": mimicry_a_to_b,
            "mimicry_b_to_a": mimicry_b_to_a,
            "mutual_mimicry": mutual_mimicry,
            "length_ratio": length_ratio,
            "sentence_pattern_similarity": sentence_pattern_similarity,
            "overall_convergence_score": overall_convergence,
            "repetition_ratio": repetition_ratio,
        }

    def _calculate_repetition(
        self, current_words: List[str], agent: str, turn_number: int
    ) -> float:
        """Calculate repetition relative to previous messages."""
        if turn_number == 0:
            return 0.0

        current_word_set = set(current_words)
        if not current_word_set:
            return 0.0

        # Use all previous words for this agent (not excluding current words)
        previous_words = self.all_agent_words[agent]

        if not previous_words:
            return 0.0

        overlap = len(current_word_set & previous_words)
        return overlap / len(current_word_set)

    def reset(self):
        """Reset calculator state for new conversation."""
        self.cumulative_vocab = {"agent_a": set(), "agent_b": set()}
        self.all_agent_words = {"agent_a": set(), "agent_b": set()}
        self.previous_messages = {"agent_a": [], "agent_b": []}
        self.turn_vocabularies = []
        self._token_cache.clear()
        self.all_messages = []
