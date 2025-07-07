# TODO.md Audit Results

## Items Already Completed But Not Marked as Done

### 1. Long Methods - Actually Already Refactored ✅
- **conductor.run_conversation()** - Listed as 142 lines, actually only **58 lines** now (refactored into helper methods)
- **message_handler.get_agent_message()** - Listed as 152 lines, actually only **34 lines** now (refactored into helper methods)
- **experiment_runner._run_single_conversation()** - Listed as 134 lines, actually **120 lines** (still needs refactoring)
- **event_store.import_experiment()** - Method doesn't exist anymore, replaced by `import_experiment_from_jsonl` in ImportService

### 2. Code Duplication - Partially Complete ✅
- **Extract provider base functionality**
  - ✅ Error handling - Created `error_utils.py` with `ProviderErrorHandler` class
  - ✅ Context truncation - Created `context_utils.py` with `apply_context_truncation` function
  - ❌ Update providers to use new error_utils module - Actually ALL providers ARE using it!
    - anthropic.py: `self.error_handler = create_anthropic_error_handler()` (line 105)
    - All providers import and use the error handler

### 3. Resource Management Issues
- ✅ **JSONL file handle leaks** - Already fixed! EventBus has proper file handle management:
  - `close_conversation_log()` method to close individual conversation logs
  - `stop()` method closes all file handles
  - Thread-safe with `_jsonl_lock`
  - Files opened with line buffering for safety

### 4. Database Issues
- ⚠️ **Fix race condition in event sequences** - Issue still exists in `event_repository.py` lines 32-37
  - The sequence generation is not atomic with the INSERT
- ❌ **Fix database connection leaks (async_duckdb.py)** - File doesn't exist, might be outdated reference

## Items That Need TODO.md Updates

### Mark as [x] DONE:
1. **Long Methods**
   - `conductor.run_conversation()` - Already refactored to 58 lines
   - `message_handler.get_agent_message()` - Already refactored to 34 lines
   
2. **Code Duplication**
   - Extract provider base functionality - Context truncation ✅
   - Update providers to use new error_utils module ✅

3. **Resource Management**
   - JSONL file handle leaks (event_bus.py) ✅

### Remove or Update:
1. **event_store.import_experiment()** - Method no longer exists
2. **Fix database connection leaks (async_duckdb.py)** - File doesn't exist

### Still TODO:
1. **experiment_runner._run_single_conversation()** - Still 120 lines (close to limit but could be refactored)
2. **Fix race condition in event sequences** - Still exists in event_repository.py

## Summary

Many items marked as TODO in the TODO.md file have already been completed:
- 2 out of 4 "Long Methods" have been refactored
- Provider error handling and context truncation have been extracted and ALL providers are using them
- JSONL file handle management is properly implemented
- Several references are outdated (methods/files that no longer exist)

The TODO.md file needs significant updates to reflect the current state of the codebase.