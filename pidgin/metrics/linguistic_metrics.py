"""Linguistic and stylistic metrics for conversation analysis."""

import math
from typing import List, Set, Dict
from collections import Counter

from .constants import (
    HEDGE_WORDS, AGREEMENT_MARKERS, DISAGREEMENT_MARKERS, 
    POLITENESS_MARKERS, FIRST_PERSON_SINGULAR, FIRST_PERSON_PLURAL, 
    SECOND_PERSON
)
from .text_analysis import TextAnalyzer


class LinguisticAnalyzer:
    """Calculates linguistic and stylistic metrics."""
    
    @staticmethod
    def calculate_entropy(counter: Counter) -> float:
        """Calculate Shannon entropy of word distribution."""
        if not counter:
            return 0.0
        
        total = sum(counter.values())
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in counter.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    @staticmethod
    def calculate_self_repetition(words: List[str]) -> float:
        """Calculate repetition within a single message."""
        if len(words) < 2:
            return 0.0
        
        # Count consecutive repeated words
        repetitions = sum(1 for i in range(1, len(words)) if words[i] == words[i-1])
        
        # Normalize by message length
        return repetitions / (len(words) - 1)
    
    @staticmethod
    def calculate_lexical_diversity_index(word_count: int, vocabulary_size: int) -> float:
        """Calculate lexical diversity (TTR variant)."""
        if word_count == 0:
            return 0.0
        # Use root TTR for length-independent measure
        return vocabulary_size / math.sqrt(word_count)
    
    @staticmethod
    def count_linguistic_markers(words: List[str]) -> Dict[str, int]:
        """Count various linguistic markers in the message."""
        words_lower = [w.lower() for w in words]
        
        return {
            'hedge_words': sum(1 for w in words_lower if w in HEDGE_WORDS),
            'agreement_markers': sum(1 for w in words_lower if w in AGREEMENT_MARKERS),
            'disagreement_markers': sum(1 for w in words_lower if w in DISAGREEMENT_MARKERS),
            'politeness_markers': sum(1 for w in words_lower if w in POLITENESS_MARKERS),
            'first_person_singular': sum(1 for w in words_lower if w in FIRST_PERSON_SINGULAR),
            'first_person_plural': sum(1 for w in words_lower if w in FIRST_PERSON_PLURAL),
            'second_person': sum(1 for w in words_lower if w in SECOND_PERSON)
        }
    
    @staticmethod
    def calculate_formality_score(text: str, words: List[str]) -> float:
        """Estimate formality based on various indicators."""
        if not words:
            return 0.5  # Neutral
        
        # Positive indicators of formality
        formal_score = 0.0
        
        # Contractions indicate informality
        contraction_count = len([w for w in words if "'" in w])
        formal_score -= (contraction_count / len(words)) * 0.3
        
        # Exclamations indicate informality
        exclamation_count = text.count('!')
        formal_score -= (exclamation_count / len(words)) * 0.2
        
        # Question marks are neutral, but multiple indicate informality
        multi_question = len([i for i in range(len(text)-1) if text[i:i+2] == '??'])
        formal_score -= (multi_question / len(words)) * 0.1
        
        # Long words indicate formality
        long_words = [w for w in words if len(w) > 7]
        formal_score += (len(long_words) / len(words)) * 0.3
        
        # Normalize to 0-1 range
        return max(0.0, min(1.0, 0.5 + formal_score))