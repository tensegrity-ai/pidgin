# pidgin/cli/constants.py
"""CLI constants and styling."""

# Nord color scheme
NORD_YELLOW = "#ebcb8b"  # nord13
NORD_RED = "#bf616a"     # nord11
NORD_GREEN = "#a3be8c"   # nord14
NORD_BLUE = "#88c0d0"    # nord8
NORD_PURPLE = "#b48ead"  # nord15
NORD_ORANGE = "#d08770"  # nord12
NORD_CYAN = "#8fbcbb"    # nord7
NORD_DARK = "#4c566a"    # nord3
NORD_LIGHT = "#eceff4"   # nord6

# ASCII Banner
BANNER = r"""[bold #88c0d0]
    ____  ________  __________   __
   / __ \/  _/ __ \/ ____/  _/ | / /
  / /_/ // // / / / / __ / //  |/ / 
 / ____// // /_/ / /_/ // // /|  /  
/_/   /___/_____/\____/___/_/ |_/   
[/bold #88c0d0]
[#4c566a]AI Conversation Laboratory[/#4c566a]
"""

# Model display configurations
MODEL_EMOJIS = {
    # OpenAI
    "gpt-4": "🧠",
    "gpt-4-turbo": "🚀",
    "gpt-4o": "⚡",
    "gpt-3.5-turbo": "💬",
    "o1-preview": "🔬",
    "o1-mini": "🔬",
    
    # Anthropic
    "claude-3-opus": "🎭",
    "claude-3-sonnet": "🎵",
    "claude-3-haiku": "📝",
    "claude-3.5-sonnet": "🎼",
    "claude-3.5-haiku": "✍️",
    
    # Google
    "gemini-1.5-pro": "✨",
    "gemini-1.5-flash": "⚡",
    "gemini-2.0-flash": "💫",
    "gemini-exp": "🧪",
    
    # xAI
    "grok-2": "🎯",
    "grok-2-vision": "👁️",
    
    # Local/Ollama
    "llama3.1": "🦙",
    "qwen2.5": "🐼",
    "deepseek": "🔍",
    "test": "🧪",
}

# Provider colors
PROVIDER_COLORS = {
    "openai": NORD_GREEN,
    "anthropic": NORD_ORANGE,
    "google": NORD_BLUE,
    "xai": NORD_PURPLE,
    "local": NORD_YELLOW,
}

# Default experiment parameters
DEFAULT_TURNS = 20
DEFAULT_TEMPERATURE = 0.7
DEFAULT_PARALLEL = 3

# Output messages
CONVERGENCE_MSGS = {
    "high": "🔄 High convergence detected",
    "pause": "⏸️  Paused for convergence review",
    "stop": "⏹️  Stopped due to convergence",
}

# File patterns
TRANSCRIPT_PATTERN = "transcript.md"
EVENTS_PATTERN = "events.jsonl"
STATE_PATTERN = "state.json"
