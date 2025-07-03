"""Prompt building utilities."""

from typing import Optional, List
from .dimensional_prompts import DimensionalPromptGenerator


def build_initial_prompt(custom_prompt: Optional[str] = None, 
                        dimensions: Optional[List[str]] = None) -> str:
    """Build the initial prompt for a conversation.
    
    Args:
        custom_prompt: Custom prompt text (overrides dimensions)
        dimensions: List of dimension specifications (e.g., ["peers:philosophy:analytical"])
        
    Returns:
        The initial prompt string
    """
    if custom_prompt:
        return custom_prompt
    
    if not dimensions:
        return "I'm looking forward to your conversation."
    
    # Use the DimensionalPromptGenerator
    generator = DimensionalPromptGenerator()
    
    # If multiple dimensions provided, use the first one
    dimensions_str = dimensions[0] if dimensions else ""
    return generator.generate(dimensions_str)