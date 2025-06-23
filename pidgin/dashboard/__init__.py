# pidgin/dashboard/__init__.py
"""Dashboard module for real-time experiment monitoring."""

from .dashboard import ExperimentDashboard, run_dashboard
from .attach import attach_to_experiment, find_running_experiments, attach_dashboard_to_experiment

__all__ = [
    "ExperimentDashboard",
    "run_dashboard",
    "attach_to_experiment",
    "find_running_experiments",
    "attach_dashboard_to_experiment"
]