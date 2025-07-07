# Recent Architecture Changes

## July 7, 2025 Updates

### Provider Refactoring

#### Context Utilities Extraction
- Created `pidgin/providers/context_utils.py` to centralize context truncation logic
- Eliminated code duplication across 5 providers (Anthropic, OpenAI, Google, xAI, Ollama)
- All providers now use unified context management with proper logging

#### Error Handling Improvements  
- Created `pidgin/providers/error_utils.py` with `ProviderErrorHandler` class
- Provides consistent error mapping and traceback suppression across providers
- Each provider now has customized error messages while sharing base functionality
- 100% test coverage on error handling utilities

### Import Service Refactoring

#### Event Replay Architecture
- Created `pidgin/io/event_deserializer.py` for converting JSON events back to dataclasses
- Created `pidgin/database/event_replay.py` for replaying events to reconstruct conversation state
- ImportService reduced from 451 to 386 lines by using event replay pattern
- Eliminated duplicate JSONL parsing code across the codebase

#### Metrics Calculation
- Discovered that only convergence metrics were calculated during live conversations
- Removed dead ExperimentEventHandler code (406 lines)
- Implemented full metrics calculation (all ~150 metrics) during import phase
- Updated database schema to store all metrics as columns instead of JSON

### Test Suite Improvements
- Fixed async mock warnings in test_conductor.py
- Properly configured Mock vs AsyncMock usage to avoid coroutine warnings
- All 290 unit tests now pass cleanly without warnings

## Architecture Benefits

1. **Cleaner Provider Code**: Each provider is now focused on its unique API interaction, with shared utilities handling common patterns

2. **Maintainable Import Process**: Event replay pattern makes the import process more understandable and testable

3. **Complete Metrics**: All promised metrics are now actually calculated and stored

4. **Better Error Messages**: Users get provider-specific, helpful error messages instead of raw API errors

## Next Steps

Remaining TODO items from refactoring:
- Port/restore repository tests (medium priority)
- Add memory management for JSONL and messages (medium priority)