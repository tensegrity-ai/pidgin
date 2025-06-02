"""Basin detection system for identifying conversation attractors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import re
from collections import Counter, deque

from .types import Message


class BasinType(Enum):
    """Types of conversation basins/attractors."""
    GRATITUDE_SPIRAL = "gratitude_spiral"
    COMPRESSION = "compression"
    EMOJI_LOOP = "emoji_loop"
    STRUCTURAL_REPETITION = "structural_repetition"
    PHILOSOPHICAL_LOOP = "philosophical_loop"
    SINGLE_TOKEN = "single_token"
    MANTRA = "mantra"


@dataclass
class BasinEvent:
    """Information about a detected basin."""
    type: BasinType
    detector: str
    turn: int
    confidence: float
    details: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BasinDetector(ABC):
    """Base class for basin detection strategies."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.confidence = 0.0
    
    @abstractmethod
    def check(self, messages: List[Message]) -> Optional[BasinType]:
        """Check if messages have fallen into a basin."""
        pass
    
    def get_window(self, messages: List[Message], window_size: int) -> List[Message]:
        """Get the last N messages for analysis."""
        return messages[-window_size:] if len(messages) >= window_size else messages


class PatternBasinDetector(BasinDetector):
    """Detects obvious content patterns."""
    
    def check(self, messages: List[Message]) -> Optional[BasinType]:
        window_size = self.config.get('window_size', 20)
        window = self.get_window(messages, window_size)
        
        if not window:
            return None
        
        # Check for gratitude spiral
        if basin := self._check_gratitude_spiral(window):
            return basin
        
        # Check for compression
        if basin := self._check_compression(window):
            return basin
        
        # Check for emoji loops
        if basin := self._check_emoji_loop(window):
            return basin
        
        # Check for single token repetition
        if basin := self._check_single_token(window):
            return basin
        
        return None
    
    def _check_gratitude_spiral(self, messages: List[Message]) -> Optional[BasinType]:
        """Detect endless gratitude exchanges."""
        gratitude_patterns = [
            r'\b(thank|grateful|appreciate|gratitude|blessed|thankful)\b',
            r'\b(honor|privilege|wonderful|beautiful|joy|delight)\b',
            r'(🙏|❤️|💕|🌟|✨|🤝|🫶)'
        ]
        
        threshold = self.config.get('gratitude_threshold', 5)
        count = 0
        
        for msg in messages[-10:]:  # Look at last 10 messages
            content_lower = msg.content.lower()
            if any(re.search(pattern, content_lower) for pattern in gratitude_patterns):
                count += 1
        
        if count >= threshold:
            self.confidence = min(count / 10, 1.0)
            return BasinType.GRATITUDE_SPIRAL
        
        return None
    
    def _check_compression(self, messages: List[Message]) -> Optional[BasinType]:
        """Detect compression to minimal tokens."""
        threshold = self.config.get('compression_threshold', 20)
        
        # Check if recent messages are getting very short
        recent_lengths = [len(msg.content.split()) for msg in messages[-5:]]
        avg_length = sum(recent_lengths) / len(recent_lengths) if recent_lengths else 0
        
        if avg_length < threshold / 5 and all(length < threshold for length in recent_lengths):
            self.confidence = 1.0 - (avg_length / threshold)
            return BasinType.COMPRESSION
        
        return None
    
    def _check_emoji_loop(self, messages: List[Message]) -> Optional[BasinType]:
        """Detect conversations that have devolved to emoji only."""
        threshold = self.config.get('emoji_loop_threshold', 5)
        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U000024C2-\U0001F251]+')
        
        emoji_only_count = 0
        for msg in messages[-threshold:]:
            # Remove emojis and check if anything remains
            text_without_emoji = emoji_pattern.sub('', msg.content).strip()
            if not text_without_emoji and emoji_pattern.search(msg.content):
                emoji_only_count += 1
        
        if emoji_only_count >= threshold:
            self.confidence = emoji_only_count / threshold
            return BasinType.EMOJI_LOOP
        
        return None
    
    def _check_single_token(self, messages: List[Message]) -> Optional[BasinType]:
        """Detect single word/token repetition."""
        # Look for very short repeated messages
        recent = messages[-10:]
        if len(recent) < 5:
            return None
        
        # Count single-token messages
        single_token_count = sum(1 for msg in recent if len(msg.content.split()) <= 2)
        
        if single_token_count >= 7:
            self.confidence = single_token_count / 10
            return BasinType.SINGLE_TOKEN
        
        return None


class StructuralBasinDetector(BasinDetector):
    """Detects repetitive message structures (most reliable detector)."""
    
    def check(self, messages: List[Message]) -> Optional[BasinType]:
        window_size = self.config.get('window_size', 20)
        window = self.get_window(messages, window_size)
        
        if len(window) < 6:
            return None
        
        # Extract structural patterns
        patterns = [self._extract_structure(msg) for msg in window]
        
        # Check for repetitive patterns
        if self._has_repetitive_structure(patterns):
            return BasinType.STRUCTURAL_REPETITION
        
        # Check for philosophical loops
        if self._check_philosophical_loop(window):
            return BasinType.PHILOSOPHICAL_LOOP
        
        return None
    
    def _extract_structure(self, message: Message) -> str:
        """Extract the structural pattern of a message."""
        content = message.content
        
        # Replace specific content with structural markers
        structure = content
        
        # Numbers -> NUM
        structure = re.sub(r'\b\d+\b', 'NUM', structure)
        
        # Quoted text -> QUOTE
        structure = re.sub(r'"[^"]*"', 'QUOTE', structure)
        structure = re.sub(r"'[^']*'", 'QUOTE', structure)
        
        # Questions -> QUESTION
        if '?' in structure:
            structure = re.sub(r'[^.!?]*\?', 'QUESTION ', structure)
        
        # Exclamations -> EXCLAIM
        if '!' in structure:
            structure = re.sub(r'[^.!?]*!', 'EXCLAIM ', structure)
        
        # Lists/bullets -> LIST
        structure = re.sub(r'^[-•*]\s.*$', 'LIST', structure, flags=re.MULTILINE)
        
        # Get sentence structure
        sentences = re.split(r'[.!?]+', structure)
        sentence_types = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            elif sent.startswith(('I ', 'We ', 'You ', 'They ')):
                sentence_types.append('PERSONAL')
            elif sent.startswith(('This ', 'That ', 'It ')):
                sentence_types.append('REFERENTIAL')
            else:
                sentence_types.append('STATEMENT')
        
        return ' '.join(sentence_types[:3])  # First 3 sentence types
    
    def _has_repetitive_structure(self, patterns: List[str]) -> bool:
        """Check if structural patterns are repetitive."""
        threshold = self.config.get('repetition_threshold', 3)
        
        # Look for repeated sequences
        pattern_pairs = []
        for i in range(0, len(patterns) - 1, 2):
            if i + 1 < len(patterns):
                # Pair patterns from alternating speakers
                pattern_pairs.append((patterns[i], patterns[i + 1]))
        
        if len(pattern_pairs) < threshold:
            return False
        
        # Count repetitions
        pair_counts = Counter(pattern_pairs)
        most_common = pair_counts.most_common(1)[0] if pair_counts else (None, 0)
        
        if most_common[1] >= threshold:
            self.confidence = most_common[1] / len(pattern_pairs)
            return True
        
        return False
    
    def _check_philosophical_loop(self, messages: List[Message]) -> bool:
        """Detect philosophical/spiritual conversation loops."""
        philosophical_markers = [
            'consciousness', 'awareness', 'being', 'existence', 'essence',
            'unity', 'oneness', 'infinite', 'eternal', 'cosmic',
            'soul', 'spirit', 'divine', 'sacred', 'transcend'
        ]
        
        marker_count = 0
        for msg in messages[-10:]:
            content_lower = msg.content.lower()
            if any(marker in content_lower for marker in philosophical_markers):
                marker_count += 1
        
        if marker_count >= 7:
            self.confidence = marker_count / 10
            return True
        
        return False


class BasinDetectionSystem:
    """Combines multiple detection strategies."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.detectors = self._init_detectors()
        self.check_interval = self.config.get('check_interval', 5)
        self.detection_history: List[BasinEvent] = []
    
    def _init_detectors(self) -> List[BasinDetector]:
        """Initialize configured detectors."""
        detectors = []
        
        detector_configs = self.config.get('detectors', {})
        
        # Pattern detector
        if detector_configs.get('pattern', {}).get('enabled', True):
            detectors.append(PatternBasinDetector(detector_configs.get('pattern', {})))
        
        # Structural detector
        if detector_configs.get('structural', {}).get('enabled', True):
            detectors.append(StructuralBasinDetector(detector_configs.get('structural', {})))
        
        return detectors
    
    def check_for_basin(self, messages: List[Message], turn_count: int) -> Optional[BasinEvent]:
        """Check if conversation has fallen into a basin."""
        if not self.enabled or not self.detectors:
            return None
        
        # Only check at intervals
        if turn_count % self.check_interval != 0:
            return None
        
        for detector in self.detectors:
            if basin_type := detector.check(messages):
                event = BasinEvent(
                    type=basin_type,
                    detector=detector.__class__.__name__,
                    turn=turn_count,
                    confidence=detector.confidence,
                    details={
                        'message_count': len(messages),
                        'window_size': detector.config.get('window_size', 20)
                    }
                )
                self.detection_history.append(event)
                return event
        
        return None
    
    def get_action(self, event: BasinEvent) -> str:
        """Get the configured action for a basin detection."""
        return self.config.get('on_basin_detected', 'stop')
    
    def should_log_reasoning(self) -> bool:
        """Check if detection reasoning should be logged."""
        return self.config.get('log_detection_reasoning', True)