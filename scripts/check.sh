#!/bin/bash
# Run all code quality checks (format check, lint, type check)

set -e

echo "=== Code Quality Checks ==="
echo ""

echo "1. Checking code formatting (black)..."
uv run black --check backend/

echo ""
echo "2. Checking import sorting (isort)..."
uv run isort --check-only backend/

echo ""
echo "3. Running flake8 linter..."
uv run flake8 backend/

echo ""
echo "4. Running mypy type checker..."
uv run mypy backend/

echo ""
echo "✓ All quality checks passed!"
