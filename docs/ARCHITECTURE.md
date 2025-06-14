# Pidgin Architecture Documentation

Pidgin is an AI conversation research tool designed for studying emergent communication patterns between language models. This document provides a comprehensive overview of the system architecture.

## System Overview

Pidgin follows a modular architecture with clear separation of concerns:

- **User Interface Layer**: CLI and configuration management
- **Conversation Engine**: Core dialogue orchestration and control
- **AI Providers**: Abstracted interfaces to different LLM APIs
- **Detection Systems**: Pattern recognition and convergence analysis
- **Management Systems**: Context tracking, checkpointing, and transcription
- **Data Models**: Type definitions and model configurations

## Core Components

### 1. Dialogue Engine (`dialogue.py`)

The heart of Pidgin, orchestrating all conversation flow:

**Key Responsibilities:**
- Manages conversation turns between agents
- Coordinates all detection systems (attractor, convergence, context)
- Handles pause/resume functionality via checkpoints
- Integrates conductor modes for human intervention
- Manages transcript saving with enhanced metrics

**Integration Points:**
- Routes messages through the Router to AI providers
- Monitors context usage via ContextManager
- Tracks conversation patterns via AttractorManager
- Calculates similarity via ConvergenceCalculator
- Saves state via CheckpointManager and TranscriptManager

### 2. Router System (`router.py`)

Handles message routing and provider coordination:

**DirectRouter Implementation:**
- Alternates between Agent A and Agent B
- Converts message formats for each provider
- Maintains conversation history in provider-specific formats
- Handles role mapping (user/assistant) for each agent's perspective

### 3. Provider Abstraction (`providers/`)

Clean abstraction layer for different LLM APIs:

**Common Interface:**
```python
async def stream_response(self, messages: List[Message]) -> AsyncIterator[str]
```

**Implementations:**
- `AnthropicProvider`: Claude models via Anthropic API
- `OpenAIProvider`: GPT models via OpenAI API
- `GoogleProvider`: Gemini models via Google API
- `xAIProvider`: Grok models via xAI API

### 4. Convergence Detection System (`convergence.py`)

The primary validated metric for conversation dynamics:

**ConvergenceCalculator:**
- Measures structural similarity between agent responses
- Tracks how agents' communication styles align over time
- Provides convergence scores (0.0 = different, 1.0 = identical)
- Includes trend analysis (increasing, decreasing, stable)

### 5. Attractor Detection System (`attractors/`)

Experimental framework for detecting conversation patterns:

**Note:** This is a hypothesis being tested, not a validated feature.

**StructuralAnalyzer:**
- Extracts structural elements from messages
- Creates signatures independent of content
- Framework exists but needs rigorous validation

**AttractorManager:**
- Orchestrates detection at configurable intervals
- Currently experimental - convergence is the only validated metric

### 6. Context Window Management (`context_manager.py`)

Intelligent tracking of conversation size vs model limits:

**Key Features:**
- Model-specific context limits (Claude: 200k, GPT: 128k tokens)
- Predictive warnings before hitting limits
- Turn estimation based on message growth patterns
- Auto-pause functionality to prevent crashes

### 7. Conductor System (`conductor.py`)

Two modes for human interaction:

**Manual Mode:**
- Pauses after each complete turn
- Allows intervention injection
- Used for debugging and careful steering

**Flowing Mode (Default):**
- Automatic conversation flow
- Pause with Ctrl+C for intervention
- Standard mode for experiments

### 8. Turn Model

The atomic unit of conversation is a **Turn** (2+1 tuple):
- Agent A message
- Agent B message  
- Optional intervention

This model captures the natural conversation flow and makes analysis cleaner.

## Data Flow Architecture

### Conversation Lifecycle

1. **Initialization**
   - User provides initial prompt
   - Conversation object created with agent configurations
   - Providers initialized based on model selections

2. **Turn Processing**
   - Context usage checked before each agent response
   - Message routed to appropriate provider
   - Response added to conversation history
   - Metrics calculated and convergence updated

3. **Detection Phase**
   - Convergence calculated every turn
   - Attractor detection runs at intervals (experimental)
   - Auto-pause triggers if thresholds exceeded

4. **Persistence**
   - Transcripts saved after each turn
   - Checkpoint creation for pause/resume
   - Metrics saved in JSON format

### Storage Strategy

**Organized Directory Structure:**
```
~/.pidgin_data/transcripts/YYYY-MM-DD/conversation_id/
├── conversation.json      # Machine-readable with full metrics
├── conversation.md        # Human-readable markdown
├── conversation.checkpoint # Resumable state
└── attractor_analysis.json # Pattern detection results (experimental)
```

## Configuration System

### YAML Configuration (`config.py`)

Hierarchical configuration loading:
1. `~/.config/pidgin/pidgin.yaml` (XDG standard)
2. `~/.config/pidgin.yaml` (recommended)
3. `~/.pidgin.yaml` (home directory)
4. `./pidgin.yaml` (current directory)

**Key Configuration Areas:**
- Convergence thresholds
- Context management limits
- Checkpoint intervals
- Experimental feature flags

### Model Management (`models.py`)

Comprehensive model database with:
- Model IDs and convenient aliases
- Context window limits
- Provider information
- Deprecation tracking

## Imminent Event Architecture

The system is about to transition to event-driven architecture:

### Core Changes Coming
1. **EventBus** as central communication system
2. **Turn-based events** with 2+1 tuple as atomic unit
3. **Streaming via events** instead of blocking calls
4. **Decoupled components** communicating only through events

### Benefits
- Parallel experiment execution
- Perfect observability
- Natural streaming updates
- Component isolation

## Current Limitations

1. **UI Polish** - Some UX rough edges (3-enter input bug)
2. **Message Types** - Confusing agent_id="system" pattern
3. **Attractor Detection** - Experimental, needs validation
4. **Provider Quirks** - Each API has different requirements

## Performance Considerations

### Token Efficiency
- Approximate tokenization for speed
- Reserved token allocation prevents API errors
- Growth trend analysis improves predictions

### Detection Intervals
- Convergence calculated every turn (lightweight)
- Attractor detection every 5 turns (configurable)
- Context checks every turn (fast)

## Future Architecture (Post-Event Implementation)

### Event-Driven Benefits
- Conversations as event streams
- Natural parallelism for experiments
- Complete observability
- Replay capability

### Research Enablement
- Run hundreds of experiments in parallel
- Real-time analysis dashboards
- Perfect reproducibility
- Event log = complete record