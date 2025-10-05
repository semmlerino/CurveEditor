#!/bin/bash
# Type checking script for CurveEditor project
# Uses basedpyright with uv-managed virtual environment

cd "$(dirname "$0")"

echo "Running basedpyright type checking..."
echo "Configuration: basedpyrightconfig.json"
echo "Virtual environment: ./.venv (managed by uv)"
echo ""

# Run basedpyright using uv (auto-activates .venv)
uv run basedpyright "$@"
