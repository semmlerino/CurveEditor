#!/bin/bash
# Script to run tests with proper Qt environment settings

# Set Qt to offscreen mode to prevent hanging
export QT_QPA_PLATFORM=offscreen
export QT_LOGGING_RULES="*.debug=false;qt.qpa.*=false"

# Run tests with timeout using uv (auto-activates .venv)
uv run pytest tests/ --timeout=10 "$@"
