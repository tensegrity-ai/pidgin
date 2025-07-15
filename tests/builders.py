"""Test data builders for Pidgin tests."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pidgin.core.types import Message, Agent, Conversation, ConversationTurn
from pidgin.core.events import (
    ConversationStartEvent,
    ConversationEndEvent,
    TurnStartEvent,
    TurnCompleteEvent,
    Turn,
    MessageRequestEvent,
    SystemPromptEvent,
    MessageChunkEvent,
    MessageCompleteEvent,
    ErrorEvent,
    APIErrorEvent,
    ProviderTimeoutEvent,
    InterruptRequestEvent,
    ConversationPausedEvent,
    ConversationResumedEvent,
    RateLimitPaceEvent,
    TokenUsageEvent,
)


# Message Builder
def make_message(
    content: str = "Test message",
    agent_id: str = "agent_a",
    role: str = "user",
    timestamp: Optional[datetime] = None,
    **kwargs
) -> Message:
    """Create a test message with defaults."""
    return Message(
        role=role,
        content=content,
        agent_id=agent_id,
        timestamp=timestamp or datetime.now(),
        **kwargs
    )


# Agent Builder
def make_agent(
    id: str = "test_agent",
    model: str = "local:test",
    display_name: Optional[str] = None,
    temperature: float = 0.7,
    **kwargs
) -> Agent:
    """Create a test agent with defaults."""
    return Agent(
        id=id,
        model=model,
        display_name=display_name or f"Test {id}",
        temperature=temperature,
        **kwargs
    )


# Conversation Builder
def make_conversation(
    id: str = "test_conv",
    num_turns: int = 3,
    agents: Optional[List[Agent]] = None,
    started_at: Optional[datetime] = None,
    **kwargs
) -> Conversation:
    """Create a test conversation with messages."""
    if agents is None:
        agents = [make_agent("agent_a"), make_agent("agent_b")]
    
    messages = []
    for i in range(num_turns * 2):
        agent_id = "agent_a" if i % 2 == 0 else "agent_b"
        role = "user" if i % 2 == 0 else "assistant"
        messages.append(make_message(
            content=f"Message {i}",
            agent_id=agent_id,
            role=role
        ))
    
    return Conversation(
        id=id,
        agents=agents,
        messages=messages,
        started_at=started_at or datetime.now(),
        **kwargs
    )


# ConversationTurn Builder
def make_turn(
    turn_number: int = 1,
    agent_a_message: Optional[Message] = None,
    agent_b_message: Optional[Message] = None,
    **kwargs
) -> ConversationTurn:
    """Create a test conversation turn."""
    return ConversationTurn(
        turn_number=turn_number,
        agent_a_message=agent_a_message,
        agent_b_message=agent_b_message,
        **kwargs
    )


# Event Builders
def make_conversation_start_event(
    conversation_id: str = "test_conv",
    agent_a_model: str = "local:test",
    agent_b_model: str = "local:test",
    initial_prompt: str = "Test prompt",
    max_turns: int = 10,
    agent_a_display_name: Optional[str] = None,
    agent_b_display_name: Optional[str] = None,
    temperature_a: Optional[float] = None,
    temperature_b: Optional[float] = None,
    **kwargs
) -> ConversationStartEvent:
    """Create a test conversation start event."""
    return ConversationStartEvent(
        conversation_id=conversation_id,
        agent_a_model=agent_a_model,
        agent_b_model=agent_b_model,
        initial_prompt=initial_prompt,
        max_turns=max_turns,
        agent_a_display_name=agent_a_display_name,
        agent_b_display_name=agent_b_display_name,
        temperature_a=temperature_a,
        temperature_b=temperature_b,
        **kwargs
    )


def make_conversation_end_event(
    conversation_id: str = "test_conv",
    reason: str = "max_turns",
    total_turns: int = 5,
    duration_ms: int = 10000,
    **kwargs
) -> ConversationEndEvent:
    """Create a test conversation end event."""
    return ConversationEndEvent(
        conversation_id=conversation_id,
        reason=reason,
        total_turns=total_turns,
        duration_ms=duration_ms,
        **kwargs
    )


def make_turn_start_event(
    conversation_id: str = "test_conv",
    turn_number: int = 1,
    **kwargs
) -> TurnStartEvent:
    """Create a test turn start event."""
    return TurnStartEvent(
        conversation_id=conversation_id,
        turn_number=turn_number,
        **kwargs
    )


def make_turn_complete_event(
    conversation_id: str = "test_conv",
    turn_number: int = 1,
    turn: Optional[Turn] = None,
    convergence_score: Optional[float] = None,
    **kwargs
) -> TurnCompleteEvent:
    """Create a test turn complete event."""
    if turn is None:
        turn = Turn(
            agent_a_message=make_message("Agent A message", "agent_a"),
            agent_b_message=make_message("Agent B message", "agent_b", role="assistant")
        )
    
    return TurnCompleteEvent(
        conversation_id=conversation_id,
        turn_number=turn_number,
        turn=turn,
        convergence_score=convergence_score,
        **kwargs
    )


def make_message_request_event(
    conversation_id: str = "test_conv",
    agent_id: str = "agent_a",
    turn_number: int = 1,
    conversation_history: Optional[List[Message]] = None,
    temperature: Optional[float] = None,
    **kwargs
) -> MessageRequestEvent:
    """Create a test message request event."""
    if conversation_history is None:
        conversation_history = []
    
    return MessageRequestEvent(
        conversation_id=conversation_id,
        agent_id=agent_id,
        turn_number=turn_number,
        conversation_history=conversation_history,
        temperature=temperature,
        **kwargs
    )


def make_message_chunk_event(
    conversation_id: str = "test_conv",
    agent_id: str = "agent_a",
    chunk: str = "Test chunk",
    chunk_index: int = 0,
    elapsed_ms: int = 100,
    **kwargs
) -> MessageChunkEvent:
    """Create a test message chunk event."""
    return MessageChunkEvent(
        conversation_id=conversation_id,
        agent_id=agent_id,
        chunk=chunk,
        chunk_index=chunk_index,
        elapsed_ms=elapsed_ms,
        **kwargs
    )


def make_message_complete_event(
    conversation_id: str = "test_conv",
    agent_id: str = "agent_a",
    message: Optional[Message] = None,
    tokens_used: int = 50,
    duration_ms: int = 100,
    **kwargs
) -> MessageCompleteEvent:
    """Create a test message complete event."""
    if message is None:
        message = make_message(agent_id=agent_id)
    
    return MessageCompleteEvent(
        conversation_id=conversation_id,
        agent_id=agent_id,
        message=message,
        tokens_used=tokens_used,
        duration_ms=duration_ms,
        **kwargs
    )


def make_error_event(
    conversation_id: str = "test_conv",
    error_type: str = "test_error",
    error_message: str = "Test error occurred",
    context: Optional[str] = None,
    **kwargs
) -> ErrorEvent:
    """Create a test error event."""
    return ErrorEvent(
        conversation_id=conversation_id,
        error_type=error_type,
        error_message=error_message,
        context=context,
        **kwargs
    )


def make_token_usage_event(
    conversation_id: str = "test_conv",
    provider: str = "openai",
    tokens_used: int = 150,
    tokens_per_minute_limit: int = 10000,
    current_usage_rate: float = 0.15,
    **kwargs
) -> TokenUsageEvent:
    """Create a test token usage event."""
    return TokenUsageEvent(
        conversation_id=conversation_id,
        provider=provider,
        tokens_used=tokens_used,
        tokens_per_minute_limit=tokens_per_minute_limit,
        current_usage_rate=current_usage_rate,
        **kwargs
    )




def make_api_error_event(
    conversation_id: str = "test_conv",
    error_type: str = "APIError",
    error_message: str = "API request failed",
    agent_id: str = "agent_a",
    provider: str = "openai",
    context: Optional[str] = None,
    retryable: bool = True,
    retry_count: int = 0,
    **kwargs
) -> APIErrorEvent:
    """Create a test API error event."""
    return APIErrorEvent(
        conversation_id=conversation_id,
        error_type=error_type,
        error_message=error_message,
        agent_id=agent_id,
        provider=provider,
        context=context,
        retryable=retryable,
        retry_count=retry_count,
        **kwargs
    )


# Provider Response Builders
def make_text_chunk(text: str) -> Dict[str, Any]:
    """Create a provider text chunk response."""
    return {"type": "text", "text": text}


def make_usage_chunk(
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    total_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """Create a provider usage chunk response."""
    if total_tokens is None:
        total_tokens = prompt_tokens + completion_tokens
    
    return {
        "type": "usage",
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
    }


# Mock Stream Builders
async def make_mock_stream(chunks: List[str], include_usage: bool = True):
    """Create a mock async generator for provider responses."""
    for chunk in chunks:
        yield make_text_chunk(chunk)
    
    if include_usage:
        yield make_usage_chunk()


# Experiment Config Builder
def make_experiment_config(
    name: str = "test_experiment",
    agent_a_model: str = "local:test",
    agent_b_model: str = "local:test",
    repetitions: int = 1,
    max_turns: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """Create a test experiment configuration."""
    config = {
        "name": name,
        "agent_a_model": agent_a_model,
        "agent_b_model": agent_b_model,
        "repetitions": repetitions,
        "max_turns": max_turns,
        "temperature_a": kwargs.get("temperature_a", 0.7),
        "temperature_b": kwargs.get("temperature_b", 0.7),
        "max_parallel": kwargs.get("max_parallel", 1),
        "display_mode": kwargs.get("display_mode", "none")
    }
    
    # Add optional fields if provided
    for key in ["custom_prompt", "dimensions", "convergence_threshold", 
                "convergence_action", "awareness", "choose_names"]:
        if key in kwargs:
            config[key] = kwargs[key]
    
    return config