# Pidgin Project Makefile
# Provides convenient shortcuts for common development tasks

.PHONY: help test test-unit test-integration test-slow test-cov test-prop test-watch \
        clean clean-pyc clean-test format lint type-check install dev-install \
        db-reset docs serve-docs

# Default target - show help
help:
	@echo "Pidgin Development Commands:"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests (fast tests only)"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-slow     - Run slow tests"
	@echo "  make test-prop     - Run property-based tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make test-watch    - Run tests in watch mode"
	@echo "  make test-failed   - Re-run only failed tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format        - Format code with black"
	@echo "  make lint          - Run linting checks"
	@echo "  make type-check    - Run type checking with mypy"
	@echo "  make check         - Run all checks (format, lint, type)"
	@echo ""
	@echo "Development:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev-install   - Install dev dependencies"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make db-reset      - Reset development database"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs          - Build documentation"
	@echo "  make serve-docs    - Serve docs locally"

# Testing targets
test:
	@echo "Running fast tests..."
	@poetry run pytest -xvs

test-unit:
	@echo "Running unit tests..."
	@poetry run pytest -xvs -m unit

test-integration:
	@echo "Running integration tests..."
	@poetry run pytest -xvs -m integration

test-slow:
	@echo "Running slow tests..."
	@poetry run pytest -xvs --runslow

test-prop:
	@echo "Running property-based tests..."
	@poetry run pytest -xvs tests/unit/test_metrics_property.py tests/unit/test_metrics_invariants.py

test-cov:
	@echo "Running tests with coverage..."
	@poetry run pytest --cov=pidgin --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

test-cov-report: test-cov
	@echo "Opening coverage report..."
	@open htmlcov/index.html || xdg-open htmlcov/index.html

test-watch:
	@echo "Running tests in watch mode..."
	@poetry run ptw -- -xvs

test-failed:
	@echo "Re-running failed tests..."
	@poetry run pytest --lf -xvs

test-specific:
	@echo "Running tests matching pattern: $(PATTERN)"
	@poetry run pytest -k "$(PATTERN)" -xvs

# Code quality targets
format:
	@echo "Formatting code..."
	@poetry run black pidgin tests
	@poetry run isort pidgin tests

lint:
	@echo "Running linting checks..."
	@poetry run flake8 pidgin tests
	@poetry run pylint pidgin

type-check:
	@echo "Running type checks..."
	@poetry run mypy pidgin

check: format lint type-check
	@echo "All checks passed!"

# Development targets
install:
	@echo "Installing dependencies..."
	@poetry install

dev-install: install
	@echo "Installing pre-commit hooks..."
	@poetry run pre-commit install

clean: clean-pyc clean-test
	@echo "Cleanup complete"

clean-pyc:
	@echo "Removing Python artifacts..."
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
	@find . -type d -name '*.egg-info' -exec rm -rf {} +

clean-test:
	@echo "Removing test artifacts..."
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache

# Database targets
db-reset:
	@echo "Resetting development database..."
	@rm -f pidgin_output/pidgin.duckdb
	@echo "Database reset complete"

db-shell:
	@echo "Opening DuckDB shell..."
	@duckdb pidgin_output/pidgin.duckdb

# Documentation targets
docs:
	@echo "Building documentation..."
	@cd docs && poetry run mkdocs build

serve-docs:
	@echo "Serving documentation at http://localhost:8000..."
	@cd docs && poetry run mkdocs serve

# Performance testing
perf-test:
	@echo "Running performance benchmarks..."
	@poetry run pytest -xvs tests/performance/ --benchmark-only

perf-profile:
	@echo "Profiling pidgin..."
	@poetry run python -m cProfile -o profile.stats pidgin/cli.py run -a local:test -b local:test -t 10
	@echo "Profile saved to profile.stats"

# Useful development shortcuts
quick-test:
	@echo "Running quick test (local providers)..."
	@poetry run pidgin run -a local:test -b local:test -t 5

quick-experiment:
	@echo "Running quick experiment..."
	@poetry run pidgin experiment run example_experiment.yaml

# CI simulation
ci:
	@echo "Running CI pipeline locally..."
	@make clean
	@make install
	@make check
	@make test-cov
	@echo "CI pipeline complete!"

# Version management
version:
	@poetry version

bump-patch:
	@poetry version patch

bump-minor:
	@poetry version minor

bump-major:
	@poetry version major