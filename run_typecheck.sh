#!/bin/bash
# Type checking script for CurveEditor project
# Uses basedpyright with the project's virtual environment

cd "$(dirname "$0")"

echo "Running basedpyright type checking..."
echo "Configuration: basedpyrightconfig.json"
echo "Virtual environment: ./venv"
echo ""

# Run basedpyright using the venv Python
./venv/bin/python -m basedpyright "$@"