#!/usr/bin/env python

"""
UI Constants for 3DE4 Curve Editor

This module defines standardized constants for consistent UI styling across the application.
All values are designed to be DPI-aware and follow modern UI/UX best practices.
"""

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
# COLORS - LIGHT THEME (WCAG AA Compliant)
# ============================================================================

COLORS_LIGHT = {
    # Text colors - Updated for WCAG AA compliance (4.5:1 contrast ratio)
    "text_primary": "#212529",  # High contrast black
    "text_secondary": "#495057",  # Medium contrast gray (4.7:1 on white)
    "text_tertiary": "#5a6268",  # Darker gray for better contrast (4.5:1 on white)
    "text_disabled": "#6c757d",  # Disabled state (still distinguishable)
    "text_link": "#0066cc",  # Blue link
    "text_error": "#dc3545",  # Red error
    "text_success": "#28a745",  # Green success
    "text_warning": "#856404",  # Darker yellow for better contrast on white
    # Background colors
    "bg_primary": "#ffffff",  # White
    "bg_secondary": "#f8f9fa",  # Light gray
    "bg_panel": "#f1f3f5",  # Panel background
    "bg_elevated": "#ffffff",  # Elevated panels (cards, dropdowns)
    "bg_surface": "#fafbfc",  # Surface background (slightly off-white)
    "bg_input": "#ffffff",  # Input background
    "bg_hover": "#e9ecef",  # Hover state
    "bg_selected": "#dee2e6",  # Selected state
    "bg_disabled": "#e9ecef",  # Disabled state
    # Validation backgrounds
    "bg_success": "#d4edda",  # Success state background
    "bg_warning": "#fff3cd",  # Warning state background
    "bg_error": "#f8d7da",  # Error state background
    # Border colors
    "border_default": "#ced4da",  # Default border
    "border_focus": "#0066cc",  # Focus border
    "border_hover": "#adb5bd",  # Hover border
    "border_error": "#dc3545",  # Error border
    "border_warning": "#ffc107",  # Warning border
    "success": "#28a745",  # Success border/color
    "error": "#dc3545",  # Error color (alias for border_error)
    "warning": "#ffc107",  # Warning color (alias for border_warning)
    # Special colors
    "grid_lines": "#dee2e6",  # Grid lines
    "grid_major": "#adb5bd",  # Major grid lines
    "selection": "rgba(0, 102, 204, 0.3)",  # Selection overlay
    # Accent colors - More vibrant and distinctive
    "accent_primary": "#007bff",  # Primary action color (vibrant blue)
    "accent_secondary": "#6c757d",  # Secondary action color (gray)
    "accent_success": "#28a745",  # Success actions (green)
    "accent_danger": "#dc3545",  # Danger/destructive actions (red)
    "accent_warning": "#ffc107",  # Warning actions (yellow)
    "accent_info": "#17a2b8",  # Info actions (cyan)
    # Additional UI colors for better visual hierarchy
    "button_primary_bg": "#007bff",  # Primary button background
    "button_primary_hover": "#0056b3",  # Primary button hover
    "button_primary_active": "#004085",  # Primary button active
    "toggle_on_bg": "#28a745",  # Toggle on state
    "toggle_off_bg": "#6c757d",  # Toggle off state
}

# ============================================================================
# COLORS - DARK THEME (WCAG AA Compliant)
# ============================================================================

COLORS_DARK = {
    # Text colors
    "text_primary": "#f8f9fa",  # High contrast white
    "text_secondary": "#adb5bd",  # Medium contrast gray
    "text_tertiary": "#868e96",  # Darker gray for subtle text
    "text_disabled": "#6c757d",  # Dark gray
    "text_link": "#66b3ff",  # Light blue link
    "text_error": "#ff6b6b",  # Light red error
    "text_success": "#51cf66",  # Light green success
    "text_warning": "#ffd43b",  # Light yellow warning
    # Background colors
    "bg_primary": "#212529",  # Dark background
    "bg_secondary": "#343a40",  # Slightly lighter
    "bg_panel": "#2b3035",  # Panel background
    "bg_elevated": "#343a40",  # Elevated panels (cards, dropdowns)
    "bg_surface": "#2f353a",  # Surface background (slightly lighter than panel)
    "bg_input": "#343a40",  # Input background
    "bg_hover": "#495057",  # Hover state
    "bg_selected": "#495057",  # Selected state
    "bg_disabled": "#343a40",  # Disabled state
    # Validation backgrounds
    "bg_success": "#155724",  # Success state background (dark)
    "bg_warning": "#856404",  # Warning state background (dark)
    "bg_error": "#721c24",  # Error state background (dark)
    # Border colors
    "border_default": "#495057",  # Default border
    "border_focus": "#66b3ff",  # Focus border
    "border_hover": "#6c757d",  # Hover border
    "border_error": "#ff6b6b",  # Error border
    "border_warning": "#ffd43b",  # Warning border
    "success": "#51cf66",  # Success border/color
    "error": "#ff6b6b",  # Error color (alias for border_error)
    "warning": "#ffd43b",  # Warning color (alias for border_warning)
    # Special colors
    "grid_lines": "#343a40",  # Grid lines
    "grid_major": "#495057",  # Major grid lines
    "selection": "rgba(102, 179, 255, 0.3)",  # Selection overlay
    # Accent colors
    "accent_primary": "#66b3ff",  # Primary action color (light blue)
    "accent_secondary": "#6c757d",  # Secondary action color (gray)
    "accent_success": "#51cf66",  # Success actions (light green)
    "accent_danger": "#ff6b6b",  # Danger/destructive actions (light red)
    "accent_warning": "#ffd43b",  # Warning actions (light yellow)
    "accent_info": "#5bc0de",  # Info actions (light cyan)
    # Additional UI colors for better visual hierarchy
    "button_primary_bg": "#66b3ff",  # Primary button background
    "button_primary_hover": "#4da3ff",  # Primary button hover
    "button_primary_active": "#3393ff",  # Primary button active
    "toggle_on_bg": "#51cf66",  # Toggle on state
    "toggle_off_bg": "#6c757d",  # Toggle off state
}

# ============================================================================
# COLORS - HIGH CONTRAST THEME
# ============================================================================

COLORS_HIGH_CONTRAST = {
    # Text colors
    "text_primary": "#000000",  # Pure black
    "text_secondary": "#000000",  # Pure black
    "text_tertiary": "#404040",  # Dark gray for subtle text
    "text_disabled": "#767676",  # Medium gray
    "text_link": "#0000ff",  # Pure blue
    "text_error": "#ff0000",  # Pure red
    "text_success": "#00ff00",  # Pure green
    "text_warning": "#ffff00",  # Pure yellow
    # Background colors
    "bg_primary": "#ffffff",  # Pure white
    "bg_secondary": "#f0f0f0",  # Light gray
    "bg_panel": "#ffffff",  # Pure white
    "bg_elevated": "#ffffff",  # Elevated panels (pure white)
    "bg_surface": "#f8f8f8",  # Surface background (very light gray)
    "bg_input": "#ffffff",  # Pure white
    "bg_hover": "#cccccc",  # Gray hover
    "bg_selected": "#0000ff",  # Blue selected
    "bg_disabled": "#cccccc",  # Gray disabled
    # Validation backgrounds
    "bg_success": "#ccffcc",  # Light green background
    "bg_warning": "#ffffcc",  # Light yellow background
    "bg_error": "#ffcccc",  # Light red background
    # Border colors
    "border_default": "#000000",  # Black border
    "border_focus": "#0000ff",  # Blue focus
    "border_hover": "#333333",  # Dark gray hover
    "border_error": "#ff0000",  # Red error
    "border_warning": "#ffff00",  # Yellow warning
    "success": "#00ff00",  # Pure green success
    "error": "#ff0000",  # Error color (alias for border_error)
    "warning": "#ffff00",  # Warning color (alias for border_warning)
    # Special colors
    "grid_lines": "#000000",  # Black grid
    "grid_major": "#000000",  # Black grid
    "selection": "rgba(0, 0, 255, 0.5)",  # Blue selection
    # Accent colors
    "accent_primary": "#0000ff",  # Primary action color (blue)
    "accent_secondary": "#767676",  # Secondary action color (gray)
    "accent_success": "#00ff00",  # Success actions (green)
    "accent_danger": "#ff0000",  # Danger/destructive actions (red)
    "accent_warning": "#ffff00",  # Warning actions (yellow)
    "accent_info": "#00ffff",  # Info actions (cyan)
}

# ============================================================================
# CURVE VISUALIZATION COLORS
# ============================================================================

CURVE_COLORS = {
    "point_normal": "#0066cc",  # Normal keyframe point
    "point_interpolated": "#ff9900",  # Interpolated point
    "point_selected": "#ff0066",  # Selected point
    "point_hover": "#00ccff",  # Hover state
    "curve_line": "#0066cc",  # Curve line color
    "tangent_line": "#666666",  # Tangent handles
    "grid_minor": (200, 208, 220, 60),  # Minor grid RGBA
    "grid_major": (180, 188, 200, 120),  # Major grid RGBA
    "axis_x": "#ff0000",  # X axis
    "axis_y": "#00ff00",  # Y axis
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
# HELPER FUNCTIONS
# ============================================================================

def get_theme_colors(theme: str = "light") -> dict[str, str]:
    """Get color palette for specified theme.

    Args:
        theme: Theme name ("light", "dark", "high_contrast")

    Returns:
        Dictionary of color values
    """
    themes = {
        "light": COLORS_LIGHT,
        "dark": COLORS_DARK,
        "high_contrast": COLORS_HIGH_CONTRAST,
    }
    return themes.get(theme, COLORS_LIGHT)

def scale_value(value: int, dpi_scale: float) -> int:
    """Scale a pixel value based on DPI.

    Args:
        value: Original pixel value
        dpi_scale: DPI scaling factor

    Returns:
        Scaled pixel value
    """
    return int(value * dpi_scale)

def get_scaled_font_size(size_key: str, dpi_scale: float) -> int:
    """Get scaled font size by key.

    Args:
        size_key: Font size key from FONT_SIZES
        dpi_scale: DPI scaling factor

    Returns:
        Scaled font size in pixels
    """
    base_size = FONT_SIZES.get(size_key, FONT_SIZES["normal"])
    return scale_value(base_size, dpi_scale)

def get_scaled_spacing(spacing_key: str, dpi_scale: float) -> int:
    """Get scaled spacing by key.

    Args:
        spacing_key: Spacing key from SPACING
        dpi_scale: DPI scaling factor

    Returns:
        Scaled spacing in pixels
    """
    base_spacing = SPACING.get(spacing_key, SPACING["m"])
    return scale_value(base_spacing, dpi_scale)

def format_rgba(color: tuple[int, int, int, int]) -> str:
    """Format RGBA tuple as CSS rgba string.

    Args:
        color: RGBA color tuple

    Returns:
        CSS rgba string
    """
    return f"rgba({color[0]}, {color[1]}, {color[2]}, {color[3] / 255})"
