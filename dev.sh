#!/usr/bin/env bash
# Development convenience commands

case "$1" in
  test)
    uv run pytest "${@:2}"
    ;;
  lint)
    uv run ruff check .
    ;;
  format)
    uv run ruff format .
    ;;
  typecheck)
    uv run mypy pidgin
    ;;
  ci)
    uv run ruff check . && \
    uv run mypy pidgin && \
    uv run pytest && \
    uv run bandit -r pidgin
    ;;
  *)
    echo "Usage: ./dev.sh {test|lint|format|typecheck|ci}"
    exit 1
    ;;
esac