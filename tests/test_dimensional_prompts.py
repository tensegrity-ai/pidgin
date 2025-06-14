"""Tests for the dimensional prompt system."""

import pytest
from pidgin.dimensional_prompts import DimensionalPromptGenerator


class TestDimensionalPromptGenerator:
    """Test dimensional prompt generation."""

    def setup_method(self):
        """Set up test generator."""
        self.generator = DimensionalPromptGenerator()

    def test_basic_dimensions(self):
        """Test basic two-dimension prompts."""
        # Peers philosophy
        prompt = self.generator.generate("peers:philosophy")
        assert (
            "Hello! I'm excited to explore the fundamental nature of reality together."
            in prompt
        )

        # Debate science
        prompt = self.generator.generate("debate:science")
        assert "I strongly disagree about how the universe works." in prompt

        # Teaching language
        prompt = self.generator.generate("teaching:language")
        assert (
            "I'd like to help you understand how we communicate and create meaning."
            in prompt
        )

    def test_three_dimensions(self):
        """Test prompts with mode dimension."""
        # Analytical mode
        prompt = self.generator.generate("peers:philosophy:analytical")
        assert "Let's systematically analyze" in prompt

        # Exploratory mode
        prompt = self.generator.generate("interview:science:exploratory")
        assert "I wonder what would happen if" in prompt

    def test_all_dimensions(self):
        """Test using all available dimensions."""
        prompt = self.generator.generate("collaboration:meta:focused:engaged:casual")
        assert "Let's" in prompt  # Casual form
        assert "actively investigating" in prompt  # Engaged energy
        assert "Let's focus specifically on" in prompt  # Focused mode

    def test_neutral_context(self):
        """Test the neutral context option."""
        prompt = self.generator.generate("neutral:creativity")
        assert (
            "Hello! I'm looking forward to discussing the creative process and imagination."
            in prompt
        )

    def test_formality_modifiers(self):
        """Test formality style modifications."""
        # Casual
        casual = self.generator.generate("peers:philosophy:analytical:calm:casual")
        assert "I'm" in casual

        # Academic
        academic = self.generator.generate("peers:philosophy:analytical:calm:academic")
        assert "I am" in academic

    def test_missing_required_dimension(self):
        """Test error when required dimension is missing."""
        with pytest.raises(ValueError) as exc_info:
            self.generator.generate("analytical")
        assert "Unknown context 'analytical'" in str(exc_info.value)

    def test_invalid_dimension_value(self):
        """Test error with invalid dimension value."""
        with pytest.raises(ValueError) as exc_info:
            self.generator.generate("peers:nonsense")
        assert "Unknown topic 'nonsense'" in str(exc_info.value)

    def test_puzzles_random(self):
        """Test random puzzle selection."""
        prompt = self.generator.generate("collaboration:puzzles")
        assert "Let's work together to figure out this puzzle:" in prompt
        # Should contain one of the default puzzles
        puzzles = [
            "What gets wetter",
            "What is so fragile",
            "What has cities",
            "What can run",
            "What can you catch",
            "What has a face",
            "What travels",
            "The more you take",
        ]
        assert any(puzzle in prompt for puzzle in puzzles)

    def test_puzzles_specific(self):
        """Test specific puzzle selection."""
        prompt = self.generator.generate("collaboration:puzzles", puzzle="towel")
        assert "What gets wetter as it dries?" in prompt

    def test_puzzles_custom_content(self):
        """Test custom puzzle content."""
        custom = "What has 13 hearts but no organs?"
        prompt = self.generator.generate("debate:puzzles", topic_content=custom)
        assert custom in prompt

    def test_thought_experiments_random(self):
        """Test random thought experiment."""
        prompt = self.generator.generate("debate:thought_experiments")
        assert "this thought experiment:" in prompt
        # Should contain one of the experiments
        experiments = [
            "ship's parts",
            "Chinese",
            "experience machine",
            "veil of ignorance",
            "runaway trolley",
            "floating",
            "zombie",
            "cat",
        ]
        assert any(exp in prompt for exp in experiments)

    def test_thought_experiments_specific(self):
        """Test specific thought experiment."""
        prompt = self.generator.generate(
            "interview:thought_experiments", experiment="trolley_problem"
        )
        assert "Is it moral to divert a trolley" in prompt

    def test_dimension_listing(self):
        """Test getting all dimensions."""
        dims = self.generator.get_all_dimensions()
        assert "context" in dims
        assert "topic" in dims
        assert "mode" in dims
        assert dims["context"].required is True
        assert dims["mode"].required is False

    def test_dimension_values(self):
        """Test getting values for a dimension."""
        contexts = self.generator.get_dimension_values("context")
        assert "peers" in contexts
        assert "debate" in contexts
        assert "neutral" in contexts

        topics = self.generator.get_dimension_values("topic")
        assert "philosophy" in topics
        assert "puzzles" in topics

    def test_dimension_description(self):
        """Test describing a dimension."""
        desc = self.generator.describe_dimension("context")
        assert "CONTEXT:" in desc
        assert "conversational relationship" in desc
        assert "peers:" in desc
        assert "debate:" in desc

    def test_unknown_puzzle(self):
        """Test error with unknown puzzle name."""
        with pytest.raises(ValueError) as exc_info:
            self.generator.generate("collaboration:puzzles", puzzle="nonexistent")
        assert "Unknown puzzle: nonexistent" in str(exc_info.value)

    def test_unknown_experiment(self):
        """Test error with unknown thought experiment."""
        with pytest.raises(ValueError) as exc_info:
            self.generator.generate(
                "debate:thought_experiments", experiment="fake_experiment"
            )
        assert "Unknown thought experiment: fake_experiment" in str(exc_info.value)

    def test_proper_punctuation(self):
        """Test that prompts have proper ending punctuation."""
        # Statement should end with period
        prompt1 = self.generator.generate("peers:philosophy")
        assert prompt1.rstrip().endswith(".")

        # Question should end with question mark
        prompt2 = self.generator.generate("interview:science")
        assert prompt2.rstrip().endswith("?") or prompt2.rstrip().endswith("...")

        # Debate should end with colon
        prompt3 = self.generator.generate("debate:language")
        assert prompt3.rstrip().endswith(":")

    def test_energy_integration(self):
        """Test that energy modifiers are properly integrated."""
        # Calm energy
        calm = self.generator.generate("peers:philosophy:analytical:calm")
        assert "gently exploring" in calm or "explore" in calm

        # Passionate energy
        passionate = self.generator.generate(
            "collaboration:science:exploratory:passionate"
        )
        assert "deeply fascinated by" in passionate or "figure out" in passionate
