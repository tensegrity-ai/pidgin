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
from .attractors import AttractorManager
from .config_manager import get_config


class DialogueEngine:
    def __init__(self, router: Router, transcript_manager: TranscriptManager, config: Optional[Dict[str, Any]] = None):
        self.router = router
        self.transcript_manager = transcript_manager
        self.conversation: Optional[Conversation] = None
        self.console = Console()
        
        # Configuration
        self.config = config or get_config()
        
        # Attractor detection
        attractor_config = self.config.get('conversation.attractor_detection', {}) if hasattr(self.config, 'get') else {}
        self.attractor_manager = AttractorManager(attractor_config)
        
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
                
                # Check for attractor detection
                message_contents = [msg.content for msg in self.conversation.messages if msg.role != "system"]
                
                # Show indicator when checking
                if self.attractor_manager.enabled and (turn + 1) % self.attractor_manager.check_interval == 0:
                    self.console.print("[dim]🔍 Checking for patterns...[/dim]", end='')
                    
                if attractor_result := self.attractor_manager.check(message_contents, turn + 1, show_progress=False):
                    self.console.print(" [red bold]ATTRACTOR FOUND![/red bold]")
                    await self._handle_attractor_detection(attractor_result)
                    if attractor_result['action'] == 'stop':
                        break
                elif self.attractor_manager.enabled and (turn + 1) % self.attractor_manager.check_interval == 0:
                    self.console.print(" [green]continuing normally.[/green]")
                
                # Auto-checkpoint at intervals
                if self.checkpoint_enabled and (turn + 1) % self.checkpoint_interval == 0:
                    checkpoint_path = self.state.save_checkpoint()
                    self.console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
                
                # Show turn counter with detection status
                detection_status = ""
                if self.attractor_manager.enabled:
                    detection_status = " [🔍 Detection Active]"
                    # Show when we're checking
                    if (turn + 1) % self.attractor_manager.check_interval == 0:
                        detection_status += " - Pattern check performed"
                
                self.console.print(f"\n[dim]Turn {turn + 1}/{max_turns} completed{detection_status}[/dim]\n")
                
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
        """Set up signal handlers for pause and stop."""
        # Ctrl+Z for pause (SIGTSTP)
        def pause_handler(signum, frame):
            self._pause_requested = True
            self.console.print("\n[yellow]⏸️  Pause requested... Finishing current turn.[/yellow]")
        
        # Ctrl+C for stop (SIGINT)
        def stop_handler(signum, frame):
            self.console.print("\n[red]🛑 Stop requested. Saving transcript...[/red]")
            raise KeyboardInterrupt()
        
        self._original_sigtstp = signal.signal(signal.SIGTSTP, pause_handler)
        self._original_sigint = signal.signal(signal.SIGINT, stop_handler)
        
        # Show controls
        self.console.print("[dim]Controls: [Ctrl+Z] Pause | [Ctrl+C] Stop[/dim]\n")
    
    def _restore_signal_handler(self):
        """Restore original signal handlers."""
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)
        if hasattr(self, '_original_sigtstp') and self._original_sigtstp:
            signal.signal(signal.SIGTSTP, self._original_sigtstp)
    
    async def _handle_pause(self):
        """Handle pause request."""
        self.console.print("\n[yellow]Pausing conversation...[/yellow]")
        checkpoint_path = self.state.save_checkpoint()
        self.console.print(f"\n[green]Checkpoint saved: {checkpoint_path}[/green]")
        self.console.print(f"[green]Resume with: pidgin resume {checkpoint_path}[/green]\n")
    
    async def _handle_attractor_detection(self, result: Dict[str, Any]):
        """Handle attractor detection event."""
        # Clear visual separator
        self.console.print(f"\n[red]{'='*60}[/red]")
        self.console.print(f"[red bold]🚨 ATTRACTOR DETECTED - Turn {result['turn_detected']}/{self.state.max_turns}[/red bold]")
        self.console.print(f"[red]{'='*60}[/red]")
        
        # Display detection details in a clear format
        self.console.print(f"[yellow]Type:[/yellow]       {result['type']}")
        self.console.print(f"[yellow]Pattern:[/yellow]    {result['description']}")
        self.console.print(f"[yellow]Confidence:[/yellow] {result['confidence']:.0%}")
        
        # Show pattern details if available
        if 'pattern' in result:
            pattern_str = result['pattern']
            if len(pattern_str) > 50:
                pattern_str = pattern_str[:50] + "..."
            self.console.print(f"[yellow]Structure:[/yellow]  {pattern_str}")
        
        self.console.print(f"[red]{'='*60}[/red]\n")
        
        # Save attractor analysis
        self.console.print("[dim]💾 Saving transcript with detection data...[/dim]")
        if self.state.transcript_path:
            analysis_path = self.attractor_manager.save_analysis(Path(self.state.transcript_path))
            if analysis_path:
                self.console.print(f"[green]✅ Analysis saved to: {analysis_path}[/green]")
        
        # Save the transcript with metadata
        await self.transcript_manager.save(self.conversation)
        self.console.print(f"[green]✅ Transcript saved to: {self.state.transcript_path}[/green]")
        
        if result['action'] == 'stop':
            self.console.print("\n[red bold]Ending conversation - Structural attractor reached[/red bold]\n")
        elif result['action'] == 'pause':
            self._pause_requested = True