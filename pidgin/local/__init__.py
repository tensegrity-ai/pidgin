"""Local model components for Pidgin."""

from .test_model import TestModel

__all__ = ["TestModel"]

# Note: Local models (except test) now use Ollama as the backend.
# See pidgin/providers/ollama.py for the implementation.