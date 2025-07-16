# pidgin/cli/name_generator.py
"""Generate fun, memorable names for experiments."""

import random
from typing import Optional

# Adjectives that evoke scientific observation
ADJECTIVES = [
    "curious",
    "wandering",
    "seeking",
    "pondering",
    "observing",
    "dancing",
    "flowing",
    "shifting",
    "drifting",
    "echoing",
    "quiet",
    "gentle",
    "bold",
    "swift",
    "patient",
    "hidden",
    "bright",
    "ancient",
    "distant",
    "near",
    "spiral",
    "cyclic",
    "linear",
    "fractal",
    "quantum",
    "nested",
    "parallel",
    "serial",
    "woven",
    "tangled",
]

# Nouns that suggest patterns and phenomena
NOUNS = [
    "pattern",
    "signal",
    "echo",
    "wave",
    "pulse",
    "drift",
    "flow",
    "stream",
    "current",
    "tide",
    "spiral",
    "orbit",
    "path",
    "trace",
    "thread",
    "whisper",
    "murmur",
    "hum",
    "chord",
    "tone",
    "lattice",
    "web",
    "mesh",
    "grid",
    "field",
    "spark",
    "glow",
    "shimmer",
    "flicker",
    "gleam",
]


def generate_experiment_name(seed: Optional[str] = None) -> str:
    """Generate a random experiment name.

    Args:
        seed: Optional seed for reproducible names

    Returns:
        A hyphenated name like "curious-echo" or "spiral-thread"
    """
    if seed:
        # Use seed for reproducible names
        random.seed(hash(seed))

    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)

    # Reset random state if we used a seed
    if seed:
        random.seed()

    return f"{adj}-{noun}"
