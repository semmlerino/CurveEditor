#!/usr/bin/env python
"""
Theme Manager for CurveEditor.

Provides a modern theme system with light, dark, and high-contrast modes.
Handles application-wide styling, color schemes, and icon management.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory, QWidget

logger = logging.getLogger("theme_manager")


class ThemeMode(Enum):
    """Available theme modes."""
    LIGHT = auto()
    DARK = auto()
    HIGH_CONTRAST = auto()
    AUTO = auto()  # Follow system theme


@dataclass
class ColorScheme:
    """Color scheme for a theme."""
    # Primary colors
    background: str = "#FFFFFF"
    foreground: str = "#000000"
    primary: str = "#0066CC"
    secondary: str = "#6C757D"
    accent: str = "#28A745"

    # UI element colors
    surface: str = "#F8F9FA"
    surface_variant: str = "#E9ECEF"
    border: str = "#DEE2E6"
    border_focus: str = "#0066CC"

    # Text colors
    text_primary: str = "#212529"
    text_secondary: str = "#6C757D"
    text_disabled: str = "#ADB5BD"
    text_link: str = "#0066CC"

    # Status colors
    success: str = "#28A745"
    warning: str = "#FFC107"
    error: str = "#DC3545"
    info: str = "#17A2B8"

    # Curve editor specific
    grid: str = "#E9ECEF"
    curve_line: str = "#0066CC"
    curve_point: str = "#28A745"
    curve_point_selected: str = "#DC3545"
    curve_keyframe: str = "#FFC107"
    curve_interpolated: str = "#6C757D"
    velocity_vector: str = "#17A2B8"

    # Transparency values
    overlay_alpha: float = 0.7
    grid_alpha: float = 0.3
    selection_alpha: float = 0.2


# Predefined color schemes
LIGHT_SCHEME = ColorScheme()

DARK_SCHEME = ColorScheme(
    background="#1E1E1E",
    foreground="#E0E0E0",
    primary="#4FC3F7",
    secondary="#9E9E9E",
    accent="#66BB6A",
    surface="#2D2D2D",
    surface_variant="#3C3C3C",
    border="#4A4A4A",
    border_focus="#4FC3F7",
    text_primary="#E0E0E0",
    text_secondary="#B0B0B0",
    text_disabled="#757575",
    text_link="#4FC3F7",
    success="#66BB6A",
    warning="#FFCA28",
    error="#EF5350",
    info="#29B6F6",
    grid="#3C3C3C",
    curve_line="#4FC3F7",
    curve_point="#66BB6A",
    curve_point_selected="#EF5350",
    curve_keyframe="#FFCA28",
    curve_interpolated="#9E9E9E",
    velocity_vector="#29B6F6",
)

HIGH_CONTRAST_SCHEME = ColorScheme(
    background="#000000",
    foreground="#FFFFFF",
    primary="#00FFFF",
    secondary="#FFFF00",
    accent="#00FF00",
    surface="#000000",
    surface_variant="#1A1A1A",
    border="#FFFFFF",
    border_focus="#00FFFF",
    text_primary="#FFFFFF",
    text_secondary="#FFFF00",
    text_disabled="#808080",
    text_link="#00FFFF",
    success="#00FF00",
    warning="#FFFF00",
    error="#FF0000",
    info="#00FFFF",
    grid="#404040",
    curve_line="#00FFFF",
    curve_point="#00FF00",
    curve_point_selected="#FF0000",
    curve_keyframe="#FFFF00",
    curve_interpolated="#C0C0C0",
    velocity_vector="#00FFFF",
)


class ThemeManager(QObject):
    """Manages application themes and styling."""

    # Signals
    theme_changed = Signal(ThemeMode)
    colors_changed = Signal(ColorScheme)

    def __init__(self, parent: QObject | None = None):
        """Initialize the theme manager."""
        super().__init__(parent)

        self._current_mode = ThemeMode.LIGHT
        self._current_scheme = LIGHT_SCHEME
        self._custom_schemes: dict[str, ColorScheme] = {}
        self._settings_path = Path.home() / ".curve_editor" / "theme.json"

        # Load saved theme preferences
        self._load_preferences()

    @property
    def current_mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._current_mode

    @property
    def current_scheme(self) -> ColorScheme:
        """Get current color scheme."""
        return self._current_scheme

    @property
    def colors(self) -> ColorScheme:
        """Alias for current_scheme for convenience."""
        return self._current_scheme

    @Slot(ThemeMode)
    def set_theme(self, mode: ThemeMode) -> None:
        """Set the application theme."""
        if mode == self._current_mode:
            return

        self._current_mode = mode

        # Select appropriate color scheme
        if mode == ThemeMode.LIGHT:
            self._current_scheme = LIGHT_SCHEME
        elif mode == ThemeMode.DARK:
            self._current_scheme = DARK_SCHEME
        elif mode == ThemeMode.HIGH_CONTRAST:
            self._current_scheme = HIGH_CONTRAST_SCHEME
        elif mode == ThemeMode.AUTO:
            # Detect system theme (simplified - would need platform-specific code)
            self._current_scheme = self._detect_system_scheme()

        # Apply theme to application
        self._apply_theme()

        # Save preference
        self._save_preferences()

        # Emit signals
        self.theme_changed.emit(mode)
        self.colors_changed.emit(self._current_scheme)

        logger.info(f"Theme changed to: {mode.name}")

    def _detect_system_scheme(self) -> ColorScheme:
        """Detect system color scheme (simplified implementation)."""
        # This would need platform-specific code to properly detect
        # For now, check if palette is dark
        app = QApplication.instance()
        if app:
            palette = app.palette()
            bg_color = palette.color(QPalette.ColorRole.Window)
            is_dark = bg_color.lightness() < 128
            return DARK_SCHEME if is_dark else LIGHT_SCHEME
        return LIGHT_SCHEME

    def _apply_theme(self) -> None:
        """Apply current theme to the application."""
        app = QApplication.instance()
        if not app:
            return

        # Create and apply palette
        palette = self._create_palette()
        app.setPalette(palette)

        # Apply stylesheet
        stylesheet = self._generate_stylesheet()
        app.setStyleSheet(stylesheet)

        # Set application style (Fusion works well with custom palettes)
        app.setStyle(QStyleFactory.create("Fusion"))

    def _create_palette(self) -> QPalette:
        """Create QPalette from current color scheme."""
        palette = QPalette()
        scheme = self._current_scheme

        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(scheme.background))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(scheme.foreground))

        # Base colors (for input widgets)
        palette.setColor(QPalette.ColorRole.Base, QColor(scheme.surface))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(scheme.surface_variant))
        palette.setColor(QPalette.ColorRole.Text, QColor(scheme.text_primary))

        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(scheme.surface))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(scheme.text_primary))

        # Highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(scheme.primary))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

        # Other colors
        palette.setColor(QPalette.ColorRole.Link, QColor(scheme.text_link))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(scheme.secondary))

        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText,
                        QColor(scheme.text_disabled))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,
                        QColor(scheme.text_disabled))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,
                        QColor(scheme.text_disabled))

        return palette

    def _generate_stylesheet(self) -> str:
        """Generate Qt stylesheet from current color scheme."""
        scheme = self._current_scheme

        stylesheet = f"""
        /* Main Window */
        QMainWindow {{
            background-color: {scheme.background};
            color: {scheme.foreground};
        }}

        /* Menus */
        QMenuBar {{
            background-color: {scheme.surface};
            color: {scheme.text_primary};
            border-bottom: 1px solid {scheme.border};
        }}

        QMenuBar::item:selected {{
            background-color: {scheme.primary};
            color: white;
        }}

        QMenu {{
            background-color: {scheme.surface};
            color: {scheme.text_primary};
            border: 1px solid {scheme.border};
        }}

        QMenu::item:selected {{
            background-color: {scheme.primary};
            color: white;
        }}

        /* Toolbars */
        QToolBar {{
            background-color: {scheme.surface};
            border: none;
            spacing: 3px;
            padding: 4px;
        }}

        QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 3px;
            padding: 4px;
        }}

        QToolButton:hover {{
            background-color: {scheme.surface_variant};
            border: 1px solid {scheme.border};
        }}

        QToolButton:pressed {{
            background-color: {scheme.primary};
            color: white;
        }}

        /* Push Buttons */
        QPushButton {{
            background-color: {scheme.surface};
            color: {scheme.text_primary};
            border: 1px solid {scheme.border};
            border-radius: 4px;
            padding: 5px 15px;
            min-width: 60px;
        }}

        QPushButton:hover {{
            background-color: {scheme.surface_variant};
            border: 1px solid {scheme.border_focus};
        }}

        QPushButton:pressed {{
            background-color: {scheme.primary};
            color: white;
        }}

        QPushButton:disabled {{
            background-color: {scheme.surface};
            color: {scheme.text_disabled};
            border: 1px solid {scheme.border};
        }}

        /* Input widgets */
        QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
            background-color: {scheme.surface};
            color: {scheme.text_primary};
            border: 1px solid {scheme.border};
            border-radius: 3px;
            padding: 4px;
        }}

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
        QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {scheme.border_focus};
        }}

        /* Checkboxes */
        QCheckBox {{
            color: {scheme.text_primary};
            spacing: 5px;
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {scheme.border};
            border-radius: 3px;
            background-color: {scheme.surface};
        }}

        QCheckBox::indicator:checked {{
            background-color: {scheme.primary};
            border: 1px solid {scheme.primary};
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            height: 6px;
            background-color: {scheme.surface_variant};
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            width: 16px;
            height: 16px;
            background-color: {scheme.primary};
            border-radius: 8px;
            margin: -5px 0;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {scheme.accent};
        }}

        /* Progress bars */
        QProgressBar {{
            background-color: {scheme.surface_variant};
            border: 1px solid {scheme.border};
            border-radius: 3px;
            text-align: center;
            color: {scheme.text_primary};
        }}

        QProgressBar::chunk {{
            background-color: {scheme.primary};
            border-radius: 2px;
        }}

        /* Tab widgets */
        QTabWidget::pane {{
            background-color: {scheme.background};
            border: 1px solid {scheme.border};
        }}

        QTabBar::tab {{
            background-color: {scheme.surface};
            color: {scheme.text_primary};
            padding: 5px 10px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {scheme.background};
            border-bottom: 2px solid {scheme.primary};
        }}

        /* Status bar */
        QStatusBar {{
            background-color: {scheme.surface};
            color: {scheme.text_secondary};
            border-top: 1px solid {scheme.border};
        }}

        /* Tooltips */
        QToolTip {{
            background-color: {scheme.surface_variant};
            color: {scheme.text_primary};
            border: 1px solid {scheme.border};
            padding: 4px;
        }}

        /* Scroll bars */
        QScrollBar:vertical {{
            background-color: {scheme.surface};
            width: 12px;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background-color: {scheme.border};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {scheme.secondary};
        }}

        QScrollBar:horizontal {{
            background-color: {scheme.surface};
            height: 12px;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {scheme.border};
            border-radius: 6px;
            min-width: 20px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {scheme.secondary};
        }}
        """

        return stylesheet

    def get_color(self, name: str) -> QColor:
        """Get a color from the current scheme by name."""
        color_str = getattr(self._current_scheme, name, "#000000")
        return QColor(color_str)

    def get_curve_colors(self) -> dict[str, QColor]:
        """Get colors specific to curve rendering."""
        scheme = self._current_scheme
        return {
            "line": QColor(scheme.curve_line),
            "point": QColor(scheme.curve_point),
            "point_selected": QColor(scheme.curve_point_selected),
            "keyframe": QColor(scheme.curve_keyframe),
            "interpolated": QColor(scheme.curve_interpolated),
            "velocity": QColor(scheme.velocity_vector),
            "grid": QColor(scheme.grid),
        }

    def _load_preferences(self) -> None:
        """Load saved theme preferences."""
        if not self._settings_path.exists():
            return

        try:
            with open(self._settings_path) as f:
                data = json.load(f)
                mode_name = data.get("mode", "LIGHT")
                if mode_name in ThemeMode.__members__:
                    self._current_mode = ThemeMode[mode_name]
                    self.set_theme(self._current_mode)
        except Exception as e:
            logger.error(f"Failed to load theme preferences: {e}")

    def _save_preferences(self) -> None:
        """Save current theme preferences."""
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._settings_path, "w") as f:
                json.dump({"mode": self._current_mode.name}, f)
        except Exception as e:
            logger.error(f"Failed to save theme preferences: {e}")

    def create_custom_scheme(self, name: str, base: ColorScheme) -> ColorScheme:
        """Create a custom color scheme based on an existing one."""
        custom = ColorScheme(**base.__dict__)
        self._custom_schemes[name] = custom
        return custom

    def apply_to_widget(self, widget: QWidget) -> None:
        """Apply current theme to a specific widget."""
        # Useful for dynamically created widgets
        palette = self._create_palette()
        widget.setPalette(palette)

        # Apply any widget-specific styling
        widget_type = widget.__class__.__name__
        if widget_type == "CurveViewWidget":
            # Special handling for curve view widget
            self._style_curve_view(widget)

    def _style_curve_view(self, widget: Any) -> None:
        """Apply theme-specific styling to curve view widget."""
        # This would set colors for curve rendering
        if hasattr(widget, "set_colors"):
            widget.set_colors(self.get_curve_colors())


# Singleton instance
_theme_manager: ThemeManager | None = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
