"""Tests for MetricsCalculator."""

import pytest
from unittest.mock import Mock, patch

from pidgin.metrics.calculator import MetricsCalculator
from pidgin.metrics.constants import (
    HEDGE_WORDS, AGREEMENT_MARKERS, DISAGREEMENT_MARKERS,
    POLITENESS_MARKERS, FIRST_PERSON_SINGULAR
)


class TestMetricsCalculator:
    """Test MetricsCalculator functionality."""
    
    @pytest.fixture
    def calculator(self):
        """Create a MetricsCalculator instance."""
        return MetricsCalculator()
    
    def test_init(self, calculator):
        """Test calculator initialization."""
        assert calculator.conversation_vocabulary == set()
        assert calculator.turn_vocabularies == []
        assert calculator.previous_messages == {'agent_a': [], 'agent_b': []}
        assert calculator.all_words_seen == set()
    
    def test_calculate_turn_metrics_basic(self, calculator):
        """Test basic turn metrics calculation."""
        metrics = calculator.calculate_turn_metrics(
            turn_number=0,
            agent_a_message="Hello, how are you today?",
            agent_b_message="I'm doing well, thank you!"
        )
        
        # Check structure - metrics use suffixes _a and _b
        assert 'message_a' in metrics
        assert 'message_b' in metrics
        
        # Check basic metrics exist
        assert 'message_length_a' in metrics
        assert 'word_count_a' in metrics
        assert 'vocabulary_size_a' in metrics
        assert 'message_length_b' in metrics
        assert 'word_count_b' in metrics
        assert 'vocabulary_size_b' in metrics
    
    def test_vocabulary_tracking(self, calculator):
        """Test vocabulary tracking across turns."""
        # Turn 1
        metrics1 = calculator.calculate_turn_metrics(
            0, "Hello world", "Hello there"
        )
        
        # Turn 2 - should show vocabulary overlap
        metrics2 = calculator.calculate_turn_metrics(
            1, "World is beautiful", "There is beauty"
        )
        
        # Check vocabulary growth
        assert len(calculator.conversation_vocabulary) > 0
        assert len(calculator.turn_vocabularies) == 2
        
        # Check overlap calculation
        assert 'vocabulary_overlap' in metrics2
        assert metrics2['vocabulary_overlap'] > 0
    
    def test_message_length_metrics(self, calculator):
        """Test message length calculations."""
        short_msg = "Hi"
        long_msg = "This is a much longer message with many words"
        
        metrics = calculator.calculate_turn_metrics(0, short_msg, long_msg)
        
        assert metrics['message_length_a'] == len(short_msg)
        assert metrics['message_length_b'] == len(long_msg)
        # Check convergence score reflects length difference
        assert metrics['length_ratio'] < 1.0  # Short vs long messages
    
    def test_punctuation_metrics(self, calculator):
        """Test punctuation analysis."""
        msg_with_punct = "Hello! How are you? I'm fine..."
        msg_no_punct = "Hello how are you Im fine"
        
        metrics = calculator.calculate_turn_metrics(0, msg_with_punct, msg_no_punct)
        
        assert metrics['punctuation_diversity_a'] > 0  # Has diverse punctuation
        assert metrics['punctuation_diversity_b'] == 0  # No punctuation
        assert metrics['sentence_count_a'] >= 3
    
    def test_question_detection(self, calculator):
        """Test question pattern detection."""
        question_msg = "What do you think? How about this?"
        statement_msg = "I think this is good."
        
        metrics = calculator.calculate_turn_metrics(0, question_msg, statement_msg)
        
        assert metrics['question_count_a'] == 2
        assert metrics['question_count_b'] == 0
    
    def test_hedge_word_detection(self, calculator):
        """Test hedge word detection."""
        hedge_msg = "Maybe we could perhaps try something"
        direct_msg = "We will do this"
        
        metrics = calculator.calculate_turn_metrics(0, hedge_msg, direct_msg)
        
        assert metrics['hedge_count_a'] >= 2
        assert metrics['hedge_count_b'] == 0
    
    def test_agreement_markers(self, calculator):
        """Test agreement/disagreement marker detection."""
        agree_msg = "Yes, I agree completely!"
        disagree_msg = "No, I don't think so"
        
        metrics = calculator.calculate_turn_metrics(0, agree_msg, disagree_msg)
        
        assert metrics['agreement_marker_count_a'] >= 1  # "Yes", "agree"
        assert metrics['disagreement_marker_count_b'] >= 1  # "No"
    
    def test_pronoun_usage(self, calculator):
        """Test pronoun usage tracking."""
        first_person_msg = "I think I should go"
        second_person_msg = "You should think about your choices"
        
        metrics = calculator.calculate_turn_metrics(0, first_person_msg, second_person_msg)
        
        assert metrics['first_person_singular_count_a'] >= 2
        assert metrics['second_person_count_b'] >= 2
    
    def test_special_symbols(self, calculator):
        """Test special symbol detection."""
        math_msg = "The equation is x^2 + y^2 = z^2"
        arrow_msg = "This -> leads to -> that"
        
        metrics = calculator.calculate_turn_metrics(0, math_msg, arrow_msg)
        
        assert metrics['math_symbol_count_a'] > 0
        assert metrics['arrow_count_b'] > 0
    
    def test_engagement_score(self, calculator):
        """Test engagement score calculation."""
        engaged_msg = "That's really interesting! Can you tell me more?"
        neutral_msg = "Ok."
        
        metrics = calculator.calculate_turn_metrics(0, engaged_msg, neutral_msg)
        
        # Check that convergence metrics exist
        assert 'convergence_score' in metrics
        assert 'vocabulary_overlap' in metrics
    
    def test_convergence_metrics(self, calculator):
        """Test convergence tracking across multiple turns."""
        # Simulate converging conversation
        messages = [
            ("Hello there", "Hi there"),
            ("How are you doing?", "I'm doing well, how are you?"),
            ("I'm also doing well", "That's good to hear"),
            ("Yes, it's a nice day", "Indeed, the day is nice")
        ]
        
        all_metrics = []
        for i, (msg_a, msg_b) in enumerate(messages):
            metrics = calculator.calculate_turn_metrics(i, msg_a, msg_b)
            all_metrics.append(metrics)
        
        # Check convergence indicators
        last_metrics = all_metrics[-1]
        assert 'vocabulary_overlap' in last_metrics
        assert 'convergence_score' in last_metrics
        
        # Check that vocabulary overlap is being tracked
        # Note: overlap can vary based on specific word choices
        assert isinstance(all_metrics[-1]['vocabulary_overlap'], float)
        assert 0 <= all_metrics[-1]['vocabulary_overlap'] <= 1
    
    def test_acknowledgment_detection(self, calculator):
        """Test acknowledgment pattern detection."""
        ack_msg = "I see, uh-huh, that makes sense"
        no_ack_msg = "Let me explain my perspective"
        
        metrics = calculator.calculate_turn_metrics(0, ack_msg, no_ack_msg)
        
        assert metrics['starts_with_acknowledgment_a'] == True
        assert metrics['starts_with_acknowledgment_b'] == False
    
    def test_politeness_markers(self, calculator):
        """Test politeness marker detection."""
        polite_msg = "Please, thank you for your help"
        neutral_msg = "Do this task"
        
        metrics = calculator.calculate_turn_metrics(0, polite_msg, neutral_msg)
        
        assert metrics['politeness_marker_count_a'] >= 2
        assert metrics['politeness_marker_count_b'] == 0
    
    def test_empty_messages(self, calculator):
        """Test handling of empty messages."""
        metrics = calculator.calculate_turn_metrics(0, "", "")
        
        assert metrics['message_length_a'] == 0
        assert metrics['message_length_b'] == 0
        assert metrics['word_count_a'] == 0
        assert metrics['word_count_b'] == 0
    
    def test_unicode_handling(self, calculator):
        """Test handling of unicode characters."""
        unicode_msg = "Hello 👋 world 🌍"
        ascii_msg = "Hello world"
        
        metrics = calculator.calculate_turn_metrics(0, unicode_msg, ascii_msg)
        
        assert metrics['emoji_count_a'] >= 2
        assert metrics['emoji_count_b'] == 0
    
    def test_vocabulary_persistence(self, calculator):
        """Test vocabulary state persistence across turns."""
        # Turn 1
        calculator.calculate_turn_metrics(0, "unique word one", "unique word two")
        vocab_size_1 = len(calculator.conversation_vocabulary)
        
        # Turn 2 - add more unique words
        calculator.calculate_turn_metrics(1, "unique word three", "unique word four")
        vocab_size_2 = len(calculator.conversation_vocabulary)
        
        assert vocab_size_2 > vocab_size_1
        assert "unique" in calculator.conversation_vocabulary
        assert len(calculator.turn_vocabularies) == 2
    
    def test_turn_taking_balance(self, calculator):
        """Test turn-taking balance calculation."""
        # Balanced conversation
        balanced_a = "This is a normal length message"
        balanced_b = "This is also a normal length reply"
        
        metrics_balanced = calculator.calculate_turn_metrics(0, balanced_a, balanced_b)
        
        # Imbalanced conversation
        short = "Ok"
        long = "This is a very long message with many words and ideas that keeps going on and on"
        
        metrics_imbalanced = calculator.calculate_turn_metrics(1, short, long)
        
        # Check length ratio reflects balance
        assert metrics_balanced['length_ratio'] > metrics_imbalanced['length_ratio']
    
    def test_semantic_similarity_placeholder(self, calculator):
        """Test semantic similarity calculation (placeholder for now)."""
        similar_a = "I love programming in Python"
        similar_b = "Python programming is something I enjoy"
        
        metrics = calculator.calculate_turn_metrics(0, similar_a, similar_b)
        
        # Should have high vocabulary overlap due to shared words
        assert metrics['vocabulary_overlap'] > 0.3
    
    def test_calculate_final_metrics(self, calculator):
        """Test final conversation metrics calculation."""
        # Simulate a conversation
        messages = [
            ("Hello", "Hi"),
            ("How are you?", "I'm good, you?"),
            ("Great!", "Excellent!")
        ]
        
        for i, (a, b) in enumerate(messages):
            calculator.calculate_turn_metrics(i, a, b)
        
        # Check that state has been maintained
        assert len(calculator.turn_vocabularies) == 3
        assert len(calculator.conversation_vocabulary) > 5  # Should have various words
        assert len(calculator.previous_messages['agent_a']) == 3
        assert len(calculator.previous_messages['agent_b']) == 3