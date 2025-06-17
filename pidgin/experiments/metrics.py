"""Comprehensive metrics calculator for conversation turns."""

import re
import math
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, asdict


# Word sets for linguistic markers
HEDGE_WORDS = {
    'maybe', 'perhaps', 'possibly', 'probably', 'might', 'could', 'seems',
    'appears', 'suggests', 'somewhat', 'fairly', 'quite', 'rather', 'sort of',
    'kind of', 'basically', 'essentially', 'generally', 'typically', 'usually'
}

AGREEMENT_MARKERS = {
    'yes', 'yeah', 'yep', 'sure', 'agreed', 'agree', 'exactly', 'precisely',
    'absolutely', 'definitely', 'certainly', 'indeed', 'right', 'correct',
    'true', 'affirmative', 'of course', 'naturally', 'obviously'
}

DISAGREEMENT_MARKERS = {
    'no', 'nope', 'not', 'disagree', 'wrong', 'incorrect', 'false', 'but',
    'however', 'although', 'though', 'actually', 'conversely', 'contrary',
    'unfortunately', 'negative', 'nah', 'doubt', 'doubtful'
}

POLITENESS_MARKERS = {
    'please', 'thank', 'thanks', 'sorry', 'excuse', 'pardon', 'appreciate',
    'grateful', 'kindly', 'respectfully', 'humbly', 'graciously', 'sincerely'
}

# Pronoun sets
FIRST_PERSON_SINGULAR = {'i', 'me', 'my', 'mine', 'myself'}
FIRST_PERSON_PLURAL = {'we', 'us', 'our', 'ours', 'ourselves'}
SECOND_PERSON = {'you', 'your', 'yours', 'yourself', 'yourselves'}

# Unicode ranges for symbol detection
EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map symbols
    "\U0001F1E0-\U0001F1FF"   # flags
    "\U00002702-\U000027B0"   # dingbats
    "\U000024C2-\U0001F251"   # enclosed characters
    "]+", flags=re.UNICODE
)

ARROW_PATTERN = re.compile(r'[→←↔⇒⇐⇔➜➡⬅↑↓⬆⬇]')
MATH_PATTERN = re.compile(r'[≈≡≠≤≥±×÷∞∑∏∂∇√∫]')


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
        
        # Pattern detection
        questions = len(re.findall(r'\?', message))
        exclamations = len(re.findall(r'!', message))
        
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
            f'vocabulary_size{suffix}': vocabulary_size,
            f'type_token_ratio{suffix}': vocabulary_size / len(words) if words else 0,
            f'hapax_legomena_count{suffix}': hapax_count,
            f'hapax_ratio{suffix}': hapax_count / vocabulary_size if vocabulary_size > 0 else 0,
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
            f'repeated_bigrams{suffix}': bigram_rep,
            f'repeated_trigrams{suffix}': trigram_rep,
            f'self_repetition_score{suffix}': self_rep,
            f'word_entropy{suffix}': word_entropy,
            f'character_entropy{suffix}': char_entropy,
            f'starts_with_acknowledgment{suffix}': starts_ack,
            f'ends_with_question{suffix}': ends_question,
            f'new_words{suffix}': len(new_words),
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
        
        # Overall convergence score (weighted average)
        convergence_score = (
            0.3 * vocab_overlap +
            0.2 * length_ratio +
            0.2 * struct_sim +
            0.3 * cross_rep
        )
        
        return {
            'convergence_score': convergence_score,
            'vocabulary_overlap': vocab_overlap,
            'length_ratio': length_ratio,
            'structural_similarity': struct_sim,
            'cross_repetition_score': cross_rep
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Simple word tokenization
        return re.findall(r'\b\w+\b', text)
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
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
        ack_patterns = [
            r'^(yes|yeah|yep|sure|okay|ok|right|correct|agreed|indeed)',
            r'^(ah|oh|hmm|hm|well|so|now)',
            r'^(i see|i understand|i agree|got it|makes sense)',
            r'^(thank|thanks|appreciate)',
        ]
        
        message_lower = message.lower().strip()
        for pattern in ack_patterns:
            if re.match(pattern, message_lower):
                return True
        return False
    
    def _count_other_symbols(self, message: str) -> int:
        """Count other Unicode symbols not covered by emoji/arrow/math."""
        # Count all non-ASCII symbols
        symbols = 0
        for char in message:
            if ord(char) > 127:  # Non-ASCII
                # Check if it's not already counted
                if not (EMOJI_PATTERN.match(char) or 
                       ARROW_PATTERN.match(char) or 
                       MATH_PATTERN.match(char)):
                    symbols += 1
        return symbols
    
    def get_word_frequencies(self, message: str, agent: str) -> Tuple[Dict[str, int], Set[str]]:
        """Get word frequencies and new words for a message."""
        words = self._tokenize(message.lower())
        word_freq = Counter(words)
        
        # Identify new words
        new_words = set(words) - self.all_words_seen
        
        return dict(word_freq), new_words