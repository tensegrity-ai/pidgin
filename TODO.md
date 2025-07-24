# TODO: Final Development Push

This document tracks remaining tasks before the Pidgin release.

## Urgent - Breaking Issues

### 0. Fix OpenAI O-series Parameter Change
**Goal**: Fix breaking API change for O-series models

- [x] OpenAI deprecated `max_tokens` in favor of `max_completion_tokens` for all models
- [x] Updated openai.py to use `max_completion_tokens` universally
- [x] Test with O-series models to confirm fix (user confirmed it works)

## High Priority - Core Functionality

### 1. Context Management Reform ✅ COMPLETED
**Goal**: Preserve research integrity by eliminating artificial message truncation

See detailed plan: [PLANS/context-truncation-plan.md](PLANS/context-truncation-plan.md)

- [x] Update context manager to use model-specific limits
- [x] Disable truncation by default
- [x] Add `--allow-truncation` CLI flag  
- [x] Handle context limit errors as natural conversation endpoints
- [x] Update documentation about the change

### 2. Model Update Monitoring ✅ COMPLETED
**Goal**: Stay informed about new frontier models without breaking curation

- [x] Create `scripts/check_model_updates.py` that:
  - [x] Maintains a static list of known models (since we can't query APIs without keys)
  - [x] Compares against our curated list
  - [x] Identifies new models not in our config
  - [x] Check PyPI for SDK updates (anthropic, openai, google-generativeai)
  - [x] Compare against versions in pyproject.toml
  - [x] Generates comprehensive change report:
    - [x] **Known models not configured**: Models we know exist but haven't added
    - [x] **Configured models not in known list**: May need to update known list
    - [x] **SDK Updates**: Shows version changes
- [x] Add GitHub issue creation:
  - [x] Create issue for any changes detected
  - [x] Use clear sections with appropriate formatting
  - [x] For SDK updates, show: "anthropic: 0.25.0 → 0.59.0"
  - [x] Include recommendations
- [x] Add GitHub Actions workflow (`.github/workflows/check-models.yml`):
  - [x] Run weekly on schedule (Mondays at 9 AM UTC)
  - [x] Execute model update check script
  - [x] Create issue only if changes found
  - [x] Prevent duplicate issues
- [x] Document update process for maintainers in scripts/README.md

Note: Simplified approach - no API calls needed, just PyPI checks and static known models list

### 3. Remove Chats Database ✅ COMPLETED
**Goal**: Eliminate unexpected second database that violates architecture principles

See detailed plan: [PLANS/remove-chats-database.md](PLANS/remove-chats-database.md)

- [x] Investigate current usage of chats.duckdb
- [x] Verify branching can work with JSONL only (already does!)
- [x] Remove get_chats_database_path() from paths.py
- [x] Remove _batch_load_chat_to_database() from conductor.py
- [x] Remove EventStore usage from conductor
- [x] Update tests to reflect removal
- [x] Add migration to clean up old chats.duckdb files

### 4. Streaming Connection Error Recovery ✅ COMPLETED
**Goal**: Handle network interruptions gracefully without terminating conversations

- [x] Fix chunked read connection errors:
  - [x] Make "incomplete chunked read" errors retryable
  - [x] Implement exponential backoff for streaming failures
  - [x] Save partial responses before retrying
  - [x] Add connection health checks during streaming
- [x] Improve error classification:
  - [x] Review which errors are marked non-retryable
  - [x] Network errors should generally be retryable
  - [x] Only mark true API errors (auth, invalid request) as non-retryable
- [x] Add graceful degradation:
  - [x] On repeated streaming failures, try non-streaming request
  - [x] Allow continuation from last successful turn
  - [x] Clear error messaging about what happened
- [x] Better timeout handling:
  - [x] 60 second timeout might be too long for UX
  - [x] Consider shorter timeout with more retry attempts

**Changes made**:
- Added streaming error patterns to `is_retryable_error()` in retry_utils.py
- Added friendly error messages for streaming failures in error_utils.py
- Updated event_wrapper to use comprehensive error classification
- Refactored all providers (Anthropic, OpenAI, Google, XAI) to use common retry wrapper
- Added fallback support to retry_with_exponential_backoff
- Reduced timeout from 5 minutes to 2 minutes in event_wrapper
- Created comprehensive tests for streaming error handling

## Medium Priority - Quality of Life

### 3. Architectural Review & Compliance Audit ✅ COMPLETED
**Goal**: Ensure recent features haven't violated core architectural principles

- [x] Review all recent features against core principles:
  - [x] Event-driven architecture - Are all state changes going through events?
  - [x] Provider agnostic - Does conductor remain unaware of provider types?
  - [x] JSONL-first data flow - Is JSONL still the single source of truth?
  - [x] Module size (<200 lines) - Have any modules grown too large?
  - [x] Single responsibility - Does each module maintain clear boundaries?
- [x] Check for architectural violations:
  - [x] Direct database writes bypassing events
  - [x] Components with multiple responsibilities
  - [x] Hidden state or coupling between components
  - [x] Features that add interpretation vs observation
- [x] Document any violations found
- [x] Create issues to fix architectural drift

**Results**: See [ARCHITECTURAL_REVIEW.md](ARCHITECTURAL_REVIEW.md) for detailed findings.

**Summary**:
- ✅ JSONL-first architecture: Perfectly implemented
- ✅ Event-driven: Good with minor violations (direct message appends)
- ⚠️ Provider agnostic: Fair with violations (hardcoded limits, provider detection)
- ⚠️ Module size: 3 modules exceed 200 lines (run.py: 863, runner.py: 646, conductor.py: 373)
- ⚠️ Single responsibility: Major violations in CLI modules

### 4. Output Directory Organization
- [ ] Fix empty human-readable experiment directories (already fixed, needs testing)
- [ ] Consider flattening structure (single experiment directory)

### 5. ~~Post-Processing Pipeline Issues~~ ✅ COMPLETED
**Goal**: Fix display runner exit and ensure correct post-processing sequence

**Fixed**: Implemented proper event-driven post-processing flow with new events and status

### 6. Error Handling & Logging
- [x] Rename misleading log files (startup_error.log → startup.log) (already fixed)
- [x] Improve error messages for common issues (API keys, rate limits)
- [x] Handle experiment name collisions gracefully:
  - [x] When auto-generated names collide, retry with a new random name
  - [x] Currently fails with ugly error when name already exists
  - [x] Should be simple retry loop in name generation
- [x] Simplify process names:
  - [x] Current implementation is overly complex
  - [x] Just use simple names: `pidgin-exp`, `pidgin-monitor`, `pidgin-tail`, `pidgin-chat`
  - [x] Remove the complex name generation with experiment IDs

## Low Priority - Nice to Have

### 7. Display Improvements
- [x] Rename "verbose" display to "chat" display throughout:
  - [x] No CLI flag - it runs by default and there is no reattach mechanism
  - [x] Internal naming: VerboseDisplay → ChatDisplay
  - [x] Documentation updates

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
- [x] Improve monitor error display to show useful details
- [x] Fix pipx installation daemon startup race condition
- [x] Implement proper event-driven post-processing flow
- [x] Add model reference documentation