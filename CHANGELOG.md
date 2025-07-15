# Changelog

All notable changes to Pidgin will be documented in this file.

## [0.1.0] - 2025-07-15 (Pre-release)

### Added
- **Wide-table metrics schema** with 150+ columns for optimal DuckDB performance
- **Auto-generated Jupyter notebooks** for each experiment
- **Man pages** for all commands (Section 1, 5, and 7)
- **API documentation** with examples and docstrings
- **System-wide monitor** command with live dashboard
- **Branch command** for exploring alternate conversation paths
- **Stop command** for graceful experiment termination
- **Support for 20+ models** including local models via Ollama

### Changed
- **Metrics overhaul**: Removed MetricsCalculatedEvent, calculate only convergence live
- **Database schema**: New `conversation_turns` wide table replaces normalized schema
- **Import service**: Batch metrics calculation during import
- **Documentation**: Complete overhaul of README, ARCHITECTURE, metrics, and database docs

### Fixed
- **OpenAI import**: Resolved circular import issues
- **Test files**: Cleaned up orphaned test files in root
- **Placeholder metrics**: Added back for schema compatibility

### Security
- All command injection vulnerabilities fixed
- Input validation added for all user inputs
- Path traversal protection implemented

## [0.8.0] - 2025-07-05

### Changed
- **MAJOR: Unified `pidgin chat` and `pidgin experiment` into single `pidgin run` command**
  - Single conversations run in foreground by default
  - Multiple conversations can run in foreground (sequential) or background (parallel)
  - Simplified mental model: no more command confusion
  
- **MAJOR: JSONL-first data architecture**
  - JSONL files are now the single source of truth
  - Manifest.json provides efficient state tracking
  - DuckDB used only for post-experiment analysis
  - Eliminated database lock contention issues
  
- **MAJOR: New default progress display**
  - Centered progress panel with turn progress, convergence, and token costs
  - `--quiet` runs in background with notification
  
- **MAJOR: Removed screen-like attach/detach behavior**
  - No more `pidgin attach` command
  - Use standard Unix tools (tail, grep, jq) for monitoring
  - Cleaner, more predictable workflow

### Added
- Process titles for daemon experiments (`pidgin-exp12345` in ps/top)
- Token usage and cost tracking in real-time
- Convergence trend indicators (↑, ↑↑, →, ↓, ↓↓)
- `pidgin import` command for batch loading JSONL to DuckDB
- Optimized state builder with mtime-based caching
- Manifest-based experiment tracking

### Fixed
- Critical command injection vulnerabilities in notification system
- Database connection leaks in async operations
- Memory leaks in event bus (unbounded growth)
- Race conditions in event sequence generation
- Resource cleanup in providers

### Removed
- `pidgin attach` command (use tail -f instead)
- Auto-attach behavior after starting experiments
- `--detach` flag (replaced by `--quiet`)
- Direct database writes during conversations

## [0.7.0] - 2025-07-03

### Added
- Read-only mode for EventStore to prevent lock conflicts
- JSONL event logging alongside database writes
- Proper daemon cleanup on exit

### Changed
- Fixed DuckDB concurrency issues
- Unified storage into single EventStore
- Improved daemon connection management

### Fixed
- Experiment list database locks
- Daemon connection leaks
- Concurrent write conflicts

## [0.6.0] - 2025-06-25

### Added
- DuckDB integration for analytics
- Real-time dashboard with metrics
- Parallel experiment execution
- Comprehensive metrics calculation

### Changed
- Migrated from file-based to database storage
- Improved experiment management
- Enhanced progress tracking

## [0.5.0] - 2025-06-20

### Added
- Experiment mode for running multiple conversations
- Background daemon execution
- Automatic metrics and analysis
- xAI (Grok) provider support

### Changed
- Separated single chat from experiment modes
- Added notification system
- Improved error handling

## [0.4.0] - 2025-06-14

### Added
- Complete event-driven architecture
- Streaming response display
- Interrupt system (Ctrl+C to pause/resume)
- Event sourcing for full observability

### Changed
- "Burn the boats" - removed checkpoint system
- Made events the core of the system
- Refactored conductor for cleaner separation

### Removed
- Legacy checkpoint and resume functionality
- Old state management system

## [0.3.0] - 2025-06-11

### Added
- Conductor mode for orchestrated conversations
- Signal flow architecture (A↔B) ⊥ C
- Provider abstraction layer
- Dimensional prompt system

### Changed
- Major streaming architecture refactor
- Improved model configuration
- Enhanced CLI interface

## [0.2.0] - 2025-06-05

### Added
- Conversation analysis and metrics
- Structural attractor detection
- Multiple model support (OpenAI, Google)
- Context window management

## [0.1.0] - 2025-06-01

### Added
- Initial release
- Basic Anthropic Claude integration
- Simple conversation runner
- JSON output format