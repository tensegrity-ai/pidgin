"""Pidgin: AI Communication Protocol Research CLI"""

__version__ = "0.1.0"
__author__ = "Pidgin Research Team"

from pidgin.core.experiment import Experiment
from pidgin.core.conversation import ConversationManager
from pidgin.llm.base import LLM
from pidgin.config.archetypes import Archetype

__all__ = ["Experiment", "ConversationManager", "LLM", "Archetype"]