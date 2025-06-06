import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from .types import Conversation


class TranscriptManager:
    def __init__(self, save_path: Optional[str] = None):
        self.save_path = save_path
        self._transcript_path: Optional[Path] = None
        
    async def save(self, conversation: Conversation, metrics: Optional[Dict[str, Any]] = None):
        # Determine save location
        if self.save_path:
            base_dir = Path(self.save_path)
        else:
            # Default: ~/.pidgin_data/transcripts/YYYY-MM-DD/conversation_id/
            date_str = datetime.now().strftime("%Y-%m-%d")
            home_dir = Path.home()
            base_dir = home_dir / ".pidgin_data" / "transcripts" / date_str / conversation.id
        
        # Create directory
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON (machine-readable) with enhanced metrics
        json_path = base_dir / "conversation.json"
        with open(json_path, 'w') as f:
            conversation_data = conversation.dict()
            
            # Add enhanced metrics to the JSON structure
            if metrics:
                conversation_data['metrics'] = metrics
            
            json.dump(conversation_data, f, indent=2, default=str)
        
        # Save Markdown (human-readable)
        md_path = base_dir / "conversation.md"
        with open(md_path, 'w') as f:
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
            ""
        ]
        
        # Add messages
        for msg in conversation.messages:
            # Use display_source if available, otherwise fallback to agent_id mapping
            if hasattr(msg, 'display_source'):
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
        
        # Calculate the path without saving
        if self.save_path:
            base_dir = Path(self.save_path)
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
            home_dir = Path.home()
            # Use a temporary conversation ID
            conv_id = datetime.now().strftime("%H%M%S")
            base_dir = home_dir / ".pidgin_data" / "transcripts" / date_str / f"conversation_{conv_id}"
        
        return base_dir / "conversation.md"