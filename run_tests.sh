#!/bin/bash
# Script to run tests with proper Qt environment settings

# Ensure we're in the virtual environment
source venv/bin/activate

# Set Qt to offscreen mode to prevent hanging
export QT_QPA_PLATFORM=offscreen
export QT_LOGGING_RULES="*.debug=false;qt.qpa.*=false"

# Run tests with timeout
python -m pytest tests/ --timeout=10 "$@"
