"""Tests for structural attractor detection."""

import pytest
from pidgin.attractors import StructuralAnalyzer, StructuralPatternDetector


class TestStructuralAnalyzer:
    """Test structural analysis of messages."""
    
    def test_extract_structure_basic(self):
        """Test basic structural extraction."""
        analyzer = StructuralAnalyzer()
        
        content = """Hey hey!
I've just completed the analysis.
- Metric 1: Improved!
- Metric 2: Also better!
- Metric 3: Amazing!
What do you think about this?
P.S. The coffee machine is still broken 😅"""
        
        structure = analyzer.extract_structure(content)
        
        # Should identify the party attractor structure
        assert len(structure) == 7
        assert structure[0].type == 'EXCITED_OPENING'
        assert structure[1].type == 'ANNOUNCEMENT'
        assert structure[2].type == 'LIST_ITEM'
        assert structure[3].type == 'LIST_ITEM'
        assert structure[4].type == 'LIST_ITEM'
        assert structure[5].type == 'QUESTION'
        assert structure[6].type == 'POSTSCRIPT'
    
    def test_structural_element_features(self):
        """Test that structural elements capture relevant features."""
        analyzer = StructuralAnalyzer()
        
        elements = analyzer.extract_structure("Hello! How are you?")
        
        assert elements[0].features['punctuation'] == '?'
        assert elements[0].features['length'] == 19
        assert 'has_emoji' in elements[0].features


class TestStructuralPatternDetector:
    """Test pattern detection in conversations."""
    
    def test_detect_party_attractor(self):
        """Test detection of the classic party attractor pattern."""
        detector = StructuralPatternDetector(window_size=6, threshold=2)
        
        # Simulate party attractor messages
        messages = [
            # First instance
            """Hey there!
We've analyzed the metrics.
- Engagement: Up 15%!
- Satisfaction: Higher!
- Efficiency: Better!
Ready for the next round?
P.S. Did you see the dancing robots? 🤖""",
            
            # Response
            "Great work! Let me check those numbers.",
            
            # Second instance (same structure)
            """Hey hey!
Just finished the review.
- Performance: Increased!
- Quality: Improved!
- Speed: Faster!
Should we continue this?
P.S. The robots are still dancing! 💃""",
            
            # Response
            "Excellent progress! Keep going.",
            
            # Third instance (triggers detection)
            """Hey friend!
I've completed the update.
- Results: Amazing!
- Trends: Positive!
- Outlook: Bright!
What's our next move?
P.S. Now the robots formed a conga line! 🚂"""
        ]
        
        result = detector.detect_attractor(messages)
        
        assert result is not None
        assert result['type'] == 'structural_attractor'
        assert result['confidence'] >= 0.3  # At least 2/6 messages match
        assert 'Party attractor' in result['description']
    
    def test_alternating_pattern_detection(self):
        """Test detection of A-B-A-B conversation patterns."""
        detector = StructuralPatternDetector(window_size=8, threshold=3)
        
        # Simulate alternating pattern
        messages = []
        for i in range(4):
            # A's structure
            messages.append("I understand. This is important. Thank you.")
            # B's structure  
            messages.append("You're right. That makes sense. I appreciate it.")
        
        result = detector.detect_attractor(messages)
        
        assert result is not None
        assert result['type'] == 'alternating_attractor'
        assert result['confidence'] >= 0.5
    
    def test_no_pattern_in_varied_conversation(self):
        """Test that varied conversations don't trigger false positives."""
        detector = StructuralPatternDetector(window_size=10, threshold=3)
        
        # Varied conversation with different structures
        messages = [
            "Hello! How can I help you today?",
            "I need assistance with my project. It's about machine learning.",
            "That sounds interesting. What specific aspect are you working on?",
            "I'm trying to implement a neural network for image classification.",
            "Here are some suggestions:\n1. Start with a simple CNN\n2. Use transfer learning\n3. Ensure proper data augmentation",
            "Thanks! Could you explain transfer learning in more detail?",
            "Transfer learning involves using a pre-trained model as a starting point.",
            "I see. What models would you recommend?",
            "ResNet50 and EfficientNet are good choices for beginners.",
            "Perfect, I'll start with those. Thank you for your help!"
        ]
        
        result = detector.detect_attractor(messages)
        
        assert result is None  # Should not detect any pattern