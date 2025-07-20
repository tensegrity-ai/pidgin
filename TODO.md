# TODO: Final Development Push

This document tracks remaining tasks before the Pidgin release.

## Urgent - Breaking Issues

### 0. Fix OpenAI O-series Parameter Change
**Goal**: Fix breaking API change for O-series models

- [x] OpenAI deprecated `max_tokens` in favor of `max_completion_tokens` for all models
- [x] Updated openai.py to use `max_completion_tokens` universally
- [x] Test with O-series models to confirm fix (user confirmed it works)

## High Priority - Core Functionality

### 1. Context Management Reform
**Goal**: Preserve research integrity by eliminating artificial message truncation

See detailed plan: [PLANS/context-truncation-plan.md](PLANS/context-truncation-plan.md)

- [ ] Update context manager to use model-specific limits
- [ ] Disable truncation by default
- [ ] Add `--allow-truncation` CLI flag  
- [ ] Handle context limit errors as natural conversation endpoints
- [ ] Update documentation about the change

### 2. Model Update Monitoring
**Goal**: Stay informed about new frontier models without breaking curation

- [ ] Create `scripts/check_model_updates.py` that:
  - [ ] Queries model endpoints for Anthropic, OpenAI, Google, xAI
  - [ ] Compares against our curated list
  - [ ] Identifies new models not in our config
  - [ ] Check PyPI for SDK updates (anthropic, openai, google-generativeai)
  - [ ] Compare against versions in pyproject.toml
  - [ ] Filters out non-conversational models:
    - [ ] Skip image-only models (DALL-E, Stable Diffusion, etc.)
    - [ ] Skip audio-only models (Whisper, TTS, etc.)
    - [ ] Skip embedding models
    - [ ] Keep text and multimodal models that support chat
  - [ ] Generates comprehensive change report:
    - [ ] **New models**: Not in our config but available via API
    - [ ] **Removed models**: In our config but no longer available
    - [ ] **Updated models**: Metadata changes (context window, pricing, etc.)
  - [ ] Track model metadata changes:
    - [ ] Context window expansions
    - [ ] Pricing tier changes
    - [ ] Deprecation warnings
    - [ ] Model family updates (e.g., "replaced by X")
- [ ] Add GitHub issue creation:
  - [ ] Create issue for any changes detected
  - [ ] Use clear sections: "New Models", "Removed Models", "Updated Models", "SDK Updates"
  - [ ] Include before/after for metadata changes
  - [ ] For SDK updates, show: "anthropic: 0.52.2 → 0.53.0"
  - [ ] Tag appropriately: "new-model", "deprecated-model", "model-update", "sdk-update"
  - [ ] Include recommendation (add/remove/update)
- [ ] Add GitHub Actions workflow (`.github/workflows/check-models.yml`):
  - [ ] Run weekly/monthly on schedule
  - [ ] Execute model update check script
  - [ ] Create issue only if new models found
  - [ ] Include diff of changes in issue body
  - [ ] Optional: Send notification to maintainers
- [ ] Add `pidgin models --check-updates` command:
  - [ ] Shows which configured models are available
  - [ ] Highlights any deprecated models
  - [ ] Suggests running update check script
- [ ] Keep Ollama models manually curated (too unstable for auto-discovery)
- [ ] Document update process for maintainers

### 3. Remove Chats Database
**Goal**: Eliminate unexpected second database that violates architecture principles

See detailed plan: [PLANS/remove-chats-database.md](PLANS/remove-chats-database.md)

- [ ] Investigate current usage of chats.duckdb
- [ ] Verify branching can work with JSONL only
- [ ] Remove get_chats_database_path() from paths.py
- [ ] Remove _load_chat_data() from conductor.py
- [ ] Remove EventStore usage from conductor
- [ ] Test branching still works correctly
- [ ] Add migration to clean up old chats.duckdb files

### 4. Streaming Connection Error Recovery
**Goal**: Handle network interruptions gracefully without terminating conversations

- [ ] Fix chunked read connection errors:
  - [ ] Make "incomplete chunked read" errors retryable
  - [ ] Implement exponential backoff for streaming failures
  - [ ] Save partial responses before retrying
  - [ ] Add connection health checks during streaming
- [ ] Improve error classification:
  - [ ] Review which errors are marked non-retryable
  - [ ] Network errors should generally be retryable
  - [ ] Only mark true API errors (auth, invalid request) as non-retryable
- [ ] Add graceful degradation:
  - [ ] On repeated streaming failures, try non-streaming request
  - [ ] Allow continuation from last successful turn
  - [ ] Clear error messaging about what happened
- [ ] Better timeout handling:
  - [ ] 60 second timeout might be too long for UX
  - [ ] Consider shorter timeout with more retry attempts

## Medium Priority - Quality of Life

### 3. Architectural Review & Compliance Audit
**Goal**: Ensure recent features haven't violated core architectural principles

- [ ] Review all recent features against core principles:
  - [ ] Event-driven architecture - Are all state changes going through events?
  - [ ] Provider agnostic - Does conductor remain unaware of provider types?
  - [ ] JSONL-first data flow - Is JSONL still the single source of truth?
  - [ ] Module size (<200 lines) - Have any modules grown too large?
  - [ ] Single responsibility - Does each module maintain clear boundaries?
- [ ] Check for architectural violations:
  - [ ] Direct database writes bypassing events
  - [ ] Components with multiple responsibilities
  - [ ] Hidden state or coupling between components
  - [ ] Features that add interpretation vs observation
- [ ] Document any violations found
- [ ] Create issues to fix architectural drift

### 4. Output Directory Organization
- [ ] Fix empty human-readable experiment directories (already fixed, needs testing)
- [ ] Consider flattening structure (single experiment directory)

### 5. ~~Post-Processing Pipeline Issues~~ ✅ COMPLETED
**Goal**: Fix display runner exit and ensure correct post-processing sequence

**Fixed**: Implemented proper event-driven post-processing flow with new events and status

### 6. Error Handling & Logging
- [ ] Rename misleading log files (startup_error.log → startup.log) (already fixed)
- [ ] Improve error messages for common issues (API keys, rate limits)
- [ ] Handle experiment name collisions gracefully:
  - [ ] When auto-generated names collide, retry with a new random name
  - [ ] Currently fails with ugly error when name already exists
  - [ ] Should be simple retry loop in name generation
- [ ] Simplify process names:
  - [ ] Current implementation is overly complex
  - [ ] Just use simple names: `pidgin-exp`, `pidgin-monitor`, `pidgin-tail`, `pidgin-chat`
  - [ ] Remove the complex name generation with experiment IDs

## Low Priority - Nice to Have

### 7. Display Improvements
- [ ] Rename "verbose" display to "chat" display throughout:
  - [ ] CLI flag: `--verbose` → `--chat` (keep --verbose as alias)
  - [ ] Internal naming: VerboseDisplay → ChatDisplay
  - [ ] Documentation updates
- [ ] Show model names instead of "Agent A/B":
  - [ ] Read model info from manifest or events
  - [ ] Use shortname (e.g., "Claude 3 Opus", "GPT-4")
  - [ ] Format: "[Model Name] thinks..." instead of "Agent A thinks..."

### 8. Documentation Updates
- [ ] Update examples to reflect best practices
- [ ] Add troubleshooting guide for common issues
- [ ] Document context limit behavior

### 9. Testing & Validation
- [ ] Add tests for context limit handling
- [ ] Verify all providers handle errors consistently
- [ ] Test migration path for existing users

## Notes

- Focus on research integrity over engineering convenience
- Avoid adding features that could skew research data
- Keep changes minimal and well-documented
- Test thoroughly with real conversations

## Completed
- [x] Consolidate development tools into Poetry scripts
- [x] Fix experiment directory naming mismatch
- [x] Remove inline TODO about token extraction
- [x] Fix daemon startup with setproctitle (made it required dependency)
- [x] Add meaningful process names for better debugging
- [x] Fix pipx installation daemon startup race condition
- [x] Implement proper event-driven post-processing flow
- [x] Add model reference documentation