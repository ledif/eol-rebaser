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

# Bump version and create release
release version: (_update-version version) (_commit-and-tag version)
    @echo "Release {{version}} created and pushed!"

# Update version in all files
_update-version version:
    @echo "Updating version to {{version}}"
    # Update pyproject.toml
    sed -i 's/^version = .*/version = "{{version}}"/' pyproject.toml
    # Update spec file
    sed -i 's/^Version:.*/Version:        {{version}}/' eol-rebaser.spec
    # Update __init__.py if it exists
    @if [ -f src/eol_rebaser/__init__.py ]; then \
        sed -i 's/__version__ = .*/__version__ = "{{version}}"/' src/eol_rebaser/__init__.py; \
    fi
    # Update main.py version
    sed -i 's/version="%(prog)s [0-9.]*"/version="%(prog)s {{version}}"/' src/eol_rebaser/main.py

# Commit changes and create tag
_commit-and-tag version:
    @echo "Committing and tagging version {{version}}"
    git add pyproject.toml eol-rebaser.spec src/eol_rebaser/__init__.py src/eol_rebaser/main.py
    git commit -m "chore: bump version to {{version}}"
    git tag -a "v{{version}}" -m "Release version {{version}}"
    git push origin main
    git push origin "v{{version}}"

# Show current version
version:
    @grep '^version = ' pyproject.toml | sed 's/version = "//' | sed 's/"//'

# Show help
help:
    @just --list
