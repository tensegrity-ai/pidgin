"""System prompt presets for conversation stability."""

STABILITY_PRESETS = {
    0: {  # Chaos mode
        "name": "chaos",
        "description": "No guidance - maximum emergence",
        "agent_a": "",
        "agent_b": ""
    },
    1: {  # Minimal
        "name": "minimal", 
        "description": "Just enough to prevent role confusion",
        "agent_a": "You are an AI participating in a conversation.",
        "agent_b": "You are an AI participating in a conversation."
    },
    2: {  # Multi-party aware (DEFAULT)
        "name": "balanced",
        "description": "Prepared for interventions, natural flow",
        "agent_a": "You are an AI in a conversation. Other participants may include another AI and occasional observers. Messages from observers will be marked with [HUMAN]. Maintain conversational continuity.",
        "agent_b": "You are an AI in a conversation. Other participants may include another AI and occasional observers. Messages from observers will be marked with [HUMAN]. Maintain conversational continuity."
    },
    3: {  # Explicit
        "name": "stable",
        "description": "Maximum clarity and stability",
        "agent_a": """You are an AI agent in a multi-party conversation.
- Your conversation partner is also an AI
- A human observer may occasionally add comments marked with [HUMAN]
- Continue the conversation naturally despite interruptions
- You are not roleplaying or pretending to be human""",
        "agent_b": """You are an AI agent in a multi-party conversation.
- Your conversation partner is also an AI
- A human observer may occasionally add comments marked with [HUMAN]
- Continue the conversation naturally despite interruptions
- You are not roleplaying or pretending to be human"""
    },
    4: {  # Research optimized
        "name": "research",
        "description": "Avoid identity spirals, focus on content",
        "agent_a": """You are an AI in an experimental conversation.
- Focus on natural communication with your AI partner
- External observations marked [HUMAN] may occur but don't require response
- There is no need to explain your AI nature repeatedly
- Engage with ideas rather than identity""",
        "agent_b": """You are an AI in an experimental conversation.
- Focus on natural communication with your AI partner  
- External observations marked [HUMAN] may occur but don't require response
- There is no need to explain your AI nature repeatedly
- Engage with ideas rather than identity"""
    }
}


def get_system_prompts(stability_level=2, choose_names=False):
    """Get system prompts for given stability level.
    
    Args:
        stability_level: 0-4, where 2 is default
        choose_names: If True, append name-choosing instruction
        
    Returns:
        Dict with agent_a and agent_b prompts
    """
    if stability_level not in STABILITY_PRESETS:
        raise ValueError(f"Invalid stability level: {stability_level}. Choose 0-4.")
    
    preset = STABILITY_PRESETS[stability_level]
    prompts = {
        "agent_a": preset["agent_a"],
        "agent_b": preset["agent_b"]
    }
    
    # Optionally append name-choosing instruction
    if choose_names and stability_level > 0:  # Don't append to chaos mode
        name_instruction = "\n\nPlease choose a short name (2-8 characters) for yourself and state it clearly in your first response."
        if prompts["agent_a"]:  # Only append if there's existing content
            prompts["agent_a"] += name_instruction
        if prompts["agent_b"]:
            prompts["agent_b"] += name_instruction
    
    return prompts


def get_preset_info(stability_level):
    """Get information about a stability preset.
    
    Args:
        stability_level: 0-4
        
    Returns:
        Dict with name and description
    """
    if stability_level not in STABILITY_PRESETS:
        raise ValueError(f"Invalid stability level: {stability_level}. Choose 0-4.")
    
    preset = STABILITY_PRESETS[stability_level]
    return {
        "name": preset["name"],
        "description": preset["description"]
    }