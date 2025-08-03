# Architectural Review & Compliance Audit

Date: 2025-07-24

## Executive Summary

This review assessed Pidgin's codebase against the core architectural principles defined in CLAUDE.md. While the architecture is generally well-implemented, several violations were found that should be addressed to maintain code quality and architectural integrity.

### Overall Assessment
- **Event-Driven Architecture**: ✅ Good (minor violations)
- **Provider Agnostic**: ⚠️ Fair (several violations)
- **JSONL-First Data Flow**: ✅ Excellent (fully compliant)
- **Module Size**: ⚠️ Poor (3 modules >200 lines)
- **Single Responsibility**: ⚠️ Fair (major violations in CLI)

## Detailed Findings

### 1. Event-Driven Architecture

**Status**: Good with minor violations

**Strengths**:
- All major state changes emit events
- Components communicate through EventBus
- Complete audit trail in JSONL files
- No direct coupling between core components

**Violations Found**:
1. **Direct State Manipulation in TurnExecutor** *(Acknowledged - see note)*:
   - Lines 112, 125, 189, 209: Direct `conversation.messages.append()`
   - **Note**: After review, these direct appends are intentional and acceptable because:
     - MessageCompleteEvent is already emitted by message_handler
     - Appends only maintain runtime conversation state
     - JSONL events remain the authoritative source of truth
     - Appends are necessary for agents to see full conversation context
   - Added clarifying comments in code (2025-08-03)

2. **NameCoordinator State Changes**:
   - Directly modifies agent display names without events
   - Should emit `NameAssignedEvent`

3. **Monitor Component Internal State**:
   - Tracks `self.truncation_occurred` directly
   - Minor issue, acceptable for display components

**Recommendation**: Create NameAssignedEvent for name changes. Message appends are acceptable as documented.

### 2. Provider Agnostic Principle

**Status**: Fair with several violations

**Strengths**:
- Clean Provider abstract base class
- No direct provider imports in core
- EventAwareProvider wrapper pattern
- Configuration-based provider selection

**Violations Found**:
1. **MessageHandler** (`message_handler.py`):
   - Hardcoded token estimation: "Rough approximation - Claude tends to use fewer tokens"
   - Provider-specific logic should be in provider configuration

2. **NameCoordinator** (`name_coordinator.py`):
   - Pattern matching on model names to detect providers
   - Should use model configuration exclusively

3. **RateLimiter** (`rate_limiter.py`):
   - Hardcoded rate limits per provider
   - Should be configuration-driven or provider-supplied

**Recommendation**: Create `ProviderCapabilities` interface for metadata.

### 3. JSONL-First Data Flow

**Status**: Excellent - Fully Compliant ✅

**Confirmed**:
- All events written to JSONL files
- JSONL files are append-only (no locking)
- manifest.json tracks progress with atomic writes
- DuckDB only used for post-experiment analysis
- State reconstructed from JSONL when needed
- No hidden state outside JSONL

**Architecture Verified**:
```
Events → EventBus → JSONL files → manifest.json → [Post-experiment] → DuckDB
```

### 4. Module Size (<200 lines)

**Status**: Poor - Major violations

**Violations**:
1. **cli/run.py**: 863 lines (331% over limit)
2. **experiments/runner.py**: 646 lines (223% over limit)
3. **core/conductor.py**: 373 lines (87% over limit)

**Near Violations**:
- **core/event_bus.py**: 332 lines
- **database/event_store.py**: 340 lines
- **cli/branch.py**: 392 lines

### 5. Single Responsibility Principle

**Status**: Fair with major violations in CLI

**Major Violations**:

1. **cli/run.py** - Multiple responsibilities:
   - Command-line parsing
   - Interactive model selection UI
   - YAML spec handling
   - Experiment orchestration
   - Display management
   - API key validation

2. **experiments/runner.py** - Mixed concerns:
   - Experiment execution
   - Parallel task management
   - Agent/provider creation
   - Post-processing (README, notebooks, database import)

3. **cli/branch.py** - Similar to run.py

**Good Examples**:
- **providers/builder.py**: Single purpose (52 lines)
- **ui/chat_display.py**: Focused on display (320 lines)

## Recommended Actions

### Priority 1 - Critical
1. **Refactor cli/run.py**:
   - Extract model selection → `model_selector.py`
   - Extract spec handling → `spec_loader.py`
   - Extract orchestration → `run_orchestrator.py`

2. **Fix Provider Abstraction**:
   - Move hardcoded limits to configuration
   - Create provider capabilities interface
   - Remove provider detection patterns

### Priority 2 - Important
1. **Extract Post-Processing**:
   - Move from runner.py → `post_processor.py`
   - Separate agent creation → `agent_factory.py`

2. **Add Missing Events**:
   - Implement `MessageAddedEvent`
   - Implement `NameAssignedEvent`
   - Update components to emit these events

### Priority 3 - Nice to Have
1. **Extract Serialization**:
   - Move from event_bus.py → `event_serializer.py`

2. **Refactor branch.py**:
   - Similar pattern to run.py refactoring

## Positive Findings

1. **JSONL architecture is perfectly implemented**
2. **Event-driven pattern is well-established**
3. **Provider abstraction exists and works**
4. **No database coupling during experiments**
5. **Clean separation between experiment and analysis**

## Conclusion

Pidgin's architecture is fundamentally sound with good adherence to core principles. The violations found are primarily in peripheral areas (CLI commands) and can be addressed without major architectural changes. The core event-driven, JSONL-first architecture is working as designed.

The main concern is code organization in CLI modules, which have accumulated too many responsibilities. These should be refactored to maintain the architectural principle of small, focused modules with single responsibilities.