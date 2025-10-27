#!/usr/bin/env python

"""
UI Constants for 3DE4 Curve Editor

This module defines standardized constants for consistent UI styling across the application.
All values are designed to be DPI-aware and follow modern UI/UX best practices.
"""

from __future__ import annotations

# Import all color functionality from color_manager for backward compatibility
# These are re-exported for other modules - pyright: ignore
from ui.color_manager import (  # noqa: F401
    COLORS_DARK,  # pyright: ignore[reportUnusedImport]
    COLORS_HIGH_CONTRAST,  # pyright: ignore[reportUnusedImport]
    COLORS_LIGHT,  # pyright: ignore[reportUnusedImport]
    CURVE_COLORS,  # pyright: ignore[reportUnusedImport]
    SPECIAL_COLORS,  # pyright: ignore[reportUnusedImport]
    STATUS_COLORS,  # pyright: ignore[reportUnusedImport]
    STATUS_COLORS_TIMELINE,  # pyright: ignore[reportUnusedImport]
    darken_color,  # pyright: ignore[reportUnusedImport]
    get_status_color,  # pyright: ignore[reportUnusedImport]
    get_timeline_color,  # pyright: ignore[reportUnusedImport]
    hex_to_rgb,  # pyright: ignore[reportUnusedImport]
    tuple_status_to_string,  # pyright: ignore[reportUnusedImport]
)

# ============================================================================
# FONT SYSTEM
# ============================================================================

# Standardized font sizes (in points) - Modern VFX tool typography
# Phase 3: Enhanced Typography - larger, more readable fonts
FONT_SIZE_SMALL = 10  # Less important labels
FONT_SIZE_NORMAL = 12  # Primary text (up from 10-11pt)
FONT_SIZE_LARGE = 14  # Section headers (up from 12pt)
FONT_SIZE_HEADING = 16  # Main headings

# Legacy dict for backward compatibility
FONT_SIZES = {
    "tiny": 10,
    "small": FONT_SIZE_SMALL,
    "normal": FONT_SIZE_NORMAL,
    "medium": FONT_SIZE_LARGE,
    "large": FONT_SIZE_LARGE,
    "xlarge": FONT_SIZE_HEADING,
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
# SPACING SYSTEM - 8px Base Grid (Phase 3: Enhanced Spacing)
# ============================================================================

# 8px base grid system for consistent spacing
SPACING_XS = 4  # Extra small (0.5 x base)
SPACING_SM = 8  # Small (1 x base)
SPACING_MD = 16  # Medium (2 x base)
SPACING_LG = 24  # Large (3 x base)
SPACING_XL = 32  # Extra large (4 x base)

# Legacy dict for backward compatibility
SPACING = {
    "xs": SPACING_XS,
    "s": SPACING_SM,
    "m": SPACING_MD,
    "l": SPACING_LG,
    "xl": SPACING_LG,
    "xxl": SPACING_XL,
}

# Standard margins and padding (using 8px grid)
MARGINS = {
    "dialog": SPACING_MD,  # 16px
    "group": SPACING_SM,  # 8px
    "control": SPACING_SM,  # 8px
    "label": SPACING_XS,  # 4px
}

PADDING = {
    "button": (SPACING_SM, SPACING_MD),  # (8px, 16px)
    "input": (SPACING_XS, SPACING_SM),  # (4px, 8px)
    "panel": SPACING_MD,  # 16px
    "toolbar": SPACING_SM,  # 8px
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
