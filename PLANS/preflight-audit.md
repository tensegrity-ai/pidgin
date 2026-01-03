# Preflight Audit Plan

Final quality pass before packaging and publishing.

## 1. Automated Checks

```bash
# Lint and format
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run mypy pidgin --strict

# Tests
uv run pytest -v
```

Fix any issues found.

---

## 2. Bug Hunting

### Known Issues
- [ ] `pidgin/analysis/cells/convergence.py:30` - `conv_id` should be `conversation_id`

### Pattern Search
```bash
# Undefined variables (common typos)
rg "conv_id|msg_id|exp_id" --type py  # Check for inconsistent naming

# TODO/FIXME/HACK comments
rg "TODO|FIXME|HACK|XXX" --type py

# Print statements (should use logger)
rg "^\s*print\(" --type py pidgin/

# Bare except clauses
rg "except:" --type py
```

---

## 3. Docstring Audit

Remove docstrings that just restate the obvious:

**Bad (remove):**
```python
def get_name(self) -> str:
    """Get the name."""
    return self.name
```

**Good (keep):**
```python
def calculate_convergence(self, window: int = 5) -> float:
    """Calculate convergence using sliding window average.

    Uses vocabulary overlap weighted by recency.
    """
```

### Directories to audit:
- [ ] `pidgin/core/` - core types and events
- [ ] `pidgin/providers/` - provider implementations
- [ ] `pidgin/database/` - repositories and event store
- [ ] `pidgin/cli/` - command handlers
- [ ] `pidgin/experiments/` - experiment runner
- [ ] `pidgin/analysis/` - notebook generation
- [ ] `pidgin/monitor/` - display builders

---

## 4. Dead Code

```bash
# Unused imports
ruff check . --select F401

# Unused variables
ruff check . --select F841

# Check for orphan files
# Look for .py files not imported anywhere
```

---

## 5. Consistency Check

- [ ] All CLI commands have `--help` text
- [ ] Error messages are user-friendly (not stack traces for expected errors)
- [ ] Nord color scheme used consistently (no hardcoded colors)
- [ ] Logging uses `get_logger()` consistently
- [ ] No emoji in output (per CLAUDE.md)

---

## 6. Documentation Accuracy

- [ ] README.md reflects current CLI commands (`run`, `branch`, `monitor`, `stop`, `models`, `config`)
- [ ] ARCHITECTURE.md matches actual code structure
- [ ] Example commands in docs actually work
- [ ] `pidgin --help` output is accurate

---

## 7. Dependency Check

```bash
# Check for unused dependencies
uv pip check

# Verify optional dependencies are truly optional
python -c "import pidgin"  # Should work without nbformat, etc.
```

---

## 8. Manual Smoke Test

```bash
# Basic conversation
pidgin run -a local:test -b local:test -t 3

# From YAML spec (if example exists)
pidgin run examples/simple.yaml

# Monitor
pidgin monitor

# Models list
pidgin models

# Branch (requires existing conversation)
pidgin branch <conversation_id> --turn 5

# Stop (requires running experiment)
pidgin stop <experiment_id>

# Config
pidgin config
```

---

## 9. Security Scan

```bash
# Check for hardcoded secrets
rg "(api_key|secret|password|token)\s*=" --type py -i

# Check for unsafe eval/exec
rg "(eval|exec)\(" --type py
```

---

## 10. Final Polish

- [ ] Version number set correctly in pyproject.toml
- [ ] CHANGELOG.md up to date (if exists)
- [ ] LICENSE file present
- [ ] .gitignore covers build artifacts
- [ ] No large files accidentally committed

---

## Execution Order

1. Run automated checks first (fastest feedback)
2. Fix known bugs
3. Pattern search for issues
4. Docstring audit (manual, time-consuming)
5. Smoke test
6. Documentation review
7. Final commit and tag
