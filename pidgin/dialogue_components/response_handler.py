"""Response handler for getting agent responses with streaming support."""

from typing import Optional, Tuple, List
import asyncio

from ..types import Message
from ..router import Router
from .display_manager import DisplayManager
from .base import Component


class ResponseHandler(Component):
    """Handles getting responses from agents with streaming support."""
    
    def __init__(self, router: Router, display_manager: DisplayManager, intervention_handler=None):
        """Initialize response handler.
        
        Args:
            router: Router for message handling
            display_manager: Display manager for status updates
            intervention_handler: Optional intervention handler for pause checking
        """
        self.router = router
        self.display_manager = display_manager
        self.intervention_handler = intervention_handler
        self.conversation_messages: List[Message] = []
        
    def reset(self):
        """Reset response handler state."""
        self.conversation_messages = []
        
    def set_conversation_messages(self, messages: List[Message]):
        """Update conversation message reference.
        
        Args:
            messages: Current conversation messages
        """
        self.conversation_messages = messages
        
    async def get_response_streaming(self, agent_id: str, agent_name: str = "") -> Tuple[Optional[Message], bool]:
        """Get response with streaming and interrupt handling.
        
        Args:
            agent_id: ID of the agent to get response from
            agent_name: Display name for the agent
            
        Returns:
            Tuple of (message, interrupted) where message may be None on error
        """
        if not self.conversation_messages:
            raise ValueError("No conversation messages set")
            
        chunks = []
        interrupted = False
        
        # Set display name
        if not agent_name:
            agent_name = "Agent A" if agent_id == "agent_a" else "Agent B"
        status_color = "green" if agent_id == "agent_a" else "magenta"
        
        # Check if intervention handler has paused
        if self.intervention_handler and hasattr(self.intervention_handler, 'is_paused'):
            if self.intervention_handler.is_paused:
                interrupted = True
                return None, interrupted
        
        # Stream response with status display
        with self.display_manager.console.status(
            f"[bold {status_color}]{agent_name} is responding...[/bold {status_color}]",
            spinner="dots",
        ):
            try:
                # Protocol limitation: async generators can't be properly typed in protocols
                async for chunk, _ in self.router.get_next_response_stream(  # type: ignore[attr-defined]
                    self.conversation_messages, agent_id
                ):
                    chunks.append(chunk)
                    
            except Exception as e:
                if "rate limit" in str(e).lower():
                    self.display_manager.console.print(
                        f"\n[red]Rate limit hit: {e}[/red]"
                    )
                    return None, False
                else:
                    raise
                    
        # Create message from chunks
        content = "".join(chunks)
        if not content:
            return None, False
            
        message = Message(
            role="assistant", 
            content=content, 
            agent_id=agent_id
        )
        
        return message, interrupted
        
    async def get_response(self, agent_id: str) -> Message:
        """Get agent response without streaming.
        
        Args:
            agent_id: ID of the agent to get response from
            
        Returns:
            Response message
            
        Raises:
            SystemExit: On rate limit errors
        """
        if not self.conversation_messages:
            raise ValueError("No conversation messages set")
            
        try:
            response = await self.router.get_next_response(
                self.conversation_messages, agent_id
            )
            return response
        except Exception as e:
            # Check if it's a rate limit error
            if "rate limit" in str(e).lower():
                self.display_manager.console.print(
                    f"\n[red bold]⚠️  Hit actual rate limit: {e}[/red bold]"
                )
                self.display_manager.console.print(
                    "[yellow]Saving checkpoint and pausing...[/yellow]"
                )
                raise SystemExit(0)  # Graceful exit
            else:
                # Other API errors
                self.display_manager.console.print(f"\n[red]❌ API Error: {e}[/red]")
                raise