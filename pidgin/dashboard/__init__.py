# pidgin/dashboard/__init__.py
"""Dashboard module for real-time experiment monitoring."""

from .dashboard import Dashboard
from .attach import attach_dashboard_to_experiment

__all__ = ["Dashboard", "attach_dashboard_to_experiment"]