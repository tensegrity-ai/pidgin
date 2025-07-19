# Remove Chats Database Plan

## Problem Statement

The codebase has an unexpected second database (`chats.duckdb`) in `~/.pidgin/` that appears to be used for branching/chat operations. This violates core principles:

1. **JSONL is the source of truth** - we shouldn't need databases for core operations
2. **Database is only for post-experiment analysis** - not for runtime functionality
3. **Confusing architecture** - two databases with unclear purposes
4. **Potential bugs** - may be creating databases at unexpected times

## Current Situation

### Two Databases Exist:
1. `pidgin_output/experiments/experiments.duckdb` - Main analysis database (correct)
2. `~/.pidgin/chats.duckdb` - Mystery chat database (incorrect)

### Code Involved:
- `conductor.py` has `_load_chat_data()` that imports JSONL to chats database
- `paths.py` defines `get_chats_database_path()` pointing to `~/.pidgin/chats.duckdb`
- EventStore is being called from conductor for branching operations

## Investigation Needed

1. **Find all uses of chats database**:
   - Where is `get_chats_database_path()` called?
   - Where is `_load_chat_data()` called?
   - What functionality depends on this database?

2. **Understand branching flow**:
   - How does branching currently work?
   - Does it actually use the chats database?
   - Can we branch directly from JSONL?

3. **Check for side effects**:
   - Will removing this break branching?
   - Are there any other features using this database?

## Proposed Solution

### 1. Remove Chats Database Infrastructure
- Delete `get_chats_database_path()` from paths.py
- Remove `_load_chat_data()` from conductor.py
- Remove any EventStore imports from conductor.py

### 2. Fix Branching to Use JSONL Directly
- Read conversation history from JSONL files
- No database needed for branching
- Keep it simple and true to architecture

### 3. Clean Up Code
- Remove any other references to chats database
- Ensure conductor doesn't create any databases
- Update tests if needed

## Implementation Steps

1. **Audit Phase**:
   ```bash
   # Find all references
   grep -r "chats.duckdb" .
   grep -r "get_chats_database_path" .
   grep -r "_load_chat_data" .
   ```

2. **Test Current Branching**:
   - Run branching with current code
   - Document exact behavior
   - Verify what actually uses the database

3. **Implement JSONL-based Branching**:
   - Read messages directly from JSONL
   - No database operations in conductor
   - Test thoroughly

4. **Remove Database Code**:
   - Delete database-related methods
   - Clean up imports
   - Update documentation

## Benefits

1. **Simpler Architecture**: One database for analysis only
2. **Clearer Mental Model**: JSONL → Experiments → Database → Analysis
3. **Fewer Bugs**: No unexpected database creation
4. **Better Performance**: No unnecessary database operations during branching

## Risks

1. **Breaking Branching**: Need to ensure branching still works
2. **Hidden Dependencies**: Other code might expect this database
3. **User Data**: Existing users might have chats.duckdb files

## Migration

- Add cleanup code to remove old `~/.pidgin/chats.duckdb` files
- Document the change in release notes
- Provide clear error messages if old code paths are hit