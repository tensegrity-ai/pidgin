# Pidgin Pre-Launch Architecture Review and Preflight Assessment

Last updated: YYYY-MM-DD

## Architecture Review

- **Core Design:** Event-driven orchestration centered on `EventBus` with JSONL-first storage and DuckDB post-processing. Clear layering: CLI → Conductor/Router → Providers → EventBus → JSONL → ImportService/Repositories → DuckDB. Modules are small and focused with sensible orchestration points.
- **Key Modules:**
  - `core/`: `conductor.py` (turn orchestration), `router.py` (perspective transforms + truncation), `event_bus.py` (pub/sub + JSONL), lifecycle/interrupt/rate-limiter handlers.
  - `experiments/`: runner, manifest, tracking event bus, post-processor, daemon/process mgmt.
  - `providers/`: Anthropic/OpenAI/Google/xAI/Ollama + `LocalProvider`/`test_model`, with retry and token tracking utilities.
  - `database/`: ImportService with wide-table `conversation_turns` and repositories, event deserializer.
  - `ui/`: rich-based displays for chat/tail/monitor.
- **Strengths:**
  - Observability via append-only JSONL; `TrackingEventBus` updates manifest in real time; event history retains traceability.
  - Separation/extensibility: provider abstraction, centralized model metadata, unified metrics pipeline.
  - Resilience: retry/backoff utilities; sequential-by-default execution; safe serialization that avoids credential leakage.
  - Local dev friendliness: `local:test` model; Ollama integration with consented install/start flow.
  - Tooling: Ruff/Black/Mypy/pytest; bandit/safety tasks; docs and man pages.
- **Notable Risks / Gaps:**
  - Concurrent JSONL writes: In parallel runs, each conversation uses its own `TrackingEventBus` but all write to the same `exp_dir/events.jsonl`. Locks are per-process/instance, so writes can interleave under `max_parallel > 1`. Risk: interleaved or corrupted lines.
    - Options: (a) per-conversation JSONL files (`conv_<id>.jsonl`), (b) single experiment-level bus as sole writer, or (c) interprocess-safe file lock around writes.
  - Docs/CLI drift:
    - README references `pidgin info models`, `pidgin info dimensions`, `pidgin list`, and a `-d` dimensions flag that aren’t implemented. Actual commands: `pidgin models`; YAML supports `dimensions`.
  - Packaging name mismatch: Docs say `pip install pidgin-ai` but `pyproject.toml` package name is `pidgin`. Align package name and installation docs before release.
  - Security of subprocess flows: Ollama install uses `shell=True` in the Homebrew path and runs a remote install script on Linux. Consent UX exists, but add explicit warnings/logging and prefer non-shell invocations where possible.
  - Type strictness: Mypy settings are permissive. Acceptable for beta, but type drift risk grows post-launch.
  - Data retention: No cleanup/rotation policy for `pidgin_output/` or DuckDB; long-running use can grow large.
  - PII/log content: Events store full message contents. Provide a redaction/masking mode and a “message-free” logging mode for sensitive runs.
  - Rate-limits: GlobalTokenTracker uses conservative defaults; ensure real-world limits are configurable per key/tenant and consider per-model overrides.
  - CI visibility: README has a CI badge; ensure workflows actually run lint/type/test/security and package publish.

## Preflight Assessment

### Release Packaging
- Name/version: Align published name (likely `pidgin-ai`) with `pyproject` and docs. Current version `0.1.0` and classifiers mark Beta.
- Entry point: `pidgin = pidgin.cli:main` is fine; consider deferring heavy rich config to reduce startup latency.
- Build/run check: Verify `poetry build` artifacts and run CLI from wheel in a clean venv.

### CLI/Docs Consistency
- Fix README examples (`info`, `list`, `dimensions`, `-d`) to match actual CLI.
- Update man pages and docs links that reference `nicholas-lange` vs `tensegrity-ai`.

### Concurrency & Data Integrity
- Fix JSONL write strategy for parallel runs: per-conversation files or single-writer bus/file locking.
- Add JSONL line validation during post-processing to catch truncated lines early.

### Security
- Run `poe security` (bandit + safety) against the release lockfile.
- Confirm all YAML loads use `safe_load` (they do).
- Add opt-in redaction flag (e.g., `--redact-content`) to avoid storing message text in JSONL/DuckDB.
- Ensure keys cannot surface in logs/events (current serializers avoid client/credential serialization).

### Operational
- Retention: Provide `pidgin cleanup` command or docs for pruning old experiments and DuckDB VACUUM/OPTIMIZE.
- Configuration paths: Document `pidgin_output` vs `pidgin_dev_output` and how to override via `--output`.
- Monitoring: Validate `pidgin monitor` behavior on large directories and without DB; ensure graceful degradation.
- Signals: Test Ctrl-C, background daemon stop paths; ensure no orphaned processes.

### Quality Gates (CI)
- CI should run `ruff check`, `ruff format --check`, `mypy`, `pytest -q` with `local:test`, and `poe security`.
- Add smoke tests:
  - Single conversation end-to-end: JSONL via `TrackingEventBus` → ImportService → rows in `conversation_turns`.
  - Parallel run (`max_parallel=2`) with per-conversation JSONL to validate no interleaving.

### Performance
- Sequential default is good. If supporting `max_parallel > 1`, measure EventBus I/O throughput on `local:test`; tune locks/buffers accordingly.
- DuckDB imports: current transaction handling is good; consider `COPY` for very large datasets later.

### User Experience
- Non-interactive modes (`--quiet`) should not block/wait unexpectedly; ensure daemonization paths are non-blocking.
- Missing API keys: maintain clear messages and suggest `local:test` as fallback.

## Top Action Items Before Launch

1. Fix parallel JSONL writing to avoid interleaving; prefer per-conversation files and update ImportService to glob all `*.jsonl`.
2. Align package name and installation docs; update README examples to match CLI.
3. Add a redaction mode to avoid storing message content in events/DB.
4. Tighten CI: run lint/type/test/security; add two smoke tests for JSONL→DuckDB and parallel runs.
5. Add cleanup guidance/command for `pidgin_output/` and DuckDB maintenance.
6. Review subprocess install flows; add explicit warnings and logs; remove `shell=True` where feasible.

## Optional Next Steps

- I can implement the per-conversation JSONL strategy (`events_{conversation_id}.jsonl`) and adjust ImportService to glob, plus README/CLI doc fixes, in a small PR.

