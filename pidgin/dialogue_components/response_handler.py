"""Response handler for getting agent responses with streaming support."""

from typing import Optional, Tuple, List
import asyncio

from ..types import Message
from ..router import Router
from .display_manager import DisplayManager
from .base import Component


class ResponseHandler(Component):
    """Handles getting responses from agents with streaming support."""

    def __init__(
        self, router: Router, display_manager: DisplayManager, intervention_handler=None
    ):
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

    async def get_response_streaming(
        self, agent_id: str, agent_name: str = ""
    ) -> Tuple[Optional[Message], bool]:
        """Get agent response with streaming."""
        chunks = []
        
        try:
            async for chunk, _ in self.router.get_next_response_stream(
                self.conversation_messages, agent_id
            ):
                chunks.append(chunk)
                
        except Exception as e:
            if "rate limit" in str(e).lower():
                self.display_manager.console.print(f"\n[red bold]⚠️  Hit rate limit: {e}[/red bold]")
                # Let the caller handle the pause
                return None, False
            else:
                raise
        
        content = ''.join(chunks)
        message = Message(
            role="assistant",
            content=content,
            agent_id=agent_id
        )
        
        return message, False  # Never interrupted

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
