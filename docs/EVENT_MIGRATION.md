# Migration to Event-Sourced Architecture

## Overview

Pidgin has been completely re-architected around an event-sourcing pattern. Events are now the single source of truth, with all other data (transcripts, checkpoints, metrics) being derived views.

## Key Changes

### Before (Multiple Data Paths)
```
DialogueEngine → TranscriptManager → JSON/Markdown files
              → CheckpointManager → .checkpoint files  
              → MetricsCollector → metrics.json
              → AttractorManager → analysis.json
```

### After (Event-First)
```
Events (JSONL) → SQLite (indexes) → Transcripts (views)
               ↘ Dashboards (live)
               ↘ Analytics (batch)
```

## What's New

### 1. Event System (`pidgin/events.py`)
- All actions emit structured events
- Events stored in append-only JSONL files
- SQLite indexes for fast queries
- Real-time subscribers for live monitoring

### 2. Event-Based Dialogue Engine (`pidgin/event_dialogue.py`)
- Replaces old `DialogueEngine`
- Emits events for every significant action
- Supports streaming interrupts via events
- No more direct file writing

### 3. Event Transcripts (`pidgin/event_transcripts.py`)
- Generates transcripts from event streams
- Multiple export formats (Markdown, JSON, Parquet, CSV)
- Timeline visualizations
- Perfect reproducibility

### 4. Configuration Updates
New configuration sections in `pidgin.yaml`:

```yaml
events:
  compression:
    enabled: true
    compress_on_completion: true
  privacy:
    enabled: false  # For sensitive deployments
    remove_content: false
    hash_models: false
  storage:
    data_dir: "~/.pidgin_data/events"
```

## Migration Path

### ⚠️ No Backwards Compatibility

Since this is alpha software, there is **no migration path** for old data. The decision is to "burn the boats" and start fresh.

**Old data locations will be ignored:**
- `~/.pidgin_data/transcripts/` - No longer used
- `*.checkpoint` files - No longer used  
- Legacy JSON formats - No longer used

**New data location:**
- `~/.pidgin_data/events/` - All events stored here

### Steps to Migrate

1. **Backup any important conversations** from old format
2. **Update your code** to use new event-based APIs
3. **Update configuration** to include event settings
4. **Start fresh** - no old data will be imported

## New Usage Patterns

### Running Conversations

```python
from pidgin.event_factory import create_event_store, create_event_dialogue_engine
from pidgin.config_manager import get_config

# Set up event system
config = get_config()
event_store = create_event_store(config)
dialogue_engine = create_event_dialogue_engine(router, event_store, config)

# Run conversation (emits events automatically)
experiment_id = await dialogue_engine.run_conversation(
    agent_a, agent_b, prompt, max_turns
)

# Generate transcripts from events
transcript_gen = TranscriptGenerator(event_store)
markdown = transcript_gen.generate_markdown(experiment_id)
json_data = transcript_gen.generate_json(experiment_id)
```

### Real-time Monitoring

```python
from pidgin.event_factory import setup_console_subscriber

# Subscribe to live events
event_store = create_event_store(config)
setup_console_subscriber(event_store, verbose=True)

# Now any events will be displayed in real-time
```

### Data Analysis

```python
# Query specific metrics
convergence_trend = event_store.query_convergence_trend(experiment_id)
interruptions = event_store.query_interruptions(experiment_id)
summary = event_store.get_experiment_summary(experiment_id)

# Export for data science
transcript_gen.export_for_analysis(experiment_id, format='parquet')
```

### Event Debugging

```bash
# Grep through events for debugging
grep "interrupted" ~/.pidgin_data/events/exp_123.events.jsonl
grep "error" ~/.pidgin_data/events/exp_123.events.jsonl | jq .

# Or use compressed files
zgrep "interrupted" ~/.pidgin_data/events/exp_123.events.jsonl.gz
```

## Benefits

### 1. **Perfect Debugging**
- Every action is logged with precise timestamps
- Can replay any conversation exactly
- No more "what happened?" questions

### 2. **Flexible Analysis**
- Generate any view from raw events
- No need to modify storage format for new metrics
- Export to any format (CSV, Parquet, JSON)

### 3. **Real-time Capabilities**
- Live dashboards subscribe to event stream
- Immediate alerts on convergence/attractors
- Cost monitoring in real-time

### 4. **Data Integrity**
- Events are append-only (no corruption)
- SQLite indexes are disposable (rebuild anytime)
- JSONL files are human-readable and greppable

### 5. **Storage Efficiency**
- Automatic compression (typically 10:1 ratio)
- Only store events once, derive everything else
- No duplicate data across multiple files

## Event Types

The system emits these event types:

**Experiment Lifecycle:**
- `experiment.started`
- `experiment.completed` 
- `experiment.failed`

**Turn Flow:**
- `turn.started`
- `response.started`
- `response.streaming`
- `response.completed`
- `response.interrupted`
- `turn.completed`

**Interventions:**
- `pause.requested`
- `conductor.intervention`
- `checkpoint.saved`

**Detections:**
- `attractor.detected`
- `convergence.measured`
- `context.usage`
- `rate_limit.warning`

**API Events:**
- `api.call.started`
- `api.call.completed`
- `api.call.failed`
- `stream.chunk.received`

## File Format

Events are stored in JSONL format:

```json
{"v":1,"id":"abc123","type":"response.completed","experiment_id":"exp_001","timestamp":1234567890.123,"turn_number":0,"agent_id":"agent_a","data":{"content":"Hello!","tokens":3,"duration":1.2}}
{"v":1,"id":"def456","type":"convergence.measured","experiment_id":"exp_001","timestamp":1234567890.456,"turn_number":0,"agent_id":null,"data":{"score":0.15}}
```

Key fields:
- `v`: Schema version for future evolution
- `id`: Unique event ID
- `type`: Event type (see list above)
- `experiment_id`: Groups events by conversation
- `timestamp`: Precise Unix timestamp
- `turn_number`: Turn in conversation (null for experiment-level events)
- `agent_id`: Which agent (null for system events)
- `data`: Event-specific payload

## Privacy and Compliance

For sensitive deployments, the privacy filter can:
- Replace content with `[REDACTED]` (keeps length/hash for analysis)
- Hash model names to anonymize providers
- Redact custom patterns from text

Enable in configuration:
```yaml
events:
  privacy:
    enabled: true
    remove_content: true
    hash_models: true
    redact_patterns: ["@username", "secret_keyword"]
```

## Performance

The event system adds minimal overhead:
- Events emit in ~1-2ms
- SQLite indexes update in background
- Compression happens after experiment completion
- No blocking operations during conversation

Storage is very efficient:
- Text conversations: ~10KB uncompressed, ~1KB compressed
- Long conversations with embeddings: ~100KB uncompressed, ~10KB compressed

## Troubleshooting

### Events not appearing
- Check data directory permissions
- Verify config `events.storage.data_dir` setting
- Look for error messages about SQLite database

### Cannot replay experiment
- Check if file is compressed (`.jsonl.gz` extension)
- Verify experiment ID is correct
- Try manual decompression: `gunzip file.jsonl.gz`

### Performance issues
- Disable compression during development: `events.compression.enabled: false`
- Reduce subscriber complexity
- Check available disk space

### Privacy concerns
- Enable privacy filter in configuration
- Review generated files for sensitive data
- Consider custom redaction patterns

## Future Extensions

The event architecture enables:
- **Multi-experiment analysis** - compare across conversations
- **Live dashboards** - real-time monitoring via WebSocket
- **A/B testing** - systematic comparison of approaches
- **Cost optimization** - track token usage across experiments
- **Collaborative research** - share event streams with teams

This foundation makes Pidgin much more suitable for serious research and production deployments.