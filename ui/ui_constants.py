#!/usr/bin/env python

"""
UI Constants for 3DE4 Curve Editor

This module defines standardized constants for consistent UI styling across the application.
All values are designed to be DPI-aware and follow modern UI/UX best practices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Import all color functionality from color_manager for backward compatibility
from ui.color_manager import (  # noqa: F401
    COLORS_DARK,
    COLORS_HIGH_CONTRAST,
    COLORS_LIGHT,
    CURVE_COLORS,
    SPECIAL_COLORS,
    STATUS_COLORS,
    STATUS_COLORS_TIMELINE,
    darken_color,
    get_status_color,
    get_timeline_color,
    hex_to_rgb,
    tuple_status_to_string,
)

if TYPE_CHECKING:
    pass

# ============================================================================
# FONT SYSTEM
# ============================================================================

# Standardized font sizes (in pixels) - will be scaled by DPI
# Updated to meet WCAG AA standards (minimum 11-12pt)
FONT_SIZES = {
    "tiny": 11,  # For less important labels (WCAG minimum)
    "small": 12,  # Standard small text
    "normal": 14,  # Default body text
    "medium": 16,  # Section headers
    "large": 18,  # Main headers
    "xlarge": 24,  # Page titles
}

# Font weights
FONT_WEIGHTS = {
    "regular": "Normal",
    "medium": "Medium",
    "bold": "Bold",
}

# Font families
FONT_FAMILIES = {
    "default": "Segoe UI, Arial, sans-serif",
    "monospace": "Consolas, 'Courier New', monospace",
}

# ============================================================================
# SPACING SYSTEM
# ============================================================================

# Standardized spacing units (in pixels) - will be scaled by DPI
SPACING = {
    "xs": 4,  # Extra small spacing
    "s": 8,  # Small spacing
    "m": 12,  # Medium spacing
    "l": 16,  # Large spacing
    "xl": 24,  # Extra large spacing
    "xxl": 32,  # Double extra large spacing
}

# Standard margins and padding
MARGINS = {
    "dialog": SPACING["l"],
    "group": SPACING["m"],
    "control": SPACING["s"],
    "label": SPACING["xs"],
}

PADDING = {
    "button": (SPACING["s"], SPACING["m"]),  # (vertical, horizontal)
    "input": (SPACING["xs"], SPACING["s"]),
    "panel": SPACING["m"],
    "toolbar": SPACING["s"],
}

# ============================================================================
# SIZING
# ============================================================================

# Minimum sizes for interactive elements (WCAG touch target guidelines)
MIN_SIZES = {
    "button_height": 32,
    "button_width": 64,
    "touch_target": 44,  # Minimum touch target size
    "input_height": 28,
    "toolbar_height": 48,
    "icon_size": 20,
    "slider_height": 24,
}

# Maximum sizes
MAX_SIZES = {
    "button_width": 120,
    "label_width": 200,
    "input_width": 300,
}

# ============================================================================
# UI STYLES
# ============================================================================

# Border radius values
BORDER_RADIUS = {
    "small": 2,
    "medium": 4,
    "large": 8,
}

# Shadow effects
SHADOWS = {
    "none": "",
    "small": "0 1px 2px rgba(0, 0, 0, 0.1)",
    "medium": "0 2px 4px rgba(0, 0, 0, 0.1)",
    "large": "0 4px 8px rgba(0, 0, 0, 0.15)",
}

# ============================================================================
# ANIMATION
# ============================================================================

ANIMATION = {
    "duration_fast": 150,  # Fast animations (ms)
    "duration_normal": 250,  # Normal animations (ms)
    "duration_slow": 400,  # Slow animations (ms)
}

# ============================================================================
# APPLICATION DEFAULTS
# ============================================================================

# Default image/canvas dimensions
DEFAULT_IMAGE_WIDTH = 1920
DEFAULT_IMAGE_HEIGHT = 1080

# History and limits
MAX_HISTORY_SIZE = 100
DEFAULT_CHUNK_SIZE = 10000

# Grid and rendering
GRID_CELL_SIZE = 100  # Grid cell size for spatial indexing
RENDER_PADDING = 100  # Padding for viewport culling

# View defaults
DEFAULT_ZOOM_FACTOR = 1.0
MIN_ZOOM_FACTOR = 0.1
MAX_ZOOM_FACTOR = 10.0
DEFAULT_BACKGROUND_OPACITY = 0.5

# Timing defaults (milliseconds)
DEFAULT_STATUS_TIMEOUT = 3000  # Status message timeout
DEFAULT_FPS = 30

# Numeric input defaults
DEFAULT_DECIMAL_PLACES = 2
DEFAULT_SMOOTHING_WINDOW = 5
DEFAULT_NUDGE_AMOUNT = 1.0

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
