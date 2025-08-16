"""Flat metrics calculator for DuckDB wide-table optimization."""

from collections import Counter
from typing import Any, Dict, List

from .convergence_metrics import ConvergenceCalculator
from .linguistic_metrics import LinguisticAnalyzer
from .text_analysis import TextAnalyzer


class FlatMetricsCalculator:
    """Calculates metrics in a flat structure optimized for DuckDB wide tables."""

    def __init__(self) -> None:
        """Initialize calculator with tracking structures."""
        # Cumulative vocabulary tracking
        self.cumulative_vocab: Dict[str, set] = {"agent_a": set(), "agent_b": set()}

        # All words seen by each agent
        self.all_agent_words: Dict[str, set] = {"agent_a": set(), "agent_b": set()}

        # Token cache to avoid re-tokenizing
        self._token_cache: Dict[str, List[str]] = {}
        self._cache_size_limit = 1000

        # Previous messages for context
        self.previous_messages: Dict[str, List[str]] = {"agent_a": [], "agent_b": []}

        # Track turn vocabularies
        self.turn_vocabularies: List[Dict[str, set]] = []

        # Initialize helper classes
        self.text_analyzer = TextAnalyzer()
        self.convergence_calc = ConvergenceCalculator()
        self.linguistic_analyzer = LinguisticAnalyzer()

        # Track all messages for repetition calculation
        self.all_messages: List[str] = []

    def _tokenize_cached(self, text: str) -> List[str]:
        """Tokenize with caching to avoid redundant processing."""
        if text in self._token_cache:
            return self._token_cache[text]

        tokens = self.text_analyzer.tokenize(text.lower())

        if len(self._token_cache) < self._cache_size_limit:
            self._token_cache[text] = tokens

        return tokens

    def calculate_turn_metrics(
        self, turn_number: int, agent_a_message: str, agent_b_message: str
    ) -> Dict[str, Any]:
        """Calculate all metrics for a turn as a flat dictionary.

        Args:
            turn_number: 0-indexed turn number
            agent_a_message: Message from agent A
            agent_b_message: Message from agent B

        Returns:
            Flat dictionary with prefixed keys (a_, b_, and convergence metrics)
        """
        # Calculate metrics for each agent
        metrics_a = self._calculate_message_metrics(
            agent_a_message, "agent_a", turn_number
        )
        metrics_b = self._calculate_message_metrics(
            agent_b_message, "agent_b", turn_number
        )

        # Calculate convergence metrics
        convergence = self._calculate_convergence(
            agent_a_message, agent_b_message, turn_number
        )

        # Update tracking structures for next turn
        self.previous_messages["agent_a"].append(agent_a_message)
        self.previous_messages["agent_b"].append(agent_b_message)
        self.all_messages.extend([agent_a_message, agent_b_message])

        # Build flat dictionary with prefixes
        flat_metrics = {}

        # Add agent A metrics with 'a_' prefix
        for key, value in metrics_a.items():
            # Skip sets and other non-serializable types
            if isinstance(value, (str, int, float, bool, type(None))):
                flat_metrics[f"a_{key}"] = value

        # Add agent B metrics with 'b_' prefix
        for key, value in metrics_b.items():
            # Skip sets and other non-serializable types
            if isinstance(value, (str, int, float, bool, type(None))):
                flat_metrics[f"b_{key}"] = value

        # Add convergence metrics without prefix
        for key, value in convergence.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                flat_metrics[key] = value

        return flat_metrics

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
        # avg_word_length = sum(len(w) for w in words) / max(word_count, 1)  # Not used currently
        avg_sentence_length = word_count / max(sentence_count, 1)

        # Linguistic analysis
        word_counter = Counter(words)
        linguistic_markers = self.linguistic_analyzer.count_linguistic_markers(words)
        entropy = self.linguistic_analyzer.calculate_entropy(word_counter)
        char_entropy = self.linguistic_analyzer.calculate_character_entropy(message)
        # lexical_diversity = self.linguistic_analyzer.calculate_lexical_diversity_index(
        #     word_count, vocab_size
        # )  # Not used currently
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
        # starts_with_ack = self.text_analyzer.starts_with_acknowledgment(message)  # Not used currently
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

        # Calculate new words
        new_words_set = unique_words - self.all_agent_words[agent]
        new_words_count = len(new_words_set)

        # Update agent's cumulative vocabulary
        self.cumulative_vocab[agent].update(unique_words)
        self.all_agent_words[agent].update(unique_words)

        # Create result dictionary (only serializable types)
        result = {
            # Basic counts
            "message_length": char_count,
            "character_count": char_count,  # Alias for consistency
            "word_count": word_count,
            "vocabulary_size": vocab_size,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "avg_sentence_length": avg_sentence_length,
            # Lexical diversity
            "unique_words": vocab_size,
            "ttr": vocab_size / max(word_count, 1),  # type-token ratio
            "hapax_ratio": hapax_ratio,
            "ldi": ldi_ngrams,
            "self_repetition": self_repetition,
            # Information theory
            "word_entropy": entropy,
            "character_entropy": char_entropy,
            "compression_ratio": compression_ratio,
            # Symbol & punctuation
            "symbol_density": symbol_density,
            "emoji_count": emoji_count,
            "arrow_count": arrow_count,
            "math_symbol_count": 0,
            "punctuation_diversity": punctuation_diversity,
            "special_char_count": special_symbol_count,
            "number_count": number_count,
            "proper_noun_count": proper_noun_count,
            # Linguistic patterns
            "question_count": question_count,
            "exclamation_count": exclamation_count,
            "formality_score": formality_score,
            "emotional_intensity": 0.0,
            # Advanced linguistic (placeholders for now)
            "syntactic_complexity": 0.0,
            "semantic_density": 0.0,
            "coherence_score": 0.0,
            "readability_score": 0.0,
            "cognitive_load": 0.0,
            "information_density": 0.0,
            "discourse_markers": 0,
            # Research-specific patterns (placeholders)
            "gratitude_markers": 0,
            "existential_language": 0,
            "compression_indicators": 0,
            "novel_symbols": 0,
            "meta_commentary": 0,
            # Repetition
            "turn_repetition": repetition,
            "new_words": new_words_count,
        }

        # Add linguistic markers
        result.update(linguistic_markers)

        # Add repeated ngrams
        result.update(repeated_ngrams)

        # Add densities
        result.update(densities)

        return result

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

        # Cumulative overlap
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

        # Length convergence
        length_ratio = self.convergence_calc.calculate_message_length_ratio(
            len(message_a), len(message_b)
        )
        length_convergence = 1.0 - abs(
            length_ratio - 1.0
        )  # Closer to 1 = more convergent

        # Sentence pattern similarity
        self.text_analyzer.split_sentences(message_a)
        self.text_analyzer.split_sentences(message_b)
        # sentence_pattern_similarity = (
        #     self.convergence_calc.calculate_sentence_pattern_similarity(
        #         sentences_a, sentences_b
        #     )
        # )  # Not used currently

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

        # Calculate repetition ratio if we have enough messages
        if len(self.all_messages) >= 4:  # At least 2 turns
            # repetition_ratio = self.convergence_calc.calculate_repetition_ratio(
            #     self.all_messages[-10:]  # Use last 5 turns (10 messages)
            # )  # Not used currently
            pass

        return {
            "vocabulary_overlap": current_overlap,
            "length_convergence": length_convergence,
            "style_similarity": structural_similarity,
            "structural_similarity": structural_similarity,
            "semantic_similarity": 0.0,
            "mimicry_score_a_to_b": mimicry_a_to_b or 0.0,
            "mimicry_score_b_to_a": mimicry_b_to_a or 0.0,
            "sentiment_convergence": 0.0,
            "formality_convergence": 0.0,
            "rhythm_convergence": 0.0,
            "overall_convergence": overall_convergence,
            "convergence_velocity": 0.0,
            "turn_taking_balance": 0.5,
            "topic_consistency": 0.0,
            "phrase_alignment": cross_repetition,
            "syntactic_convergence": 0.0,
            "lexical_entrainment": current_overlap,
            "prosodic_alignment": 0.0,
            "discourse_coherence": 0.0,
            "cumulative_convergence": cumulative_overlap,
        }

    def _calculate_repetition(
        self, current_words: List[str], agent: str, turn_number: int
    ) -> float:
        """Calculate repetition relative to previous messages."""
        if turn_number == 0:
            return 0.0

        # Get previous messages for this agent
        prev_messages = self.previous_messages[agent]
        if not prev_messages:
            return 0.0

        # Calculate overlap with previous messages
        current_set = set(current_words)
        total_overlap = 0.0

        for prev_msg in prev_messages:
            prev_words = set(self._tokenize_cached(prev_msg))
            if prev_words:
                overlap = len(current_set.intersection(prev_words)) / len(prev_words)
                total_overlap += overlap

        return total_overlap / len(prev_messages)
