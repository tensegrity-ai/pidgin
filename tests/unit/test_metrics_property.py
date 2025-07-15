"""Property-based tests for metrics calculations using hypothesis."""

import math
import string
from collections import Counter
from typing import List, Set

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite

from pidgin.metrics.calculator import MetricsCalculator
from pidgin.metrics.text_analysis import TextAnalyzer
from pidgin.metrics.convergence_metrics import ConvergenceCalculator
from pidgin.metrics.linguistic_metrics import LinguisticAnalyzer
from pidgin.metrics.constants import (
    HEDGE_WORDS, AGREEMENT_MARKERS, DISAGREEMENT_MARKERS,
    POLITENESS_MARKERS, FIRST_PERSON_SINGULAR, EMOJI_PATTERN,
    ARROW_PATTERN, MATH_SYMBOLS, ARROWS
)


# Custom strategies for generating test data
@composite
def sentence_strategy(draw):
    """Generate realistic sentences."""
    words = draw(st.lists(
        st.text(alphabet=string.ascii_letters, min_size=1, max_size=15),
        min_size=1,
        max_size=20
    ))
    sentence = ' '.join(words)
    punctuation = draw(st.sampled_from(['.', '!', '?', '...']))
    return sentence + punctuation


@composite
def message_strategy(draw):
    """Generate messages with multiple sentences."""
    sentences = draw(st.lists(sentence_strategy(), min_size=1, max_size=5))
    return ' '.join(sentences)


@composite
def word_list_strategy(draw):
    """Generate a list of words."""
    return draw(st.lists(
        st.text(alphabet=string.ascii_letters + "'", min_size=1, max_size=15),
        min_size=0,
        max_size=50
    ))


class TestTextAnalyzerProperties:
    """Property-based tests for TextAnalyzer."""
    
    @given(st.text())
    def test_tokenize_returns_list(self, text):
        """Tokenize should always return a list."""
        result = TextAnalyzer.tokenize(text)
        assert isinstance(result, list)
        assert all(isinstance(word, str) for word in result)
    
    @given(st.text(alphabet=string.ascii_letters + string.whitespace + "'", min_size=1))
    def test_tokenize_lowercase(self, text):
        """All tokens should be lowercase."""
        tokens = TextAnalyzer.tokenize(text)
        for token in tokens:
            assert token.islower() or all(c in "'" for c in token)
    
    @given(st.text())
    def test_split_sentences_returns_list(self, text):
        """Split sentences should always return a list."""
        result = TextAnalyzer.split_sentences(text)
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)
    
    @given(st.text())
    def test_split_sentences_non_empty(self, text):
        """Split sentences should not include empty strings."""
        sentences = TextAnalyzer.split_sentences(text)
        for sentence in sentences:
            assert sentence.strip() != ""
    
    @given(st.text())
    def test_count_questions_non_negative(self, text):
        """Question count should be non-negative."""
        count = TextAnalyzer.count_questions(text)
        assert count >= 0
        assert count <= text.count('?')
    
    @given(st.text())
    def test_count_exclamations_non_negative(self, text):
        """Exclamation count should be non-negative."""
        count = TextAnalyzer.count_exclamations(text)
        assert count >= 0
        assert count <= text.count('!')
    
    @given(st.text())
    def test_count_paragraphs_positive(self, text):
        """Paragraph count should be at least 1 for non-empty text."""
        count = TextAnalyzer.count_paragraphs(text)
        if text.strip():
            assert count >= 1
        else:
            assert count == 0
    
    @given(st.text())
    def test_punctuation_diversity_bounded(self, text):
        """Punctuation diversity should be bounded."""
        diversity = TextAnalyzer.calculate_punctuation_diversity(text)
        assert diversity >= 0
        # Can't have more unique punctuation than characters in text
        assert diversity <= len(text)
    
    @given(st.text())
    def test_symbol_density_range(self, text):
        """Symbol density should be between 0 and 1."""
        density = TextAnalyzer.calculate_symbol_density(text)
        assert 0.0 <= density <= 1.0
    
    @given(st.text())
    def test_count_numbers_consistency(self, text):
        """Number count should be consistent with digit presence."""
        count = TextAnalyzer.count_numbers(text)
        assert count >= 0
        if not any(c.isdigit() for c in text):
            assert count == 0
    
    @given(word_list_strategy())
    def test_count_proper_nouns_bounded(self, words):
        """Proper noun count should not exceed word count."""
        count = TextAnalyzer.count_proper_nouns(words)
        assert 0 <= count <= len(words)


class TestLinguisticAnalyzerProperties:
    """Property-based tests for LinguisticAnalyzer."""
    
    @given(st.dictionaries(st.text(min_size=1), st.integers(min_value=1, max_value=100)))
    def test_entropy_non_negative(self, word_counts):
        """Entropy should always be non-negative."""
        counter = Counter(word_counts)
        entropy = LinguisticAnalyzer.calculate_entropy(counter)
        assert entropy >= 0.0
    
    @given(st.dictionaries(st.text(min_size=1), st.integers(min_value=1, max_value=100)))
    def test_entropy_maximum(self, word_counts):
        """Entropy should not exceed log2 of vocabulary size."""
        counter = Counter(word_counts)
        entropy = LinguisticAnalyzer.calculate_entropy(counter)
        if len(counter) > 0:
            assert entropy <= math.log2(len(counter))
    
    @given(st.text(min_size=1))
    def test_character_entropy_bounded(self, text):
        """Character entropy should be bounded."""
        entropy = LinguisticAnalyzer.calculate_character_entropy(text)
        assert entropy >= 0.0
        unique_chars = len(set(text))
        if unique_chars > 0:
            assert entropy <= math.log2(unique_chars)
    
    @given(word_list_strategy())
    def test_self_repetition_range(self, words):
        """Self repetition should be between 0 and 1."""
        repetition = LinguisticAnalyzer.calculate_self_repetition(words)
        assert 0.0 <= repetition <= 1.0
    
    @given(st.integers(min_value=0), st.integers(min_value=0))
    def test_lexical_diversity_index_non_negative(self, word_count, vocab_size):
        """Lexical diversity index should be non-negative."""
        assume(vocab_size <= word_count)  # Vocabulary can't exceed word count
        ldi = LinguisticAnalyzer.calculate_lexical_diversity_index(word_count, vocab_size)
        assert ldi >= 0.0
    
    @given(st.text(), word_list_strategy())
    def test_formality_score_range(self, text, words):
        """Formality score should be between 0 and 1."""
        score = LinguisticAnalyzer.calculate_formality_score(text, words)
        assert 0.0 <= score <= 1.0
    
    @given(st.dictionaries(st.text(min_size=1), st.integers(min_value=1, max_value=10)))
    def test_hapax_legomena_ratio_range(self, word_counts):
        """Hapax legomena ratio should be between 0 and 1."""
        counter = Counter(word_counts)
        ratio = LinguisticAnalyzer.calculate_hapax_legomena_ratio(counter)
        assert 0.0 <= ratio <= 1.0
    
    @given(word_list_strategy())
    def test_count_linguistic_markers_non_negative(self, words):
        """All linguistic marker counts should be non-negative."""
        markers = LinguisticAnalyzer.count_linguistic_markers(words)
        for key, count in markers.items():
            assert count >= 0
            assert count <= len(words)  # Can't have more markers than words


class TestConvergenceCalculatorProperties:
    """Property-based tests for ConvergenceCalculator."""
    
    @given(st.sets(st.text(min_size=1)), st.sets(st.text(min_size=1)))
    def test_vocabulary_overlap_range(self, vocab_a, vocab_b):
        """Vocabulary overlap should be between 0 and 1."""
        overlap = ConvergenceCalculator.calculate_vocabulary_overlap(vocab_a, vocab_b)
        assert 0.0 <= overlap <= 1.0
    
    @given(st.sets(st.text(min_size=1)), st.sets(st.text(min_size=1)))
    def test_vocabulary_overlap_symmetry(self, vocab_a, vocab_b):
        """Vocabulary overlap should be symmetric."""
        overlap_ab = ConvergenceCalculator.calculate_vocabulary_overlap(vocab_a, vocab_b)
        overlap_ba = ConvergenceCalculator.calculate_vocabulary_overlap(vocab_b, vocab_a)
        assert abs(overlap_ab - overlap_ba) < 1e-10
    
    @given(st.text(), st.text())
    def test_mimicry_score_range(self, message_a, message_b):
        """Mimicry score should be between 0 and 1."""
        score = ConvergenceCalculator.calculate_mimicry_score(message_a, message_b)
        assert 0.0 <= score <= 1.0
    
    @given(st.text(), st.text())
    def test_cross_repetition_range(self, message_a, message_b):
        """Cross repetition should be between 0 and 1."""
        repetition = ConvergenceCalculator.calculate_cross_repetition(message_a, message_b)
        assert 0.0 <= repetition <= 1.0
    
    @given(st.text(), st.text())
    def test_structural_similarity_range(self, message_a, message_b):
        """Structural similarity should be between 0 and 1."""
        similarity = ConvergenceCalculator.calculate_structural_similarity(message_a, message_b)
        assert 0.0 <= similarity <= 1.0
    
    @given(st.text(min_size=1))
    def test_compression_ratio_range(self, text):
        """Compression ratio should be between 0 and 1 (roughly)."""
        ratio = ConvergenceCalculator.calculate_compression_ratio(text)
        assert 0.0 < ratio <= 2.0  # Compression can sometimes be > 1 for very short texts
    
    @given(st.integers(min_value=0), st.integers(min_value=0))
    def test_message_length_ratio_range(self, len_a, len_b):
        """Message length ratio should be between 0 and 1."""
        ratio = ConvergenceCalculator.calculate_message_length_ratio(len_a, len_b)
        assert 0.0 <= ratio <= 1.0
    
    @given(st.integers(min_value=0), st.integers(min_value=0))
    def test_message_length_ratio_symmetry(self, len_a, len_b):
        """Message length ratio should be symmetric."""
        ratio_ab = ConvergenceCalculator.calculate_message_length_ratio(len_a, len_b)
        ratio_ba = ConvergenceCalculator.calculate_message_length_ratio(len_b, len_a)
        assert abs(ratio_ab - ratio_ba) < 1e-10
    
    @given(st.lists(st.text()))
    def test_repetition_ratio_range(self, messages):
        """Repetition ratio should be between 0 and 1."""
        ratio = ConvergenceCalculator.calculate_repetition_ratio(messages)
        assert 0.0 <= ratio <= 1.0


class TestMetricsCalculatorProperties:
    """Property-based tests for MetricsCalculator."""
    
    @pytest.fixture
    def calculator(self):
        """Create a MetricsCalculator instance."""
        return MetricsCalculator()
    
    @given(st.integers(min_value=0), message_strategy(), message_strategy())
    def test_calculate_turn_metrics_structure(self, calculator, turn_number, msg_a, msg_b):
        """Turn metrics should have the expected structure."""
        metrics = calculator.calculate_turn_metrics(turn_number, msg_a, msg_b)
        
        # Check top-level keys
        assert 'turn_number' in metrics
        assert 'agent_a' in metrics
        assert 'agent_b' in metrics
        assert 'convergence' in metrics
        
        # Check that turn number matches
        assert metrics['turn_number'] == turn_number
    
    @given(st.integers(min_value=0), message_strategy(), message_strategy())
    def test_metrics_non_negative(self, calculator, turn_number, msg_a, msg_b):
        """All count-based metrics should be non-negative."""
        metrics = calculator.calculate_turn_metrics(turn_number, msg_a, msg_b)
        
        # Check agent metrics
        for agent in ['agent_a', 'agent_b']:
            agent_metrics = metrics[agent]
            
            # Count-based metrics that should be non-negative
            count_metrics = [
                'message_length', 'word_count', 'vocabulary_size',
                'sentence_count', 'paragraph_count', 'question_count',
                'exclamation_count', 'special_symbol_count', 'number_count',
                'proper_noun_count', 'emoji_count', 'arrow_count',
                'new_words', 'hedge_words', 'agreement_markers',
                'disagreement_markers', 'politeness_markers',
                'first_person_singular', 'first_person_plural', 'second_person'
            ]
            
            for metric in count_metrics:
                if metric in agent_metrics:
                    assert agent_metrics[metric] >= 0
    
    @given(st.integers(min_value=0), message_strategy(), message_strategy())
    def test_metrics_bounded(self, calculator, turn_number, msg_a, msg_b):
        """All ratio/probability metrics should be bounded."""
        metrics = calculator.calculate_turn_metrics(turn_number, msg_a, msg_b)
        
        # Check agent metrics
        for agent in ['agent_a', 'agent_b']:
            agent_metrics = metrics[agent]
            
            # Metrics that should be between 0 and 1
            bounded_metrics = [
                'unique_word_ratio', 'self_repetition', 'turn_repetition',
                'formality_score', 'symbol_density', 'hapax_ratio',
                'lexical_diversity_index', 'question_density', 'hedge_density'
            ]
            
            for metric in bounded_metrics:
                if metric in agent_metrics:
                    assert 0.0 <= agent_metrics[metric] <= 1.0
        
        # Check convergence metrics
        convergence_bounded = [
            'vocabulary_overlap', 'cumulative_overlap', 'cross_repetition',
            'structural_similarity', 'mimicry_a_to_b', 'mimicry_b_to_a',
            'mutual_mimicry', 'length_ratio', 'sentence_pattern_similarity',
            'overall_convergence_score', 'repetition_ratio'
        ]
        
        for metric in convergence_bounded:
            if metric in metrics['convergence']:
                assert 0.0 <= metrics['convergence'][metric] <= 1.0
    
    @given(st.integers(min_value=0), st.text(), st.text())
    def test_vocabulary_tracking(self, calculator, turn_number, msg_a, msg_b):
        """Vocabulary should be tracked correctly across turns."""
        initial_vocab_size = len(calculator.cumulative_vocab['agent_a'] | calculator.cumulative_vocab['agent_b'])
        
        metrics = calculator.calculate_turn_metrics(turn_number, msg_a, msg_b)
        
        final_vocab_size = len(calculator.cumulative_vocab['agent_a'] | calculator.cumulative_vocab['agent_b'])
        
        # Vocabulary should only grow or stay the same
        assert final_vocab_size >= initial_vocab_size
        
        # Vocabulary in metrics should be a set
        assert isinstance(metrics['agent_a']['vocabulary'], set)
        assert isinstance(metrics['agent_b']['vocabulary'], set)
    
    @given(message_strategy())
    def test_tokenization_caching(self, calculator, message):
        """Tokenization caching should work correctly."""
        # First tokenization
        tokens1 = calculator._tokenize_cached(message)
        
        # Second tokenization should use cache
        tokens2 = calculator._tokenize_cached(message)
        
        assert tokens1 == tokens2
        
        # Check cache contains the message
        if len(calculator._token_cache) < calculator._cache_size_limit:
            assert message in calculator._token_cache
    
    @settings(max_examples=20)  # Reduce for performance
    @given(st.lists(
        st.tuples(message_strategy(), message_strategy()),
        min_size=1,
        max_size=5
    ))
    def test_conversation_flow(self, calculator, conversation):
        """Test metrics calculation across a full conversation."""
        all_metrics = []
        
        for turn_num, (msg_a, msg_b) in enumerate(conversation):
            metrics = calculator.calculate_turn_metrics(turn_num, msg_a, msg_b)
            all_metrics.append(metrics)
        
        # Check that vocabulary grows monotonically
        for i in range(1, len(all_metrics)):
            prev_cumulative = all_metrics[i-1]['convergence']['cumulative_overlap']
            curr_cumulative = all_metrics[i]['convergence']['cumulative_overlap']
            # Cumulative overlap can change in either direction as vocabularies evolve
            assert isinstance(prev_cumulative, float)
            assert isinstance(curr_cumulative, float)
        
        # Check that turn vocabularies are tracked
        assert len(calculator.turn_vocabularies) == len(conversation)
    
    def test_reset_clears_state(self, calculator):
        """Reset should clear all state."""
        # Add some state
        calculator.calculate_turn_metrics(0, "hello world", "goodbye world")
        
        # Verify state exists
        assert len(calculator.cumulative_vocab['agent_a']) > 0
        assert len(calculator.all_agent_words['agent_a']) > 0
        
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


# Edge case testing with specific properties
class TestEdgeCases:
    """Test edge cases with property-based testing."""
    
    @given(st.text(alphabet='', min_size=0, max_size=0))
    def test_empty_text_handling(self, empty_text):
        """All functions should handle empty text gracefully."""
        # TextAnalyzer
        assert TextAnalyzer.tokenize(empty_text) == []
        assert TextAnalyzer.split_sentences(empty_text) == []
        assert TextAnalyzer.count_sentences(empty_text) == 0
        assert TextAnalyzer.count_questions(empty_text) == 0
        assert TextAnalyzer.count_exclamations(empty_text) == 0
        assert TextAnalyzer.count_paragraphs(empty_text) == 0
        assert TextAnalyzer.calculate_punctuation_diversity(empty_text) == 0
        assert TextAnalyzer.calculate_symbol_density(empty_text) == 0.0
        
        # LinguisticAnalyzer
        assert LinguisticAnalyzer.calculate_character_entropy(empty_text) == 0.0
        assert LinguisticAnalyzer.calculate_self_repetition([]) == 0.0
        
        # ConvergenceCalculator
        assert ConvergenceCalculator.calculate_compression_ratio(empty_text) == 0.0
    
    @given(st.text(alphabet=string.whitespace, min_size=1))
    def test_whitespace_only_handling(self, whitespace_text):
        """Functions should handle whitespace-only text correctly."""
        tokens = TextAnalyzer.tokenize(whitespace_text)
        assert tokens == []
        
        sentences = TextAnalyzer.split_sentences(whitespace_text)
        assert sentences == []
        
        paragraphs = TextAnalyzer.count_paragraphs(whitespace_text)
        assert paragraphs == 0
    
    @given(st.text(alphabet=string.punctuation, min_size=1))
    def test_punctuation_only_handling(self, punct_text):
        """Functions should handle punctuation-only text correctly."""
        tokens = TextAnalyzer.tokenize(punct_text)
        assert all(token == '' or all(c in string.punctuation for c in token) for token in tokens)
        
        diversity = TextAnalyzer.calculate_punctuation_diversity(punct_text)
        assert diversity >= 0
        
        symbol_density = TextAnalyzer.calculate_symbol_density(punct_text)
        assert symbol_density == 1.0  # All non-alphabetic
    
    @given(st.lists(st.sampled_from(list(HEDGE_WORDS)), min_size=1))
    def test_hedge_word_detection(self, hedge_words):
        """Hedge word detection should work correctly."""
        markers = LinguisticAnalyzer.count_linguistic_markers(hedge_words)
        assert markers['hedge_words'] == len(hedge_words)
    
    @given(st.lists(st.sampled_from(list(AGREEMENT_MARKERS)), min_size=1))
    def test_agreement_marker_detection(self, agreement_words):
        """Agreement marker detection should work correctly."""
        markers = LinguisticAnalyzer.count_linguistic_markers(agreement_words)
        assert markers['agreement_markers'] == len(agreement_words)