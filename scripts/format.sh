#!/bin/bash
# Format all Python code with black and isort

set -e

echo "Running black formatter..."
uv run black backend/

echo ""
echo "Running isort import sorter..."
uv run isort backend/

echo ""
echo "✓ Code formatting complete!"
