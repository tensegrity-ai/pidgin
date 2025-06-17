"""Tests for experiment metrics calculation."""

import pytest
from pidgin.experiments.metrics import MetricsCalculator


def test_basic_metrics():
    """Test basic metric calculations."""
    calc = MetricsCalculator()
    
    metrics = calc.calculate_turn_metrics(
        0,
        "Hello! How are you today?",
        "I'm doing well, thank you! How about you?"
    )
    
    # Check agent A metrics
    assert metrics['message_length_a'] == 25
    assert metrics['word_count_a'] == 5
    assert metrics['sentence_count_a'] == 2
    assert metrics['vocabulary_size_a'] == 5
    assert metrics['type_token_ratio_a'] == 1.0  # All unique words
    assert metrics['question_count_a'] == 1
    assert metrics['exclamation_count_a'] == 1
    
    # Check agent B metrics  
    assert metrics['message_length_b'] == 41
    assert metrics['word_count_b'] == 9
    assert metrics['sentence_count_b'] == 2
    assert metrics['vocabulary_size_b'] == 8
    assert metrics['question_count_b'] == 1
    assert metrics['exclamation_count_b'] == 1


def test_linguistic_markers():
    """Test detection of linguistic markers."""
    calc = MetricsCalculator()
    
    metrics = calc.calculate_turn_metrics(
        0,
        "Maybe we should discuss this. Please consider my perspective.",
        "Yes, I agree. Thank you for your thoughtful input."
    )
    
    # Agent A should have hedge and politeness markers
    assert metrics['hedge_count_a'] == 1  # "Maybe"
    assert metrics['politeness_marker_count_a'] == 1  # "Please"
    
    # Agent B should have agreement and politeness markers
    assert metrics['agreement_marker_count_b'] >= 2  # "Yes", "agree"
    assert metrics['politeness_marker_count_b'] == 1  # "Thank"


def test_pronoun_detection():
    """Test pronoun counting."""
    calc = MetricsCalculator()
    
    metrics = calc.calculate_turn_metrics(
        0,
        "I think we should work together. You and I can achieve this.",
        "You're right. We can do it ourselves if we try."
    )
    
    # Agent A pronouns
    assert metrics['first_person_singular_count_a'] == 2  # "I" twice
    assert metrics['second_person_count_a'] == 1  # "You"
    assert metrics['first_person_plural_count_a'] == 1  # "we"
    
    # Agent B pronouns
    assert metrics['first_person_plural_count_b'] == 3  # "We", "ourselves", "we"
    assert metrics['second_person_count_b'] == 1  # "You're"


def test_convergence_metrics():
    """Test convergence calculations between messages."""
    calc = MetricsCalculator()
    
    # Similar messages should have high convergence
    metrics = calc.calculate_turn_metrics(
        0,
        "I really enjoy discussing philosophy and ethics.",
        "I also enjoy discussing philosophy and ethics!"
    )
    
    assert 'convergence_score' in metrics
    assert 'vocabulary_overlap' in metrics
    assert 'length_ratio' in metrics
    
    # High vocabulary overlap expected
    assert metrics['vocabulary_overlap'] > 0.5
    
    # Similar lengths
    assert metrics['length_ratio'] > 0.8


def test_repetition_tracking():
    """Test cross-turn repetition detection."""
    calc = MetricsCalculator()
    
    # First turn
    metrics1 = calc.calculate_turn_metrics(
        0,
        "Let's explore the concept of consciousness.",
        "Yes, consciousness is fascinating to explore."
    )
    
    # Second turn with repetition
    metrics2 = calc.calculate_turn_metrics(
        1,
        "The concept of consciousness remains mysterious.",
        "Indeed, consciousness is still very mysterious."
    )
    
    # Should detect repeated phrases from previous turn
    assert metrics2['repeated_bigrams_a'] > 0  # "concept of", "of consciousness"
    assert metrics2['repeated_bigrams_b'] > 0  # "consciousness is"


def test_entropy_calculation():
    """Test information theory metrics."""
    calc = MetricsCalculator()
    
    # Repetitive message should have lower entropy
    metrics = calc.calculate_turn_metrics(
        0,
        "Test test test test.",
        "This message has more variety in word choice."
    )
    
    assert metrics['word_entropy_a'] < metrics['word_entropy_b']
    assert metrics['character_entropy_a'] < metrics['character_entropy_b']


def test_symbol_detection():
    """Test symbol and emoji detection."""
    calc = MetricsCalculator()
    
    metrics = calc.calculate_turn_metrics(
        0,
        "Here's an arrow → and some math: 2 + 2 ≈ 4",
        "Great! 😊 I see your point ← Let me add ∑"
    )
    
    # Agent A symbols
    assert metrics['arrow_count_a'] == 1  # →
    assert metrics['math_symbol_count_a'] == 1  # ≈
    
    # Agent B symbols  
    assert metrics['emoji_count_b'] == 1  # 😊
    assert metrics['arrow_count_b'] == 1  # ←
    assert metrics['math_symbol_count_b'] == 1  # ∑


def test_acknowledgment_detection():
    """Test detection of acknowledgments."""
    calc = MetricsCalculator()
    
    metrics = calc.calculate_turn_metrics(
        0,
        "What do you think about this?",
        "Yes, I see your point. That's interesting."
    )
    
    assert metrics['starts_with_acknowledgment_a'] == False
    assert metrics['starts_with_acknowledgment_b'] == True
    
    # Test various acknowledgment patterns
    test_cases = [
        ("I agree with that.", True),
        ("Hmm, let me think.", True),
        ("Thank you for asking.", True),
        ("Let's discuss this.", False),
        ("Oh, that's interesting!", True),
    ]
    
    for message, expected in test_cases:
        calc2 = MetricsCalculator()
        metrics = calc2.calculate_turn_metrics(0, "Test", message)
        assert metrics['starts_with_acknowledgment_b'] == expected


def test_new_words_tracking():
    """Test tracking of new vocabulary."""
    calc = MetricsCalculator()
    
    # First turn
    metrics1 = calc.calculate_turn_metrics(
        0,
        "Hello world",
        "Hello friend"
    )
    
    # All words are new in first turn
    assert metrics1['new_words_a'] == 2
    assert metrics1['new_words_b'] == 2
    
    # Second turn with some repeated words
    metrics2 = calc.calculate_turn_metrics(
        1,
        "Hello again world",  # "again" is new
        "Goodbye friend"      # "Goodbye" is new
    )
    
    assert metrics2['new_words_a'] == 1  # Only "again" is new
    assert metrics2['new_words_b'] == 1  # Only "Goodbye" is new


def test_structural_similarity():
    """Test structural similarity calculation."""
    calc = MetricsCalculator()
    
    # Similar structure
    metrics1 = calc.calculate_turn_metrics(
        0,
        "This is great! What do you think? I'm excited.",
        "That's wonderful! How do you feel? I'm happy."
    )
    
    # Very different structure
    metrics2 = calc.calculate_turn_metrics(
        1,
        "Yes.",
        "Well, I think this is a complex topic that requires careful consideration and analysis."
    )
    
    assert metrics1['structural_similarity'] > metrics2['structural_similarity']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])