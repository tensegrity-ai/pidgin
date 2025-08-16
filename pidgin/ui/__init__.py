"""User interface and display components for pidgin."""

from .chat_display import ChatDisplay
from .display_filter import DisplayFilter
from .tail import TailDisplay

__all__ = [
    "ChatDisplay",
    "DisplayFilter",
    "TailDisplay",
]
