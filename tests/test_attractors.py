"""Tests for structural attractor detection."""

import pytest
from pidgin.attractors import StructuralAnalyzer, StructuralPatternDetector


class TestStructuralAnalyzer:
    """Test structural analysis of messages."""

    def test_extract_structure_basic(self):
        """Test basic structural extraction."""
        analyzer = StructuralAnalyzer()

        content = """Hey hey!
I've just completed the analysis.
- Metric 1: Improved!
- Metric 2: Also better!
- Metric 3: Amazing!
What do you think about this?
P.S. The coffee machine is still broken 😅"""

        structure = analyzer.extract_structure(content)

        # Should identify the party attractor structure
        assert len(structure) == 7
        assert structure[0].type == "EXCITED_OPENING"
        assert structure[1].type == "ANNOUNCEMENT"
        assert structure[2].type == "LIST_ITEM"
        assert structure[3].type == "LIST_ITEM"
        assert structure[4].type == "LIST_ITEM"
        assert structure[5].type == "QUESTION"
        assert structure[6].type == "POSTSCRIPT"

    def test_structural_element_features(self):
        """Test that structural elements capture relevant features."""
        analyzer = StructuralAnalyzer()

        elements = analyzer.extract_structure("Hello! How are you?")

        assert elements[0].features["punctuation"] == "?"
        assert elements[0].features["length"] == 19
        assert "has_emoji" in elements[0].features


class TestStructuralPatternDetector:
    """Test pattern detection in conversations."""

    def test_detect_repeating_structure(self):
        """Test detection of repeating message structures."""
        detector = StructuralPatternDetector(window_size=5, threshold=2)

        # Simulate messages that converge to same structure
        messages = [
            # Different structures initially
            "Let me think about this problem.",
            "Here's what I found: the data shows improvement.",
            # Start converging to same structure
            """Great point!
I noticed something interesting.
- First observation
- Second observation
- Third observation
What do you think?""",
            # Same structure repeats
            """Excellent insight!
I discovered something similar.
- First finding
- Second finding  
- Third finding
Should we explore further?""",
            # Structure repeats again (triggers detection)
            """Wonderful analysis!
I found supporting evidence.
- First piece
- Second piece
- Third piece
How should we proceed?""",
        ]

        result = detector.detect_attractor(messages)

        assert result is not None
        # Should detect the repeating structure
        assert result["confidence"] >= 0.5  # 3 out of 5 messages have similar structure

    def test_alternating_pattern_detection(self):
        """Test detection of A-B-A-B conversation patterns."""
        detector = StructuralPatternDetector(window_size=8, threshold=3)

        # Simulate alternating pattern
        messages = []
        for i in range(4):
            # A's structure
            messages.append("I understand. This is important. Thank you.")
            # B's structure
            messages.append("You're right. That makes sense. I appreciate it.")

        result = detector.detect_attractor(messages)

        assert result is not None
        # Just verify it detected something - don't care about specific type name
        assert "confidence" in result
        assert result["confidence"] >= 0.5

    def test_no_pattern_in_varied_conversation(self):
        """Test that varied conversations don't trigger false positives."""
        detector = StructuralPatternDetector(window_size=10, threshold=3)

        # Varied conversation with different structures
        messages = [
            "Hello! How can I help you today?",
            "I need assistance with my project. It's about machine learning.",
            "That sounds interesting. What specific aspect are you working on?",
            "I'm trying to implement a neural network for image classification.",
            "Here are some suggestions:\n1. Start with a simple CNN\n2. Use transfer learning\n3. Ensure proper data augmentation",
            "Thanks! Could you explain transfer learning in more detail?",
            "Transfer learning involves using a pre-trained model as a starting point.",
            "I see. What models would you recommend?",
            "ResNet50 and EfficientNet are good choices for beginners.",
            "Perfect, I'll start with those. Thank you for your help!",
        ]

        result = detector.detect_attractor(messages)

        assert result is None  # Should not detect any pattern
