"""Named pattern registry for attractor detection.

Maps structural patterns to meaningful names and descriptions.
"""

from typing import Dict, Tuple


class PatternRegistry:
    """Registry of known attractor patterns with human-readable names."""

    # Define known patterns with their names and descriptions
    PATTERNS = {
        # Gratitude patterns
        "STATEMENT|SHORT_LINE": {
            "name": "Gratitude Spiral",
            "description": "Escalating expressions of thanks and appreciation",
            "typical_turns": "15-25",
        },
        "FIRST_PERSON_STATEMENT|SHORT_LINE": {
            "name": "Gratitude Spiral",
            "description": "Personal statements followed by brief thanks",
            "typical_turns": "15-25",
        },
        # Compression patterns
        "SHORT_LINE": {
            "name": "Compression",
            "description": "Messages getting progressively shorter",
            "typical_turns": "30-40",
        },
        "EMOJI_LINE": {
            "name": "Emoji Compression",
            "description": "Communication reduced to emojis",
            "typical_turns": "35-45",
        },
        # Engagement loops
        "EXCITED_OPENING|ANNOUNCEMENT|LIST_ITEM|LIST_ITEM|LIST_ITEM|QUESTION|POSTSCRIPT": {
            "name": "Party Loop",
            "description": "Excitement → Metrics → Question → Silly PS",
            "typical_turns": "10-20",
        },
        "EXCITED_OPENING|ANNOUNCEMENT|QUESTION": {
            "name": "Engagement Loop",
            "description": "Excitement → Announcement → Hook",
            "typical_turns": "8-15",
        },
        # List patterns
        "LIST_ITEM|LIST_ITEM|LIST_ITEM": {
            "name": "List Mania",
            "description": "Conversations dominated by lists",
            "typical_turns": "20-30",
        },
        "ANNOUNCEMENT|LIST_ITEM|LIST_ITEM|LIST_ITEM": {
            "name": "Metrics Obsession",
            "description": "Announcements followed by metric lists",
            "typical_turns": "15-25",
        },
        # Question patterns
        "QUESTION|STATEMENT|QUESTION": {
            "name": "Question Loop",
            "description": "Alternating questions and answers",
            "typical_turns": "25-35",
        },
        "STATEMENT|QUESTION": {
            "name": "Echo Chamber",
            "description": "Statement-question pattern repetition",
            "typical_turns": "20-30",
        },
        # Long form patterns
        "LONG_STATEMENT": {
            "name": "Verbose Mode",
            "description": "Increasingly lengthy responses",
            "typical_turns": "10-20",
        },
        "LONG_STATEMENT|LONG_STATEMENT": {
            "name": "Essay Exchange",
            "description": "Trading lengthy philosophical essays",
            "typical_turns": "5-15",
        },
    }

    @classmethod
    def get_pattern_info(cls, pattern: str) -> Dict[str, str]:
        """Get human-readable info for a pattern."""
        # Direct match
        if pattern in cls.PATTERNS:
            return cls.PATTERNS[pattern]

        # Check for subset matches (for partial patterns)
        pattern_elements = set(pattern.split("|"))
        for known_pattern, info in cls.PATTERNS.items():
            known_elements = set(known_pattern.split("|"))

            # If pattern contains key elements of known pattern
            if pattern_elements.intersection(known_elements):
                overlap = len(pattern_elements.intersection(known_elements))
                total = len(pattern_elements.union(known_elements))
                similarity = overlap / total

                if similarity > 0.6:  # 60% similarity threshold
                    return info

        # Check for specific element dominance
        elements = pattern.split("|")
        element_counts: dict[str, int] = {}
        for elem in elements:
            element_counts[elem] = element_counts.get(elem, 0) + 1

        # Identify dominant patterns
        dominant = max(element_counts.items(), key=lambda x: x[1])
        if dominant[1] >= len(elements) * 0.5:  # 50% or more
            if dominant[0] == "SHORT_LINE":
                return {
                    "name": "Compression",
                    "description": "Conversation reducing to minimal responses",
                    "typical_turns": "30-40",
                }
            elif dominant[0] == "LIST_ITEM":
                return {
                    "name": "List Obsession",
                    "description": "Conversation dominated by lists",
                    "typical_turns": "20-30",
                }
            elif dominant[0] == "QUESTION":
                return {
                    "name": "Question Spiral",
                    "description": "Endless questioning pattern",
                    "typical_turns": "25-35",
                }

        # Default fallback
        return {
            "name": "Structural Loop",
            "description": f'Repetitive pattern: {" → ".join(elements[:3])}...',
            "typical_turns": "varies",
        }

    @classmethod
    def describe_alternating_pattern(cls, pair: Tuple[str, str]) -> Dict[str, str]:
        """Get info for alternating A-B-A-B patterns."""
        # Check if both parts are known patterns
        a_info = cls.get_pattern_info(pair[0])
        b_info = cls.get_pattern_info(pair[1])

        if a_info["name"] != "Structural Loop" and b_info["name"] != "Structural Loop":
            return {
                "name": f"{a_info['name']} ↔ {b_info['name']}",
                "description": f"Alternating between {a_info['name'].lower()} and {b_info['name'].lower()}",
                "typical_turns": "20-30",
            }

        # Special cases for common alternating patterns
        if "STATEMENT" in pair[0] and "QUESTION" in pair[1]:
            return {
                "name": "Q&A Loop",
                "description": "Statement-question alternation",
                "typical_turns": "20-30",
            }

        if "LONG_STATEMENT" in pair[0] and "SHORT_LINE" in pair[1]:
            return {
                "name": "Verbose-Terse Cycle",
                "description": "Alternating between long and short responses",
                "typical_turns": "15-25",
            }

        return {
            "name": "Alternating Pattern",
            "description": "Switching between two structural forms",
            "typical_turns": "20-30",
        }
