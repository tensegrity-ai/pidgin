#!/usr/bin/env python3
"""
Demo script for the Pidgin Live Dashboard.

This demonstrates how to use the dashboard to monitor experiments in real-time.

Usage:
    python examples/dashboard_demo.py [path_to_experiments.db]
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pidgin.dashboard import ExperimentDashboard


def main():
    """Run the dashboard demo."""
    # Default database path
    db_path = Path("./pidgin_output/experiments/experiments.db")
    
    # Check for command line argument
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    
    # Check if database exists
    if not db_path.exists():
        print(f"◆ Database not found: {db_path}")
        print("◇ Start an experiment first:")
        print("  pidgin experiment start -a claude -b gpt -r 10")
        sys.exit(1)
    
    print("◆ Pidgin Live Dashboard Demo")
    print(f"◇ Database: {db_path}")
    print("○ Controls:")
    print("  [q] Quit")
    print("  [e] Export data")
    print("  [p] Pause/unpause")
    print("  [r] Force refresh")
    print("\n◆ Starting dashboard...\n")
    
    # Create and run dashboard
    dashboard = ExperimentDashboard(db_path, refresh_rate=0.25)
    
    try:
        asyncio.run(dashboard.run())
    except KeyboardInterrupt:
        print("\n◆ Dashboard interrupted")
    except Exception as e:
        print(f"\n◆ Error: {e}")
        raise


if __name__ == "__main__":
    main()