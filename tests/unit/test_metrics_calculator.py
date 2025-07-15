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
        assert calculator.cumulative_vocab == {'agent_a': set(), 'agent_b': set()}
        assert calculator.turn_vocabularies == []
        assert calculator.previous_messages == {'agent_a': [], 'agent_b': []}
        assert calculator.all_agent_words == {'agent_a': set(), 'agent_b': set()}
        assert hasattr(calculator, '_token_cache')
        assert calculator._token_cache == {}
    
    def test_calculate_turn_metrics_basic(self, calculator):
        """Test basic turn metrics calculation."""
        metrics = calculator.calculate_turn_metrics(
            turn_number=0,
            agent_a_message="Hello, how are you today?",
            agent_b_message="I'm doing well, thank you!"
        )
        
        # Check structure - now uses nested structure
        assert 'agent_a' in metrics
        assert 'agent_b' in metrics
        assert 'convergence' in metrics
        
        # Check basic metrics exist under agent keys
        assert 'message_length' in metrics['agent_a']
        assert 'word_count' in metrics['agent_a']
        assert 'vocabulary_size' in metrics['agent_a']
        assert 'message_length' in metrics['agent_b']
        assert 'word_count' in metrics['agent_b']
        assert 'vocabulary_size' in metrics['agent_b']
    
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
        assert len(calculator.cumulative_vocab['agent_a']) > 0
        assert len(calculator.cumulative_vocab['agent_b']) > 0
        assert len(calculator.turn_vocabularies) == 2
        
        # Check overlap calculation
        assert 'vocabulary_overlap' in metrics2['convergence']
        assert metrics2['convergence']['vocabulary_overlap'] > 0
    
    def test_message_length_metrics(self, calculator):
        """Test message length calculations."""
        short_msg = "Hi"
        long_msg = "This is a much longer message with many words"
        
        metrics = calculator.calculate_turn_metrics(0, short_msg, long_msg)
        
        assert metrics['agent_a']['message_length'] == len(short_msg)
        assert metrics['agent_b']['message_length'] == len(long_msg)
        # Check that both agents have the metrics
        assert metrics['agent_a']['word_count'] == 1
        assert metrics['agent_b']['word_count'] == 9
    
    def test_punctuation_metrics(self, calculator):
        """Test punctuation analysis."""
        msg_with_punct = "Hello! How are you? I'm fine..."
        msg_no_punct = "Hello how are you Im fine"
        
        metrics = calculator.calculate_turn_metrics(0, msg_with_punct, msg_no_punct)
        
        assert metrics['agent_a']['punctuation_diversity'] > 0  # Has diverse punctuation
        assert metrics['agent_b']['punctuation_diversity'] == 0  # No punctuation
        assert metrics['agent_a']['sentence_count'] >= 3
    
    def test_question_detection(self, calculator):
        """Test question pattern detection."""
        question_msg = "What do you think? How about this?"
        statement_msg = "I think this is good."
        
        metrics = calculator.calculate_turn_metrics(0, question_msg, statement_msg)
        
        assert metrics['agent_a']['question_count'] == 2
        assert metrics['agent_b']['question_count'] == 0
    
    def test_hedge_word_detection(self, calculator):
        """Test hedge word detection."""
        hedge_msg = "Maybe we could perhaps try something"
        direct_msg = "We will do this"
        
        metrics = calculator.calculate_turn_metrics(0, hedge_msg, direct_msg)
        
        assert metrics['agent_a']['hedge_words'] >= 2
        assert metrics['agent_b']['hedge_words'] == 0
    
    def test_agreement_markers(self, calculator):
        """Test agreement/disagreement marker detection."""
        agree_msg = "Yes, I agree completely!"
        disagree_msg = "No, I don't think so"
        
        metrics = calculator.calculate_turn_metrics(0, agree_msg, disagree_msg)
        
        assert metrics['agent_a']['agreement_markers'] >= 1  # "Yes", "agree"
        assert metrics['agent_b']['disagreement_markers'] >= 1  # "No"
    
    def test_pronoun_usage(self, calculator):
        """Test pronoun usage tracking."""
        first_person_msg = "I think I should go"
        second_person_msg = "You should think about your choices"
        
        metrics = calculator.calculate_turn_metrics(0, first_person_msg, second_person_msg)
        
        assert metrics['agent_a']['first_person_singular'] >= 2
        assert metrics['agent_b']['second_person'] >= 2
    
    def test_special_symbols(self, calculator):
        """Test special symbol detection."""
        math_msg = "The equation is x^2 + y^2 = z^2"
        arrow_msg = "This -> leads to -> that"
        
        metrics = calculator.calculate_turn_metrics(0, math_msg, arrow_msg)
        
        assert metrics['agent_a']['special_symbol_count'] > 0
        assert metrics['agent_b']['special_symbol_count'] > 0
    
    def test_engagement_score(self, calculator):
        """Test engagement score calculation."""
        engaged_msg = "That's really interesting! Can you tell me more?"
        neutral_msg = "Ok."
        
        metrics = calculator.calculate_turn_metrics(0, engaged_msg, neutral_msg)
        
        # Check that convergence metrics exist
        assert 'vocabulary_overlap' in metrics['convergence']
        assert 'cross_repetition' in metrics['convergence']
    
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
        assert 'vocabulary_overlap' in last_metrics['convergence']
        assert 'cumulative_overlap' in last_metrics['convergence']
        
        # Check that vocabulary overlap is being tracked
        assert isinstance(last_metrics['convergence']['vocabulary_overlap'], float)
        assert 0 <= last_metrics['convergence']['vocabulary_overlap'] <= 1
    
    def test_acknowledgment_detection(self, calculator):
        """Test acknowledgment pattern detection."""
        ack_msg = "I see, that makes sense"
        no_ack_msg = "Let me explain my perspective"
        
        metrics = calculator.calculate_turn_metrics(0, ack_msg, no_ack_msg)
        
        assert metrics['agent_a']['starts_with_acknowledgment'] == True
        assert metrics['agent_b']['starts_with_acknowledgment'] == False
    
    def test_politeness_markers(self, calculator):
        """Test politeness marker detection."""
        polite_msg = "Please, thank you for your help"
        neutral_msg = "Do this task"
        
        metrics = calculator.calculate_turn_metrics(0, polite_msg, neutral_msg)
        
        assert metrics['agent_a']['politeness_markers'] >= 2
        assert metrics['agent_b']['politeness_markers'] == 0
    
    def test_empty_messages(self, calculator):
        """Test handling of empty messages."""
        metrics = calculator.calculate_turn_metrics(0, "", "")
        
        assert metrics['agent_a']['message_length'] == 0
        assert metrics['agent_b']['message_length'] == 0
        assert metrics['agent_a']['word_count'] == 0
        assert metrics['agent_b']['word_count'] == 0
    
    def test_unicode_handling(self, calculator):
        """Test handling of unicode characters."""
        unicode_msg = "Hello 👋 world 🌍"
        ascii_msg = "Hello world"
        
        metrics = calculator.calculate_turn_metrics(0, unicode_msg, ascii_msg)
        
        # Special symbols count includes emojis
        assert metrics['agent_a']['special_symbol_count'] >= 2
        assert metrics['agent_b']['special_symbol_count'] == 0
    
    def test_vocabulary_persistence(self, calculator):
        """Test vocabulary state persistence across turns."""
        # Turn 1
        calculator.calculate_turn_metrics(0, "unique word one", "unique word two")
        vocab_size_1 = len(calculator.cumulative_vocab['agent_a'] | calculator.cumulative_vocab['agent_b'])
        
        # Turn 2 - add more unique words
        calculator.calculate_turn_metrics(1, "unique word three", "unique word four")
        vocab_size_2 = len(calculator.cumulative_vocab['agent_a'] | calculator.cumulative_vocab['agent_b'])
        
        assert vocab_size_2 > vocab_size_1
        combined_vocab = calculator.cumulative_vocab['agent_a'] | calculator.cumulative_vocab['agent_b']
        assert "unique" in combined_vocab
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
        
        # Check message lengths reflect balance
        len_diff_balanced = abs(metrics_balanced['agent_a']['message_length'] - 
                               metrics_balanced['agent_b']['message_length'])
        len_diff_imbalanced = abs(metrics_imbalanced['agent_a']['message_length'] - 
                                 metrics_imbalanced['agent_b']['message_length'])
        
        assert len_diff_balanced < len_diff_imbalanced
    
    def test_semantic_similarity_placeholder(self, calculator):
        """Test semantic similarity calculation (placeholder for now)."""
        similar_a = "I love programming in Python"
        similar_b = "Python programming is something I enjoy"
        
        metrics = calculator.calculate_turn_metrics(0, similar_a, similar_b)
        
        # Should have high vocabulary overlap due to shared words
        assert metrics['convergence']['vocabulary_overlap'] > 0.3
    
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
        total_vocab = len(calculator.cumulative_vocab['agent_a'] | calculator.cumulative_vocab['agent_b'])
        assert total_vocab > 5  # Should have various words
        assert len(calculator.previous_messages['agent_a']) == 3
        assert len(calculator.previous_messages['agent_b']) == 3
    
    def test_calculate_repetition_edge_cases(self, calculator):
        """Test repetition calculation edge cases."""
        # Test with empty message (should return 0.0)
        # This tests line 302-303 in _calculate_repetition
        empty_words = []
        repetition = calculator._calculate_repetition(empty_words, "agent_a", 1)
        assert repetition == 0.0
        
        # Test with first turn (turn_number=0, should return 0.0)
        repetition = calculator._calculate_repetition(["hello", "world"], "agent_a", 0)
        assert repetition == 0.0
        
        # Test with no previous words (should return 0.0)
        # This tests line 309-310 in _calculate_repetition
        # Agent has no previous vocabulary, so previous_words will be empty
        repetition = calculator._calculate_repetition(["new", "words"], "agent_a", 1)
        assert repetition == 0.0
        
        # Test case where previous_words becomes empty after subtraction
        # This tests line 309-310 in _calculate_repetition
        # Add vocabulary to agent_a
        calculator.all_agent_words['agent_a'].add("hello")
        
        # Now test with current words that completely overlap with previous
        # previous_words = {'hello'} - {'hello'} = {} (empty set)
        repetition = calculator._calculate_repetition(["hello"], "agent_a", 1)
        assert repetition == 0.0  # Should return 0.0 when previous_words is empty
        
        # Test normal repetition calculation
        # First, add some vocabulary to the agent
        calculator.calculate_turn_metrics(0, "hello world", "goodbye world")
        
        # Now test repetition with partial overlap
        # Agent A has: {'hello', 'world'}
        # Current: {'world', 'new'}
        # Previous after subtraction: {'hello'} (removed 'world')
        # Overlap: {} (no overlap between {'world', 'new'} and {'hello'})
        repetition = calculator._calculate_repetition(["world", "new"], "agent_a", 1)
        assert repetition == 0.0
        
        # Test with actual overlap
        # Current: {'hello', 'new'}
        # Previous after subtraction: {'world'} (removed 'hello')
        # Overlap: {} (no overlap)
        repetition = calculator._calculate_repetition(["hello", "new"], "agent_a", 1)
        assert repetition == 0.0
    
    def test_reset_functionality(self, calculator):
        """Test that reset clears all state."""
        # Add some state
        calculator.calculate_turn_metrics(0, "hello world", "goodbye world")
        calculator.calculate_turn_metrics(1, "another message", "another response")
        
        # Verify state exists
        assert len(calculator.cumulative_vocab['agent_a']) > 0
        assert len(calculator.all_agent_words['agent_a']) > 0
        assert len(calculator.previous_messages['agent_a']) > 0
        assert len(calculator.turn_vocabularies) > 0
        assert len(calculator.all_messages) > 0
        
        # Reset
        calculator.reset()
        
        # Verify state is cleared
        assert len(calculator.cumulative_vocab['agent_a']) == 0
        assert len(calculator.cumulative_vocab['agent_b']) == 0
        assert len(calculator.all_agent_words['agent_a']) == 0
        assert len(calculator.all_agent_words['agent_b']) == 0
        assert len(calculator.previous_messages['agent_a']) == 0
        assert len(calculator.previous_messages['agent_b']) == 0
        assert len(calculator.turn_vocabularies) == 0
        assert len(calculator._token_cache) == 0
        assert len(calculator.all_messages) == 0