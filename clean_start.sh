#!/bin/bash
# Clean start script to reset experiments

echo "Cleaning up old experiments..."

# Kill any running daemons
if [ -d "pidgin_output/experiments/active" ]; then
    for pidfile in pidgin_output/experiments/active/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            echo "Killing daemon PID $pid"
            kill -9 "$pid" 2>/dev/null
        fi
    done
fi

# Remove old data
rm -rf pidgin_output/

echo "Clean start complete. You can now run new experiments."