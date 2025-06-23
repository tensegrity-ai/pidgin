"""Output directory manager for conversations."""

import os
from pathlib import Path
from datetime import datetime
import random
import string
from typing import Tuple


class OutputManager:
    """Manages output directory structure for conversations."""
    
    def __init__(self, base_dir: str = None):
        """Initialize output manager.
        
        Args:
            base_dir: Base directory for all output (default: ./pidgin_output in current working directory)
        """
        if base_dir is None:
            # Try to use PWD environment variable which reflects the shell's working directory
            # This is more reliable than os.getcwd() when the command changes directories
            shell_pwd = os.environ.get('PWD')
            if shell_pwd and os.path.exists(shell_pwd):
                self.base_dir = Path(shell_pwd) / "pidgin_output"
            else:
                # Fallback to current working directory
                self.base_dir = Path(os.getcwd()) / "pidgin_output"
        else:
            self.base_dir = Path(base_dir)
        
    def create_conversation_dir(self, conversation_id: str = None) -> Tuple[str, Path]:
        """Create directory for new conversation.

        Args:
            conversation_id: Optional pre-assigned conversation ID

        Returns:
            Tuple of (conversation_id, directory_path)
        """
        # Create date directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.base_dir / "conversations" / date_str

        # Use provided ID or create unique conversation ID
        if conversation_id is None:
            time_str = datetime.now().strftime("%H%M%S")
            hash_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            conv_id = f"{time_str}_{hash_suffix}"
        else:
            conv_id = conversation_id

        # Create conversation directory
        conv_dir = date_dir / conv_id
        conv_dir.mkdir(parents=True, exist_ok=True)

        return conv_id, conv_dir
    