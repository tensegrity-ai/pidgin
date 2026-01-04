# Analysis & Notebooks

Pidgin automatically generates Jupyter notebooks for post-experiment analysis. These notebooks provide a starting point for exploring conversation data, metrics, and convergence patterns.

## Auto-Generated Notebooks

After an experiment completes, Pidgin generates an `analysis.ipynb` notebook in the experiment directory:

```
pidgin_output/experiments/experiment_abc123_my_experiment_2024-01-15/
├── manifest.json
├── conv_xyz_events.jsonl
├── README.md
├── analysis.ipynb          # Auto-generated notebook
└── transcripts/
    └── conv_xyz.md
```

### Requirements

Notebook generation requires the `nbformat` library:

```bash
pip install nbformat
# or
uv add nbformat
```

If `nbformat` is not installed, notebook generation is skipped without error.

## Notebook Contents

The generated notebook includes several analysis sections:

### 1. Setup

- Experiment metadata and configuration
- Library imports (pandas, matplotlib, duckdb)
- Data loading from manifest and database

### 2. Basic Statistics

- Turn counts and message counts
- Message length distributions
- Token usage summaries
- Per-agent statistics

### 3. Convergence Analysis

- Turn-by-turn convergence scores
- Convergence trend visualization
- Component breakdown (content, structure, vocabulary)

### 4. Vocabulary Analysis

- Vocabulary overlap between agents
- Word frequency analysis
- Unique terms per agent

### 5. Visualizations

- Message length over time
- Token usage patterns
- Convergence score trends

### 6. Data Export

- Export to CSV for external tools
- Export to JSON for programmatic access

## Convergence Algorithm

Pidgin calculates convergence by comparing recent messages from both agents across multiple dimensions.

### Window Size

By default, the algorithm considers the last 10 messages from each agent. This sliding window captures recent conversation dynamics rather than overall similarity.

### Metrics

| Metric | Weight | Description |
|--------|--------|-------------|
| Content | 0.40 | Word and character overlap |
| Length | 0.15 | Message length similarity |
| Sentences | 0.20 | Sentence pattern similarity |
| Structure | 0.15 | Paragraphs, lists, questions, code blocks |
| Punctuation | 0.10 | Punctuation pattern similarity |

### Convergence Profiles

Different profiles adjust the metric weights:

```bash
# Default balanced approach
pidgin run -a claude -b gpt --convergence-profile balanced

# Emphasize structural patterns
pidgin run -a claude -b gpt --convergence-profile structural

# Emphasize semantic content
pidgin run -a claude -b gpt --convergence-profile semantic

# Strict matching across all dimensions
pidgin run -a claude -b gpt --convergence-profile strict
```

### Trend Analysis

The algorithm also tracks convergence trends:

- **Increasing**: Score rising over recent turns
- **Decreasing**: Score falling over recent turns
- **Stable**: Score relatively constant
- **Fluctuating**: Score varying without clear direction

## Manual Analysis

### Using the EventStore API

```python
from pidgin.database.event_store import EventStore

# Initialize EventStore
store = EventStore()

# Get experiment data
experiment = store.get_experiment("experiment_id")
conversations = store.get_experiment_conversations("experiment_id")

# Get turn metrics for a conversation
metrics = store.get_conversation_turn_metrics("conversation_id")

# Get messages
messages = store.get_conversation_messages("conversation_id")
```

### Direct DuckDB Queries

The database is located at `pidgin_output/experiments/experiments.duckdb`:

```python
import duckdb

conn = duckdb.connect("pidgin_output/experiments/experiments.duckdb")

# List all experiments
experiments = conn.execute("""
    SELECT experiment_id, name, status, created_at
    FROM experiments
    ORDER BY created_at DESC
""").fetchall()

# Get conversation metrics
metrics = conn.execute("""
    SELECT
        turn_number,
        agent_a_tokens,
        agent_b_tokens,
        convergence_score
    FROM turn_metrics
    WHERE conversation_id = ?
    ORDER BY turn_number
""", ["your_conversation_id"]).fetchall()

# Aggregate statistics
stats = conn.execute("""
    SELECT
        COUNT(*) as total_turns,
        AVG(convergence_score) as avg_convergence,
        SUM(agent_a_tokens + agent_b_tokens) as total_tokens
    FROM turn_metrics
    WHERE experiment_id = ?
""", ["your_experiment_id"]).fetchone()
```

### Exporting Data

```python
import pandas as pd
import duckdb

conn = duckdb.connect("pidgin_output/experiments/experiments.duckdb")

# Export to DataFrame
df = conn.execute("""
    SELECT * FROM turn_metrics
    WHERE experiment_id = ?
""", ["your_experiment_id"]).df()

# Save to CSV
df.to_csv("experiment_metrics.csv", index=False)

# Save to JSON
df.to_json("experiment_metrics.json", orient="records")
```

## JSONL Event Analysis

For real-time or streaming analysis, work directly with JSONL files:

```python
import json
from pathlib import Path

experiment_dir = Path("pidgin_output/experiments/experiment_abc123_name_date")

# Read events from JSONL
events = []
for jsonl_file in experiment_dir.glob("*_events.jsonl"):
    with open(jsonl_file) as f:
        for line in f:
            events.append(json.loads(line))

# Filter by event type
messages = [e for e in events if e.get("type") == "MessageCompleteEvent"]
thinking = [e for e in events if e.get("type") == "ThinkingCompleteEvent"]
```

## Related Documentation

- [Database](database.md) - Full database schema reference
- [Metrics](metrics.md) - Complete metrics specification
- [Extended Thinking](extended-thinking.md) - Analyzing thinking traces
