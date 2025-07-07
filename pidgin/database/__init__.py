"""Database package for Pidgin using DuckDB."""

from .event_store import EventStore

__all__ = ["EventStore"]