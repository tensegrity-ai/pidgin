#!/usr/bin/env python3
"""Test script to verify JSONL-first approach is working."""

import sys
import time
from pathlib import Path

# Add pidgin to path
sys.path.insert(0, str(Path(__file__).parent))

from pidgin.experiments.state_builder import StateBuilder
from pidgin.io.paths import get_experiments_dir


def test_state_builder():
    """Test building state from JSONL files."""
    print("Testing StateBuilder...")
    
    exp_base = get_experiments_dir()
    print(f"Experiments directory: {exp_base}")
    
    # Find an experiment directory
    exp_dirs = list(exp_base.glob("exp_*"))
    if not exp_dirs:
        print("No experiments found. Run an experiment first.")
        return
    
    # Test with first experiment
    exp_dir = exp_dirs[0]
    print(f"\nTesting with experiment: {exp_dir.name}")
    
    # Build state
    state = StateBuilder.from_experiment_dir(exp_dir)
    if not state:
        print("Failed to build state")
        return
    
    # Display state info
    print(f"\nExperiment State:")
    print(f"  ID: {state.experiment_id}")
    print(f"  Name: {state.name}")
    print(f"  Status: {state.status}")
    print(f"  Progress: {state.progress[0]}/{state.progress[1]}")
    print(f"  Active conversations: {state.active_conversations}")
    
    # Show conversation details
    if state.conversations:
        print(f"\nConversations ({len(state.conversations)}):")
        for conv_id, conv in list(state.conversations.items())[:3]:  # Show first 3
            print(f"  {conv_id[:16]}...")
            print(f"    Status: {conv.status}")
            print(f"    Turn: {conv.current_turn}/{conv.max_turns}")
            print(f"    Models: {conv.agent_a_model} ↔ {conv.agent_b_model}")
            if conv.last_convergence:
                print(f"    Last convergence: {conv.last_convergence:.3f}")
    
    print("\n✓ StateBuilder test passed!")


def test_live_monitoring():
    """Test monitoring a running experiment."""
    print("\nTesting live monitoring...")
    
    exp_base = get_experiments_dir()
    
    # Find active experiments
    active_states = StateBuilder.from_active_experiments(exp_base)
    
    if not active_states:
        print("No active experiments found.")
        return
    
    print(f"Found {len(active_states)} active experiment(s)")
    
    # Monitor first active experiment
    state = active_states[0]
    print(f"\nMonitoring {state.name} for 10 seconds...")
    
    for i in range(5):
        # Rebuild state
        state = StateBuilder.from_experiment_dir(exp_base / state.experiment_id)
        
        completed, total = state.progress
        print(f"\r  Progress: {completed}/{total} ({completed/total*100:.0f}%)", end="", flush=True)
        
        time.sleep(2)
    
    print("\n✓ Live monitoring test passed!")


if __name__ == "__main__":
    print("=== Testing JSONL-First Approach ===\n")
    
    test_state_builder()
    test_live_monitoring()
    
    print("\n=== All tests completed ===")