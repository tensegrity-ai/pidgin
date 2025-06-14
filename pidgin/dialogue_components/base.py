"""Base component interface for dialogue components."""

from abc import ABC, abstractmethod


class Component(ABC):
    """Base class for dialogue components.

    Provides a common interface for lifecycle management.
    """

    @abstractmethod
    def reset(self):
        """Reset component state for new conversation.

        This method should clear any internal state and prepare
        the component for a fresh conversation.
        """
        pass
