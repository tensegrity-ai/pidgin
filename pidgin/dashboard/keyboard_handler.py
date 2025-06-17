"""Keyboard input handler for the dashboard."""

import asyncio
import sys
import termios
import tty
from typing import Optional, Callable, Dict
import select


class KeyboardHandler:
    """Non-blocking keyboard input handler for the dashboard."""
    
    def __init__(self):
        self.original_settings = None
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        
    def register_handler(self, key: str, handler: Callable):
        """Register a handler for a specific key."""
        self.handlers[key] = handler
        
    def start(self):
        """Start keyboard handling."""
        if sys.stdin.isatty():
            self.original_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            self.running = True
            
    def stop(self):
        """Stop keyboard handling and restore terminal settings."""
        if self.original_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
        self.running = False
        
    def check_key(self) -> Optional[str]:
        """Check if a key has been pressed (non-blocking)."""
        if not self.running or not sys.stdin.isatty():
            return None
            
        # Check if input is available
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None
        
    async def handle_input(self):
        """Handle keyboard input asynchronously."""
        while self.running:
            key = self.check_key()
            if key and key in self.handlers:
                handler = self.handlers[key]
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            await asyncio.sleep(0.05)  # Small delay to prevent CPU spinning
            
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()