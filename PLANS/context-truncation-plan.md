# Context Truncation Reform Plan

## Problem Statement

The current context management approach corrupts research data by:
- Truncating messages mid-conversation when context limits are approached
- Using conservative limits (80% of actual model limits)
- Using provider-level defaults instead of model-specific context windows
- Creating artificial conversation continuations that break self-attention patterns

## Research Impact

Context truncation fundamentally alters conversations:
1. **Broken self-attention**: Models can't refer back to earlier context
2. **Artificial amnesia**: Conversations become incoherent as models lose track
3. **Skewed patterns**: Convergence/divergence patterns become meaningless
4. **False continuity**: Conversations appear continuous but are actually fragmented

## Proposed Solution

### 1. Use Model-Specific Context Windows

Update `ProviderContextManager` to:
- Import `get_model_config` from `pidgin.config.models`
- Look up actual model context window from ModelConfig
- Remove provider-level CONTEXT_LIMITS (keep only as ultimate fallback)
- Remove conservative 80% reduction - use full context windows

### 2. Disable Truncation by Default

Add `allow_truncation` parameter to context manager:
- Default: `False` (no truncation)
- When `False` and context exceeds limit:
  - Log warning about approaching/exceeding context limit
  - Return all messages unchanged
  - Let provider API return context limit error
- When `True`: Use current truncation logic (for backwards compatibility)

### 3. Add CLI Flag for Optional Truncation

Add `--allow-truncation` flag to run command:
```bash
pidgin run -a claude -b gpt-4 --allow-truncation  # Allows truncation
pidgin run -a claude -b gpt-4                      # No truncation (default)
```

### 4. Handle Context Limit Errors Gracefully

When provider APIs return context limit errors:
- Catch the specific error from each provider
- Mark conversation as completed with status: "context_limit_reached"
- Log clearly that conversation ended due to context limits
- This provides natural conversation endpoints for research

## Implementation Details

### Files to Modify

1. `pidgin/providers/context_manager.py`:
   - Add model config lookup
   - Add allow_truncation parameter
   - Update prepare_context method

2. `pidgin/cli/run.py`:
   - Add --allow-truncation flag
   - Pass flag through to providers

3. `pidgin/providers/*.py` (all provider implementations):
   - Pass allow_truncation to context manager
   - Handle context limit errors appropriately

4. `pidgin/core/conversation_lifecycle.py`:
   - Add "context_limit_reached" as completion reason

### Backwards Compatibility

- Existing code continues to work (truncation available via flag)
- Default behavior changes to preserve research integrity
- Clear documentation about the change

## Benefits

1. **Research Integrity**: Natural conversation flow preserved
2. **Clear Boundaries**: Conversations end cleanly at context limits
3. **Reproducibility**: No hidden alterations to conversation flow
4. **Transparency**: Researchers see actual model limitations
5. **Optional Override**: Truncation still available when explicitly requested

## Migration Notes

Users who rely on truncation behavior should:
- Add `--allow-truncation` flag to maintain current behavior
- Consider whether truncation is actually needed for their use case
- Be aware that truncated conversations may not be suitable for research