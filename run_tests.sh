#!/bin/bash
# Script to run tests with proper Qt environment settings

# Set Qt to offscreen mode to prevent hanging
export QT_QPA_PLATFORM=offscreen
export QT_LOGGING_RULES="*.debug=false;qt.qpa.*=false"

# Run tests using uv (auto-activates .venv)
# Timeout comes from pytest.ini (60s) - don't override here
uv run pytest tests/ "$@"
