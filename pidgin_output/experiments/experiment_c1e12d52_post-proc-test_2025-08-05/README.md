# Experiment: post-proc-test

**ID**: `experiment_c1e12d52`  
**Started**: 2025-08-05 19:38:34 UTC  
**Completed**: 2025-08-05 19:38:51 UTC  
**Duration**: 17s  
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

1. `conv_cbb3037b` - 0 turns ✓

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
pidgin import experiment_c1e12d52
```