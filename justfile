# Justfile for eol-rebaser development tasks

# Format all Python code with black
format:
    uv run black src/ tests/

# Check formatting without making changes
format-check:
    uv run black --check src/ tests/

# Run linting with flake8
lint:
    uv run flake8 src/ tests/

# Run type checking with mypy
typecheck:
    uv run mypy src/

# Run tests
test:
    uv run pytest tests/ -v

# Run all checks (format check, lint, typecheck, test)
check: format-check lint typecheck test

# Install development dependencies
install:
    uv sync --extra dev

# Setup lefthook git hooks
setup-hooks:
    lefthook install

# Clean up Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Show help
help:
    @just --list
