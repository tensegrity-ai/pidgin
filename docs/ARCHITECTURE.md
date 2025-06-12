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
async def get_response(self, messages: List[Message]) -> str
```

**Implementations:**
- `AnthropicProvider`: Claude models via Anthropic API
- `OpenAIProvider`: GPT models via OpenAI API

### 4. Attractor Detection System (`attractors/`)

The breakthrough innovation - detecting structural conversation patterns:

**Core Insight:** Conversations fall into structural templates long before content becomes repetitive.

**StructuralAnalyzer:**
- Extracts structural elements from messages (EXCITED_OPENING, LIST_ITEM, QUESTION, etc.)
- Creates structural signatures independent of content
- Identifies formal patterns in conversation flow

**StructuralPatternDetector:**
- Detects repeating structural patterns with configurable thresholds
- Identifies alternating A-B-A-B patterns
- Calculates confidence scores for pattern detection

**AttractorManager:**
- Orchestrates detection at configurable intervals
- Maps detected patterns to known attractors (Party Loop, Gratitude Spiral, etc.)
- Triggers actions (stop, pause, log) based on configuration

### 5. Context Window Management (`context_manager.py`)

Intelligent tracking of conversation size vs model limits:

**Key Features:**
- Model-specific context limits (Claude: 200k, GPT: 128k tokens)
- Predictive warnings before hitting limits
- Turn estimation based on message growth patterns
- Auto-pause functionality to prevent crashes

**Token Management:**
- Approximate tokenization (1 token ≈ 4 characters)
- Reserved token allocation for system prompts
- Growth trend analysis for better predictions

### 6. Conductor Modes (`conductor.py`)

Two sophisticated modes for human interaction:

**Manual Mode (`ConductorMiddleware`):**
- Step-by-step message approval
- Edit, inject, or skip any message
- Full conversation control

**Flowing Mode (`FlowingConductorMiddleware`):**
- Automatic conversation flow
- Pause on Ctrl+Z for intervention
- Convergence trend display when paused
- Seamless resume functionality

### 7. Convergence Tracking (`convergence.py`)

Measures how similar agents become over time:

**Analysis Dimensions:**
- Message length similarity
- Sentence pattern matching
- Structural similarity (paragraphs, lists, questions)
- Punctuation pattern analysis

**Output:**
- Convergence score (0.0 = different, 1.0 = identical)
- Trend analysis (increasing, decreasing, stable, fluctuating)
- Auto-warnings at high convergence (≥75%)

## Data Flow Architecture

### Conversation Lifecycle

1. **Initialization**
   - User provides initial prompt (direct or dimensional)
   - Conversation object created with agent configurations
   - Providers initialized based on model selections

2. **Turn Processing**
   - Context usage checked before each agent response
   - Message routed to appropriate provider
   - Conductor processes message (edit/inject/approve)
   - Response added to conversation history
   - Metrics calculated and convergence updated

3. **Detection Phase**
   - Attractor detection runs at intervals
   - Convergence warnings if similarity too high
   - Auto-pause triggers if thresholds exceeded

4. **Persistence**
   - Auto-save transcripts after each turn
   - Checkpoint creation for pause/resume
   - Enhanced metrics saved to JSON format

### Storage Strategy

**Organized Directory Structure:**
```
~/.pidgin_data/transcripts/YYYY-MM-DD/conversation_id/
├── conversation.json      # Machine-readable with full metrics
├── conversation.md        # Human-readable markdown
├── conversation.checkpoint # Resumable state
└── attractor_analysis.json # Pattern detection results
```

**Enhanced Metrics Integration:**
- Turn-by-turn convergence history
- Conductor intervention tracking
- Structural pattern analysis
- Phase detection timestamps

## Configuration System

### YAML Configuration (`config_manager.py`)

Hierarchical configuration loading:
1. `~/.config/pidgin/pidgin.yaml` (XDG standard)
2. `~/.config/pidgin.yaml` (recommended)
3. `~/.pidgin.yaml` (home directory)
4. `./pidgin.yaml` (current directory)

**Key Configuration Areas:**
- Attractor detection parameters
- Context management thresholds
- Checkpoint intervals
- Experiment profiles

### Model Management (`models.py`)

Comprehensive model database with:
- Model IDs and convenient aliases
- Context window limits and pricing tiers
- Conversation characteristics (verbosity, style)
- Recommended pairings for research
- Deprecation tracking

## Research Features

### Dimensional Prompts (`dimensional_prompts.py`)

Systematic prompt generation from orthogonal dimensions:

**Dimension Categories:**
- **Context**: peers, teaching, debate, interview, collaboration
- **Topic**: philosophy, language, science, meta, puzzles, thought_experiments
- **Mode**: analytical, intuitive, exploratory, focused
- **Energy**: calm, engaged, passionate
- **Formality**: casual, professional, academic

**Example:**
`peers:philosophy:analytical` → "Hello! I'm excited to explore the fundamental nature of reality together. Let's systematically analyze..."

### Checkpoint/Resume System (`checkpoint.py`)

Robust state management for long-running experiments:

**Features:**
- Atomic checkpoint writing (no corruption)
- Full conversation state serialization
- Resume info extraction
- Cleanup utilities for old checkpoints

### Transcript Management (`transcripts.py`)

Dual-format output for different use cases:

**JSON Format:**
- Complete message history with metadata
- Enhanced metrics and analysis data
- Machine-readable for post-processing

**Markdown Format:**
- Human-readable conversation flow
- Clean formatting with agent identification
- Suitable for sharing and review

## Extensibility Points

### Adding New Providers

1. Implement `Provider` interface in `providers/`
2. Add model configurations to `models.py`
3. Update router logic if needed

### Custom Attractor Patterns

1. Add pattern definitions to `attractors/patterns.py`
2. Extend structural element detection in `attractors/structural.py`
3. Configure detection thresholds

### New Detection Systems

1. Create detector class with `check()` method
2. Integrate into dialogue engine loop
3. Add configuration options

## Performance Considerations

### Token Efficiency
- Approximate tokenization for speed vs. accuracy trade-off
- Reserved token allocation prevents API errors
- Growth trend analysis improves prediction accuracy

### Detection Intervals
- Attractor detection runs every 5 turns (configurable)
- Convergence calculated every turn but lightweight
- Context checks are fast and run every turn

### Memory Management
- Message history grows with conversation length
- Checkpoint system prevents data loss
- Transcript streaming reduces memory pressure

## Security and Error Handling

### API Key Management
- Environment variable-based configuration
- Clear error messages for missing keys
- Provider-specific error handling

### Graceful Degradation
- Context window auto-pause prevents crashes
- Checkpoint system ensures no data loss
- Signal handling for clean interruption

### Validation
- Message format validation
- Configuration schema checking
- Model compatibility verification

## Future Architecture Considerations

### Scalability
- Multi-conversation management
- Distributed conversation processing
- Shared attractor pattern database

### Analytics
- Cross-conversation pattern analysis
- Model behavior comparison
- Convergence trend aggregation

### Integration
- API endpoints for programmatic access
- Webhook notifications for events
- External tool integration