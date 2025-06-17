import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from ..core.types import Conversation


class TranscriptManager:
    def __init__(self, output_dir: Path):
        """Initialize transcript manager.
        
        Args:
            output_dir: Directory where transcripts should be saved
        """
        self.output_dir = output_dir
        self._transcript_path: Optional[Path] = None

    async def save(
        self, conversation: Conversation, metrics: Optional[Dict[str, Any]] = None
    ):
        """Save conversation transcript to the output directory.
        
        Args:
            conversation: The conversation to save
            metrics: Optional metrics to include in the JSON output
        """
        # Use the provided output directory
        base_dir = self.output_dir
        
        # Directory should already exist from OutputManager
        if not base_dir.exists():
            base_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON (machine-readable) with enhanced metrics
        json_path = base_dir / "conversation.json"
        with open(json_path, "w") as f:
            conversation_data = conversation.dict()

            # Add enhanced metrics to the JSON structure
            if metrics:
                conversation_data["metrics"] = metrics

            json.dump(conversation_data, f, indent=2, default=str)

        # Save Markdown (human-readable)
        md_path = base_dir / "conversation.md"
        with open(md_path, "w") as f:
            f.write(self._to_markdown(conversation))

        # Store the path for later use
        self._transcript_path = md_path

    def _to_markdown(self, conversation: Conversation) -> str:
        lines = [
            "# Pidgin Conversation",
            "",
            f"**Date**: {conversation.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Agents**: {conversation.agents[0].model} ↔ {conversation.agents[1].model}",
            f"**Turns**: {len(conversation.messages) // 2}",
            f"**Initial Prompt**: {conversation.initial_prompt}",
            "",
            "---",
            "",
        ]

        # Add messages
        for msg in conversation.messages:
            # Use display_source if available, otherwise fallback to agent_id mapping
            if hasattr(msg, "display_source"):
                source_name = msg.display_source
            else:
                # Fallback for backward compatibility
                if msg.agent_id == "system":
                    source_name = "System"
                elif msg.agent_id == "human":
                    source_name = "Human"
                elif msg.agent_id == "mediator":
                    source_name = "Mediator"
                elif msg.agent_id == "agent_a":
                    source_name = "Agent A"
                elif msg.agent_id == "agent_b":
                    source_name = "Agent B"
                else:
                    source_name = msg.agent_id.title()

            lines.append(f"**{source_name}**: {msg.content}\n")

        return "\n".join(lines)

    def get_transcript_path(self) -> Path:
        """Get the path where the transcript will be saved."""
        if self._transcript_path:
            return self._transcript_path
        
        # Return the markdown path in the output directory
        return self.output_dir / "conversation.md"
