#!/usr/bin/env python3
"""Test script for progress display functionality."""

import asyncio
from pidgin.display.progress_panel import ProgressPanel
from rich.console import Console
from rich.live import Live

async def test_progress_panel():
    """Test the progress panel display."""
    console = Console()
    
    # Create panel for single conversation
    panel = ProgressPanel(
        experiment_name="test_conversation",
        agent_a="Claude",
        agent_b="GPT-4",
        conv_total=1,
        turn_total=10
    )
    
    with Live(panel.render(), console=console, refresh_per_second=0.5, screen=True) as live:
        # Simulate conversation progress
        for turn in range(1, 11):
            panel.update_turn(turn)
            
            # Simulate convergence updates
            convergence = turn * 0.05
            panel.update_convergence(convergence)
            
            # Simulate token usage
            tokens = 100 + turn * 20
            cost = tokens * 0.00001
            panel.add_tokens(tokens, cost)
            
            # Update display
            live.update(panel.render())
            
            # Wait a bit
            await asyncio.sleep(1)
    
    print("\nSingle conversation test complete!")
    
    # Test multiple conversations
    panel2 = ProgressPanel(
        experiment_name="batch_test",
        agent_a="Claude",
        agent_b="GPT-4", 
        conv_total=5,
        turn_total=10
    )
    
    with Live(panel2.render(), console=console, refresh_per_second=0.5, screen=True) as live:
        for conv in range(1, 6):
            panel2.update_conversation(conv, conv-1, 0)
            
            for turn in range(1, 11):
                panel2.update_turn(turn)
                convergence = turn * 0.05 + conv * 0.02
                panel2.update_convergence(convergence)
                
                tokens = 100 + turn * 20
                cost = tokens * 0.00001
                panel2.add_tokens(tokens, cost)
                
                live.update(panel2.render())
                await asyncio.sleep(0.5)
            
            # Complete conversation
            panel2.complete_conversation(1200, convergence)
    
    print("\nMultiple conversation test complete!")

if __name__ == "__main__":
    asyncio.run(test_progress_panel())