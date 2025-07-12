"""Simplified dimensional prompt generation system for Pidgin.

This module implements a simplified dimensional approach focusing on three core dimensions:
CONTEXT (how they relate), TOPIC (what they discuss), and MODE (how they think).
"""

import random
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import yaml

from ..io.logger import get_logger

logger = get_logger("dimensional_prompts")


@dataclass
class Dimension:
    """Represents a single dimension with its possible values."""

    name: str
    description: str
    required: bool
    values: Dict[str, str]  # key -> template or description


class DimensionalPromptGenerator:
    """Generate initial prompts from dimensional specifications.

    Examples:
        peers:philosophy → "Hello! I'm excited to explore the fundamental nature of reality together."
        debate:language:analytical → "I strongly disagree about how we communicate and create meaning. Here's why: Let's systematically analyze what we discover."
    """

    # Core dimension definitions (expanded to 6x6x6)
    RELATIONSHIP_DIMENSION = Dimension(
        name="relationship",
        description="The conversational relationship",
        required=True,
        values={
            "peers": "Hello! I'm excited to explore {topic} together.",
            "mentor": "Let's explore {topic} with one of you guiding and teaching the other.",
            "debate": "I'd love to see you debate different perspectives on {topic}.",
            "interview": "I'm curious to see one of you interview the other about {topic}.",
            "collaboration": "Please work together to explore {topic}.",
            "socratic": "Let's explore {topic} through thoughtful questioning and dialogue.",
        },
    )

    TOPIC_DIMENSION = Dimension(
        name="topic",
        description="The subject matter",
        required=True,
        values={
            "philosophy": "the fundamental nature of reality",
            "language": "how we communicate and create meaning",
            "science": "how the universe works",
            "creativity": "the creative process and imagination",
            "ethics": "moral reasoning and ethical questions",
            "meta": "our own conversation and thinking"
        },
    )

    MODIFIER_DIMENSION = Dimension(
        name="modifier",
        description="The conversational style or approach",
        required=False,
        values={
            "analytical": "Let's see you systematically analyze what you discover.",
            "intuitive": "I have a feeling that fascinating patterns will emerge as you explore.",
            "exploratory": "I wonder what happens if you follow your curiosity wherever it leads.",
            "critical": "Please examine this topic with careful scrutiny and questioning.",
            "playful": "Have fun with this exploration and see where creativity takes you!",
            "supportive": "I encourage you to build on each other's ideas constructively.",
        },
    )


    def __init__(self):
        """Initialize the generator with the three core dimensions."""
        self.dimensions = {
            "relationship": self.RELATIONSHIP_DIMENSION,
            "topic": self.TOPIC_DIMENSION,
            "modifier": self.MODIFIER_DIMENSION,
        }

    def generate(
        self,
        dimension_spec: str,
    ) -> str:
        """Generate a prompt from dimensional specification.

        Args:
            dimension_spec: Colon-separated dimensions (e.g., "peers:philosophy:analytical")

        Returns:
            Generated prompt string
        """
        # Parse dimensions
        parsed = self._parse_dimensions(dimension_spec)

        # Validate required dimensions
        self._validate_dimensions(parsed)

        # Get topic value
        topic = parsed.get("topic", "philosophy")
        topic_value = self.TOPIC_DIMENSION.values[topic]

        # Build the prompt
        prompt = self._build_prompt(parsed, topic_value)

        return prompt

    def _parse_dimensions(self, dimension_spec: str) -> Dict[str, str]:
        """Parse a dimension specification into a dictionary."""
        parts = dimension_spec.split(":")

        # Map positional arguments based on common patterns
        parsed = {}

        # First is always relationship if provided
        if len(parts) >= 1:
            parsed["relationship"] = parts[0]

        # Second is topic if provided
        if len(parts) >= 2:
            parsed["topic"] = parts[1]

        # Remaining are optional dimensions
        for i, part in enumerate(parts[2:]):
            # Try to identify which dimension this is
            for dim_name, dim in self.dimensions.items():
                if dim_name in ["relationship", "topic"]:
                    continue
                if part in dim.values:
                    parsed[dim_name] = part
                    break

        return parsed

    def _validate_dimensions(self, parsed: Dict[str, str]):
        """Validate that all required dimensions are present and valid."""
        # Check required dimensions (relationship and topic)
        if "relationship" not in parsed:
            raise ValueError(
                f"Missing required dimension 'relationship'. "
                f"Available values: {', '.join(self.RELATIONSHIP_DIMENSION.values.keys())}"
            )
        
        if "topic" not in parsed:
            raise ValueError(
                f"Missing required dimension 'topic'. "
                f"Available values: {', '.join(self.TOPIC_DIMENSION.values.keys())}"
            )

        # Validate all provided values
        for dim_name, value in parsed.items():
            if dim_name in self.dimensions:
                if value not in self.dimensions[dim_name].values:
                    raise ValueError(
                        f"Unknown {dim_name} '{value}'. "
                        f"Available: {', '.join(self.dimensions[dim_name].values.keys())}"
                    )


    def _build_prompt(self, parsed: Dict[str, str], topic_value: str) -> str:
        """Build the prompt from dimensions using simplified composition logic."""
        # 1. Get relationship template (required)
        relationship = parsed.get("relationship", "peers")
        prompt = self.RELATIONSHIP_DIMENSION.values[relationship].format(topic=topic_value)
        
        # 2. Add modifier if specified (optional)
        if "modifier" in parsed:
            modifier_sentence = self.MODIFIER_DIMENSION.values[parsed["modifier"]]
            prompt = f"{prompt} {modifier_sentence}"
        
        # 3. Ensure proper ending
        if not prompt.rstrip().endswith((".", "!", "?", ":")):
            prompt = prompt.rstrip() + "."
        
        return prompt



    def get_all_dimensions(self) -> Dict[str, Dimension]:
        """Get all available dimensions."""
        return self.dimensions

    def get_dimension_values(self, dimension_name: str) -> List[str]:
        """Get all values for a specific dimension."""
        if dimension_name in self.dimensions:
            return list(self.dimensions[dimension_name].values.keys())
        return []

    def describe_dimension(self, dimension_name: str) -> str:
        """Get a description of a dimension and its values."""
        if dimension_name not in self.dimensions:
            return f"Unknown dimension: {dimension_name}"

        dim = self.dimensions[dimension_name]
        lines = [
            f"{dim.name.upper()}: {dim.description}",
            f"Required: {'Yes' if dim.required else 'No'}",
            "",
            "Values:",
        ]

        for value, desc in dim.values.items():
            if desc == "[SPECIAL]":
                lines.append(f"  • {value}: Requires additional content")
            else:
                lines.append(
                    f"  • {value}: {desc[:60]}{'...' if len(desc) > 60 else ''}"
                )

        return "\n".join(lines)
