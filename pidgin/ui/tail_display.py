"""Tail display for showing formatted event stream in console.

This module re-exports the TailDisplay class from the refactored
tail package for backwards compatibility.
"""

from .tail import TailDisplay

__all__ = ["TailDisplay"]