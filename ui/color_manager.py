#!/usr/bin/env python
"""
Color management system for CurveEditor with user customization support.

This module consolidates all color-related functionality including theme definitions,
color utilities, and runtime color management with user customization capabilities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

if TYPE_CHECKING:
    from core.models import PointStatus


# ============================================================================
# THEME DEFINITIONS
# ============================================================================

# WCAG AA Compliant Light Theme
THEME_LIGHT = {
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

# WCAG AA Compliant Dark Theme
THEME_DARK = {
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
    "grid_lines": "#6c757d",  # Grid lines (brightened for better visibility)
    "grid_major": "#868e96",  # Major grid lines (even brighter)
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

# High Contrast Theme for Accessibility
THEME_HIGH_CONTRAST = {
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
# COLOR UTILITY FUNCTIONS
# ============================================================================


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string (with or without #)

    Returns:
        RGB tuple (r, g, b) with values 0-255
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def darken_color(hex_color: str, factor: float = 0.6) -> tuple[int, int, int]:
    """Darken a hex color by factor and return RGB tuple.

    Args:
        hex_color: Hex color string
        factor: Darkening factor (0=black, 1=original)

    Returns:
        Darkened RGB tuple
    """
    r, g, b = hex_to_rgb(hex_color)
    return (int(r * factor), int(g * factor), int(b * factor))


def validate_hex_color(color: str) -> bool:
    """Validate a hex color string.

    Args:
        color: Color string to validate

    Returns:
        True if valid hex color, False otherwise
    """
    # Remove # if present
    color = color.lstrip("#")

    # Check length (should be 6 or 8 for RGBA)
    if len(color) not in (6, 8):
        return False

    # Check if all characters are hex
    try:
        _ = int(color, 16)
        return True
    except ValueError:
        return False


def tuple_status_to_string(status_value: str | bool | None) -> str:
    """Convert tuple status value to string.

    Args:
        status_value: Status from tuple (str, bool, or None)

    Returns:
        Status string for color lookup
    """
    if isinstance(status_value, str):
        return status_value
    elif status_value is True:
        return "interpolated"
    else:
        return "normal"


# ============================================================================
# STATUS COLOR SYSTEM - Single Source of Truth
# ============================================================================

# Primary status colors for curve view points
STATUS_COLORS = {
    "normal": "#5599ff",  # Blue - default state
    "keyframe": "#ff4444",  # Red - user-defined keyframes
    "tracked": "#00bfff",  # Bright cyan - auto-tracked points
    "interpolated": "#99ccff",  # Light blue - calculated between keyframes
    "endframe": "#ff4444",  # Red - marks segment end
}

# Timeline-specific colors (RGB tuples for QColor)
# Dynamically generated from STATUS_COLORS for consistency
STATUS_COLORS_TIMELINE = {
    "no_points": (52, 58, 64),  # Dark gray - no points at frame
    "normal": darken_color(STATUS_COLORS["normal"], 0.6),  # Darkened white (light gray)
    "keyframe": darken_color(STATUS_COLORS["keyframe"], 0.6),  # Darkened green
    "tracked": darken_color(STATUS_COLORS["tracked"], 0.6),  # Darkened cyan
    "interpolated": darken_color(STATUS_COLORS["interpolated"], 0.6),  # Darkened orange
    "endframe": darken_color(STATUS_COLORS["endframe"], 0.6),  # Darkened red
    "startframe": darken_color(STATUS_COLORS["keyframe"], 0.7),  # Slightly brighter green
    "inactive": (30, 30, 30),  # Dark gray - inactive segments
    "mixed": (70, 70, 30),  # Yellow tint - multiple statuses
    "selected": (73, 80, 87),  # Selected state
}

# Special UI colors
SPECIAL_COLORS = {
    "selected_point": "#ffff00",  # Yellow - selected points
    "current_frame": "#ff00ff",  # Magenta - current frame indicator
    "hover": "#00ccff",  # Light cyan - hover state
}

# Curve visualization colors
# Now defined after STATUS_COLORS to reference them directly (DRY principle)
CURVE_COLORS = {
    "point_normal": STATUS_COLORS["normal"],  # Normal point - white
    "point_keyframe": STATUS_COLORS["keyframe"],  # Keyframe - bright green
    "point_tracked": STATUS_COLORS["tracked"],  # Tracked - bright cyan
    "point_interpolated": STATUS_COLORS["interpolated"],  # Interpolated - orange
    "point_endframe": STATUS_COLORS["endframe"],  # Endframe - red
    "point_selected": SPECIAL_COLORS["selected_point"],  # Selected - yellow
    "point_hover": SPECIAL_COLORS["hover"],  # Hover state
    "curve_line": "#0066cc",  # Curve line color
    "tangent_line": "#666666",  # Tangent handles
    "grid_minor": (140, 150, 160, 100),  # Minor grid RGBA (brightened)
    "grid_major": (160, 170, 180, 180),  # Major grid RGBA (much brighter)
    "axis_x": "#ff0000",  # X axis
    "axis_y": "#00ff00",  # Y axis
}


def get_status_color(status: str | PointStatus) -> str:
    """Get color hex string for a PointStatus value.

    Args:
        status: PointStatus enum or string value

    Returns:
        Hex color string
    """
    # Import here to avoid circular dependency
    from core.models import PointStatus

    if isinstance(status, PointStatus):
        status = status.value
    return STATUS_COLORS.get(status, STATUS_COLORS["normal"])


def get_timeline_color(status: str) -> tuple[int, int, int]:
    """Get RGB tuple for timeline tab color.

    Args:
        status: Status string (keyframe, tracked, etc.)

    Returns:
        RGB tuple for QColor
    """
    return STATUS_COLORS_TIMELINE.get(status, STATUS_COLORS_TIMELINE["no_points"])


# ============================================================================
# COLOR MANAGER CLASS
# ============================================================================


class ColorManager(QObject):
    """Singleton color manager for runtime theme management and user customization.

    This class handles:
    - Theme switching with signal emission
    - User color overrides
    - Color caching for performance
    - Preference persistence
    """

    _instance: ColorManager | None = None
    theme_changed: Signal = Signal(str)  # Emitted when theme changes

    def __init__(self):
        """Initialize the color manager."""
        super().__init__()
        self._current_theme: str = "dark"  # Default theme
        self._themes: dict[str, dict[str, str]] = {
            "dark": THEME_DARK,
            "light": THEME_LIGHT,
            "high_contrast": THEME_HIGH_CONTRAST,
        }
        self._user_overrides: dict[str, str] = {}
        self._color_cache: dict[str, QColor] = {}  # Cache QColor objects
        self._preferences_file: Path = Path.home() / ".curveeditor" / "color_preferences.json"

        # Load user preferences if they exist
        self._load_preferences()

    @classmethod
    def instance(cls) -> ColorManager:
        """Get or create the singleton instance.

        Returns:
            The ColorManager singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_color(self, key: str, fallback: str = "#ffffff") -> str:
        """Get color value with fallback chain: user -> theme -> default.

        Args:
            key: Color key to look up
            fallback: Default color if key not found

        Returns:
            Hex color string
        """
        # Check user overrides first
        if key in self._user_overrides:
            return self._user_overrides[key]

        # Then check current theme
        if key in self._themes[self._current_theme]:
            return self._themes[self._current_theme][key]

        # Finally use fallback
        return fallback

    def get_qcolor(self, key: str, fallback: str = "#ffffff") -> QColor:
        """Get cached QColor object for performance.

        Args:
            key: Color key to look up
            fallback: Default color if key not found

        Returns:
            QColor object
        """
        cache_key = f"{self._current_theme}:{key}"

        if cache_key not in self._color_cache:
            color_str = self.get_color(key, fallback)
            self._color_cache[cache_key] = QColor(color_str)

        return self._color_cache[cache_key]

    def set_theme(self, theme_name: str) -> None:
        """Switch to a different theme.

        Args:
            theme_name: Name of theme to switch to (dark, light, high_contrast)
        """
        if theme_name in self._themes:
            self._current_theme = theme_name
            self._color_cache.clear()  # Clear cache when theme changes
            self.theme_changed.emit(theme_name)
            self._save_preferences()

    def get_current_theme(self) -> str:
        """Get the name of the current theme.

        Returns:
            Current theme name
        """
        return self._current_theme

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.

        Returns:
            List of theme names
        """
        return list(self._themes.keys())

    def override_color(self, key: str, value: str) -> bool:
        """Set a user color override.

        Args:
            key: Color key to override
            value: New color value (hex string)

        Returns:
            True if override was successful, False if invalid color
        """
        if not validate_hex_color(value):
            return False

        self._user_overrides[key] = value
        self._color_cache.clear()  # Clear cache when colors change
        self._save_preferences()
        return True

    def reset_overrides(self) -> None:
        """Clear all user color overrides."""
        self._user_overrides.clear()
        self._color_cache.clear()
        self._save_preferences()

    def get_overrides(self) -> dict[str, str]:
        """Get all current user overrides.

        Returns:
            Dictionary of color key to hex value overrides
        """
        return self._user_overrides.copy()

    def _save_preferences(self) -> None:
        """Save current preferences to JSON file."""
        try:
            # Create directory if it doesn't exist
            self._preferences_file.parent.mkdir(parents=True, exist_ok=True)

            preferences = {
                "current_theme": self._current_theme,
                "user_overrides": self._user_overrides,
            }

            with open(self._preferences_file, "w") as f:
                json.dump(preferences, f, indent=2)
        except Exception:
            # Silently fail - preferences are optional
            pass

    def _load_preferences(self) -> None:
        """Load preferences from JSON file if it exists."""
        try:
            if self._preferences_file.exists():
                with open(self._preferences_file) as f:
                    preferences: dict[str, Any] = json.load(f)

                # Load theme
                theme = preferences.get("current_theme", "dark")
                if isinstance(theme, str) and theme in self._themes:
                    self._current_theme = theme

                # Load user overrides
                overrides = preferences.get("user_overrides", {})
                if isinstance(overrides, dict):
                    # Validate each override before accepting
                    for key, value in overrides.items():
                        if isinstance(key, str) and isinstance(value, str) and validate_hex_color(value):
                            self._user_overrides[key] = value
        except Exception:
            # Silently fail - use defaults if preferences can't be loaded
            pass

    def export_theme(self, path: Path | str) -> bool:
        """Export current theme with overrides to a file.

        Args:
            path: Path to export file

        Returns:
            True if export successful, False otherwise
        """
        try:
            path = Path(path)

            # Combine current theme with overrides
            theme_data = self._themes[self._current_theme].copy()
            theme_data.update(self._user_overrides)

            export_data = {
                "name": f"{self._current_theme}_custom",
                "base_theme": self._current_theme,
                "colors": theme_data,
            }

            with open(path, "w") as f:
                json.dump(export_data, f, indent=2)
            return True
        except Exception:
            return False

    def import_theme(self, path: Path | str) -> bool:
        """Import a theme from a file.

        Args:
            path: Path to theme file

        Returns:
            True if import successful, False otherwise
        """
        try:
            path = Path(path)

            with open(path) as f:
                theme_data: dict[str, Any] = json.load(f)

            # Validate theme structure
            if "colors" not in theme_data:
                return False

            colors = theme_data["colors"]
            if not isinstance(colors, dict):
                return False

            # Validate all colors
            validated_colors: dict[str, str] = {}
            for key, value in colors.items():
                if not isinstance(key, str):
                    continue
                if not isinstance(value, str):
                    continue  # Skip non-string values (like rgba)
                if not validate_hex_color(value):
                    return False
                validated_colors[key] = value

            # Add theme
            theme_name = theme_data.get("name", "imported")
            if isinstance(theme_name, str):
                self._themes[theme_name] = validated_colors
                return True
            return False
        except Exception:
            return False


# ============================================================================
# MODULE INTERFACE
# ============================================================================


def get_color_manager() -> ColorManager:
    """Get the global ColorManager instance.

    Returns:
        The singleton ColorManager instance
    """
    return ColorManager.instance()


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Aliases for existing code that expects these names
COLORS_DARK = THEME_DARK
COLORS_LIGHT = THEME_LIGHT
COLORS_HIGH_CONTRAST = THEME_HIGH_CONTRAST
