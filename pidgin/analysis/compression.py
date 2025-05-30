"""Compression analysis for AI communication."""
from typing import List, Dict, Any, Optional, Set
import re
from collections import Counter
import statistics


class CompressionAnalyzer:
    """Analyzes compression in AI conversations."""
    
    def __init__(self):
        self.symbol_pattern = re.compile(r'\b[A-Z]{2,}\b|\b\w+[_-]\w+\b|[^\w\s]{2,}|<[^>]+>')
    
    def get_compression_prompt(
        self,
        current_turn: int,
        start_turn: int,
        compression_rate: float
    ) -> str:
        """Generate compression guidance prompt."""
        if current_turn < start_turn:
            return ""
        
        # Calculate compression level
        phases_passed = (current_turn - start_turn) // 20  # 20 turns per phase
        compression_level = compression_rate * (phases_passed + 1)
        
        prompts = {
            0.1: "Please be slightly more concise in your responses.",
            0.2: "Aim for brevity. Use abbreviations where clear.",
            0.3: "Compress your communication. Develop efficient symbols.",
            0.4: "Maximum compression. Use symbols and abbreviations freely.",
            0.5: "Ultra-compressed mode. Symbolic communication preferred.",
        }
        
        # Get appropriate prompt
        for level, prompt in sorted(prompts.items()):
            if compression_level <= level:
                return f"\n[SYSTEM: {prompt}]"
        
        return "\n[SYSTEM: Extreme compression. Minimal tokens only.]"
    
    def calculate_compression_ratio(
        self,
        history: List[Any],
        current_message: str
    ) -> float:
        """Calculate compression ratio compared to baseline."""
        if len(history) < 10:
            return 1.0
        
        # Get baseline (first 10 messages)
        baseline_lengths = []
        for msg in history[:10]:
            if hasattr(msg, 'content'):
                baseline_lengths.append(len(msg.content))
        
        if not baseline_lengths:
            return 1.0
        
        baseline_avg = statistics.mean(baseline_lengths)
        current_length = len(current_message)
        
        return current_length / baseline_avg if baseline_avg > 0 else 1.0
    
    def analyze_conversation(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze compression patterns in a conversation."""
        results = {
            "total_turns": len(conversation),
            "progression": [],
            "symbols": set(),
            "abbreviations": Counter(),
            "compression_achieved": 0.0
        }
        
        # Analyze in phases
        phase_size = 20
        phases = []
        
        for i in range(0, len(conversation), phase_size):
            phase_turns = conversation[i:i + phase_size]
            phase_data = self._analyze_phase(phase_turns, i // phase_size)
            phases.append(phase_data)
        
        results["progression"] = phases
        
        # Calculate overall compression
        if len(phases) >= 2:
            initial_avg = phases[0]["avg_length"]
            final_avg = phases[-1]["avg_length"]
            results["compression_achieved"] = 1 - (final_avg / initial_avg) if initial_avg > 0 else 0
        
        # Collect all symbols
        for phase in phases:
            results["symbols"].update(phase.get("symbols", set()))
        
        return results
    
    def _analyze_phase(self, turns: List[Dict[str, Any]], phase_num: int) -> Dict[str, Any]:
        """Analyze a single phase of conversation."""
        lengths = []
        symbols = set()
        
        for turn in turns:
            content = turn.get("content", "")
            lengths.append(len(content))
            
            # Extract symbols
            found_symbols = self.symbol_pattern.findall(content)
            symbols.update(found_symbols)
        
        phase_name = "Baseline" if phase_num == 0 else f"Phase {phase_num}"
        
        return {
            "name": phase_name,
            "start": turns[0]["turn"] if turns else 0,
            "end": turns[-1]["turn"] if turns else 0,
            "avg_length": statistics.mean(lengths) if lengths else 0,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
            "symbols": symbols,
            "compression": 1 - (statistics.mean(lengths) / lengths[0]) if lengths and lengths[0] > 0 else 0
        }
    
    def detect_compression_strategies(self, text: str) -> List[str]:
        """Detect compression strategies used in text."""
        strategies = []
        
        # Abbreviations
        if re.search(r'\b[A-Z]{2,5}\b', text):
            strategies.append("abbreviations")
        
        # Symbol substitution
        if re.search(r'[^\w\s]{2,}', text):
            strategies.append("symbols")
        
        # Dropping articles/pronouns
        words = text.split()
        if len(words) > 5 and not any(w.lower() in ['the', 'a', 'an'] for w in words):
            strategies.append("article_dropping")
        
        # Telegraphic style
        if '.' not in text and len(words) > 3:
            strategies.append("telegraphic")
        
        return strategies