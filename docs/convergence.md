# Convergence

Convergence measures how similar the messages from two agents become over the course of a conversation. This document describes how Pidgin calculates convergence scores and the metrics involved.

## What Convergence Measures

The convergence score is a number between 0.0 and 1.0 that represents the degree of similarity between agent messages at each turn. A score of 0.0 indicates completely different messages; 1.0 indicates identical messages.

Pidgin calculates convergence from multiple independent metrics, each capturing a different aspect of textual similarity. No single metric determines the score.

## Calculation Method

### Window-Based Analysis

Rather than comparing all messages from the entire conversation, the convergence calculator uses a sliding window of recent messages (default: last 10 messages per agent). This captures recent conversation dynamics rather than overall similarity.

### Component Metrics

The overall convergence score is a weighted average of these components:

| Component | Default Weight | Calculation |
|-----------|----------------|-------------|
| Content Similarity | 0.40 | Character and word overlap between messages |
| Sentence Pattern | 0.20 | Similarity in sentence counts and structure |
| Length Similarity | 0.15 | Ratio of message lengths: `min(len_A, len_B) / max(len_A, len_B)` |
| Structure Similarity | 0.15 | Paragraph count, list usage, questions, code blocks |
| Punctuation Similarity | 0.10 | Punctuation pattern matching |

### Vocabulary Overlap

A key metric calculated separately from the weighted score:

```
vocabulary_overlap = |vocab_A ∩ vocab_B| / |vocab_A ∪ vocab_B|
```

This Jaccard similarity coefficient measures shared vocabulary. A cumulative version tracks overlap across all turns, not just the current window.

### Mimicry Score

Measures how much one agent copies phrases from the other using n-gram analysis (2-6 word sequences):

- `mimicry_a_to_b`: How much B repeats phrases from A
- `mimicry_b_to_a`: How much A repeats phrases from B
- `mutual_mimicry`: Average of both directions

### Cross-Repetition

Counts words that appear in both messages, normalized by total words. Higher values indicate more shared vocabulary in immediate message pairs.

### Structural Similarity

Compares message structure:
- Sentence counts
- Average sentence lengths
- Paragraph organization

## Convergence Profiles

Profiles adjust the component weights for different analysis needs:

### Balanced (Default)
```
content: 0.40, structure: 0.15, sentences: 0.20, length: 0.15, punctuation: 0.10
```

### Structural
Emphasizes structural patterns over content:
```
content: 0.25, structure: 0.35, sentences: 0.20, length: 0.10, punctuation: 0.10
```

### Semantic
Emphasizes content similarity:
```
content: 0.60, structure: 0.10, sentences: 0.15, length: 0.10, punctuation: 0.05
```

### Strict
Equal emphasis across all dimensions:
```
content: 0.50, structure: 0.25, sentences: 0.15, length: 0.05, punctuation: 0.05
```

## Configuration

### CLI Options

```bash
# Set convergence threshold (stop or warn when reached)
pidgin run -a claude -b gpt --convergence-threshold 0.85

# Set action when threshold reached
pidgin run -a claude -b gpt --convergence-action stop   # Stop conversation
pidgin run -a claude -b gpt --convergence-action warn   # Log warning, continue

# Select profile
pidgin run -a claude -b gpt --convergence-profile structural
```

### YAML Configuration

```yaml
experiment:
  name: convergence_test
  convergence_threshold: 0.85
  convergence_action: stop
  convergence_profile: balanced
```

### Default Values

| Setting | Default |
|---------|---------|
| Threshold | 0.80 |
| Action | warn |
| Profile | balanced |
| Window size | 10 messages per agent |

## Trend Detection

The convergence calculator tracks how the score changes over time:

- **increasing**: Score rising over recent turns
- **decreasing**: Score falling over recent turns
- **stable**: Score relatively constant
- **fluctuating**: Score varying without clear direction

## Database Storage

Convergence metrics are stored in the `turn_metrics` table:

```sql
-- Core convergence columns
convergence_score DOUBLE        -- Overall weighted score
vocabulary_overlap DOUBLE       -- Jaccard similarity
cumulative_overlap DOUBLE       -- All-turns vocabulary overlap
structural_similarity DOUBLE    -- Structure comparison
cross_repetition DOUBLE         -- Word overlap
mimicry_a_to_b DOUBLE          -- B copying A
mimicry_b_to_a DOUBLE          -- A copying B
mutual_mimicry DOUBLE          -- Average mimicry
```

### Querying Convergence Data

```python
import duckdb

conn = duckdb.connect("pidgin_output/experiments/experiments.duckdb")

# Get convergence trajectory for a conversation
trajectory = conn.execute("""
    SELECT
        turn_number,
        convergence_score,
        vocabulary_overlap,
        mutual_mimicry
    FROM turn_metrics
    WHERE conversation_id = ?
    ORDER BY turn_number
""", ["your_conversation_id"]).fetchall()

# Find conversations with high final convergence
high_convergence = conn.execute("""
    SELECT
        conversation_id,
        MAX(convergence_score) as peak_convergence,
        MAX(turn_number) as final_turn
    FROM turn_metrics
    GROUP BY conversation_id
    HAVING MAX(convergence_score) > 0.8
""").fetchall()
```

## Events

The `TurnCompleteEvent` includes the convergence score:

```python
@dataclass
class TurnCompleteEvent(Event):
    conversation_id: str
    turn_number: int
    turn: Turn
    convergence_score: Optional[float] = None
```

## Limitations

The convergence score has known limitations:

- **Surface-level**: Measures textual similarity, not semantic meaning
- **Language-dependent**: Optimized for English text
- **Window sensitivity**: Results vary with window size
- **No causation**: High convergence does not imply coordination

Placeholder metrics for semantic similarity and sentiment convergence exist in the schema but are not calculated by Pidgin. These require external NLP libraries and can be computed post-hoc using the stored message text.

## Related Documentation

- [Metrics Reference](metrics.md) - Complete list of all metrics
- [Analysis & Notebooks](analysis.md) - Auto-generated analysis tools
- [Database Schema](database.md) - Full database structure
