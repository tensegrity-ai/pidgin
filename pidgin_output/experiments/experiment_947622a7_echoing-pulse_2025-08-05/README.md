# Experiment: echoing-pulse

**ID**: `experiment_947622a7`  
**Started**: 2025-08-05 23:04:16 UTC  
**Completed**: In progress  
**Status**: Post_Processing

## Configuration

**Agents**:
- Agent A: `unknown`
- Agent B: `unknown`

**Parameters**:
- Max turns: 0
- Temperature A: default
- Temperature B: default
- Initial prompt: "Not specified"

## Results Summary

**Conversations**: 1 of 1 completed  
**Total turns**: 0 (avg: 0.0 per conversation)  

## Conversations

1. `conv_d19b3cd3` - 0 turns ✓

## Files

- `manifest.json` - Complete experiment metadata
- `conv_*.jsonl` - Raw event streams for each conversation
- `.imported` - Indicates data has been imported to DuckDB (if present)

## Quick Analysis

```bash
# View manifest
cat manifest.json | jq .

# Search for specific events
grep "MessageCompleteEvent" conv_*.jsonl | jq .content

# Import to database (if not already done)
pidgin import experiment_947622a7
```