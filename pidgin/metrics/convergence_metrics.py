"""Convergence and similarity metrics for conversation analysis."""

import math
import zlib
from typing import Set, List, Dict, Tuple
from collections import Counter

from .text_analysis import TextAnalyzer


class ConvergenceCalculator:
    """Calculates convergence-related metrics between messages."""
    
    @staticmethod
    def calculate_vocabulary_overlap(vocab_a: Set[str], vocab_b: Set[str]) -> float:
        """Calculate Jaccard similarity between vocabularies."""
        if not vocab_a or not vocab_b:
            return 0.0
        union = vocab_a | vocab_b
        if not union:
            return 0.0
        return len(vocab_a & vocab_b) / len(union)
    
    @staticmethod
    def calculate_mimicry_score(message_a: str, message_b: str) -> float:
        """Calculate how much message_b mimics phrases from message_a."""
        words_a = TextAnalyzer.tokenize(message_a.lower())
        words_b = TextAnalyzer.tokenize(message_b.lower())
        
        if not words_a or not words_b:
            return 0.0
        
        mimicry_score = 0.0
        
        # Check for copied phrases of different lengths
        for n in range(2, min(6, len(words_a), len(words_b)) + 1):
            ngrams_a = set(zip(*[words_a[i:] for i in range(n)]))
            ngrams_b = set(zip(*[words_b[i:] for i in range(n)]))
            
            if ngrams_a:
                overlap = len(ngrams_a & ngrams_b) / len(ngrams_a)
                # Weight longer phrases more heavily
                mimicry_score += overlap * (n - 1)
        
        # Normalize by maximum possible score
        max_n = min(6, len(words_a), len(words_b))
        if max_n > 1:
            max_score = sum(range(1, max_n))
            if max_score > 0:
                mimicry_score /= max_score
        
        return mimicry_score
    
    @staticmethod
    def calculate_cross_repetition(message_a: str, message_b: str) -> float:
        """Calculate word repetition between messages."""
        words_a = TextAnalyzer.tokenize(message_a.lower())
        words_b = TextAnalyzer.tokenize(message_b.lower())
        
        if not words_a or not words_b:
            return 0.0
        
        # Count shared words
        counter_a = Counter(words_a)
        counter_b = Counter(words_b)
        
        shared_count = 0
        for word in set(words_a) & set(words_b):
            shared_count += min(counter_a[word], counter_b[word])
        
        # Normalize by total words
        total_words = len(words_a) + len(words_b)
        return (2 * shared_count) / total_words if total_words > 0 else 0.0
    
    @staticmethod
    def calculate_structural_similarity(message_a: str, message_b: str) -> float:
        """Calculate structural similarity between messages."""
        sentences_a = TextAnalyzer.split_sentences(message_a)
        sentences_b = TextAnalyzer.split_sentences(message_b)
        
        # Compare sentence counts
        len_similarity = 1 - abs(len(sentences_a) - len(sentences_b)) / max(
            len(sentences_a), len(sentences_b), 1
        )
        
        # Compare average sentence lengths
        avg_len_a = sum(len(s.split()) for s in sentences_a) / max(len(sentences_a), 1)
        avg_len_b = sum(len(s.split()) for s in sentences_b) / max(len(sentences_b), 1)
        
        length_similarity = 1 - abs(avg_len_a - avg_len_b) / max(avg_len_a, avg_len_b, 1)
        
        # Weight both factors
        return 0.5 * len_similarity + 0.5 * length_similarity
    
    @staticmethod
    def calculate_compression_ratio(text: str) -> float:
        """Calculate compression ratio as a complexity metric."""
        if not text:
            return 0.0
        
        original_size = len(text.encode('utf-8'))
        compressed_size = len(zlib.compress(text.encode('utf-8')))
        
        return compressed_size / original_size if original_size > 0 else 0.0