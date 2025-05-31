import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from .types import Conversation


class TranscriptManager:
    def __init__(self, save_path: Optional[str] = None):
        self.save_path = save_path
        
    async def save(self, conversation: Conversation):
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
        
        # Save JSON (machine-readable)
        json_path = base_dir / "conversation.json"
        with open(json_path, 'w') as f:
            json.dump(conversation.dict(), f, indent=2, default=str)
        
        # Save Markdown (human-readable)
        md_path = base_dir / "conversation.md"
        with open(md_path, 'w') as f:
            f.write(self._to_markdown(conversation))
    
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
            if msg.agent_id == "system":
                lines.append(f"**System**: {msg.content}\n")
            elif msg.agent_id == "agent_a":
                lines.append(f"**Agent A**: {msg.content}\n")
            else:
                lines.append(f"**Agent B**: {msg.content}\n")
        
        return "\n".join(lines)