#!/bin/bash
# Run linting and formatting checks

set -e

echo "Running ruff linter..."
uv run ruff check .

echo ""
echo "Running ruff format check..."
uv run ruff format --check .

echo ""
echo "✓ All checks passed!"
