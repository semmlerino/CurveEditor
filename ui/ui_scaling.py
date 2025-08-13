#!/usr/bin/env python

"""
DPI-aware UI scaling utilities for the Curve Editor.

This module provides utilities for creating responsive, DPI-aware user interfaces
that adapt to different screen sizes, resolutions, and scaling factors.
"""

import logging
from typing import NamedTuple

from PySide6.QtCore import QSize
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QApplication

from ui import ui_constants

# Create logger directly to avoid circular dependency with services
logger = logging.getLogger("ui_scaling")


class ScreenInfo(NamedTuple):
    """Information about the current screen configuration."""

    width: int
    height: int
    dpi: float
    device_pixel_ratio: float
    physical_dpi: float


class UIScaling:
    """Utility class for DPI-aware UI scaling and responsive design."""

    _cached_screen_info: ScreenInfo | None = None
    _base_font_size: int = 12  # Base font size for scaling calculations
    _current_theme: str = "light"  # Current UI theme

    @classmethod
    def get_screen_info(cls) -> ScreenInfo:
        """Get current screen information with caching.

        Returns:
            ScreenInfo: Current screen dimensions, DPI, and scaling information
        """
        if cls._cached_screen_info is None:
            cls._refresh_screen_info()
        return cls._cached_screen_info

    @classmethod
    def _refresh_screen_info(cls) -> None:
        """Refresh cached screen information."""
        app = QApplication.instance()
        if app is None:
            # Fallback values for testing or edge cases
            cls._cached_screen_info = ScreenInfo(1920, 1080, 96.0, 1.0, 96.0)
            logger.warning("No QApplication instance found, using fallback screen info")
            return

        # Cast to QGuiApplication to access primaryScreen method
        gui_app = QGuiApplication.instance()
        if gui_app is None:
            gui_app = app  # QApplication inherits from QGuiApplication
        primary_screen = gui_app.primaryScreen()
        if primary_screen is None:
            cls._cached_screen_info = ScreenInfo(1920, 1080, 96.0, 1.0, 96.0)
            logger.warning("No primary screen found, using fallback screen info")
            return

        geometry = primary_screen.geometry()
        dpi = primary_screen.logicalDotsPerInch()
        device_pixel_ratio = primary_screen.devicePixelRatio()
        physical_dpi = primary_screen.physicalDotsPerInch()

        cls._cached_screen_info = ScreenInfo(
            width=geometry.width(),
            height=geometry.height(),
            dpi=dpi,
            device_pixel_ratio=device_pixel_ratio,
            physical_dpi=physical_dpi,
        )

        logger.debug(f"Screen info updated: {cls._cached_screen_info}")

    @classmethod
    def get_scaling_factor(cls) -> float:
        """Get the current UI scaling factor.

        This combines DPI scaling and font scaling to provide a comprehensive
        scaling factor for UI elements.

        Returns:
            float: Scaling factor (1.0 = standard DPI/font, >1.0 = scaled up)
        """
        screen_info = cls.get_screen_info()

        # DPI-based scaling (96 DPI is considered standard)
        dpi_scale = screen_info.dpi / 96.0

        # Font-based scaling (12pt is considered base size)
        app = QApplication.instance()
        if app is not None:
            # Cast to QGuiApplication to access font method
            gui_app = QGuiApplication.instance()
            if gui_app is None:
                gui_app = app  # QApplication inherits from QGuiApplication
            current_font = gui_app.font()
            font_scale = current_font.pointSize() / cls._base_font_size
        else:
            font_scale = 1.0

        # Use the maximum of DPI and font scaling to ensure readability
        scaling_factor = max(dpi_scale, font_scale, screen_info.device_pixel_ratio)

        logger.debug(
            f"Calculated scaling factor: {scaling_factor} "
            f"(DPI: {dpi_scale}, Font: {font_scale}, "
            f"Device ratio: {screen_info.device_pixel_ratio})"
        )

        return scaling_factor

    @classmethod
    def get_scale_factor(cls) -> float:
        """Alias for get_scaling_factor for backward compatibility.

        Returns:
            float: Scaling factor (1.0 = standard DPI/font, >1.0 = scaled up)
        """
        return cls.get_scaling_factor()

    @classmethod
    def scale_px(cls, base_pixels: int) -> int:
        """Scale pixel values based on current DPI and font settings.

        Args:
            base_pixels: Base pixel value designed for standard DPI

        Returns:
            int: Scaled pixel value appropriate for current display
        """
        scaling_factor = cls.get_scale_factor()
        scaled = int(base_pixels * scaling_factor)

        # Ensure minimum of 1 pixel for non-zero inputs
        if base_pixels > 0 and scaled < 1:
            scaled = 1

        logger.debug(f"Scaled {base_pixels}px to {scaled}px (factor: {scaling_factor})")
        return scaled

    @classmethod
    def scale_size(cls, base_size: QSize) -> QSize:
        """Scale a QSize based on current DPI and font settings.

        Args:
            base_size: Base size designed for standard DPI

        Returns:
            QSize: Scaled size appropriate for current display
        """
        return QSize(cls.scale_px(base_size.width()), cls.scale_px(base_size.height()))

    @classmethod
    def calculate_responsive_height(cls, target_ratio: float, min_px: int, max_px: int | None = None) -> int:
        """Calculate responsive height based on screen size and constraints.

        Args:
            target_ratio: Target ratio of screen height (0.0-1.0)
            min_px: Minimum height in pixels (will be DPI-scaled)
            max_px: Maximum height in pixels (will be DPI-scaled), None for no max

        Returns:
            int: Calculated height in pixels
        """
        screen_info = cls.get_screen_info()

        # Calculate target height based on screen ratio
        target_height = int(screen_info.height * target_ratio)

        # Apply DPI scaling to constraints
        scaled_min = cls.scale_px(min_px)
        scaled_max = cls.scale_px(max_px) if max_px is not None else None

        # Apply constraints
        result_height = max(scaled_min, target_height)
        if scaled_max is not None:
            result_height = min(result_height, scaled_max)

        logger.debug(
            f"Calculated responsive height: {result_height}px "
            f"(target ratio: {target_ratio}, min: {scaled_min}px, "
            f"max: {scaled_max}px, screen: {screen_info.height}px)"
        )

        return result_height

    @classmethod
    def calculate_responsive_width(cls, target_ratio: float, min_px: int, max_px: int | None = None) -> int:
        """Calculate responsive width based on screen size and constraints.

        Args:
            target_ratio: Target ratio of screen width (0.0-1.0)
            min_px: Minimum width in pixels (will be DPI-scaled)
            max_px: Maximum width in pixels (will be DPI-scaled), None for no max

        Returns:
            int: Calculated width in pixels
        """
        screen_info = cls.get_screen_info()

        # Calculate target width based on screen ratio
        target_width = int(screen_info.width * target_ratio)

        # Apply DPI scaling to constraints
        scaled_min = cls.scale_px(min_px)
        scaled_max = cls.scale_px(max_px) if max_px is not None else None

        # Apply constraints
        result_width = max(scaled_min, target_width)
        if scaled_max is not None:
            result_width = min(result_width, scaled_max)

        logger.debug(
            f"Calculated responsive width: {result_width}px "
            f"(target ratio: {target_ratio}, min: {scaled_min}px, "
            f"max: {scaled_max}px, screen: {screen_info.width}px)"
        )

        return result_width

    @classmethod
    def get_content_based_height(cls, font: QFont | None = None, lines: int = 1, padding: int = 8) -> int:
        """Calculate height based on font metrics and content requirements.

        Args:
            font: Font to use for calculations, None for application default
            lines: Number of text lines to accommodate
            padding: Additional padding in pixels (will be DPI-scaled)

        Returns:
            int: Calculated height in pixels
        """
        app = QApplication.instance()
        if app is None:
            # Fallback calculation
            return cls.scale_px(24 * lines + padding)

        if font is None:
            # Cast to QGuiApplication to access font method
            gui_app = QGuiApplication.instance()
            if gui_app is None:
                gui_app = app  # QApplication inherits from QGuiApplication
            font = gui_app.font()

        # Calculate font metrics
        # Use QFontMetrics constructor instead of deprecated app.fontMetrics()
        from PySide6.QtGui import QFontMetrics

        font_metrics = QFontMetrics(font)
        line_height = font_metrics.height()

        # Calculate total height with padding
        total_height = (line_height * lines) + cls.scale_px(padding)

        logger.debug(
            f"Calculated content-based height: {total_height}px "
            f"(lines: {lines}, line height: {line_height}px, "
            f"padding: {cls.scale_px(padding)}px)"
        )

        return total_height

    @classmethod
    def is_small_screen(cls, threshold_width: int = 1366, threshold_height: int = 768) -> bool:
        """Check if the current screen should be considered 'small'.

        Args:
            threshold_width: Width threshold in pixels
            threshold_height: Height threshold in pixels

        Returns:
            bool: True if screen is considered small
        """
        screen_info = cls.get_screen_info()
        is_small = screen_info.width <= threshold_width or screen_info.height <= threshold_height

        logger.debug(
            f"Screen size check: {screen_info.width}x{screen_info.height} -> {'small' if is_small else 'normal'}"
        )

        return is_small

    @classmethod
    def get_layout_mode(cls) -> str:
        """Determine the appropriate layout mode based on screen characteristics.

        Returns:
            str: Layout mode ('compact', 'normal', 'spacious')
        """
        screen_info = cls.get_screen_info()

        # Small screens get compact layout
        if cls.is_small_screen():
            return "compact"

        # Very large screens can use spacious layout
        if screen_info.width >= 2560 and screen_info.height >= 1440:
            return "spacious"

        # Default to normal layout
        return "normal"

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached screen information to force refresh on next access."""
        cls._cached_screen_info = None
        logger.debug("Screen info cache cleared")

    # ========================================================================
    # UI Constants Integration
    # ========================================================================

    @classmethod
    def set_theme(cls, theme: str) -> None:
        """Set the current UI theme.

        Args:
            theme: Theme name ('light', 'dark', 'high_contrast')
        """
        if theme in ["light", "dark", "high_contrast"]:
            cls._current_theme = theme
            logger.debug(f"UI theme set to: {theme}")
        else:
            logger.warning(f"Invalid theme '{theme}', keeping current theme '{cls._current_theme}'")

    @classmethod
    def get_theme(cls) -> str:
        """Get the current UI theme.

        Returns:
            str: Current theme name
        """
        return cls._current_theme

    @classmethod
    def get_font_size(cls, size_key: str = "normal") -> int:
        """Get scaled font size from ui_constants.

        Args:
            size_key: Font size key from ui_constants.FONT_SIZES

        Returns:
            int: Scaled font size in pixels
        """
        scaling_factor = cls.get_scale_factor()
        return ui_constants.get_scaled_font_size(size_key, scaling_factor)

    @classmethod
    def get_font(cls, size_key: str = "normal", weight_key: str = "regular", family: str = "default") -> QFont:
        """Get a properly scaled QFont object.

        Args:
            size_key: Font size key from ui_constants.FONT_SIZES
            weight_key: Font weight key from ui_constants.FONT_WEIGHTS
            family: Font family key from ui_constants.FONT_FAMILIES or custom family

        Returns:
            QFont: Configured font object
        """
        font_size = cls.get_font_size(size_key)
        font_family = ui_constants.FONT_FAMILIES.get(family, family)

        font = QFont()
        font.setFamily(font_family)
        font.setPixelSize(font_size)

        # Set weight
        weight_str = ui_constants.FONT_WEIGHTS.get(weight_key, "Normal")
        if weight_str == "Bold":
            font.setBold(True)
        elif weight_str == "Medium":
            font.setWeight(QFont.Weight.Medium)

        return font

    @classmethod
    def get_spacing(cls, spacing_key: str = "m") -> int:
        """Get scaled spacing value from ui_constants.

        Args:
            spacing_key: Spacing key from ui_constants.SPACING

        Returns:
            int: Scaled spacing in pixels
        """
        scaling_factor = cls.get_scale_factor()
        return ui_constants.get_scaled_spacing(spacing_key, scaling_factor)

    @classmethod
    def get_margin(cls, margin_key: str = "control") -> int:
        """Get scaled margin value.

        Args:
            margin_key: Margin key from ui_constants.MARGINS

        Returns:
            int: Scaled margin in pixels
        """
        base_margin = ui_constants.MARGINS.get(margin_key, ui_constants.SPACING["m"])
        return cls.scale_px(base_margin)

    @classmethod
    def get_padding(cls, padding_key: str = "panel") -> tuple[int, int]:
        """Get scaled padding values.

        Args:
            padding_key: Padding key from ui_constants.PADDING

        Returns:
            tuple[int, int]: Scaled padding (vertical, horizontal) or single value
        """
        base_padding = ui_constants.PADDING.get(padding_key, ui_constants.SPACING["m"])

        if isinstance(base_padding, tuple):
            return (cls.scale_px(base_padding[0]), cls.scale_px(base_padding[1]))
        else:
            scaled = cls.scale_px(base_padding)
            return (scaled, scaled)

    @classmethod
    def get_min_size(cls, size_key: str) -> int:
        """Get scaled minimum size value.

        Args:
            size_key: Size key from ui_constants.MIN_SIZES

        Returns:
            int: Scaled minimum size in pixels
        """
        base_size = ui_constants.MIN_SIZES.get(size_key, 32)
        return cls.scale_px(base_size)

    @classmethod
    def get_max_size(cls, size_key: str) -> int:
        """Get scaled maximum size value.

        Args:
            size_key: Size key from ui_constants.MAX_SIZES

        Returns:
            int: Scaled maximum size in pixels
        """
        base_size = ui_constants.MAX_SIZES.get(size_key, 300)
        return cls.scale_px(base_size)

    @classmethod
    def get_color(cls, color_key: str, theme: str | None = None) -> str:
        """Get color value for current or specified theme.

        Args:
            color_key: Color key from theme color dictionaries
            theme: Override theme, None uses current theme

        Returns:
            str: Color value as hex string
        """
        theme = theme or cls._current_theme
        colors = ui_constants.get_theme_colors(theme)
        return colors.get(color_key, "#000000")

    @classmethod
    def get_curve_color(cls, color_key: str) -> str:
        """Get curve visualization color.

        Args:
            color_key: Color key from ui_constants.CURVE_COLORS

        Returns:
            str: Color value as hex string or rgba string
        """
        color = ui_constants.CURVE_COLORS.get(color_key, "#000000")

        # Convert RGBA tuples to CSS format
        if isinstance(color, tuple) and len(color) == 4:
            return ui_constants.format_rgba(color)

        return color

    @classmethod
    def get_border_radius(cls, radius_key: str = "medium") -> int:
        """Get scaled border radius value.

        Args:
            radius_key: Radius key from ui_constants.BORDER_RADIUS

        Returns:
            int: Scaled border radius in pixels
        """
        base_radius = ui_constants.BORDER_RADIUS.get(radius_key, 4)
        return cls.scale_px(base_radius)

    @classmethod
    def apply_theme_stylesheet(cls, widget, component_type: str = "default") -> None:
        """Apply theme-aware stylesheet to a widget.

        Args:
            widget: Qt widget to style
            component_type: Component type for specific styling
        """
        colors = ui_constants.get_theme_colors(cls._current_theme)
        # spacing = cls.get_spacing("s")  # Not used in current stylesheet
        padding = cls.get_padding("button")
        border_radius = cls.get_border_radius("medium")

        # Base stylesheet template
        stylesheet = f"""
        QWidget {{
            background-color: {colors["bg_primary"]};
            color: {colors["text_primary"]};
            font-size: {cls.get_font_size("normal")}px;
        }}
        QPushButton {{
            background-color: {colors["bg_secondary"]};
            border: 1px solid {colors["border_default"]};
            border-radius: {border_radius}px;
            padding: {padding[0]}px {padding[1]}px;
            min-height: {cls.get_min_size("button_height")}px;
            min-width: {cls.get_min_size("button_width")}px;
        }}
        QPushButton:hover {{
            background-color: {colors["bg_hover"]};
        }}
        QPushButton:pressed {{
            background-color: {colors["bg_selected"]};
        }}
        QPushButton:focus {{
            border: 2px solid {colors["border_focus"]};
            outline: 2px solid {colors["border_focus"]};
            outline-offset: 2px;
        }}
        QPushButton:disabled {{
            background-color: {colors["bg_disabled"]};
            color: {colors["text_disabled"]};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors["bg_input"]};
            border: 1px solid {colors["border_default"]};
            border-radius: {cls.get_border_radius("small")}px;
            padding: {cls.get_spacing("xs")}px;
            min-height: {cls.get_min_size("input_height")}px;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {colors["border_focus"]};
            outline: none;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 2px solid {colors["border_focus"]};
            outline: none;
        }}
        QSlider:focus {{
            outline: 2px solid {colors["border_focus"]};
            outline-offset: 2px;
        }}
        QCheckBox:focus, QRadioButton:focus {{
            outline: 2px solid {colors["border_focus"]};
            outline-offset: 2px;
        }}
        QLabel {{
            color: {colors["text_secondary"]};
        }}
        QGroupBox {{
            font-weight: 600;
            font-size: {cls.get_font_size("normal")}px;
            color: {colors["text_primary"]};
            border: 2px solid {colors["accent_primary"]};
            border-radius: {cls.get_border_radius("medium")}px;
            margin-top: {cls.scale_px(14)}px;
            padding-top: {cls.scale_px(10)}px;
            background-color: {colors["bg_secondary"]};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 {cls.get_spacing("s")}px;
            left: {cls.scale_px(12)}px;
            background-color: {colors["bg_primary"]};
            color: {colors["accent_primary"]};
        }}
        """

        widget.setStyleSheet(stylesheet)


# Convenience functions for common operations
def scale_px(pixels: int) -> int:
    """Convenience function for scaling pixels."""
    return UIScaling.scale_px(pixels)


def get_responsive_height(target_ratio: float, min_px: int, max_px: int | None = None) -> int:
    """Convenience function for calculating responsive height."""
    return UIScaling.calculate_responsive_height(target_ratio, min_px, max_px)


def get_responsive_width(target_ratio: float, min_px: int, max_px: int | None = None) -> int:
    """Convenience function for calculating responsive width."""
    return UIScaling.calculate_responsive_width(target_ratio, min_px, max_px)


def get_content_height(lines: int = 1, padding: int = 8) -> int:
    """Convenience function for calculating content-based height."""
    return UIScaling.get_content_based_height(lines=lines, padding=padding)
