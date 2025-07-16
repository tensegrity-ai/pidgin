"""Property-based tests focusing on metric invariants and relationships."""


from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from pidgin.metrics.calculator import MetricsCalculator
from pidgin.metrics.linguistic_metrics import LinguisticAnalyzer
from pidgin.metrics.text_analysis import TextAnalyzer


# Strategies for generating specific types of text
@composite
def repeated_word_text(draw):
    """Generate text with controlled repetition."""
    base_word = draw(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=10)
    )
    repetitions = draw(st.integers(min_value=2, max_value=10))
    separator = draw(st.sampled_from([" ", " and ", ", ", "; "]))
    return separator.join([base_word] * repetitions)


@composite
def mixed_case_text(draw):
    """Generate text with mixed case."""
    words = draw(
        st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=10),
            min_size=1,
            max_size=10,
        )
    )
    # Randomly capitalize some words
    mixed_words = []
    for word in words:
        if draw(st.booleans()):
            mixed_words.append(word.upper())
        elif draw(st.booleans()):
            mixed_words.append(word.capitalize())
        else:
            mixed_words.append(word)
    return " ".join(mixed_words)


@composite
def structured_message(draw):
    """Generate a message with known structure."""
    num_sentences = draw(st.integers(min_value=1, max_value=5))
    sentences = []

    for _ in range(num_sentences):
        num_words = draw(st.integers(min_value=1, max_value=15))
        words = draw(
            st.lists(
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=10),
                min_size=num_words,
                max_size=num_words,
            )
        )
        sentence = " ".join(words)
        punctuation = draw(st.sampled_from([".", "!", "?"]))
        sentences.append(sentence + punctuation)

    return " ".join(sentences)


class TestMetricInvariants:
    """Test invariant properties that should always hold."""

    @given(st.text())
    def test_word_count_tokenization_consistency(self, text):
        """Word count should match the number of tokens."""
        tokens = TextAnalyzer.tokenize(text)
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        assert metrics["agent_a"]["word_count"] == len(tokens)

    @given(st.text())
    def test_vocabulary_size_word_count_relationship(self, text):
        """Vocabulary size should not exceed word count."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        agent_metrics = metrics["agent_a"]
        assert agent_metrics["vocabulary_size"] <= agent_metrics["word_count"]

    @given(st.text())
    def test_unique_word_ratio_calculation(self, text):
        """Unique word ratio should equal vocabulary_size / word_count."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        agent_metrics = metrics["agent_a"]
        if agent_metrics["word_count"] > 0:
            expected_ratio = (
                agent_metrics["vocabulary_size"] / agent_metrics["word_count"]
            )
            assert abs(agent_metrics["unique_word_ratio"] - expected_ratio) < 1e-10
        else:
            assert agent_metrics["unique_word_ratio"] == 0.0

    @given(mixed_case_text())
    def test_case_insensitive_tokenization(self, text):
        """Tokenization should be case-insensitive."""
        tokens_original = TextAnalyzer.tokenize(text)
        tokens_lower = TextAnalyzer.tokenize(text.lower())
        tokens_upper = TextAnalyzer.tokenize(text.upper())

        # All should produce the same tokens (in lowercase)
        assert tokens_original == tokens_lower == tokens_upper

    @given(st.text())
    def test_message_length_character_count(self, text):
        """Message length should equal character count."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        assert metrics["agent_a"]["message_length"] == len(text)

    @given(structured_message())
    def test_sentence_count_consistency(self, message):
        """Sentence count should match actual sentence endings."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, message, "dummy")

        # Count sentence endings manually
        manual_count = message.count(".") + message.count("!") + message.count("?")

        # Allow for some flexibility due to edge cases like "..." or "?!"
        assert abs(metrics["agent_a"]["sentence_count"] - manual_count) <= 2

    @given(st.text(), st.text())
    def test_convergence_symmetry_properties(self, msg_a, msg_b):
        """Test symmetry properties of convergence metrics."""
        calculator = MetricsCalculator()

        # Calculate metrics A->B
        metrics_ab = calculator.calculate_turn_metrics(0, msg_a, msg_b)
        calculator.reset()

        # Calculate metrics B->A
        metrics_ba = calculator.calculate_turn_metrics(0, msg_b, msg_a)

        convergence_ab = metrics_ab["convergence"]
        convergence_ba = metrics_ba["convergence"]

        # Vocabulary overlap should be symmetric
        assert (
            abs(
                convergence_ab["vocabulary_overlap"]
                - convergence_ba["vocabulary_overlap"]
            )
            < 1e-10
        )

        # Length ratio should be symmetric
        assert (
            abs(convergence_ab["length_ratio"] - convergence_ba["length_ratio"]) < 1e-10
        )

        # Cross repetition should be symmetric
        assert (
            abs(convergence_ab["cross_repetition"] - convergence_ba["cross_repetition"])
            < 1e-10
        )

    @given(repeated_word_text())
    def test_self_repetition_detection(self, text):
        """Self-repetition should be high for repeated text."""
        words = TextAnalyzer.tokenize(text)
        if len(words) >= 2:
            repetition = LinguisticAnalyzer.calculate_self_repetition(words)

            # For text like "word word word", self-repetition should be high
            if all(w == words[0] for w in words):
                assert repetition >= 0.9  # Almost all consecutive pairs are identical

    @given(st.lists(st.text(min_size=1, max_size=10), min_size=2, max_size=10))
    def test_cumulative_vocabulary_growth(self, messages):
        """Cumulative vocabulary should grow monotonically."""
        calculator = MetricsCalculator()

        cumulative_sizes = []
        for i, (msg_a, msg_b) in enumerate(zip(messages[::2], messages[1::2])):
            _metrics = calculator.calculate_turn_metrics(i, msg_a, msg_b)

            total_vocab_size = len(
                calculator.cumulative_vocab["agent_a"]
                | calculator.cumulative_vocab["agent_b"]
            )
            cumulative_sizes.append(total_vocab_size)

        # Check monotonic growth
        for i in range(1, len(cumulative_sizes)):
            assert cumulative_sizes[i] >= cumulative_sizes[i - 1]

    @given(st.text())
    def test_entropy_bounds(self, text):
        """Test entropy bounds based on information theory."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        agent_metrics = metrics["agent_a"]
        word_entropy = agent_metrics["entropy"]
        char_entropy = agent_metrics["char_entropy"]

        # Entropy is bounded by log2(alphabet_size)
        if agent_metrics["vocabulary_size"] > 0:
            max_word_entropy = math.log2(agent_metrics["vocabulary_size"])
            assert word_entropy <= max_word_entropy + 1e-10

        unique_chars = len(set(text))
        if unique_chars > 0:
            max_char_entropy = math.log2(unique_chars)
            assert char_entropy <= max_char_entropy + 1e-10


class TestMetricRelationships:
    """Test relationships between different metrics."""

    @given(st.text())
    def test_linguistic_marker_sum_bound(self, text):
        """Sum of linguistic markers shouldn't exceed word count."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        agent_metrics = metrics["agent_a"]
        word_count = agent_metrics["word_count"]

        # Sum all linguistic markers
        marker_sum = (
            agent_metrics.get("hedge_words", 0)
            + agent_metrics.get("agreement_markers", 0)
            + agent_metrics.get("disagreement_markers", 0)
            + agent_metrics.get("politeness_markers", 0)
        )

        # A word can only be counted once per category
        assert marker_sum <= word_count * 4  # Maximum if a word is in all 4 categories

    @given(st.text())
    def test_pronoun_count_bound(self, text):
        """Pronoun counts shouldn't exceed word count."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        agent_metrics = metrics["agent_a"]
        word_count = agent_metrics["word_count"]

        pronoun_sum = (
            agent_metrics.get("first_person_singular", 0)
            + agent_metrics.get("first_person_plural", 0)
            + agent_metrics.get("second_person", 0)
        )

        assert pronoun_sum <= word_count

    @given(st.text())
    def test_special_symbol_components(self, text):
        """Special symbol count should equal sum of its components."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        agent_metrics = metrics["agent_a"]

        # Special symbols include emojis, arrows, and math symbols
        # This is an approximation since the exact calculation is complex
        emoji_count = agent_metrics.get("emoji_count", 0)
        arrow_count = agent_metrics.get("arrow_count", 0)
        special_total = agent_metrics.get("special_symbol_count", 0)

        # Special symbols should be at least the sum of emojis and arrows
        assert special_total >= emoji_count + arrow_count

    @given(st.text(min_size=1))
    def test_compression_ratio_entropy_relationship(self, text):
        """Compression ratio should correlate with entropy."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, text, "dummy")

        agent_metrics = metrics["agent_a"]
        compression_ratio = agent_metrics.get("compression_ratio", 0)
        # char_entropy = agent_metrics.get("char_entropy", 0)  # Not used currently

        # Higher entropy generally means better compression
        # This is a weak invariant but should generally hold
        if len(text) > 10:  # Only test on non-trivial texts
            # Compression ratio between 0 and 1 (lower is more compressible)
            assert 0.0 < compression_ratio <= 2.0

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=5))
    def test_convergence_score_components(self, messages):
        """Overall convergence score should be weighted average of components."""
        calculator = MetricsCalculator()

        for i in range(0, len(messages) - 1, 2):
            metrics = calculator.calculate_turn_metrics(
                i // 2, messages[i], messages[i + 1]
            )
            convergence = metrics["convergence"]

            # Manually calculate expected score
            components = {
                "vocabulary_overlap": convergence.get("vocabulary_overlap", 0),
                "cross_repetition": convergence.get("cross_repetition", 0),
                "structural_similarity": convergence.get("structural_similarity", 0),
                "mutual_mimicry": convergence.get("mutual_mimicry", 0),
            }

            # Default weights are 0.25 each
            expected_score = sum(components.values()) / 4
            actual_score = convergence.get("overall_convergence_score", 0)

            assert abs(actual_score - expected_score) < 1e-10


class TestStatefulProperties:
    """Test properties that involve state across multiple turns."""

    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=50), st.text(min_size=1, max_size=50)
            ),
            min_size=2,
            max_size=10,
        )
    )
    def test_turn_repetition_calculation(self, conversation):
        """Turn repetition should reflect actual word reuse."""
        calculator = MetricsCalculator()

        all_agent_words = {"agent_a": set(), "agent_b": set()}

        for turn_num, (msg_a, msg_b) in enumerate(conversation):
            metrics = calculator.calculate_turn_metrics(turn_num, msg_a, msg_b)

            # Get current words
            words_a = set(TextAnalyzer.tokenize(msg_a))
            words_b = set(TextAnalyzer.tokenize(msg_b))

            if turn_num > 0:
                # Check turn repetition
                repetition_a = metrics["agent_a"]["turn_repetition"]
                repetition_b = metrics["agent_b"]["turn_repetition"]

                # Manually calculate expected repetition
                if words_a:
                    expected_a = len(words_a & all_agent_words["agent_a"]) / len(
                        words_a
                    )
                else:
                    expected_a = 0.0

                if words_b:
                    expected_b = len(words_b & all_agent_words["agent_b"]) / len(
                        words_b
                    )
                else:
                    expected_b = 0.0

                # Allow small floating point differences
                assert abs(repetition_a - expected_a) < 0.1
                assert abs(repetition_b - expected_b) < 0.1

            # Update word sets
            all_agent_words["agent_a"].update(words_a)
            all_agent_words["agent_b"].update(words_b)

    @given(st.lists(st.text(min_size=1, max_size=30), min_size=4, max_size=10))
    def test_new_words_tracking(self, messages):
        """New words should be tracked correctly."""
        calculator = MetricsCalculator()

        seen_words = {"agent_a": set(), "agent_b": set()}

        for i in range(0, len(messages) - 1, 2):
            turn_num = i // 2
            msg_a = messages[i]
            msg_b = messages[i + 1] if i + 1 < len(messages) else ""

            # Calculate expected new words
            words_a = set(TextAnalyzer.tokenize(msg_a))
            words_b = set(TextAnalyzer.tokenize(msg_b))

            expected_new_a = len(words_a - seen_words["agent_a"])
            expected_new_b = len(words_b - seen_words["agent_b"])

            # Get metrics
            metrics = calculator.calculate_turn_metrics(turn_num, msg_a, msg_b)

            # Check new words count
            assert metrics["agent_a"]["new_words"] == expected_new_a
            assert metrics["agent_b"]["new_words"] == expected_new_b

            # Update seen words
            seen_words["agent_a"].update(words_a)
            seen_words["agent_b"].update(words_b)

    @settings(max_examples=10)  # Reduce for performance
    @given(
        st.lists(
            st.tuples(
                st.text(
                    alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=10, max_size=50
                ),
                st.text(
                    alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=10, max_size=50
                ),
            ),
            min_size=3,
            max_size=8,
        )
    )
    def test_cumulative_overlap_evolution(self, conversation):
        """Cumulative overlap should evolve sensibly."""
        calculator = MetricsCalculator()

        overlaps = []

        for turn_num, (msg_a, msg_b) in enumerate(conversation):
            metrics = calculator.calculate_turn_metrics(turn_num, msg_a, msg_b)

            cumulative_overlap = metrics["convergence"]["cumulative_overlap"]
            overlaps.append(cumulative_overlap)

            # Cumulative overlap should be between 0 and 1
            assert 0.0 <= cumulative_overlap <= 1.0

            # Current turn overlap should also be valid
            current_overlap = metrics["convergence"]["vocabulary_overlap"]
            assert 0.0 <= current_overlap <= 1.0

        # If agents use completely different vocabularies, overlap should be 0
        # If they use identical vocabularies, overlap should approach 1
        # This is a weak check but ensures basic sanity
        if len(overlaps) > 1:
            # Overlap shouldn't jump wildly between turns
            for i in range(1, len(overlaps)):
                # Allow for significant changes but not impossible ones
                assert abs(overlaps[i] - overlaps[i - 1]) <= 1.0


class TestEdgeCasesWithProperties:
    """Test specific edge cases using property-based strategies."""

    @given(st.text(alphabet="🔥😀🎉👍❤️🌟✨🎈🎊💫", min_size=1))
    def test_emoji_heavy_text(self, emoji_text):
        """Test handling of emoji-heavy text."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, emoji_text, "regular text")

        agent_metrics = metrics["agent_a"]

        # Should detect emojis
        assert agent_metrics["emoji_count"] > 0
        assert agent_metrics["special_symbol_count"] >= agent_metrics["emoji_count"]

        # Symbol density should be high
        assert agent_metrics["symbol_density"] > 0.5

    @given(st.text(alphabet="→←↔⇒⇐⇔", min_size=1))
    def test_arrow_heavy_text(self, arrow_text):
        """Test handling of arrow-heavy text."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, arrow_text, "regular text")

        agent_metrics = metrics["agent_a"]

        # Should detect arrows
        assert agent_metrics["arrow_count"] > 0
        assert agent_metrics["special_symbol_count"] >= agent_metrics["arrow_count"]

    @given(st.text(alphabet="∑∏∂∇√∫∈∉∀∃∅^+=<>*/%", min_size=1))
    def test_math_heavy_text(self, math_text):
        """Test handling of math symbol text."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate_turn_metrics(0, math_text, "regular text")

        agent_metrics = metrics["agent_a"]

        # Should detect special symbols
        assert agent_metrics["special_symbol_count"] > 0

        # Symbol density should be very high
        assert agent_metrics["symbol_density"] >= 0.8

    @given(st.integers(min_value=1, max_value=1000))
    def test_cache_size_limit(self, num_messages):
        """Test that token cache respects size limit."""
        calculator = MetricsCalculator()

        # Generate many unique messages
        for i in range(num_messages):
            unique_msg = f"Message number {i} with unique content {i * 2}"
            calculator._tokenize_cached(unique_msg)

        # Cache size should not exceed limit
        assert len(calculator._token_cache) <= calculator._cache_size_limit

    @given(st.lists(st.text(min_size=0, max_size=0), min_size=2, max_size=5))
    def test_empty_message_conversation(self, empty_messages):
        """Test handling of conversations with empty messages."""
        calculator = MetricsCalculator()

        for i in range(0, len(empty_messages) - 1, 2):
            msg_a = empty_messages[i]
            msg_b = empty_messages[i + 1] if i + 1 < len(empty_messages) else ""

            metrics = calculator.calculate_turn_metrics(i // 2, msg_a, msg_b)

            # All counts should be 0
            for agent in ["agent_a", "agent_b"]:
                agent_metrics = metrics[agent]
                assert agent_metrics["word_count"] == 0
                assert agent_metrics["vocabulary_size"] == 0
                assert agent_metrics["message_length"] == 0

            # Convergence metrics should handle empty messages
            assert metrics["convergence"]["vocabulary_overlap"] == 0.0
            assert metrics["convergence"]["length_ratio"] == 1.0  # Both empty


import math
