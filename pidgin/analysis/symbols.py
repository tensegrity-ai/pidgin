"""Symbol detection and analysis for emergent communication."""
import re
from typing import List, Dict, Any, Set, Tuple
from collections import Counter, defaultdict
import string


class SymbolDetector:
    """Detects and analyzes emergent symbols in AI communication."""
    
    def __init__(self):
        # Patterns for potential symbols
        self.patterns = {
            'abbreviation': re.compile(r'\b[A-Z]{2,8}\b'),
            'compound': re.compile(r'\b\w+[_-]\w+\b'),
            'bracketed': re.compile(r'<[^>]+>|\[[^\]]+\]|\{[^}]+\}'),
            'special': re.compile(r'[^\w\s]{2,}'),
            'coded': re.compile(r'\b[A-Z]\d+\b|\b\d+[A-Z]+\b'),
            'emoji_like': re.compile(r':[a-z_]+:'),
        }
        
        # Common words to exclude
        self.common_abbreviations = {
            'AI', 'ML', 'API', 'URL', 'ID', 'OK', 'FAQ', 'CEO', 'USA', 'UK'
        }
    
    def detect_symbols(self, text: str) -> List[str]:
        """Detect potential symbols in text."""
        symbols = []
        
        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                # Filter out common abbreviations
                if pattern_name == 'abbreviation' and match in self.common_abbreviations:
                    continue
                symbols.append(match)
        
        return symbols
    
    def analyze_conversation(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze symbol emergence in a conversation."""
        symbol_timeline = defaultdict(list)  # symbol -> list of turn numbers
        symbol_users = defaultdict(set)      # symbol -> set of users
        symbol_contexts = defaultdict(list)  # symbol -> list of contexts
        
        for turn in conversation:
            turn_num = turn.get("turn", 0)
            speaker = turn.get("speaker", "unknown")
            content = turn.get("content", "")
            
            # Detect symbols
            symbols = self.detect_symbols(content)
            
            for symbol in symbols:
                symbol_timeline[symbol].append(turn_num)
                symbol_users[symbol].add(speaker)
                
                # Extract context (words around symbol)
                context = self._extract_context(content, symbol)
                symbol_contexts[symbol].append(context)
        
        # Analyze patterns
        results = {
            "total_symbols": len(symbol_timeline),
            "symbols": {},
            "emergence_pattern": self._classify_emergence_pattern(symbol_timeline),
            "cross_adoption": self._analyze_cross_adoption(symbol_users),
        }
        
        # Detailed symbol analysis
        for symbol, turns in symbol_timeline.items():
            stability = self._calculate_stability(turns, len(conversation))
            
            results["symbols"][symbol] = {
                "first_seen": min(turns),
                "last_seen": max(turns),
                "frequency": len(turns),
                "users": list(symbol_users[symbol]),
                "stability": stability,
                "contexts": symbol_contexts[symbol][:3],  # First 3 contexts
            }
        
        return results
    
    def _extract_context(self, text: str, symbol: str, window: int = 5) -> str:
        """Extract context around a symbol."""
        words = text.split()
        symbol_indices = [i for i, w in enumerate(words) if symbol in w]
        
        if not symbol_indices:
            return ""
        
        idx = symbol_indices[0]
        start = max(0, idx - window)
        end = min(len(words), idx + window + 1)
        
        context_words = words[start:end]
        # Highlight the symbol
        context_words[idx - start] = f"**{context_words[idx - start]}**"
        
        return " ".join(context_words)
    
    def _calculate_stability(self, turns: List[int], total_turns: int) -> float:
        """Calculate symbol stability (how consistently it's used)."""
        if len(turns) < 2:
            return 0.0
        
        # Look at gaps between uses
        gaps = [turns[i+1] - turns[i] for i in range(len(turns)-1)]
        if not gaps:
            return 0.0
        
        avg_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        
        # Stability is higher when gaps are smaller and more consistent
        consistency = 1.0 - (max_gap - avg_gap) / max_gap if max_gap > 0 else 1.0
        frequency = len(turns) / total_turns
        
        return consistency * frequency
    
    def _classify_emergence_pattern(self, symbol_timeline: Dict[str, List[int]]) -> str:
        """Classify the pattern of symbol emergence."""
        if not symbol_timeline:
            return "none"
        
        # Get first appearance of each symbol
        first_appearances = [min(turns) for turns in symbol_timeline.values()]
        
        if len(first_appearances) < 3:
            return "sparse"
        
        # Check if symbols appear in bursts
        sorted_appearances = sorted(first_appearances)
        gaps = [sorted_appearances[i+1] - sorted_appearances[i] 
                for i in range(len(sorted_appearances)-1)]
        
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        
        if avg_gap < 5:
            return "burst"
        elif avg_gap < 15:
            return "gradual"
        else:
            return "sporadic"
    
    def _analyze_cross_adoption(self, symbol_users: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Analyze how symbols are adopted across participants."""
        single_user_symbols = sum(1 for users in symbol_users.values() if len(users) == 1)
        multi_user_symbols = sum(1 for users in symbol_users.values() if len(users) > 1)
        
        return {
            "single_user": single_user_symbols,
            "multi_user": multi_user_symbols,
            "adoption_rate": multi_user_symbols / len(symbol_users) if symbol_users else 0
        }
    
    def find_symbol_evolution(self, conversation: List[Dict[str, Any]]) -> List[Tuple[str, str, int]]:
        """Find symbols that evolved from other symbols."""
        evolutions = []
        symbol_timeline = defaultdict(list)
        
        # Build timeline
        for turn in conversation:
            symbols = self.detect_symbols(turn.get("content", ""))
            for symbol in symbols:
                symbol_timeline[symbol].append(turn.get("turn", 0))
        
        # Look for potential evolutions
        symbols = list(symbol_timeline.keys())
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                # Check if sym2 might be evolution of sym1
                if self._is_potential_evolution(sym1, sym2):
                    # Check temporal relationship
                    if min(symbol_timeline[sym2]) > max(symbol_timeline[sym1]):
                        turn = min(symbol_timeline[sym2])
                        evolutions.append((sym1, sym2, turn))
        
        return evolutions
    
    def _is_potential_evolution(self, sym1: str, sym2: str) -> bool:
        """Check if sym2 might be an evolution of sym1."""
        # Similar length
        if abs(len(sym1) - len(sym2)) > 3:
            return False
        
        # Share characters
        common = set(sym1) & set(sym2)
        if len(common) < len(sym1) * 0.5:
            return False
        
        # Could be abbreviated or extended
        if sym1 in sym2 or sym2 in sym1:
            return True
        
        # Edit distance would be better here
        return False