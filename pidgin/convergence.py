"""Convergence metrics for tracking when AI agents start sounding alike."""

import re
from typing import List, Tuple
from .types import Message


class ConvergenceCalculator:
    """Calculate structural similarity between agent responses."""
    
    def __init__(self, window_size: int = 10):
        """Initialize convergence calculator.
        
        Args:
            window_size: Number of recent messages to consider
        """
        self.window_size = window_size
        self.history: List[float] = []
        
    def calculate(self, messages: List[Message]) -> float:
        """Calculate structural similarity between recent A and B messages.
        
        Returns 0.0 (completely different) to 1.0 (identical).
        
        Args:
            messages: Full conversation history
            
        Returns:
            Convergence score between 0.0 and 1.0
        """
        # Get recent messages from each agent
        recent_messages = messages[-self.window_size:] if len(messages) > self.window_size else messages
        
        recent_a = [m for m in recent_messages if m.agent_id == 'agent_a']
        recent_b = [m for m in recent_messages if m.agent_id == 'agent_b']
        
        if not recent_a or not recent_b:
            return 0.0
            
        # Calculate multiple structural similarity metrics
        length_sim = self._length_similarity(recent_a, recent_b)
        sentence_sim = self._sentence_pattern_similarity(recent_a, recent_b)
        structure_sim = self._structure_similarity(recent_a, recent_b)
        punctuation_sim = self._punctuation_similarity(recent_a, recent_b)
        
        # Weighted average (can be tuned based on what matters most)
        weights = {
            'length': 0.2,
            'sentences': 0.3,
            'structure': 0.3,
            'punctuation': 0.2
        }
        
        similarity = (
            length_sim * weights['length'] +
            sentence_sim * weights['sentences'] +
            structure_sim * weights['structure'] +
            punctuation_sim * weights['punctuation']
        )
        
        # Track history
        self.history.append(similarity)
        
        return round(similarity, 2)
    
    def _length_similarity(self, messages_a: List[Message], messages_b: List[Message]) -> float:
        """Calculate similarity based on message lengths."""
        if not messages_a or not messages_b:
            return 0.0
            
        # Compare average message lengths
        avg_len_a = sum(len(m.content) for m in messages_a) / len(messages_a)
        avg_len_b = sum(len(m.content) for m in messages_b) / len(messages_b)
        
        if avg_len_a == 0 or avg_len_b == 0:
            return 0.0
            
        # Ratio similarity (closer to 1.0 means more similar)
        ratio = min(avg_len_a, avg_len_b) / max(avg_len_a, avg_len_b)
        return ratio
    
    def _sentence_pattern_similarity(self, messages_a: List[Message], messages_b: List[Message]) -> float:
        """Calculate similarity based on sentence patterns."""
        # Extract sentences using simple regex
        sentence_pattern = r'[.!?]+[\s]'
        
        def avg_sentences(messages):
            total_sentences = 0
            for m in messages:
                # Count sentences (add 1 for last sentence if no trailing punctuation)
                count = len(re.findall(sentence_pattern, m.content))
                if m.content and not m.content.strip().endswith(('.', '!', '?')):
                    count += 1
                total_sentences += count
            return total_sentences / len(messages) if messages else 0
        
        avg_sent_a = avg_sentences(messages_a)
        avg_sent_b = avg_sentences(messages_b)
        
        if avg_sent_a == 0 or avg_sent_b == 0:
            return 0.0
            
        ratio = min(avg_sent_a, avg_sent_b) / max(avg_sent_a, avg_sent_b)
        return ratio
    
    def _structure_similarity(self, messages_a: List[Message], messages_b: List[Message]) -> float:
        """Calculate similarity based on structural patterns (paragraphs, lists, questions)."""
        def extract_features(messages):
            features = {
                'paragraphs': 0,
                'lists': 0,
                'questions': 0,
                'code_blocks': 0
            }
            
            for m in messages:
                content = m.content
                # Count paragraphs (double newlines)
                features['paragraphs'] += len(re.findall(r'\n\n', content)) + 1
                # Count list items (lines starting with -, *, or numbers)
                features['lists'] += len(re.findall(r'^[\s]*[-*•]|\d+\.', content, re.MULTILINE))
                # Count questions
                features['questions'] += content.count('?')
                # Count code blocks (triple backticks)
                features['code_blocks'] += content.count('```')
                
            # Normalize by message count
            for key in features:
                features[key] = features[key] / len(messages) if messages else 0
                
            return features
        
        features_a = extract_features(messages_a)
        features_b = extract_features(messages_b)
        
        # Calculate similarity for each feature
        similarities = []
        for key in features_a:
            if features_a[key] == 0 and features_b[key] == 0:
                similarities.append(1.0)  # Both have none, that's similar
            elif features_a[key] == 0 or features_b[key] == 0:
                similarities.append(0.0)  # One has none, that's different
            else:
                ratio = min(features_a[key], features_b[key]) / max(features_a[key], features_b[key])
                similarities.append(ratio)
                
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _punctuation_similarity(self, messages_a: List[Message], messages_b: List[Message]) -> float:
        """Calculate similarity based on punctuation patterns."""
        def punctuation_profile(messages):
            profile = {
                'exclamations': 0,
                'commas': 0,
                'semicolons': 0,
                'colons': 0,
                'dashes': 0
            }
            
            total_chars = 0
            for m in messages:
                content = m.content
                total_chars += len(content)
                profile['exclamations'] += content.count('!')
                profile['commas'] += content.count(',')
                profile['semicolons'] += content.count(';')
                profile['colons'] += content.count(':')
                profile['dashes'] += content.count('-') + content.count('—')
                
            # Normalize by total characters
            for key in profile:
                profile[key] = profile[key] / total_chars if total_chars > 0 else 0
                
            return profile
        
        profile_a = punctuation_profile(messages_a)
        profile_b = punctuation_profile(messages_b)
        
        # Calculate similarity
        similarities = []
        for key in profile_a:
            if profile_a[key] == 0 and profile_b[key] == 0:
                similarities.append(1.0)
            elif profile_a[key] == 0 or profile_b[key] == 0:
                similarities.append(0.0)
            else:
                ratio = min(profile_a[key], profile_b[key]) / max(profile_a[key], profile_b[key])
                similarities.append(ratio)
                
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def get_trend(self) -> str:
        """Get the trend of convergence (increasing, decreasing, stable)."""
        if len(self.history) < 3:
            return "insufficient data"
            
        recent = self.history[-3:]
        
        # Check if increasing
        if recent[-1] > recent[-2] > recent[-3]:
            return "increasing"
        # Check if decreasing
        elif recent[-1] < recent[-2] < recent[-3]:
            return "decreasing"
        # Check if relatively stable (within 0.1)
        elif all(abs(recent[i] - recent[i-1]) < 0.1 for i in range(1, len(recent))):
            return "stable"
        else:
            return "fluctuating"
    
    def get_recent_history(self, n: int = 5) -> List[Tuple[int, float]]:
        """Get recent convergence history with turn numbers.
        
        Args:
            n: Number of recent turns to return
            
        Returns:
            List of (turn_number, convergence_score) tuples
        """
        if not self.history:
            return []
            
        start_idx = max(0, len(self.history) - n)
        return [(i + 1, score) for i, score in enumerate(self.history[start_idx:], start=start_idx)]