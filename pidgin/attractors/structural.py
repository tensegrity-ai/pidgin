"""Structural pattern detection for conversation attractors.

This module implements the CORE INSIGHT: conversations fall into structural
templates long before content becomes repetitive. By analyzing message
structure rather than content, we can detect attractors as they form.
"""

import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import logging

from .patterns import PatternRegistry

logger = logging.getLogger(__name__)


@dataclass
class StructuralElement:
    """Represents a structural component of a message."""
    type: str  # OPENING, LIST, QUESTION, etc.
    position: int
    features: dict  # Length, punctuation, keywords


class StructuralAnalyzer:
    """
    THE CORE OF ATTRACTOR DETECTION.
    Analyzes the formal structure of messages, not their content.
    """
    
    def extract_structure(self, content: str) -> List[StructuralElement]:
        """
        Convert a message into its structural skeleton.
        This is the KEY INNOVATION that makes detection work.
        """
        lines = content.strip().split('\n')
        elements = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            element = self._analyze_line(line, i)
            elements.append(element)
            
        return elements
    
    def _analyze_line(self, line: str, position: int) -> StructuralElement:
        """Classify a line by its structural role."""
        
        features = {
            'length': len(line),
            'punctuation': line[-1] if line else '',
            'starts_with': line.split()[0].lower() if line else '',
            'caps_ratio': sum(1 for c in line if c.isupper()) / max(len(line), 1),
            'has_emoji': bool(re.search(r'[\U0001F300-\U0001F9FF]', line)),
            'is_list': bool(re.match(r'^[\-\*\•\d]\.\s', line))
        }
        
        # CRITICAL: Identify structural patterns, not content
        if position == 0 and features['punctuation'] in '!?' and features['length'] < 50:
            return StructuralElement('EXCITED_OPENING', position, features)
            
        if re.match(r'^(I\'ve|We\'ve|Just|Still|Now|Today|Here\'s)', line):
            return StructuralElement('ANNOUNCEMENT', position, features)
            
        if re.match(r'^(I |We |My |Our |This |That )', line):
            return StructuralElement('FIRST_PERSON_STATEMENT', position, features)
            
        if features['is_list'] or line.startswith(('- ', '* ', '• ', '1.', '2.', '3.')):
            return StructuralElement('LIST_ITEM', position, features)
            
        if features['punctuation'] == '?':
            return StructuralElement('QUESTION', position, features)
            
        if features['punctuation'] in ['!', '!!', '!!!'] and features['length'] < 100:
            return StructuralElement('EXCLAMATION', position, features)
            
        if any(marker in line.lower() for marker in ['p.s.', 'ps:', 'p.s:', 'note:', 'btw:']):
            return StructuralElement('POSTSCRIPT', position, features)
            
        if features['has_emoji'] and features['length'] < 50:
            return StructuralElement('EMOJI_LINE', position, features)
            
        if features['length'] < 20:
            return StructuralElement('SHORT_LINE', position, features)
            
        if features['length'] > 150:
            return StructuralElement('LONG_STATEMENT', position, features)
            
        return StructuralElement('STATEMENT', position, features)


class StructuralPatternDetector:
    """Detects when conversations fall into repetitive structural patterns."""
    
    def __init__(self, window_size: int = 10, threshold: int = 3):
        self.window_size = window_size
        self.threshold = threshold
        self.analyzer = StructuralAnalyzer()
        
    def detect_attractor(self, messages: List[str]) -> Optional[Dict]:
        """
        Check if the conversation has entered a structural attractor.
        Returns details about the detected pattern if found.
        """
        if len(messages) < self.window_size:
            return None
            
        # Extract structures for recent messages
        structures = []
        for msg in messages[-self.window_size:]:
            structure = self.analyzer.extract_structure(msg)
            signature = self._create_signature(structure)
            structures.append(signature)
            
        # Look for repeating patterns
        pattern = self._find_repeating_pattern(structures)
        if pattern:
            pattern_info = PatternRegistry.get_pattern_info(pattern['signature'])
            return {
                'type': pattern_info['name'],
                'pattern': pattern['signature'],
                'frequency': pattern['count'],
                'confidence': pattern['count'] / len(structures),
                'sample_positions': pattern['positions'],
                'description': pattern_info['description'],
                'typical_turns': pattern_info.get('typical_turns', 'varies')
            }
            
        # Also check for alternating patterns (A-B-A-B)
        alt_pattern = self._find_alternating_pattern(structures)
        if alt_pattern:
            pattern_info = PatternRegistry.describe_alternating_pattern(alt_pattern['pair'])
            return {
                'type': pattern_info['name'],
                'pattern': alt_pattern['pair'],
                'frequency': alt_pattern['count'],
                'confidence': alt_pattern['count'] / (len(structures) // 2),
                'sample_positions': alt_pattern['positions'],
                'description': pattern_info['description'],
                'typical_turns': pattern_info.get('typical_turns', 'varies')
            }
            
        return None
        
    def _create_signature(self, elements: List[StructuralElement]) -> str:
        """Create a signature representing the message structure."""
        return '|'.join(e.type for e in elements)
        
    def _find_repeating_pattern(self, signatures: List[str]) -> Optional[Dict]:
        """Find the most common repeating pattern."""
        pattern_counts = {}
        for i, sig in enumerate(signatures):
            if sig in pattern_counts:
                pattern_counts[sig]['count'] += 1
                pattern_counts[sig]['positions'].append(i)
            else:
                pattern_counts[sig] = {
                    'signature': sig,
                    'count': 1,
                    'positions': [i]
                }
                
        # Find patterns that exceed threshold AND have high confidence
        for pattern_data in pattern_counts.values():
            if pattern_data['count'] >= self.threshold:
                # Calculate confidence
                confidence = pattern_data['count'] / len(signatures)
                
                # Only trigger detection if confidence is >= 80%
                if confidence >= 0.8:
                    return pattern_data
                
        return None
        
    def _find_alternating_pattern(self, signatures: List[str]) -> Optional[Dict]:
        """Find alternating A-B-A-B patterns (common in conversations)."""
        if len(signatures) < 4:
            return None
            
        # Check pairs of signatures
        pair_counts = {}
        for i in range(0, len(signatures) - 3, 2):
            pair = (signatures[i], signatures[i + 1])
            next_pair = (signatures[i + 2], signatures[i + 3]) if i + 3 < len(signatures) else None
            
            if next_pair and pair == next_pair:
                key = f"{pair[0]}|||{pair[1]}"
                if key in pair_counts:
                    pair_counts[key]['count'] += 1
                    pair_counts[key]['positions'].extend([i, i + 1])
                else:
                    pair_counts[key] = {
                        'pair': pair,
                        'count': 2,
                        'positions': [i, i + 1, i + 2, i + 3]
                    }
                    
        # Check if any alternating pattern exceeds threshold AND has high confidence
        for pattern_data in pair_counts.values():
            if pattern_data['count'] >= self.threshold - 1:  # Slightly lower threshold for alternating
                # Calculate confidence for alternating patterns
                confidence = pattern_data['count'] / (len(signatures) // 2)
                
                # Only trigger detection if confidence is >= 80%
                if confidence >= 0.8:
                    return pattern_data
                
        return None
        
    def _describe_pattern(self, signature: str) -> str:
        """Generate human-readable description of the pattern."""
        elements = signature.split('|')
        
        # Common attractor patterns
        if elements == ['EXCITED_OPENING', 'ANNOUNCEMENT', 'LIST_ITEM', 'LIST_ITEM', 'LIST_ITEM', 'QUESTION', 'POSTSCRIPT']:
            return "Party attractor: Excitement → Metrics → Question → Silly PS"
        elif 'LIST_ITEM' in elements and elements.count('LIST_ITEM') >= 3:
            return "List-heavy structure (often metrics or observations)"
        elif elements[0] == 'EXCITED_OPENING' and elements[-1] in ['QUESTION', 'POSTSCRIPT']:
            return "Engagement loop: Excitement → Content → Hook"
        elif all(e in ['SHORT_LINE', 'EMOJI_LINE'] for e in elements):
            return "Compression attractor: Minimal responses"
        else:
            return f"Structure: {' → '.join(elements[:3])}..."
            
    def _describe_alternating_pattern(self, pair: Tuple[str, str]) -> str:
        """Describe an alternating pattern."""
        return f"Alternating between:\nA: {pair[0][:50]}...\nB: {pair[1][:50]}..."