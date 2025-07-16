"""Tests for metrics display module."""


from pidgin.metrics.display import (
    calculate_structural_similarity,
    calculate_turn_metrics,
    count_emojis,
    update_phase_detection,
)


class TestCalculateTurnMetrics:
    """Test turn metrics calculation."""

    def test_basic_text(self):
        """Test metrics for basic text."""
        result = calculate_turn_metrics("Hello world. How are you?")

        assert result["length"] == 25
        assert result["sentences"] == 2
        assert result["word_diversity"] == 1.0  # All unique words
        assert result["emoji_density"] == 0.0
        assert result["emoji_count"] == 0

    def test_empty_text(self):
        """Test metrics for empty text."""
        result = calculate_turn_metrics("")

        assert result["length"] == 0
        assert result["sentences"] == 1  # Default to 1
        assert result["word_diversity"] == 0
        assert result["emoji_density"] == 0.0
        assert result["emoji_count"] == 0

    def test_text_with_emojis(self):
        """Test metrics for text with emojis."""
        result = calculate_turn_metrics("Hello 😊 world! 🌍")

        # Emojis can be multi-byte, so length might vary
        assert result["length"] > 10
        assert result["sentences"] == 1
        assert result["emoji_count"] >= 2  # At least 2 emojis
        assert result["emoji_density"] > 0

    def test_repeated_words(self):
        """Test word diversity with repeated words."""
        result = calculate_turn_metrics("hello hello world world")

        assert result["word_diversity"] == 0.5  # 2 unique out of 4 total

    def test_punctuation_only(self):
        """Test text with only punctuation."""
        result = calculate_turn_metrics("...")

        assert result["length"] == 3
        assert result["sentences"] == 1  # Defaults to 1
        assert result["word_diversity"] == 0  # No words


class TestCountEmojis:
    """Test emoji counting."""

    def test_no_emojis(self):
        """Test text without emojis."""
        assert count_emojis("Hello world") == 0

    def test_single_emoji(self):
        """Test single emoji."""
        assert count_emojis("Hello 😊") == 1

    def test_multiple_emojis(self):
        """Test multiple emojis."""
        # Should count at least the visible emojis
        assert count_emojis("😊🌍🎉") >= 3

    def test_mixed_symbols(self):
        """Test mix of emojis and other symbols."""
        # Mathematical symbols are So category but not emojis
        assert count_emojis("2 + 2 = 4 😊") == 1

    def test_unicode_symbols(self):
        """Test various Unicode symbols."""
        # These are in Symbol, Other category
        assert count_emojis("♠♣♥♦") >= 4


class TestCalculateStructuralSimilarity:
    """Test structural similarity calculation."""

    def test_identical_messages(self):
        """Test identical message patterns."""
        messages_a = ["Hello", "How are you?", "Good!"]
        messages_b = ["Hello", "How are you?", "Good!"]

        result = calculate_structural_similarity(messages_a, messages_b)
        assert result["avg_length_ratio"] == 1.0
        assert result["sentence_pattern_similarity"] == 1.0
        # Punctuation might not be exactly 1.0 due to normalization

    def test_different_lengths(self):
        """Test messages with different lengths."""
        messages_a = ["Hi", "How are you doing today?"]
        messages_b = ["Hello there!", "Good"]

        result = calculate_structural_similarity(messages_a, messages_b)
        assert 0 < result["avg_length_ratio"] < 1
        assert 0 <= result["sentence_pattern_similarity"] <= 1
        assert 0 <= result["punctuation_similarity"] <= 1

    def test_empty_lists(self):
        """Test empty message lists."""
        result = calculate_structural_similarity([], [])
        assert result["avg_length_ratio"] == 0.0
        assert result["sentence_pattern_similarity"] == 0.0
        assert result["punctuation_similarity"] == 0.0

    def test_one_empty_list(self):
        """Test one empty list."""
        messages_a = ["Hello"]
        messages_b = []

        result = calculate_structural_similarity(messages_a, messages_b)
        assert result["avg_length_ratio"] == 0.0
        assert result["sentence_pattern_similarity"] == 0.0
        assert result["punctuation_similarity"] == 0.0


class TestUpdatePhaseDetection:
    """Test phase detection updates."""

    def test_high_convergence_detection(self):
        """Test detection of high convergence phase."""
        phase_detection = {
            "high_convergence_start": None,
            "emoji_phase_start": None,
            "symbolic_phase_start": None,
        }

        # Low convergence - no update
        metrics = {"convergence": 0.5}
        update_phase_detection(phase_detection, metrics, 1)
        assert phase_detection["high_convergence_start"] is None

        # High convergence - should update
        metrics = {"convergence": 0.8}
        update_phase_detection(phase_detection, metrics, 5)
        assert phase_detection["high_convergence_start"] == 5

        # Already detected - no change
        metrics = {"convergence": 0.9}
        update_phase_detection(phase_detection, metrics, 10)
        assert phase_detection["high_convergence_start"] == 5

    def test_emoji_phase_detection(self):
        """Test detection of emoji phase."""
        phase_detection = {
            "high_convergence_start": None,
            "emoji_phase_start": None,
            "symbolic_phase_start": None,
        }

        # Low emoji density - no update
        metrics = {"emoji_density": 0.005}
        update_phase_detection(phase_detection, metrics, 1)
        assert phase_detection["emoji_phase_start"] is None

        # Above threshold - should update
        metrics = {"emoji_density": 0.02}
        update_phase_detection(phase_detection, metrics, 3)
        assert phase_detection["emoji_phase_start"] == 3

    def test_symbolic_phase_detection(self):
        """Test detection of symbolic phase."""
        phase_detection = {
            "high_convergence_start": None,
            "emoji_phase_start": None,
            "symbolic_phase_start": None,
        }

        # Medium density - no symbolic phase
        metrics = {"emoji_density": 0.05}
        update_phase_detection(phase_detection, metrics, 1)
        assert phase_detection["symbolic_phase_start"] is None

        # High density - symbolic phase
        metrics = {"emoji_density": 0.15}
        update_phase_detection(phase_detection, metrics, 7)
        assert phase_detection["symbolic_phase_start"] == 7

    def test_missing_metrics(self):
        """Test phase detection with missing metrics."""
        phase_detection = {
            "high_convergence_start": None,
            "emoji_phase_start": None,
            "symbolic_phase_start": None,
        }

        # Missing convergence metric
        metrics = {"other": 0.5}
        update_phase_detection(phase_detection, metrics, 1)
        assert phase_detection["high_convergence_start"] is None

        # Missing emoji_density metric
        metrics = {"convergence": 0.9}
        update_phase_detection(phase_detection, metrics, 2)
        assert phase_detection["emoji_phase_start"] is None
