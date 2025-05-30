"""General metrics analysis for experiments."""
from typing import List, Dict, Any, Optional
import statistics
from datetime import datetime


class MetricsAnalyzer:
    """Analyzes general metrics for experiments."""
    
    def analyze_experiment(self, experiment) -> Dict[str, Any]:
        """Analyze basic metrics for an experiment."""
        metrics = {
            "total_turns": experiment.metrics.total_turns,
            "total_tokens": experiment.metrics.total_tokens,
            "duration": experiment.metrics.duration,
        }
        
        # Calculate derived metrics
        if experiment.conversation_history:
            metrics.update(self._analyze_conversation_metrics(experiment.conversation_history))
        
        if metrics["total_turns"] > 0:
            metrics["avg_tokens_per_turn"] = metrics["total_tokens"] / metrics["total_turns"]
        else:
            metrics["avg_tokens_per_turn"] = 0
        
        if metrics.get("duration") and metrics["total_turns"] > 0:
            metrics["avg_turn_time"] = metrics["duration"] / metrics["total_turns"]
        
        # Model-specific metrics
        metrics["model_contributions"] = self._analyze_model_contributions(experiment)
        
        return metrics
    
    def _analyze_conversation_metrics(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation-specific metrics."""
        turn_lengths = []
        response_times = []
        speakers = set()
        
        prev_timestamp = None
        for turn in conversation:
            content = turn.get("content", "")
            turn_lengths.append(len(content))
            
            speaker = turn.get("speaker", "Unknown")
            speakers.add(speaker)
            
            # Calculate response times
            if "timestamp" in turn and prev_timestamp:
                try:
                    current = datetime.fromisoformat(turn["timestamp"])
                    prev = datetime.fromisoformat(prev_timestamp)
                    response_time = (current - prev).total_seconds()
                    response_times.append(response_time)
                except:
                    pass
                
            prev_timestamp = turn.get("timestamp")
        
        metrics = {
            "avg_turn_length": statistics.mean(turn_lengths) if turn_lengths else 0,
            "min_turn_length": min(turn_lengths) if turn_lengths else 0,
            "max_turn_length": max(turn_lengths) if turn_lengths else 0,
            "turn_length_std": statistics.stdev(turn_lengths) if len(turn_lengths) > 1 else 0,
            "num_speakers": len(speakers),
        }
        
        if response_times:
            metrics.update({
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
            })
        
        return metrics
    
    def _analyze_model_contributions(self, experiment) -> Dict[str, Any]:
        """Analyze contributions by each model."""
        contributions = {}
        
        for turn in experiment.conversation_history:
            speaker = turn.get("speaker", "Unknown")
            if speaker not in contributions:
                contributions[speaker] = {
                    "turns": 0,
                    "total_length": 0,
                    "total_tokens": 0,
                }
            
            contributions[speaker]["turns"] += 1
            contributions[speaker]["total_length"] += len(turn.get("content", ""))
            
            if "usage" in turn:
                contributions[speaker]["total_tokens"] += turn["usage"].get("total_tokens", 0)
        
        # Calculate averages
        for speaker, data in contributions.items():
            if data["turns"] > 0:
                data["avg_length"] = data["total_length"] / data["turns"]
                data["avg_tokens"] = data["total_tokens"] / data["turns"] if data["total_tokens"] > 0 else 0
        
        return contributions
    
    def calculate_engagement_score(self, conversation: List[Dict[str, Any]]) -> float:
        """Calculate an engagement score based on conversation dynamics."""
        if len(conversation) < 2:
            return 0.0
        
        # Factors for engagement
        scores = []
        
        # Response length consistency
        lengths = [len(turn.get("content", "")) for turn in conversation]
        if len(lengths) > 1:
            cv = statistics.stdev(lengths) / statistics.mean(lengths) if statistics.mean(lengths) > 0 else 1
            length_score = 1 / (1 + cv)  # Lower variation = higher score
            scores.append(length_score)
        
        # Turn-taking balance
        speakers = [turn.get("speaker", "") for turn in conversation]
        speaker_counts = {}
        for speaker in speakers:
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        
        if len(speaker_counts) > 1:
            counts = list(speaker_counts.values())
            balance = min(counts) / max(counts) if max(counts) > 0 else 0
            scores.append(balance)
        
        # Conversation momentum (no long gaps)
        response_times = []
        prev_timestamp = None
        for turn in conversation:
            if "timestamp" in turn and prev_timestamp:
                try:
                    current = datetime.fromisoformat(turn["timestamp"])
                    prev = datetime.fromisoformat(prev_timestamp)
                    response_time = (current - prev).total_seconds()
                    response_times.append(response_time)
                except:
                    pass
            prev_timestamp = turn.get("timestamp")
        
        if response_times:
            # Penalize long response times
            avg_response = statistics.mean(response_times)
            momentum_score = 1 / (1 + avg_response / 60)  # Normalize by minutes
            scores.append(momentum_score)
        
        return statistics.mean(scores) if scores else 0.0
    
    def find_conversation_phases(self, conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify distinct phases in the conversation."""
        if len(conversation) < 10:
            return [{"phase": 1, "start": 0, "end": len(conversation)-1, "type": "single"}]
        
        phases = []
        phase_size = 20
        
        for i in range(0, len(conversation), phase_size):
            phase_turns = conversation[i:i + phase_size]
            
            # Characterize phase
            avg_length = statistics.mean([len(t.get("content", "")) for t in phase_turns])
            
            # Simple classification based on length
            if i == 0:
                phase_type = "opening"
            elif i + phase_size >= len(conversation):
                phase_type = "closing"
            elif avg_length < 50:
                phase_type = "compressed"
            elif avg_length > 200:
                phase_type = "expansive"
            else:
                phase_type = "normal"
            
            phases.append({
                "phase": len(phases) + 1,
                "start": i,
                "end": min(i + phase_size - 1, len(conversation) - 1),
                "type": phase_type,
                "avg_length": avg_length
            })
        
        return phases