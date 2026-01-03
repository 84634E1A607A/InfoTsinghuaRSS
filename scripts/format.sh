#!/bin/bash
# Auto-fix linting and formatting issues

set -e

echo "Running ruff linter with auto-fix..."
uv run ruff check --fix .

echo ""
echo "Running ruff format..."
uv run ruff format .

echo ""
echo "✓ Code formatted and linted!"
