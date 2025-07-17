#!/usr/bin/env python3
"""
Convergence Weight Analysis Script

Replay existing conversations with different convergence weights to test 
how they would behave under the new configuration.

Usage:
    python scripts/analyze_convergence_weights.py --conversation-path ./pidgin_output/conversations/20241215_143022_powerpoint_conversation/
    python scripts/analyze_convergence_weights.py --experiment-path ./pidgin_output/experiments/my_experiment/
    python scripts/analyze_convergence_weights.py --jsonl ./path/to/events.jsonl
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt
import pandas as pd

# Add pidgin to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from pidgin.analysis.convergence import ConvergenceCalculator
from pidgin.constants.metrics import DEFAULT_CONVERGENCE_WEIGHTS, ConvergenceProfiles
from pidgin.io.event_deserializer import EventDeserializer
from pidgin.core.events import MessageCompleteEvent


@dataclass
class ConvergenceAnalysis:
    """Results of analyzing a conversation with different weights."""
    conversation_id: str
    total_turns: int
    
    # Results for each weight profile
    profiles: Dict[str, Dict[str, Any]]  # profile_name -> {scores, halt_turn, etc}


class ConvergenceWeightAnalyzer:
    """Analyze how different convergence weights affect conversation outcomes."""
    
    def __init__(self):
        self.deserializer = EventDeserializer()
        
        # Test profiles (including proposed new ones)
        self.weight_profiles = {
            "current_balanced": {
                "content": 0.4, "structure": 0.15, "sentences": 0.2,
                "length": 0.15, "punctuation": 0.1
            },
            "current_structural": {
                "content": 0.25, "structure": 0.35, "sentences": 0.2,
                "length": 0.1, "punctuation": 0.1
            },
            "proposed_balanced": {
                "content": 0.30, "structure": 0.35, "sentences": 0.25,
                "length": 0.05, "punctuation": 0.05
            },
            "proposed_structural": {
                "content": 0.20, "structure": 0.50, "sentences": 0.25,
                "length": 0.03, "punctuation": 0.02
            },
            "proposed_behavioral": {
                "content": 0.15, "structure": 0.55, "sentences": 0.25,
                "length": 0.03, "punctuation": 0.02
            }
        }
    
    def analyze_conversation(self, jsonl_path: Path, thresholds: List[float] = None) -> ConvergenceAnalysis:
        """Analyze a single conversation with different weight profiles."""
        if thresholds is None:
            thresholds = [0.70, 0.75, 0.80, 0.85]
        
        # Load and parse events
        messages = self._extract_messages_from_jsonl(jsonl_path)
        if not messages:
            raise ValueError(f"No messages found in {jsonl_path}")
        
        conversation_id = self._extract_conversation_id(jsonl_path)
        analysis = ConvergenceAnalysis(
            conversation_id=conversation_id,
            total_turns=len(messages) // 2,  # Assuming alternating agents
            profiles={}
        )
        
        # Test each weight profile
        for profile_name, weights in self.weight_profiles.items():
            profile_results = self._analyze_with_weights(messages, weights, thresholds)
            analysis.profiles[profile_name] = profile_results
        
        return analysis
    
    def _extract_messages_from_jsonl(self, jsonl_path: Path) -> List[Any]:
        """Extract message objects from JSONL event stream."""
        messages = []
        
        with open(jsonl_path, 'r') as f:
            for line in f:
                if line.strip():
                    event_data = json.loads(line)
                    event = self.deserializer.deserialize(event_data)
                    
                    if isinstance(event, MessageCompleteEvent):
                        # Create a message-like object for convergence calculation
                        message = type('Message', (), {
                            'agent_id': event.agent_id,
                            'content': event.content,
                            'turn_number': event.turn_number
                        })()
                        messages.append(message)
        
        return messages
    
    def _extract_conversation_id(self, jsonl_path: Path) -> str:
        """Extract conversation ID from the file path or contents."""
        # Try to get from path first
        if 'conversations' in str(jsonl_path):
            parts = str(jsonl_path).split('/')
            for i, part in enumerate(parts):
                if part == 'conversations' and i + 1 < len(parts):
                    return parts[i + 1]
        
        # Fallback to reading from file
        with open(jsonl_path, 'r') as f:
            first_line = f.readline()
            if first_line.strip():
                event_data = json.loads(first_line)
                return event_data.get('conversation_id', str(jsonl_path.stem))
        
        return str(jsonl_path.stem)
    
    def _analyze_with_weights(self, messages: List[Any], weights: Dict[str, float], 
                            thresholds: List[float]) -> Dict[str, Any]:
        """Analyze conversation with specific weights."""
        calc = ConvergenceCalculator(weights=weights)
        
        scores = []
        halt_turns = {}  # threshold -> turn where it would halt
        
        # Replay the conversation turn by turn
        for i in range(2, len(messages) + 1, 2):  # Every 2 messages is a complete turn
            current_messages = messages[:i]
            score = calc.calculate(current_messages)
            scores.append(score)
            
            # Check if any threshold would trigger a halt
            turn_number = i // 2
            for threshold in thresholds:
                if threshold not in halt_turns and score >= threshold:
                    halt_turns[threshold] = turn_number
        
        return {
            "scores": scores,
            "final_score": scores[-1] if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "halt_turns": halt_turns,
            "trend": self._calculate_trend(scores[-3:] if len(scores) >= 3 else scores)
        }
    
    def _calculate_trend(self, recent_scores: List[float]) -> str:
        """Calculate if scores are increasing, decreasing, or stable."""
        if len(recent_scores) < 2:
            return "insufficient_data"
        
        if len(recent_scores) == 2:
            return "increasing" if recent_scores[1] > recent_scores[0] else "decreasing"
        
        # For 3+ scores, check if generally trending up/down
        diffs = [recent_scores[i] - recent_scores[i-1] for i in range(1, len(recent_scores))]
        avg_diff = sum(diffs) / len(diffs)
        
        if avg_diff > 0.05:
            return "increasing"
        elif avg_diff < -0.05:
            return "decreasing"
        else:
            return "stable"
    
    def compare_profiles(self, analysis: ConvergenceAnalysis, threshold: float = 0.75) -> pd.DataFrame:
        """Compare how different profiles would have handled the conversation."""
        data = []
        
        for profile_name, results in analysis.profiles.items():
            halt_turn = results["halt_turns"].get(threshold, "never")
            row = {
                "Profile": profile_name,
                "Final Score": results["final_score"],
                "Max Score": results["max_score"],
                f"Halt Turn (≥{threshold})": halt_turn,
                "Trend": results["trend"],
                "Total Turns": analysis.total_turns
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        return df.sort_values("Final Score", ascending=False)
    
    def plot_convergence_comparison(self, analysis: ConvergenceAnalysis, threshold: float = 0.75):
        """Plot convergence scores over time for different profiles."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: All profiles over time
        for profile_name, results in analysis.profiles.items():
            scores = results["scores"]
            turns = list(range(1, len(scores) + 1))
            ax1.plot(turns, scores, marker='o', label=profile_name, linewidth=2)
        
        ax1.axhline(y=threshold, color='red', linestyle='--', alpha=0.7, 
                   label=f'Threshold ({threshold})')
        ax1.set_xlabel('Turn Number')
        ax1.set_ylabel('Convergence Score')
        ax1.set_title(f'Convergence Scores Over Time - {analysis.conversation_id}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Halt comparison
        halt_data = []
        for profile_name, results in analysis.profiles.items():
            halt_turn = results["halt_turns"].get(threshold, analysis.total_turns + 1)
            halt_data.append((profile_name, halt_turn))
        
        halt_data.sort(key=lambda x: x[1])
        profiles, halt_turns = zip(*halt_data)
        
        colors = ['red' if h <= analysis.total_turns else 'green' for h in halt_turns]
        bars = ax2.bar(profiles, halt_turns, color=colors, alpha=0.7)
        
        ax2.axhline(y=analysis.total_turns, color='blue', linestyle='--', alpha=0.7,
                   label=f'Actual End ({analysis.total_turns})')
        ax2.set_ylabel('Turn Number')
        ax2.set_title(f'When Each Profile Would Halt (Threshold: {threshold})')
        ax2.legend()
        
        # Rotate x-axis labels
        plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        
        # Add text annotations
        for bar, halt_turn in zip(bars, halt_turns):
            if halt_turn <= analysis.total_turns:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{halt_turn}', ha='center', va='bottom', fontweight='bold')
            else:
                ax2.text(bar.get_x() + bar.get_width()/2, analysis.total_turns + 0.5,
                        'Never', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.show()
    
    def analyze_batch(self, conversation_paths: List[Path], threshold: float = 0.75) -> pd.DataFrame:
        """Analyze multiple conversations and summarize results."""
        results = []
        
        for path in conversation_paths:
            try:
                jsonl_path = self._find_events_jsonl(path)
                if not jsonl_path:
                    print(f"No events.jsonl found in {path}")
                    continue
                
                analysis = self.analyze_conversation(jsonl_path, [threshold])
                
                for profile_name, profile_results in analysis.profiles.items():
                    halt_turn = profile_results["halt_turns"].get(threshold, "never")
                    would_halt = halt_turn != "never" and halt_turn <= analysis.total_turns
                    
                    results.append({
                        "conversation_id": analysis.conversation_id,
                        "profile": profile_name,
                        "total_turns": analysis.total_turns,
                        "final_score": profile_results["final_score"],
                        "max_score": profile_results["max_score"],
                        "halt_turn": halt_turn,
                        "would_halt": would_halt,
                        "trend": profile_results["trend"]
                    })
                    
            except Exception as e:
                print(f"Error analyzing {path}: {e}")
        
        return pd.DataFrame(results)
    
    def _find_events_jsonl(self, path: Path) -> Path:
        """Find events.jsonl file in a conversation directory."""
        if path.is_file() and path.suffix == '.jsonl':
            return path
        
        # Look for events.jsonl in the directory
        events_file = path / 'events.jsonl'
        if events_file.exists():
            return events_file
        
        # Look in subdirectories
        for jsonl_file in path.glob('**/events.jsonl'):
            return jsonl_file
        
        return None


def main():
    """Command line interface for convergence analysis."""
    parser = argparse.ArgumentParser(description='Analyze convergence weights on existing conversations')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--conversation-path', type=Path, 
                      help='Path to single conversation directory')
    group.add_argument('--experiment-path', type=Path,
                      help='Path to experiment directory (analyzes all conversations)')
    group.add_argument('--jsonl', type=Path,
                      help='Path to specific events.jsonl file')
    
    parser.add_argument('--threshold', type=float, default=0.75,
                       help='Convergence threshold to test (default: 0.75)')
    parser.add_argument('--plot', action='store_true',
                       help='Show plots of convergence over time')
    parser.add_argument('--output', type=Path,
                       help='Save results to CSV file')
    
    args = parser.parse_args()
    
    analyzer = ConvergenceWeightAnalyzer()
    
    if args.jsonl:
        # Single file analysis
        analysis = analyzer.analyze_conversation(args.jsonl, [args.threshold])
        
        print(f"\nAnalysis for {analysis.conversation_id}")
        print(f"Total turns: {analysis.total_turns}")
        print("\nComparison of weight profiles:")
        
        comparison = analyzer.compare_profiles(analysis, args.threshold)
        print(comparison.to_string(index=False))
        
        if args.plot:
            analyzer.plot_convergence_comparison(analysis, args.threshold)
    
    elif args.conversation_path:
        # Single conversation analysis
        jsonl_path = analyzer._find_events_jsonl(args.conversation_path)
        if not jsonl_path:
            print(f"No events.jsonl found in {args.conversation_path}")
            return
        
        analysis = analyzer.analyze_conversation(jsonl_path, [args.threshold])
        
        print(f"\nAnalysis for {analysis.conversation_id}")
        print(f"Total turns: {analysis.total_turns}")
        print("\nComparison of weight profiles:")
        
        comparison = analyzer.compare_profiles(analysis, args.threshold)
        print(comparison.to_string(index=False))
        
        if args.plot:
            analyzer.plot_convergence_comparison(analysis, args.threshold)
    
    elif args.experiment_path:
        # Batch analysis of experiment
        conversation_dirs = []
        
        # Find all conversation directories
        for conv_dir in args.experiment_path.glob('conversations/*/'):
            if conv_dir.is_dir():
                conversation_dirs.append(conv_dir)
        
        if not conversation_dirs:
            print(f"No conversation directories found in {args.experiment_path}")
            return
        
        print(f"Analyzing {len(conversation_dirs)} conversations...")
        results_df = analyzer.analyze_batch(conversation_dirs, args.threshold)
        
        if results_df.empty:
            print("No valid conversations analyzed")
            return
        
        # Summary statistics
        print(f"\nBatch Analysis Summary (threshold: {args.threshold})")
        print("=" * 50)
        
        summary = results_df.groupby('profile').agg({
            'would_halt': ['count', 'sum'],
            'final_score': ['mean', 'std'],
            'halt_turn': lambda x: (x != 'never').sum()
        }).round(3)
        
        print(summary)
        
        if args.output:
            results_df.to_csv(args.output, index=False)
            print(f"\nDetailed results saved to {args.output}")


if __name__ == '__main__':
    main()