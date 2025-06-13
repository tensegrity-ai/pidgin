"""Refactored dialogue engine - orchestrates conversation components."""

import signal
from typing import Optional, Dict, Any
from rich.console import Console

from .dialogue_components import (
    DisplayManager,
    MetricsTracker,
    ProgressTracker,
    ResponseHandler,
    StateManager
)
from .attractors import AttractorManager
from .checkpoint import ConversationState
from .intervention_handler import InterventionHandler
from .config import get_config
from .context_manager import ContextWindowManager
from .router import Router
from .transcripts import TranscriptManager
from .types import Agent, Conversation, Message


class DialogueEngine:
    """Orchestrates conversations between agents using modular components."""
    
    def __init__(
        self,
        router: Router,
        transcript_manager: TranscriptManager,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize dialogue engine with components.
        
        Args:
            router: Router for message handling
            transcript_manager: Manager for saving transcripts
            config: Optional configuration dictionary
        """
        self.router = router
        self.transcript_manager = transcript_manager
        self.config = config or get_config()
        
        # Initialize core components
        self.console = Console()
        self.display = DisplayManager(self.console)
        self.metrics = MetricsTracker()
        self.state_manager = StateManager()
        
        # These will be initialized per conversation
        self.response_handler: Optional[ResponseHandler] = None
        self.progress: Optional[ProgressTracker] = None
        self.conversation: Optional[Conversation] = None
        self.intervention_handler: Optional[InterventionHandler] = None
        
        # Optional components based on config
        self._init_optional_components()
        
        # Signal handling
        self._original_sigint = None
        self._pause_requested = False
        
    def _init_optional_components(self):
        """Initialize optional components based on configuration."""
        # Attractor detection
        attractor_config = (
            self.config.get("conversation.attractor_detection", {})
            if hasattr(self.config, "get")
            else {}
        )
        self.attractor_manager = AttractorManager(attractor_config) if attractor_config.get("enabled", True) else None
        
        # Context management
        context_config = (
            self.config.get("context_management", {})
            if hasattr(self.config, "get")
            else {}
        )
        if context_config.get("enabled", True):
            self.context_manager = ContextWindowManager()
            self.context_warning_threshold = context_config.get("warning_threshold", 80)
            self.context_auto_pause_threshold = context_config.get("auto_pause_threshold", 95)
        else:
            self.context_manager = None
            
        # Checkpoint configuration
        checkpoint_config = (
            self.config.get("conversation.checkpoint", {})
            if hasattr(self.config, "get")
            else {}
        )
        self.state_manager.set_checkpoint_config(
            enabled=checkpoint_config.get("enabled", True),
            interval=checkpoint_config.get("auto_save_interval", 10)
        )
        
    async def run_conversation(
        self,
        agent_a: Agent,
        agent_b: Agent,
        initial_prompt: str,
        max_turns: int,
        resume_from_state: Optional[ConversationState] = None,
        show_token_warnings: bool = True,
        manual_mode: bool = False,
        convergence_threshold: float = 0.75,
    ):
        """Run a conversation between two agents.
        
        Args:
            agent_a: First agent
            agent_b: Second agent  
            initial_prompt: Initial prompt to start conversation
            max_turns: Maximum number of turns
            resume_from_state: Optional state to resume from
            show_token_warnings: Whether to show context warnings
            manual_mode: Whether to use manual intervention mode
            convergence_threshold: Threshold for convergence detection
        """
        # Setup signal handler
        self._setup_signal_handler()
        
        # Initialize intervention handler
        mode = "manual" if manual_mode else "flowing"
        self.intervention_handler = InterventionHandler(self.console, mode=mode)
        self.display.show_mode_info(mode)
        
        # Initialize response handler with intervention handler
        self.response_handler = ResponseHandler(
            self.router, self.display, self.intervention_handler
        )
        
        # Setup conversation state
        if resume_from_state:
            self._resume_conversation(resume_from_state, agent_a, agent_b)
        else:
            self._setup_new_conversation(agent_a, agent_b, initial_prompt, max_turns)
            
        # Initialize progress tracker
        start_turn = self.state_manager.get_turn_count()
        self.progress = ProgressTracker(max_turns, start_turn)
        
        # Set metrics threshold
        self.metrics.set_convergence_threshold(convergence_threshold)
        
        # Main conversation loop
        try:
            while self.progress.should_continue():
                # Check for pause
                if self._check_pause_requested():
                    break
                    
                # Run single turn
                turn_result = await self._run_single_turn(agent_a, agent_b)
                
                if turn_result == "pause":
                    await self._handle_pause()
                    break
                elif turn_result == "stop":
                    break
                    
                # Complete turn
                self.progress.complete_turn()
                
        except KeyboardInterrupt:
            # Handled by signal handler
            pass
        finally:
            await self._finalize_conversation()
            
    def _setup_new_conversation(self, agent_a: Agent, agent_b: Agent, 
                               initial_prompt: str, max_turns: int):
        """Setup a new conversation."""
        # Initialize conversation
        self.conversation = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt=initial_prompt,
        )
        
        # Initialize state
        transcript_path = self.transcript_manager.get_transcript_path()
        self.state_manager.initialize_state(
            agent_a, agent_b, initial_prompt, max_turns, str(transcript_path)
        )
        
        # Add system context
        system_context = """You are Agent A in this conversation.
You are speaking with Agent B.
Any message marked [HUMAN NOTE] comes from a human observer who is monitoring this conversation.
Your conversation partner (Agent B) is NOT the human observer - they are another participant like you.
Please engage naturally with Agent B."""
        
        context_message = Message(
            role="system",
            content=system_context,
            agent_id="system"
        )
        self.conversation.messages.append(context_message)
        self.state_manager.add_message(context_message)
        
        # Add initial prompt
        first_message = Message(
            role="user",
            content=initial_prompt,
            agent_id="researcher",
        )
        self.conversation.messages.append(first_message)
        self.state_manager.add_message(first_message)
        
        # Display initial prompt
        self.display.show_initial_prompt(initial_prompt)
        
        # Display context windows if enabled
        if self.context_manager:
            self.display.show_context_windows([agent_a, agent_b], self.context_manager)
            
    def _resume_conversation(self, state: ConversationState, agent_a: Agent, agent_b: Agent):
        """Resume from a saved state."""
        self.state_manager.load_state(state)
        self.conversation = Conversation(
            agents=[agent_a, agent_b],
            initial_prompt=state.initial_prompt,
            messages=state.messages.copy(),
        )
        
        # Show resume info
        self.display.show_resume_info(state.turn_count)
        
        # Show context usage if available
        if self.context_manager and "context_stats" in state.metadata:
            context_stats = state.metadata["context_stats"]
            self.console.print(
                f"[dim]Context usage at pause: "
                f"Agent A: {context_stats['agent_a']['percentage']:.1f}%, "
                f"Agent B: {context_stats['agent_b']['percentage']:.1f}%[/dim]"
            )
            
    async def _run_single_turn(self, agent_a: Agent, agent_b: Agent) -> str:
        """Run a single conversation turn.
        
        Returns:
            "continue", "pause", or "stop"
        """
        turn = self.progress.current_turn
        
        # Check context limits
        if await self._check_context_limits(agent_a, agent_b):
            return "pause"
            
        # Update response handler with current messages
        self.response_handler.set_conversation_messages(self.conversation.messages)
        
        # Get Agent A response
        response_a, interrupted_a = await self.response_handler.get_response_streaming(
            agent_a.id, f"Agent A ({agent_a.model})"
        )
        if response_a is None:
            return "pause"
            
        # Add to conversation
        self.conversation.messages.append(response_a)
        self.state_manager.add_message(response_a)
        
        # Display response
        context_info_a = self._get_context_info(agent_a.model) if self.context_manager else None
        self.display.display_message(response_a, agent_a.model, context_info_a)
        
        # Update metrics
        self.metrics.update_metrics(response_a, turn)
        
        # Get Agent B response
        response_b, interrupted_b = await self.response_handler.get_response_streaming(
            agent_b.id, f"Agent B ({agent_b.model})"
        )
        if response_b is None:
            return "pause"
            
        # Add to conversation
        self.conversation.messages.append(response_b)
        self.state_manager.add_message(response_b)
        
        # Display response
        context_info_b = self._get_context_info(agent_b.model) if self.context_manager else None
        self.display.display_message(response_b, agent_b.model, context_info_b)
        
        # Update metrics
        self.metrics.update_metrics(response_b, turn)
        
        # Calculate convergence
        self.metrics.calculate_convergence(self.conversation.messages)
        self.metrics.update_convergence_history(turn)
        
        # Check for interventions
        if self.intervention_handler:
            from .types import ConversationTurn
            current_turn = ConversationTurn(
                agent_a_message=response_a,
                agent_b_message=response_b,
                turn_number=turn + 1,
            )
            intervention = self.intervention_handler.get_intervention(current_turn)
            if intervention:
                self.conversation.messages.append(intervention)
                self.state_manager.add_message(intervention)
                self.display.display_message(intervention, "")
                
        # Save transcript
        await self.transcript_manager.save(
            self.conversation,
            metrics=self.metrics.get_current_metrics()
        )
        
        # Check for attractors
        if self.attractor_manager:
            message_contents = [
                msg.content for msg in self.conversation.messages
                if msg.role != "system"
            ]
            if result := self.attractor_manager.check(message_contents, turn + 1):
                self.display.show_attractor_detection(result)
                await self._handle_attractor_detection(result)
                if result["action"] == "stop":
                    self.progress.mark_stopped("attractor")
                    return "stop"
                    
        # Check convergence pause
        if self.metrics.check_convergence_pause():
            self.console.print(
                f"\n[red bold]⚠️  AUTO-PAUSE: Convergence reached {self.metrics.current_convergence:.2f}[/red bold]"
            )
            self.console.print(
                "[yellow]Agents are highly synchronized. Consider intervention.[/yellow]\n"
            )
            self._pause_requested = True
            return "pause"
            
        # Auto-checkpoint
        if self.progress.is_checkpoint_due(self.state_manager.checkpoint_interval):
            self._save_checkpoint()
            
        # Show progress
        display_metrics = self.metrics.get_display_metrics()
        if self.context_manager:
            display_metrics["context_usage"] = self._get_max_context_usage()
        self.display.show_turn_progress(turn, self.progress.max_turns, display_metrics)
        
        return "continue"
        
    async def _check_context_limits(self, agent_a: Agent, agent_b: Agent) -> bool:
        """Check context window limits.
        
        Returns:
            True if should pause due to context limits
        """
        if not self.context_manager or len(self.conversation.messages) <= 2:
            return False
            
        capacity_a = self.context_manager.get_remaining_capacity(
            self.conversation.messages, agent_a.model
        )
        capacity_b = self.context_manager.get_remaining_capacity(
            self.conversation.messages, agent_b.model
        )
        
        max_usage = max(capacity_a["percentage"], capacity_b["percentage"])
        
        if max_usage >= self.context_warning_threshold:
            most_constrained = (
                agent_a.model if capacity_a["percentage"] >= capacity_b["percentage"]
                else agent_b.model
            )
            turns_remaining = self.context_manager.predict_turns_remaining(
                self.conversation.messages, most_constrained
            )
            self.display.show_context_warning(max_usage, turns_remaining, most_constrained)
            
            if max_usage >= self.context_auto_pause_threshold:
                self.display.show_context_pause(max_usage, most_constrained)
                self._pause_requested = True
                return True
                
        return False
        
    def _get_context_info(self, model: str) -> Dict[str, Any]:
        """Get context usage info for a model."""
        if not self.context_manager:
            return {}
        return self.context_manager.get_remaining_capacity(
            self.conversation.messages, model
        )
        
    def _get_max_context_usage(self) -> float:
        """Get maximum context usage across agents."""
        if not self.context_manager or not self.conversation:
            return 0.0
            
        agents = self.conversation.agents
        usages = []
        for agent in agents:
            capacity = self.context_manager.get_remaining_capacity(
                self.conversation.messages, agent.model
            )
            usages.append(capacity["percentage"])
            
        return max(usages) if usages else 0.0
        
    def _check_pause_requested(self) -> bool:
        """Check if pause was requested."""
        if self._pause_requested:
            if self.intervention_handler and self.intervention_handler.is_paused:
                # Intervention handler is handling it
                self._pause_requested = False
                self.console.print(
                    "[yellow]🎼 Intervention handler paused - ready for interventions[/yellow]\n"
                )
            else:
                # Regular pause
                return True
        return False
        
    async def _handle_pause(self):
        """Handle pause request."""
        self.console.print("\n[yellow]Pausing conversation...[/yellow]")
        
        # Update context stats
        if self.context_manager and self.conversation:
            agents = self.conversation.agents
            self.state_manager.update_metadata("context_stats", {
                "agent_a": self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agents[0].model
                ),
                "agent_b": self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agents[1].model
                ),
            })
            
        # Save intervention data
        if self.intervention_handler:
            intervention_summary = self.intervention_handler.get_intervention_summary()
            if intervention_summary["total_interventions"] > 0:
                self.state_manager.update_metadata(
                    "conductor_interventions", intervention_summary
                )
                
        # Save checkpoint
        checkpoint_path = self.state_manager.save_checkpoint(force=True)
        if checkpoint_path:
            self.display.show_checkpoint_saved(str(checkpoint_path))
            
    async def _handle_attractor_detection(self, result: Dict[str, Any]):
        """Handle attractor detection event."""
        # Save attractor analysis
        if self.state_manager.state and self.state_manager.state.transcript_path:
            from pathlib import Path
            analysis_path = self.attractor_manager.save_analysis(
                Path(self.state_manager.state.transcript_path)
            )
            if analysis_path:
                self.console.print(
                    f"[green]✅ Analysis saved to: {analysis_path}[/green]"
                )
                
        # Update transcript with metadata
        if self.conversation:
            await self.transcript_manager.save(
                self.conversation, 
                metrics=self.metrics.get_current_metrics()
            )
            
    def _save_checkpoint(self):
        """Save checkpoint with context stats."""
        if self.context_manager and self.conversation:
            agents = self.conversation.agents
            self.state_manager.update_metadata("context_stats", {
                "agent_a": self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agents[0].model
                ),
                "agent_b": self.context_manager.get_remaining_capacity(
                    self.conversation.messages, agents[1].model
                ),
            })
            
        checkpoint_path = self.state_manager.save_checkpoint(force=True)
        if checkpoint_path:
            self.console.print(f"[dim]Checkpoint saved: {checkpoint_path}[/dim]")
            
    async def _finalize_conversation(self):
        """Finalize conversation and cleanup."""
        # Restore signal handler
        self._restore_signal_handler()
        
        # Save final intervention data
        if self.intervention_handler:
            intervention_summary = self.intervention_handler.get_intervention_summary()
            if intervention_summary["total_interventions"] > 0:
                self.state_manager.update_metadata(
                    "conductor_interventions", intervention_summary
                )
                self.console.print(
                    f"\n[dim]Intervention count: "
                    f"{intervention_summary['interventions']} interventions[/dim]"
                )
                
        # Save final transcript
        if self.conversation:
            await self.transcript_manager.save(
                self.conversation,
                metrics=self.metrics.get_current_metrics()
            )
            
    def _setup_signal_handler(self):
        """Set up minimal signal handler for Ctrl+C."""
        def interrupt_handler(signum, frame):
            if self.intervention_handler:
                self.intervention_handler.is_paused = True
                self.console.print(
                    "\n[yellow]⏸️  Paused. Intervention available at next turn.[/yellow]"
                )
            else:
                self.console.print("\n[red]Stopped by user[/red]")
                raise KeyboardInterrupt()
                
        self._original_sigint = signal.signal(signal.SIGINT, interrupt_handler)
        self.console.print("[dim]Press Ctrl+C anytime to pause[/dim]\n")
        
    def _restore_signal_handler(self):
        """Restore original signal handler."""
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)