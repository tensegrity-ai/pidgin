import asyncio
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .types import Message, Conversation, Agent
from .router import Router
from .transcripts import TranscriptManager


class DialogueEngine:
    def __init__(self, router: Router, transcript_manager: TranscriptManager):
        self.router = router
        self.transcript_manager = transcript_manager
        self.conversation: Optional[Conversation] = None
        self.console = Console()
    
    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent, 
        initial_prompt: str,
        max_turns: int
    ):
        # Initialize conversation
        self.conversation = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt=initial_prompt
        )
        
        # Initial message
        first_message = Message(
            role="user",
            content=initial_prompt,
            agent_id="system"  # System provides initial prompt
        )
        self.conversation.messages.append(first_message)
        
        # Display initial prompt
        self.console.print(Panel(
            initial_prompt, 
            title="[bold blue]Initial Prompt[/bold blue]",
            border_style="blue"
        ))
        self.console.print()
        
        # Run conversation loop
        try:
            for turn in range(max_turns):
                # Agent A responds
                response_a = await self._get_agent_response(agent_a.id)
                self.conversation.messages.append(response_a)
                self._display_message(response_a, agent_a.model)
                
                # Agent B responds  
                response_b = await self._get_agent_response(agent_b.id)
                self.conversation.messages.append(response_b)
                self._display_message(response_b, agent_b.model)
                
                # Auto-save after each turn
                await self.transcript_manager.save(self.conversation)
                
                # Show turn counter
                self.console.print(f"\n[dim]Turn {turn + 1}/{max_turns} completed[/dim]\n")
                
        except KeyboardInterrupt:
            # Graceful shutdown on Ctrl+C
            self.console.print("\n\n[yellow]Conversation interrupted. Saving transcript...[/yellow]")
            await self.transcript_manager.save(self.conversation)
            raise
    
    def _display_message(self, message: Message, model_name: str):
        """Display a message in the terminal with Rich formatting"""
        if message.agent_id == "agent_a":
            title = f"[bold green]Agent A ({model_name})[/bold green]"
            border_style = "green"
        else:
            title = f"[bold magenta]Agent B ({model_name})[/bold magenta]"
            border_style = "magenta"
        
        self.console.print(Panel(
            message.content,
            title=title,
            border_style=border_style
        ))
        self.console.print()
            
    async def _get_agent_response(self, agent_id: str) -> Message:
        # Create a message from this agent
        last_message = self.conversation.messages[-1]
        
        # Route through the router
        response = await self.router.route_message(last_message, self.conversation)
        
        return response