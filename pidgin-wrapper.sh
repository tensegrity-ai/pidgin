#!/usr/bin/env bash
# Wrapper script for pidgin that respects current working directory

# Find the pidgin project directory (where this script lives)
PIDGIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Save current directory
CURRENT_DIR="$(pwd)"

# Change to pidgin directory, activate environment, then go back and run
cd "$PIDGIN_DIR" && poetry run bash -c "cd '$CURRENT_DIR' && python -m pidgin.cli $*"