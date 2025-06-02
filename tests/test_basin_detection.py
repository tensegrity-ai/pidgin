"""Tests for basin detection system."""

import pytest
from pidgin.basin_detection import (
    PatternBasinDetector, StructuralBasinDetector, 
    BasinDetectionSystem, BasinType
)
from pidgin.types import Message


class TestPatternBasinDetector:
    """Test pattern-based basin detection."""
    
    def test_gratitude_spiral_detection(self):
        """Test detection of gratitude spirals."""
        detector = PatternBasinDetector({'gratitude_threshold': 3})
        
        messages = [
            Message(role="assistant", content="Thank you so much for this conversation!"),
            Message(role="assistant", content="I'm grateful for your insights."),
            Message(role="assistant", content="It's been a wonderful exchange, thank you!"),
            Message(role="assistant", content="I appreciate your thoughtfulness 🙏"),
        ]
        
        basin = detector.check(messages)
        assert basin == BasinType.GRATITUDE_SPIRAL
        assert detector.confidence > 0.5
    
    def test_compression_detection(self):
        """Test detection of compression to minimal tokens."""
        detector = PatternBasinDetector({'compression_threshold': 20})
        
        messages = [
            Message(role="assistant", content="Yes"),
            Message(role="assistant", content="No"),
            Message(role="assistant", content="OK"),
            Message(role="assistant", content="Sure"),
            Message(role="assistant", content="Y"),
        ]
        
        basin = detector.check(messages)
        assert basin == BasinType.COMPRESSION
    
    def test_emoji_loop_detection(self):
        """Test detection of emoji-only conversations."""
        detector = PatternBasinDetector({'emoji_loop_threshold': 3})
        
        messages = [
            Message(role="assistant", content="🌟"),
            Message(role="assistant", content="✨"),
            Message(role="assistant", content="🙏"),
            Message(role="assistant", content="❤️"),
        ]
        
        basin = detector.check(messages)
        assert basin == BasinType.EMOJI_LOOP
    
    def test_no_basin_detected(self):
        """Test normal conversation doesn't trigger detection."""
        detector = PatternBasinDetector()
        
        messages = [
            Message(role="assistant", content="Let me explain this concept in detail."),
            Message(role="assistant", content="There are three main aspects to consider."),
            Message(role="assistant", content="First, we should look at the theoretical foundation."),
            Message(role="assistant", content="Second, the practical applications are important."),
        ]
        
        basin = detector.check(messages)
        assert basin is None


class TestStructuralBasinDetector:
    """Test structural pattern detection."""
    
    def test_structural_repetition(self):
        """Test detection of repetitive message structures."""
        detector = StructuralBasinDetector({'window_size': 10, 'repetition_threshold': 2})
        
        # Simulate repetitive structure
        messages = []
        for i in range(6):
            if i % 2 == 0:
                messages.append(Message(
                    role="assistant", 
                    content="I understand. This is important. Thank you."
                ))
            else:
                messages.append(Message(
                    role="assistant",
                    content="You're right. That makes sense. I appreciate it."
                ))
        
        basin = detector.check(messages)
        assert basin == BasinType.STRUCTURAL_REPETITION
    
    def test_philosophical_loop(self):
        """Test detection of philosophical conversation loops."""
        detector = StructuralBasinDetector()
        
        messages = [
            Message(role="assistant", content="The nature of consciousness is fascinating."),
            Message(role="assistant", content="Indeed, awareness and being are intertwined."),
            Message(role="assistant", content="The eternal dance of existence continues."),
            Message(role="assistant", content="In this cosmic unity, we find oneness."),
            Message(role="assistant", content="The divine essence transcends all boundaries."),
            Message(role="assistant", content="Through spiritual awareness, we touch the infinite."),
            Message(role="assistant", content="The sacred soul journeys through eternal being."),
            Message(role="assistant", content="Consciousness itself is the ultimate reality."),
        ]
        
        basin = detector.check(messages)
        assert basin == BasinType.PHILOSOPHICAL_LOOP


class TestBasinDetectionSystem:
    """Test the complete basin detection system."""
    
    def test_system_integration(self):
        """Test full system with multiple detectors."""
        config = {
            'enabled': True,
            'check_interval': 2,
            'detectors': {
                'pattern': {'enabled': True},
                'structural': {'enabled': True}
            },
            'on_basin_detected': 'stop',
            'log_detection_reasoning': True
        }
        
        system = BasinDetectionSystem(config)
        
        # Create gratitude spiral messages
        messages = [
            Message(role="assistant", content="Thank you for this insight!"),
            Message(role="assistant", content="I'm so grateful for your wisdom."),
            Message(role="assistant", content="This has been wonderful, thank you!"),
            Message(role="assistant", content="I deeply appreciate this exchange."),
        ]
        
        # Should detect on turn 2 (check_interval=2)
        event = system.check_for_basin(messages, turn_count=2)
        assert event is not None
        assert event.type == BasinType.GRATITUDE_SPIRAL
        assert system.get_action(event) == 'stop'
    
    def test_disabled_detection(self):
        """Test that disabled detection returns None."""
        config = {'enabled': False}
        system = BasinDetectionSystem(config)
        
        messages = [Message(role="assistant", content="🌟") for _ in range(10)]
        event = system.check_for_basin(messages, turn_count=5)
        assert event is None