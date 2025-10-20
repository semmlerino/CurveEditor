#!/usr/bin/env python
"""
Application-wide default constants.

These constants are used by core business logic and services.
UI-specific constants remain in ui/ui_constants.py.
"""

# Image dimensions
DEFAULT_IMAGE_WIDTH: int = 1920
DEFAULT_IMAGE_HEIGHT: int = 1080

# Interaction defaults
DEFAULT_NUDGE_AMOUNT: float = 1.0

# UI operation defaults
DEFAULT_STATUS_TIMEOUT: int = 3000  # milliseconds

# View constraints
MAX_ZOOM_FACTOR: float = 10.0
MIN_ZOOM_FACTOR: float = 0.1

# Rendering defaults
GRID_CELL_SIZE: int = 100
RENDER_PADDING: int = 100
