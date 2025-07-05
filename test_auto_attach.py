#!/usr/bin/env python3
"""Test script to verify auto-attach functionality."""

import subprocess
import time
import signal
import sys

def test_auto_attach():
    """Test that experiment start automatically attaches."""
    print("Testing auto-attach feature...")
    
    # Start an experiment (should auto-attach)
    cmd = ["pidgin", "experiment", "start", "-a", "local:test", "-b", "local:test", 
           "-r", "3", "-t", "5", "--name", "test_attach"]
    
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)
    
    # Let it run for a few seconds to see the attach UI
    time.sleep(5)
    
    # Send Ctrl+C to detach
    print("\nSending Ctrl+C to detach...")
    proc.send_signal(signal.SIGINT)
    
    # Wait for it to handle the signal
    time.sleep(2)
    
    # Check if process exited cleanly
    if proc.poll() is None:
        print("Process still running after detach - terminating...")
        proc.terminate()
    else:
        print("Process exited with code:", proc.poll())
    
    print("\nNow testing --detach flag...")
    
    # Start with --detach (should not attach)
    cmd2 = ["pidgin", "experiment", "start", "-a", "local:test", "-b", "local:test", 
            "-r", "3", "-t", "5", "--name", "test_detach", "--detach"]
    
    print(f"Running: {' '.join(cmd2)}")
    result = subprocess.run(cmd2, capture_output=True, text=True)
    
    print("Output:")
    print(result.stdout)
    
    if result.returncode == 0:
        print("✓ --detach flag worked correctly")
    else:
        print("✗ --detach flag failed:", result.stderr)

if __name__ == "__main__":
    test_auto_attach()