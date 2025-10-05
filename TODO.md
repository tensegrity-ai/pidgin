# Pidgin Launch TODO

## Critical Before Launch

### 1. ✅ Package Name & Installation
- [x] Update pyproject.toml to `pidgin-ai` 
- [x] Update installation docs to prioritize uv/pipx
- [x] Rebuild package with new name

### 2. ✅ Fix Parallel JSONL Concurrency 
- [x] Implement per-conversation JSONL files (`events_{conversation_id}.jsonl`)
- [x] Update ImportService to glob all `*.jsonl` files  
- [x] Test with `max_parallel > 1` to verify no interleaving

### 3. ✅ CI/CD Pipeline
- [x] GitHub Actions workflow configured
- [x] Linting: `ruff check`, `ruff format --check`
- [x] Type checking: `mypy`
- [x] Testing: `pytest` across Python 3.9-3.12
- [x] Security scanning: `bandit` + `safety`
- [x] Add smoke tests:
  - [x] Single conversation JSONL → DuckDB flow (test_full_experiment_pipeline)
  - [x] Parallel run with `max_parallel=2` (test_parallel_experiment_execution)

### 4. ✅ Security Review
- [x] Review Ollama install subprocess flows
- [x] Remove `shell=True` where possible
- [x] Add explicit user warnings for remote script execution

## Nice to Have

### Documentation
- [x] Fix README command examples that don't exist (`info`, `list`, `-d` flag)
- [x] Update GitHub links from `nicholas-lange` to `tensegrity-ai` (already correct)
- [ ] Add PyPI badge once published

### Developer Experience
- [ ] Improve mypy strictness settings
- [ ] Add pre-commit hooks configuration
- [ ] Document development workflow

### Performance
- [ ] Benchmark EventBus I/O with high parallel counts
- [ ] Consider COPY for large DuckDB imports
- [ ] Profile startup time with rich imports

## In Progress

### Model/Pricing Updates ✅
- [x] JSON-based model configuration system implemented
- [x] Schema defined for model data (`pidgin/data/models_schema.json`)
- [x] Model loader with user override support
- [x] Case-insensitive alias resolution
- [x] Dynamic Ollama model detection in `pidgin models`
- [x] Add Ollama models to models.json (qwen, phi, mistral, gpt-oss variants)
- [x] Add config option for Ollama auto-start consent
- [x] Support PIDGIN_OLLAMA_AUTO_START environment variable
- [x] Set up `pidgin-tools` repo for model data generation
- [x] Move scripts from `/scripts/` to pidgin-tools repo
- [ ] Automated monthly updates via GitHub Actions

## Post-Launch Roadmap

### Analytics & Insights
- Statistical analysis tools
- Automated report generation
- Pattern detection algorithms

### Multi-modal Support
- Image/video conversation support
- Multi-party conversations
- Tool use between models