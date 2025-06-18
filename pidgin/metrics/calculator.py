"""Comprehensive metrics calculator for conversation analysis."""

import re
import math
import zlib
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional

from .constants import (
    HEDGE_WORDS, AGREEMENT_MARKERS, DISAGREEMENT_MARKERS, POLITENESS_MARKERS,
    FIRST_PERSON_SINGULAR, FIRST_PERSON_PLURAL, SECOND_PERSON,
    EMOJI_PATTERN, ARROW_PATTERN, MATH_PATTERN, ALL_SPECIAL_SYMBOLS,
    SENTENCE_ENDINGS, QUESTION_PATTERN, EXCLAMATION_PATTERN,
    ACKNOWLEDGMENT_REGEX
)


class MetricsCalculator:
    """Calculates comprehensive metrics for conversation turns."""
    
    def __init__(self):
        """Initialize calculator with cross-turn tracking."""
        self.conversation_vocabulary: Set[str] = set()
        self.turn_vocabularies: List[Dict[str, Set[str]]] = []
        self.previous_messages: Dict[str, List[str]] = {
            'agent_a': [],
            'agent_b': []
        }
        self.all_words_seen: Set[str] = set()
    
    def calculate_turn_metrics(self, turn_number: int, 
                             agent_a_message: str, 
                             agent_b_message: str) -> Dict[str, Any]:
        """Calculate all metrics for a turn.
        
        Args:
            turn_number: 0-indexed turn number
            agent_a_message: Message from agent A
            agent_b_message: Message from agent B
            
        Returns:
            Dictionary with all calculated metrics
        """
        # Calculate metrics for each agent
        metrics_a = self._calculate_message_metrics(
            agent_a_message, 'agent_a', turn_number
        )
        metrics_b = self._calculate_message_metrics(
            agent_b_message, 'agent_b', turn_number
        )
        
        # Calculate convergence metrics between agents
        convergence_metrics = self._calculate_convergence_metrics(
            agent_a_message, agent_b_message, metrics_a, metrics_b
        )
        
        # Store messages for cross-turn analysis
        self.previous_messages['agent_a'].append(agent_a_message)
        self.previous_messages['agent_b'].append(agent_b_message)
        
        # Track vocabularies
        words_a = set(self._tokenize(agent_a_message))
        words_b = set(self._tokenize(agent_b_message))
        self.turn_vocabularies.append({
            'agent_a': words_a,
            'agent_b': words_b
        })
        self.conversation_vocabulary.update(words_a | words_b)
        self.all_words_seen.update(words_a | words_b)
        
        # Combine all metrics
        return {**metrics_a, **metrics_b, **convergence_metrics}
    
    def _calculate_message_metrics(self, message: str, 
                                 agent: str, 
                                 turn_number: int) -> Dict[str, Any]:
        """Calculate metrics for a single message."""
        # Basic text processing
        words = self._tokenize(message)
        sentences = self._split_sentences(message)
        word_freq = Counter(words)
        
        # Vocabulary metrics
        vocabulary = set(words)
        vocabulary_size = len(vocabulary)
        hapax_count = sum(1 for w, c in word_freq.items() if c == 1)
        
        # Calculate which words are new
        new_words = vocabulary - self.all_words_seen
        
        # Calculate additional metrics
        compression_ratio = self._calculate_compression_ratio(message)
        lexical_diversity_index = self._calculate_lexical_diversity_index(len(words), vocabulary_size)
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        punctuation_diversity = self._calculate_punctuation_diversity(message)
        paragraph_count = self._count_paragraphs(message)
        proper_noun_count = self._count_proper_nouns(words)
        number_count = self._count_numbers(message)
        
        # Pattern detection
        questions = len(QUESTION_PATTERN.findall(message))
        exclamations = len(EXCLAMATION_PATTERN.findall(message))
        
        # Linguistic markers
        words_lower = [w.lower() for w in words]
        hedge_count = sum(1 for w in words_lower if w in HEDGE_WORDS)
        agreement_count = sum(1 for w in words_lower if w in AGREEMENT_MARKERS)
        disagreement_count = sum(1 for w in words_lower if w in DISAGREEMENT_MARKERS)
        politeness_count = sum(1 for w in words_lower if w in POLITENESS_MARKERS)
        
        # Symbol detection
        emoji_matches = EMOJI_PATTERN.findall(message)
        emoji_count = len(emoji_matches)
        arrow_count = len(ARROW_PATTERN.findall(message))
        math_count = len(MATH_PATTERN.findall(message))
        other_symbols = self._count_other_symbols(message)
        
        # Pronoun usage
        first_singular = sum(1 for w in words_lower if w in FIRST_PERSON_SINGULAR)
        first_plural = sum(1 for w in words_lower if w in FIRST_PERSON_PLURAL)
        second_person = sum(1 for w in words_lower if w in SECOND_PERSON)
        
        # Repetition metrics
        bigram_rep, trigram_rep = self._calculate_repetition(
            message, agent, turn_number
        )
        self_rep = self._calculate_self_repetition(words)
        
        # Information theory
        word_entropy = self._calculate_entropy(word_freq)
        char_entropy = self._calculate_entropy(Counter(message))
        
        # Response characteristics
        starts_ack = self._starts_with_acknowledgment(message)
        ends_question = message.strip().endswith('?')
        
        # Return metrics with agent suffix
        suffix = '_a' if agent == 'agent_a' else '_b'
        return {
            f'message{suffix}': message,
            f'message_length{suffix}': len(message),
            f'word_count{suffix}': len(words),
            f'sentence_count{suffix}': len(sentences),
            f'paragraph_count{suffix}': paragraph_count,
            f'vocabulary_size{suffix}': vocabulary_size,
            f'type_token_ratio{suffix}': vocabulary_size / len(words) if words else 0,
            f'hapax_legomena_count{suffix}': hapax_count,
            f'hapax_ratio{suffix}': hapax_count / vocabulary_size if vocabulary_size > 0 else 0,
            f'compression_ratio{suffix}': compression_ratio,
            f'lexical_diversity_index{suffix}': lexical_diversity_index,
            f'average_sentence_length{suffix}': avg_sentence_length,
            f'punctuation_diversity{suffix}': punctuation_diversity,
            f'question_count{suffix}': questions,
            f'exclamation_count{suffix}': exclamations,
            f'hedge_count{suffix}': hedge_count,
            f'agreement_marker_count{suffix}': agreement_count,
            f'disagreement_marker_count{suffix}': disagreement_count,
            f'politeness_marker_count{suffix}': politeness_count,
            f'emoji_count{suffix}': emoji_count,
            f'emoji_density{suffix}': emoji_count / len(words) if words else 0,
            f'arrow_count{suffix}': arrow_count,
            f'math_symbol_count{suffix}': math_count,
            f'other_symbol_count{suffix}': other_symbols,
            f'first_person_singular_count{suffix}': first_singular,
            f'first_person_plural_count{suffix}': first_plural,
            f'second_person_count{suffix}': second_person,
            f'number_count{suffix}': number_count,
            f'proper_noun_count{suffix}': proper_noun_count,
            f'repeated_bigrams{suffix}': bigram_rep,
            f'repeated_trigrams{suffix}': trigram_rep,
            f'self_repetition_score{suffix}': self_rep,
            f'word_entropy{suffix}': word_entropy,
            f'character_entropy{suffix}': char_entropy,
            f'starts_with_acknowledgment{suffix}': starts_ack,
            f'ends_with_question{suffix}': ends_question,
            f'new_words_count{suffix}': len(new_words),
            f'new_words_ratio{suffix}': len(new_words) / len(words) if words else 0
        }
    
    def _calculate_convergence_metrics(self, message_a: str, message_b: str,
                                     metrics_a: Dict[str, Any],
                                     metrics_b: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate convergence metrics between two messages."""
        # Extract vocabularies
        words_a = set(self._tokenize(message_a))
        words_b = set(self._tokenize(message_b))
        
        # Vocabulary overlap (Jaccard similarity)
        if words_a or words_b:
            vocab_overlap = len(words_a & words_b) / len(words_a | words_b)
        else:
            vocab_overlap = 0.0
        
        # Length ratio
        len_a = metrics_a['message_length_a']
        len_b = metrics_b['message_length_b']
        if max(len_a, len_b) > 0:
            length_ratio = min(len_a, len_b) / max(len_a, len_b)
        else:
            length_ratio = 1.0
        
        # Structural similarity (sentence patterns)
        struct_sim = self._calculate_structural_similarity(message_a, message_b)
        
        # Cross-agent repetition
        cross_rep = self._calculate_cross_repetition(message_a, message_b)
        
        # Mimicry score - how much B copies from A
        mimicry_score = self._calculate_mimicry_score(message_a, message_b)
        
        # Overall convergence score (weighted average)
        convergence_score = (
            0.25 * vocab_overlap +
            0.15 * length_ratio +
            0.15 * struct_sim +
            0.25 * cross_rep +
            0.20 * mimicry_score
        )
        
        return {
            'convergence_score': convergence_score,
            'vocabulary_overlap': vocab_overlap,
            'length_ratio': length_ratio,
            'structural_similarity': struct_sim,
            'cross_repetition_score': cross_rep,
            'mimicry_score': mimicry_score
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Simple word tokenization
        return re.findall(r'\b\w+\b', text)
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = SENTENCE_ENDINGS.split(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_entropy(self, counter: Counter) -> float:
        """Calculate Shannon entropy."""
        if not counter:
            return 0.0
        
        total = sum(counter.values())
        entropy = 0.0
        
        for count in counter.values():
            if count > 0:
                prob = count / total
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _calculate_repetition(self, message: str, agent: str, 
                            turn_number: int) -> Tuple[int, int]:
        """Calculate bigram/trigram repetition from previous turn."""
        if turn_number == 0 or not self.previous_messages[agent]:
            return 0, 0
        
        words = self._tokenize(message.lower())
        if len(self.previous_messages[agent]) > 0:
            prev_words = self._tokenize(self.previous_messages[agent][-1].lower())
        else:
            return 0, 0
        
        # Count repeated bigrams
        bigrams = set(zip(words[:-1], words[1:]))
        prev_bigrams = set(zip(prev_words[:-1], prev_words[1:]))
        repeated_bigrams = len(bigrams & prev_bigrams)
        
        # Count repeated trigrams
        trigrams = set(zip(words[:-2], words[1:-1], words[2:]))
        prev_trigrams = set(zip(prev_words[:-2], prev_words[1:-1], prev_words[2:]))
        repeated_trigrams = len(trigrams & prev_trigrams)
        
        return repeated_bigrams, repeated_trigrams
    
    def _calculate_self_repetition(self, words: List[str]) -> float:
        """Calculate repetition within the same message."""
        if len(words) < 2:
            return 0.0
        
        # Count repeated words (excluding common words)
        word_freq = Counter(w.lower() for w in words)
        repeated = sum(1 for w, c in word_freq.items() if c > 1)
        
        return repeated / len(word_freq) if word_freq else 0.0
    
    def _calculate_cross_repetition(self, message_a: str, message_b: str) -> float:
        """Calculate phrase repetition between agents."""
        words_a = self._tokenize(message_a.lower())
        words_b = self._tokenize(message_b.lower())
        
        if not words_a or not words_b:
            return 0.0
        
        # Find common n-grams
        common_score = 0.0
        
        # Bigrams
        bigrams_a = set(zip(words_a[:-1], words_a[1:]))
        bigrams_b = set(zip(words_b[:-1], words_b[1:]))
        if bigrams_a or bigrams_b:
            common_score += len(bigrams_a & bigrams_b) / max(len(bigrams_a), len(bigrams_b))
        
        # Trigrams
        if len(words_a) > 2 and len(words_b) > 2:
            trigrams_a = set(zip(words_a[:-2], words_a[1:-1], words_a[2:]))
            trigrams_b = set(zip(words_b[:-2], words_b[1:-1], words_b[2:]))
            if trigrams_a or trigrams_b:
                common_score += len(trigrams_a & trigrams_b) / max(len(trigrams_a), len(trigrams_b))
        
        return min(common_score, 1.0)
    
    def _calculate_structural_similarity(self, message_a: str, message_b: str) -> float:
        """Calculate structural similarity between messages."""
        # Compare sentence patterns
        sent_a = self._split_sentences(message_a)
        sent_b = self._split_sentences(message_b)
        
        if not sent_a or not sent_b:
            return 0.0
        
        # Compare number of sentences
        sent_ratio = min(len(sent_a), len(sent_b)) / max(len(sent_a), len(sent_b))
        
        # Compare punctuation patterns
        punct_a = re.findall(r'[.!?,;:]', message_a)
        punct_b = re.findall(r'[.!?,;:]', message_b)
        
        if punct_a or punct_b:
            punct_ratio = min(len(punct_a), len(punct_b)) / max(len(punct_a), len(punct_b))
        else:
            punct_ratio = 1.0
        
        return (sent_ratio + punct_ratio) / 2
    
    def _starts_with_acknowledgment(self, message: str) -> bool:
        """Check if message starts with acknowledgment."""
        message_lower = message.lower().strip()
        return bool(ACKNOWLEDGMENT_REGEX.match(message_lower))
    
    def _count_other_symbols(self, message: str) -> int:
        """Count other Unicode symbols not covered by emoji/arrow/math."""
        # Count all non-ASCII symbols
        symbols = 0
        for char in message:
            if ord(char) > 127:  # Non-ASCII
                # Check if it's not already counted
                if not (EMOJI_PATTERN.match(char) or 
                       char in ALL_SPECIAL_SYMBOLS):
                    symbols += 1
        return symbols
    
    def get_word_frequencies(self, message: str, agent: str) -> Tuple[Dict[str, int], Set[str]]:
        """Get word frequencies and new words for a message."""
        words = self._tokenize(message.lower())
        word_freq = Counter(words)
        
        # Identify new words
        new_words = set(words) - self.all_words_seen
        
        return dict(word_freq), new_words
    
    def _calculate_compression_ratio(self, text: str) -> float:
        """Calculate compression ratio using zlib."""
        if not text:
            return 0.0
        original_size = len(text.encode('utf-8'))
        compressed_size = len(zlib.compress(text.encode('utf-8')))
        return compressed_size / original_size
    
    def _calculate_lexical_diversity_index(self, word_count: int, vocabulary_size: int) -> float:
        """Calculate lexical diversity index (unique words / sqrt(total words))."""
        if word_count == 0:
            return 0.0
        return vocabulary_size / math.sqrt(word_count)
    
    def _calculate_punctuation_diversity(self, text: str) -> int:
        """Count unique punctuation marks used."""
        punct_pattern = r'[.,;:!?\'"()\[\]{}\-–—…]'
        punctuation = set(re.findall(punct_pattern, text))
        return len(punctuation)
    
    def _count_paragraphs(self, text: str) -> int:
        """Count paragraphs (separated by double newlines)."""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return len([p for p in paragraphs if p.strip()])
    
    def _count_proper_nouns(self, words: List[str]) -> int:
        """Count likely proper nouns (capitalized words not at sentence start)."""
        if len(words) < 2:
            return 0
        
        proper_count = 0
        for i, word in enumerate(words[1:], 1):
            # Check if capitalized and previous word doesn't end sentence
            if word and word[0].isupper() and words[i-1][-1] not in '.!?':
                proper_count += 1
        
        return proper_count
    
    def _count_numbers(self, text: str) -> int:
        """Count numeric tokens in text."""
        # Match integers, decimals, and formatted numbers
        number_pattern = r'\b\d+(?:[.,]\d+)*\b'
        return len(re.findall(number_pattern, text))
    
    def _calculate_mimicry_score(self, message_a: str, message_b: str) -> float:
        """Calculate how much message_b mimics phrases from message_a."""
        words_a = self._tokenize(message_a.lower())
        words_b = self._tokenize(message_b.lower())
        
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
        
        return min(mimicry_score, 1.0)