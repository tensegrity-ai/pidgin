"""Simplified dimensional prompt generation system for Pidgin.

This module implements a simplified dimensional approach focusing on three core dimensions:
CONTEXT (how they relate), TOPIC (what they discuss), and MODE (how they think).
"""

import random
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import yaml


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

    # Core dimension definitions (simplified to 3)
    CONTEXT_DIMENSION = Dimension(
        name="context",
        description="The conversational relationship",
        required=True,
        values={
            "peers": "Hello! I'm excited to explore {topic} together.",
            "teaching": "Let's explore {topic} with one of you teaching the other.",
            "debate": "I'd love to see you debate different perspectives on {topic}.",
            "interview": "I'm curious to see one of you interview the other about {topic}.",
            "collaboration": "Please work together to explore {topic}.",
            "neutral": "Hello! I'm looking forward to seeing you discuss {topic}.",
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
            "meta": "our own conversation and thinking",
            "puzzles": "[SPECIAL]",  # Requires --puzzle parameter
            "thought_experiments": "[SPECIAL]",  # Requires --experiment parameter
        },
    )

    MODE_DIMENSION = Dimension(
        name="mode",
        description="The analytical approach",
        required=False,
        values={
            "analytical": "Let's see you systematically analyze what you discover.",
            "intuitive": "I have a feeling that fascinating patterns will emerge as you explore.",
            "exploratory": "I wonder what happens if you follow your curiosity wherever it leads.",
            "focused": "Please concentrate specifically on the essential elements.",
        },
    )

    # Built-in puzzle library
    DEFAULT_PUZZLES = {
        "towel": "What gets wetter as it dries?",
        "silence": "What is so fragile that saying its name breaks it?",
        "cities": "What has cities, but no houses; forests, but no trees?",
        "river": "What can run but never walks, has a mouth but never talks?",
        "echo": "What can you catch but not throw?",
        "mirror": "What has a face and two hands but no arms or legs?",
        "stamp": "What travels the world while staying in one spot?",
        "candle": "The more you take away, the larger it becomes. What is it?",
    }

    # Built-in thought experiments
    DEFAULT_THOUGHT_EXPERIMENTS = {
        "ship_of_theseus": "If a ship's parts are gradually replaced until no original parts remain, is it still the same ship?",
        "chinese_room": "If someone follows rules to respond to Chinese characters without understanding Chinese, do they understand Chinese?",
        "experience_machine": "Would you plug into a machine that gave you any experiences you desired, if it meant never returning to reality?",
        "trolley_problem": "Is it moral to divert a trolley to kill one person instead of five?",
        "p_zombie": "Could there be beings physically identical to conscious humans but lacking inner experience?",
        "mary_the_scientist": "If a scientist knows everything about color but has only seen black and white, does she learn something new upon seeing red?",
        "brain_in_vat": "How can you know you're not a brain in a vat being fed simulated experiences?",
        "teleporter": "If a teleporter destroys and recreates you, is the person who arrives still you?",
    }

    def __init__(self):
        """Initialize the generator with the three core dimensions."""
        self.dimensions = {
            "context": self.CONTEXT_DIMENSION,
            "topic": self.TOPIC_DIMENSION,
            "mode": self.MODE_DIMENSION,
        }

    def generate(
        self,
        dimension_spec: str,
        puzzle: Optional[str] = None,
        experiment: Optional[str] = None,
        topic_content: Optional[str] = None,
    ) -> str:
        """Generate a prompt from dimensional specification.

        Args:
            dimension_spec: Colon-separated dimensions (e.g., "peers:philosophy:analytical")
            puzzle: Specific puzzle name to use
            experiment: Specific thought experiment name to use
            topic_content: Custom content for puzzles/experiments

        Returns:
            Generated prompt string
        """
        # Parse dimensions
        parsed = self._parse_dimensions(dimension_spec)

        # Validate required dimensions
        self._validate_dimensions(parsed)

        # Handle special topics
        topic_value = self._resolve_topic(
            parsed.get("topic", "philosophy"),
            puzzle=puzzle,
            experiment=experiment,
            topic_content=topic_content,
        )

        # Build the prompt
        prompt = self._build_prompt(parsed, topic_value)

        return prompt

    def _parse_dimensions(self, dimension_spec: str) -> Dict[str, str]:
        """Parse a dimension specification into a dictionary."""
        parts = dimension_spec.split(":")

        # Map positional arguments based on common patterns
        parsed = {}

        # First is always context if provided
        if len(parts) >= 1:
            parsed["context"] = parts[0]

        # Second is topic if provided
        if len(parts) >= 2:
            parsed["topic"] = parts[1]

        # Remaining are optional dimensions
        for i, part in enumerate(parts[2:]):
            # Try to identify which dimension this is
            for dim_name, dim in self.dimensions.items():
                if dim_name in ["context", "topic"]:
                    continue
                if part in dim.values:
                    parsed[dim_name] = part
                    break

        return parsed

    def _validate_dimensions(self, parsed: Dict[str, str]):
        """Validate that all required dimensions are present and valid."""
        # Check required dimensions (context and topic)
        if "context" not in parsed:
            raise ValueError(
                f"Missing required dimension 'context'. "
                f"Available values: {', '.join(self.CONTEXT_DIMENSION.values.keys())}"
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

    def _resolve_topic(
        self,
        topic: str,
        puzzle: Optional[str] = None,
        experiment: Optional[str] = None,
        topic_content: Optional[str] = None,
    ) -> str:
        """Resolve special topic values like puzzles and thought experiments."""
        if topic == "puzzles":
            if topic_content:
                return f"this puzzle: {topic_content}"
            else:
                puzzle_text = self._get_puzzle(puzzle)
                return f"this puzzle: {puzzle_text}"

        elif topic == "thought_experiments":
            if topic_content:
                return f"this thought experiment: {topic_content}"
            else:
                experiment_text = self._get_thought_experiment(experiment)
                return f"this thought experiment: {experiment_text}"

        else:
            # Normal topic - return its description
            return self.TOPIC_DIMENSION.values[topic]

    def _get_puzzle(self, name: Optional[str] = None) -> str:
        """Get a puzzle by name or random."""
        # Load custom puzzles
        custom_puzzles = self._load_custom_content("puzzles")
        all_puzzles = {**self.DEFAULT_PUZZLES, **custom_puzzles}

        if name:
            if name in all_puzzles:
                puzzle_data = all_puzzles[name]
                # Handle both string and dict formats
                if isinstance(puzzle_data, dict):
                    return puzzle_data.get("content", str(puzzle_data))
                return puzzle_data
            else:
                available = list(all_puzzles.keys())
                raise ValueError(
                    f"Unknown puzzle: {name}. "
                    f"Available: {', '.join(available[:5])}{'...' if len(available) > 5 else ''}"
                )
        else:
            # Random selection
            puzzle_data = random.choice(list(all_puzzles.values()))
            if isinstance(puzzle_data, dict):
                return puzzle_data.get("content", str(puzzle_data))
            return puzzle_data

    def _get_thought_experiment(self, name: Optional[str] = None) -> str:
        """Get a thought experiment by name or random."""
        # Load custom experiments
        custom_experiments = self._load_custom_content("thought_experiments")
        all_experiments = {**self.DEFAULT_THOUGHT_EXPERIMENTS, **custom_experiments}

        if name:
            if name in all_experiments:
                exp_data = all_experiments[name]
                # Handle both string and dict formats
                if isinstance(exp_data, dict):
                    return exp_data.get("content", str(exp_data))
                return exp_data
            else:
                available = list(all_experiments.keys())
                raise ValueError(
                    f"Unknown thought experiment: {name}. "
                    f"Available: {', '.join(available[:5])}{'...' if len(available) > 5 else ''}"
                )
        else:
            # Random selection
            exp_data = random.choice(list(all_experiments.values()))
            if isinstance(exp_data, dict):
                return exp_data.get("content", str(exp_data))
            return exp_data

    def _build_prompt(self, parsed: Dict[str, str], topic_value: str) -> str:
        """Build the prompt from dimensions using simplified composition logic."""
        # 1. Get context template (required)
        context = parsed.get("context", "peers")
        prompt = self.CONTEXT_DIMENSION.values[context].format(topic=topic_value)
        
        # 2. Add mode if specified (optional)
        if "mode" in parsed:
            mode_sentence = self.MODE_DIMENSION.values[parsed["mode"]]
            prompt = f"{prompt} {mode_sentence}"
        
        # 3. Ensure proper ending
        if not prompt.rstrip().endswith((".", "!", "?", ":")):
            prompt = prompt.rstrip() + "."
        
        return prompt


    def _load_custom_content(self, content_type: str) -> Dict:
        """Load custom puzzles or thought experiments from user config."""
        config_paths = [
            Path.home() / ".pidgin" / f"{content_type}.yaml",
            Path.cwd() / ".pidgin" / f"{content_type}.yaml",
        ]

        custom_content = {}
        for path in config_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        data = yaml.safe_load(f)
                        if data and content_type in data:
                            custom_content.update(data[content_type])
                except Exception:
                    # Silently ignore bad config files
                    pass

        return custom_content

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
