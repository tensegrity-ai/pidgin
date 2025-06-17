# Experiments Guide

## Overview

The experiments system enables running hundreds of AI conversations in parallel for statistical analysis. Experiments run as background daemons and capture ~150 metrics per conversation turn.

## Basic Usage

### Starting an Experiment

```bash
# Basic experiment
pidgin experiment start -a claude -b gpt -r 50

# With all options
pidgin experiment start \
  -a claude \                    # Agent A model
  -b gpt \                       # Agent B model  
  -r 100 \                       # Repetitions
  -t 50 \                        # Max turns per conversation
  -p "Let's discuss physics" \   # Initial prompt
  --name "physics_discussion" \  # Experiment name
  --max-parallel 8 \             # Override parallelism
  --foreground                   # Run in foreground (debugging)
```

### Monitoring Experiments

```bash
# List all experiments
pidgin experiment status

# View logs
pidgin experiment logs <experiment_id>

# Follow logs in real-time (like tail -f)
pidgin experiment logs <experiment_id> -f

# Stop an experiment
pidgin experiment stop <experiment_id>
```

## Captured Metrics

Each conversation turn captures ~150 metrics including:

### Basic Metrics
- Message length, word count, sentence count
- Type-token ratio (vocabulary richness)
- Vocabulary size and hapax legomena

### Convergence Metrics
- Overall convergence score
- Vocabulary overlap (Jaccard similarity)
- Structural similarity
- Length ratios

### Linguistic Patterns
- Hedge words (maybe, perhaps, possibly)
- Agreement markers (yes, indeed, exactly)
- Disagreement markers (no, however, but)
- Politeness markers (please, thank you)

### Symbol Usage
- Emoji count and density
- Arrow symbols (→ ← ↔)
- Mathematical symbols (≈ ≡ ∞)
- Other special characters

### Advanced Metrics
- Shannon entropy (information content)
- Pronoun usage patterns
- Cross-agent repetition
- Self-repetition scores

## Database Schema

All data is stored in SQLite at `./pidgin_output/experiments/experiments.db`

Key tables:
- `experiments` - Experiment metadata
- `conversations` - Individual conversation configs
- `turns` - All metrics for each turn
- `word_frequencies` - Word usage tracking
- `agent_names` - Self-chosen names if enabled

## Analyzing Results

```sql
-- Average convergence by turn
SELECT 
  turn_number,
  AVG(convergence_score) as avg_convergence,
  COUNT(*) as sample_size
FROM turns
GROUP BY turn_number
ORDER BY turn_number;

-- Model comparison
SELECT 
  c.agent_a_model,
  c.agent_b_model,
  AVG(t.convergence_score) as avg_convergence
FROM conversations c
JOIN turns t ON c.conversation_id = t.conversation_id
WHERE t.turn_number > 20
GROUP BY c.agent_a_model, c.agent_b_model;

-- Name choices by model
SELECT 
  chosen_name,
  COUNT(*) as frequency
FROM agent_names
WHERE agent_id = 'agent_a'
GROUP BY chosen_name
ORDER BY frequency DESC;
```

## Rate Limits

The system automatically manages rate limits:
- Anthropic: 5 parallel conversations
- OpenAI: 8 parallel conversations  
- Google: 5 parallel conversations
- xAI: 5 parallel conversations

For mixed-provider experiments, defaults to 3 parallel conversations.

## Tips

1. **Start small**: Test with 5-10 conversations before running hundreds
2. **Monitor logs**: Use `-f` flag to watch progress in real-time
3. **Check costs**: Use cheap models (haiku, gpt-4o-mini) for large experiments
4. **Background execution**: Experiments continue even if you disconnect
5. **Graceful shutdown**: Use `stop` command for clean termination

## Common Issues

### Experiment won't start
- Check API keys are set
- Verify models are valid (use `pidgin models`)
- Check logs: `./pidgin_output/experiments/logs/<experiment_id>.log`

### Conversations failing
- Usually rate limit issues - reduce parallelism with `--max-parallel`
- Check individual conversation logs for specific errors

### Database queries
- Use `.mode column` and `.headers on` in sqlite3 for readable output
- Export to CSV: `.mode csv` then `.output results.csv`