import asyncio
import signal
from typing import Optional, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .types import Message, Conversation, Agent
from .router import Router
from .transcripts import TranscriptManager
from .checkpoint import ConversationState, CheckpointManager
from .basin_detection import BasinDetectionSystem, BasinEvent
from .configuration import get_config


class DialogueEngine:
    def __init__(self, router: Router, transcript_manager: TranscriptManager, config: Optional[Dict[str, Any]] = None):
        self.router = router
        self.transcript_manager = transcript_manager
        self.conversation: Optional[Conversation] = None
        self.console = Console()
        
        # Configuration
        self.config = config or get_config()
        
        # Basin detection
        basin_config = self.config.get_basin_config() if hasattr(self.config, 'get_basin_config') else {}
        self.basin_detector = BasinDetectionSystem(basin_config)
        
        # Checkpoint management
        self.state: Optional[ConversationState] = None
        self.checkpoint_manager = CheckpointManager()
        self.checkpoint_enabled = self.config.get('conversation.checkpoint.enabled', True) if hasattr(self.config, 'get') else True
        self.checkpoint_interval = self.config.get('conversation.checkpoint.auto_save_interval', 10) if hasattr(self.config, 'get') else 10
        
        # Signal handling for graceful pause
        self._original_sigint = None
        self._pause_requested = False
    
    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent, 
        initial_prompt: str,
        max_turns: int,
        resume_from_state: Optional[ConversationState] = None
    ):
        # Set up signal handler for graceful pause
        self._setup_signal_handler()
        
        # Initialize or resume conversation
        if resume_from_state:
            self.state = resume_from_state
            self.conversation = Conversation(
                agents=[agent_a, agent_b],
                initial_prompt=initial_prompt,
                messages=self.state.messages.copy()
            )
            start_turn = self.state.turn_count
            self.console.print(f"[green]Resuming conversation from turn {start_turn}[/green]\n")
        else:
            self.conversation = Conversation(
                agents=[agent_a, agent_b],
                initial_prompt=initial_prompt
            )
            self.state = ConversationState(
                model_a=agent_a.model,
                model_b=agent_b.model,
                agent_a_id=agent_a.id,
                agent_b_id=agent_b.id,
                max_turns=max_turns,
                initial_prompt=initial_prompt,
                transcript_path=str(self.transcript_manager.get_transcript_path())
            )
            start_turn = 0
        
        # Initial message (only if not resuming)
        if not resume_from_state:
            first_message = Message(
                role="user",
                content=initial_prompt,
                agent_id="system"  # System provides initial prompt
            )
            self.conversation.messages.append(first_message)
            self.state.add_message(first_message)
            
            # Display initial prompt
            self.console.print(Panel(
                initial_prompt, 
                title="[bold blue]Initial Prompt[/bold blue]",
                border_style="blue"
            ))
            self.console.print()
        
        # Run conversation loop
        try:
            for turn in range(start_turn, max_turns):
                # Check for pause request
                if self._pause_requested:
                    await self._handle_pause()
                    break
                
                # Agent A responds
                response_a = await self._get_agent_response(agent_a.id)
                self.conversation.messages.append(response_a)
                self.state.add_message(response_a)
                self._display_message(response_a, agent_a.model)
                
                # Agent B responds  
                response_b = await self._get_agent_response(agent_b.id)
                self.conversation.messages.append(response_b)
                self.state.add_message(response_b)
                self._display_message(response_b, agent_b.model)
                
                # Auto-save transcript after each turn
                await self.transcript_manager.save(self.conversation)
                
                # Check for basin detection
                if basin_event := self.basin_detector.check_for_basin(self.conversation.messages, turn + 1):
                    await self._handle_basin_detection(basin_event)
                    if self.basin_detector.get_action(basin_event) == 'stop':
                        break
                
                # Auto-checkpoint at intervals
                if self.checkpoint_enabled and (turn + 1) % self.checkpoint_interval == 0:
                    checkpoint_path = self.state.save_checkpoint()
                    self.console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
                
                # Show turn counter
                self.console.print(f"\n[dim]Turn {turn + 1}/{max_turns} completed[/dim]\n")
                
        except KeyboardInterrupt:
            # Handled by signal handler
            pass
        finally:
            # Restore original signal handler
            self._restore_signal_handler()
            # Save final transcript
            await self.transcript_manager.save(self.conversation)
    
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
    
    def _setup_signal_handler(self):
        """Set up signal handler for graceful pause."""
        def signal_handler(signum, frame):
            self._pause_requested = True
            self.console.print("\n[yellow]Pause requested... Finishing current turn.[/yellow]")
        
        self._original_sigint = signal.signal(signal.SIGINT, signal_handler)
    
    def _restore_signal_handler(self):
        """Restore original signal handler."""
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)
    
    async def _handle_pause(self):
        """Handle pause request."""
        self.console.print("\n[yellow]Pausing conversation...[/yellow]")
        checkpoint_path = self.state.save_checkpoint()
        self.console.print(f"\n[green]Checkpoint saved: {checkpoint_path}[/green]")
        self.console.print(f"[green]Resume with: pidgin resume {checkpoint_path}[/green]\n")
    
    async def _handle_basin_detection(self, event: BasinEvent):
        """Handle basin detection event."""
        self.console.print(f"\n[red]Basin Detected: {event.type.value} - Turn {event.turn}[/red]")
        self.console.print(f"[red]Detector: {event.detector} (confidence: {event.confidence:.2f})[/red]")
        
        if self.basin_detector.should_log_reasoning():
            # Save basin analysis
            basin_path = Path(self.state.transcript_path).with_suffix('.basin')
            with open(basin_path, 'w') as f:
                f.write(f"Basin Detection Report\n")
                f.write(f"====================\n\n")
                f.write(f"Type: {event.type.value}\n")
                f.write(f"Turn: {event.turn}\n")
                f.write(f"Detector: {event.detector}\n")
                f.write(f"Confidence: {event.confidence:.2f}\n")
                f.write(f"Details: {event.details}\n")
            self.console.print(f"[dim]Basin analysis saved to: {basin_path}[/dim]")
        
        action = self.basin_detector.get_action(event)
        if action == 'stop':
            self.console.print("[red]Ending conversation early[/red]\n")