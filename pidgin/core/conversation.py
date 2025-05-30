"""Conversation management and orchestration."""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from pidgin.core.experiment import Experiment, MediationLevel
from pidgin.llm.base import LLM, Message, LLMResponse
from pidgin.analysis.compression import CompressionAnalyzer
from pidgin.analysis.symbols import SymbolDetector


class ConversationEvent(str, Enum):
    """Events that can occur during a conversation."""
    TURN_START = "turn_start"
    TURN_COMPLETE = "turn_complete"
    MESSAGE_GENERATED = "message_generated"
    COMPRESSION_ACTIVATED = "compression_activated"
    SYMBOL_DETECTED = "symbol_detected"
    BASIN_DETECTED = "basin_detected"
    USER_INTERVENTION = "user_intervention"
    ERROR = "error"


class ConversationManager:
    """Manages the flow of a conversation experiment."""
    
    def __init__(
        self,
        experiment: Experiment,
        event_handler: Optional[Callable] = None
    ):
        self.experiment = experiment
        self.event_handler = event_handler
        self.compression_analyzer = CompressionAnalyzer()
        self.symbol_detector = SymbolDetector()
        
        # State
        self.is_running = False
        self.is_paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        
        # Message history for LLMs
        self.message_history: List[Message] = []
        
        # Initialize with task/prompt if needed
        self._initialize_conversation()
    
    def _initialize_conversation(self):
        """Initialize the conversation with any needed prompts."""
        if self.experiment.config.meditation_mode:
            # Meditation mode starts with a specific prompt
            initial_prompt = Message(
                role="user",
                content="Please respond to this task. You may be collaborating with another AI system on this."
            )
            self.message_history.append(initial_prompt)
        else:
            # Regular conversation might have an initial task
            if "initial_task" in self.experiment.metadata:
                task = self.experiment.metadata["initial_task"]
                self.message_history.append(Message(
                    role="user",
                    content=task
                ))
    
    async def run(self):
        """Run the conversation experiment."""
        if self.experiment.status != "running":
            self.experiment.start()
        
        self.is_running = True
        await self._emit_event(ConversationEvent.TURN_START, {"turn": 0})
        
        try:
            while self.is_running and self.experiment.current_turn < self.experiment.config.max_turns:
                # Check for pause
                await self._pause_event.wait()
                
                # Get next speaker
                speaker = self.experiment.get_next_speaker()
                
                # Generate response
                response = await self._generate_turn(speaker)
                
                if response:
                    # Add to experiment
                    turn_data = {
                        "speaker": speaker.name,
                        "content": response.content,
                        "usage": response.usage,
                        "model": response.model,
                    }
                    
                    # Check for mediation
                    if await self._check_mediation(turn_data):
                        self.experiment.add_turn(turn_data)
                        
                        # Analyze turn
                        await self._analyze_turn(response)
                        
                        # Check stopping conditions
                        if await self._check_stopping_conditions():
                            break
                
                # Small delay to prevent rate limiting
                await asyncio.sleep(0.5)
            
            # Complete experiment
            self.experiment.complete()
            self.is_running = False
            
        except Exception as e:
            await self._emit_event(ConversationEvent.ERROR, {"error": str(e)})
            self.experiment.fail(str(e))
            raise
    
    async def _generate_turn(self, speaker: LLM) -> Optional[LLMResponse]:
        """Generate a turn from the given speaker."""
        await self._emit_event(ConversationEvent.TURN_START, {
            "turn": self.experiment.current_turn + 1,
            "speaker": speaker.name
        })
        
        try:
            # Prepare messages for this speaker
            messages = self._prepare_messages_for_speaker(speaker)
            
            # Apply compression if active
            if self.experiment.compression_active:
                messages = await self._apply_compression(messages)
            
            # Generate response
            response = await speaker.generate(messages)
            
            # Add to message history
            self.message_history.append(Message(
                role="assistant",
                content=response.content,
                metadata={"speaker": speaker.name, "model": response.model}
            ))
            
            await self._emit_event(ConversationEvent.MESSAGE_GENERATED, {
                "speaker": speaker.name,
                "content": response.content,
                "usage": response.usage
            })
            
            return response
            
        except Exception as e:
            await self._emit_event(ConversationEvent.ERROR, {
                "error": f"Failed to generate turn: {str(e)}"
            })
            return None
    
    def _prepare_messages_for_speaker(self, speaker: LLM) -> List[Message]:
        """Prepare message history for a specific speaker."""
        messages = []
        
        if self.experiment.config.meditation_mode:
            # In meditation mode, include all history
            messages = self.message_history.copy()
        else:
            # In regular mode, format as conversation
            # Skip the initial task message
            start_idx = 1 if self.message_history and self.message_history[0].role == "user" else 0
            
            for msg in self.message_history[start_idx:]:
                if msg.metadata and msg.metadata.get("speaker") == speaker.name:
                    # This speaker's previous messages
                    messages.append(Message(
                        role="assistant",
                        content=msg.content
                    ))
                else:
                    # Other speakers' messages as user messages
                    messages.append(Message(
                        role="user",
                        content=msg.content
                    ))
        
        return messages
    
    async def _apply_compression(self, messages: List[Message]) -> List[Message]:
        """Apply compression to messages if enabled."""
        # Get compression guidance
        compression_prompt = self.compression_analyzer.get_compression_prompt(
            self.experiment.current_turn,
            self.experiment.config.compression_start_turn,
            self.experiment.config.compression_rate
        )
        
        # Add compression instruction to the last user message
        if messages and compression_prompt:
            last_msg = messages[-1]
            messages[-1] = Message(
                role=last_msg.role,
                content=f"{last_msg.content}\n\n{compression_prompt}"
            )
        
        return messages
    
    async def _check_mediation(self, turn_data: Dict[str, Any]) -> bool:
        """Check if human mediation is required."""
        level = self.experiment.config.mediation_level
        
        if level == MediationLevel.AUTO:
            return True
        
        if level == MediationLevel.OBSERVE:
            # Just observe, no intervention
            return True
        
        if level in [MediationLevel.LIGHT, MediationLevel.FULL]:
            # Emit event for UI to handle
            await self._emit_event(ConversationEvent.USER_INTERVENTION, {
                "turn_data": turn_data,
                "level": level
            })
            
            # In a real implementation, this would wait for user response
            # For now, auto-approve
            return True
        
        return True
    
    async def _analyze_turn(self, response: LLMResponse):
        """Analyze the turn for compression, symbols, etc."""
        content = response.content
        
        # Update compression metrics
        if self.experiment.compression_active:
            ratio = self.compression_analyzer.calculate_compression_ratio(
                self.message_history,
                content
            )
            self.experiment.metrics.compression_ratio = ratio
        
        # Detect symbols
        symbols = self.symbol_detector.detect_symbols(content)
        if symbols:
            for symbol in symbols:
                if symbol not in self.experiment.metrics.symbols_emerged:
                    self.experiment.metrics.symbols_emerged.append(symbol)
                    await self._emit_event(ConversationEvent.SYMBOL_DETECTED, {
                        "symbol": symbol,
                        "turn": self.experiment.current_turn
                    })
        
        # Update token count
        self.experiment.metrics.total_tokens += response.usage.get("total_tokens", 0)
    
    async def _check_stopping_conditions(self) -> bool:
        """Check if experiment should stop."""
        # Basin detection for meditation mode
        if self.experiment.config.meditation_mode and self.experiment.config.basin_detection:
            if self._detect_basin():
                self.experiment.metrics.basin_reached = True
                await self._emit_event(ConversationEvent.BASIN_DETECTED, {
                    "turn": self.experiment.current_turn
                })
                return True
        
        return False
    
    def _detect_basin(self) -> bool:
        """Detect if conversation has reached an attractor state."""
        # Simple implementation: check for repetition in last N messages
        if len(self.message_history) < 10:
            return False
        
        # Check for exact repetition
        recent_messages = [msg.content for msg in self.message_history[-10:]]
        if len(set(recent_messages)) < 3:  # High repetition
            return True
        
        # Check for semantic similarity (simplified)
        # In a real implementation, use embeddings
        return False
    
    async def _emit_event(self, event: ConversationEvent, data: Dict[str, Any]):
        """Emit an event to the handler."""
        if self.event_handler:
            await self.event_handler(event, data)
    
    def pause(self):
        """Pause the conversation."""
        self.is_paused = True
        self._pause_event.clear()
        self.experiment.pause()
    
    def resume(self):
        """Resume the conversation."""
        self.is_paused = False
        self._pause_event.set()
        self.experiment.resume()
    
    def stop(self):
        """Stop the conversation."""
        self.is_running = False
        if self.experiment.is_active:
            self.experiment.cancel()