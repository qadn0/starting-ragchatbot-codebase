#!/bin/bash
# Run code quality checks (flake8, mypy)

set -e

echo "Running flake8 linter..."
uv run flake8 backend/

echo ""
echo "Running mypy type checker..."
uv run mypy backend/

echo ""
echo "✓ All linting checks passed!"
