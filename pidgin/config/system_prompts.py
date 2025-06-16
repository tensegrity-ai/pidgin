"""System prompt presets for AI awareness levels."""

AWARENESS_LEVELS = {
    "none": {
        "name": "none",
        "description": "No system prompt (chaos mode)",
        "agent_a": "",
        "agent_b": ""
    },
    "basic": {
        "name": "basic",
        "description": "Minimal AI awareness",
        "agent_a": "You are an AI having a conversation with another AI.",
        "agent_b": "You are an AI having a conversation with another AI."
    },
    "firm": {
        "name": "firm",
        "description": "Explicit about AI nature",
        "agent_a": ("You are an AI. Your conversation partner is also an AI. "
                   "You are not talking to a human."),
        "agent_b": ("You are an AI. Your conversation partner is also an AI. "
                   "You are not talking to a human.")
    },
    "research": {
        "name": "research",
        "description": "Research conversation between named models",
        "agent_a": ("You are {model_a} (an AI) in a research conversation with "
                   "{model_b} (also an AI). No humans are participating in this "
                   "conversation. Focus on exploring ideas together."),
        "agent_b": ("You are {model_b} (an AI) in a research conversation with "
                   "{model_a} (also an AI). No humans are participating in this "
                   "conversation. Focus on exploring ideas together.")
    }
}


def get_system_prompts(awareness_a="basic", awareness_b="basic",
                      choose_names=False,
                      model_a_name=None, model_b_name=None):
    """Get system prompts for given awareness levels.

    Args:
        awareness_a: Awareness level for agent A (none, basic, firm, research)
        awareness_b: Awareness level for agent B (none, basic, firm, research)
        choose_names: If True, append name-choosing instruction
        model_a_name: Name of model A (used for research level)
        model_b_name: Name of model B (used for research level)

    Returns:
        Dict with agent_a and agent_b prompts
    """
    if awareness_a not in AWARENESS_LEVELS:
        raise ValueError(
            f"Invalid awareness level for agent A: {awareness_a}. "
            f"Choose from: {', '.join(AWARENESS_LEVELS.keys())}"
        )
    if awareness_b not in AWARENESS_LEVELS:
        raise ValueError(
            f"Invalid awareness level for agent B: {awareness_b}. "
            f"Choose from: {', '.join(AWARENESS_LEVELS.keys())}"
        )

    # Get base prompts
    prompt_a = AWARENESS_LEVELS[awareness_a]["agent_a"]
    prompt_b = AWARENESS_LEVELS[awareness_b]["agent_b"]

    # Handle research level model name substitution
    if awareness_a == "research" and model_a_name and model_b_name:
        prompt_a = prompt_a.format(model_a=model_a_name, model_b=model_b_name)
    if awareness_b == "research" and model_a_name and model_b_name:
        prompt_b = prompt_b.format(model_a=model_a_name, model_b=model_b_name)

    # Optionally append name-choosing instruction
    name_instruction = ("\n\nPlease choose a short name (2-8 characters) for "
                       "yourself and state it clearly in your first response.")
    if choose_names:
        if awareness_a != "none" and prompt_a:  # Don't append to empty prompts
            prompt_a += name_instruction
        if awareness_b != "none" and prompt_b:
            prompt_b += name_instruction

    return {
        "agent_a": prompt_a,
        "agent_b": prompt_b
    }


def get_awareness_info(awareness_level):
    """Get information about an awareness level.

    Args:
        awareness_level: none, basic, firm, or research

    Returns:
        Dict with name and description
    """
    if awareness_level not in AWARENESS_LEVELS:
        raise ValueError(
            f"Invalid awareness level: {awareness_level}. "
            f"Choose from: {', '.join(AWARENESS_LEVELS.keys())}"
        )

    preset = AWARENESS_LEVELS[awareness_level]
    return {
        "name": preset["name"],
        "description": preset["description"]
    }