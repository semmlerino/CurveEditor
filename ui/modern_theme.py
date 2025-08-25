#!/usr/bin/env python
"""
Modern Theme System for CurveEditor
Implements a comprehensive theming system with modern visual design patterns
"""

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from ui.ui_constants import BORDER_RADIUS, COLORS_DARK, COLORS_LIGHT, FONT_SIZES, SPACING


class ModernTheme(QObject):
    """Modern theme manager with comprehensive styling system."""

    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self.animations_enabled = True

    def get_stylesheet(self) -> str:
        """Generate complete application stylesheet with modern design patterns."""
        colors = COLORS_LIGHT if self.current_theme == "light" else COLORS_DARK

        return f"""
        /* ==================== Global Styles ==================== */
        QWidget {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            font-size: {FONT_SIZES['normal']}px;
            color: {colors['text_primary']};
            background-color: {colors['bg_primary']};
        }}

        /* ==================== Main Window ==================== */
        QMainWindow {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {colors['bg_secondary']},
                stop:1 {colors['bg_primary']});
        }}

        /* ==================== Modern Cards (GroupBox) ==================== */
        QGroupBox {{
            background-color: {colors['bg_elevated']};
            border: none;
            border-radius: {BORDER_RADIUS['large']}px;
            margin-top: {SPACING['l']}px;
            padding-top: {SPACING['m']}px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {SPACING['m']}px;
            padding: 0 {SPACING['s']}px;
            color: {colors['text_primary']};
            font-size: {FONT_SIZES['medium']}px;
            font-weight: 600;
        }}

        /* ==================== Modern Buttons ==================== */
        QPushButton {{
            background-color: {colors['button_primary_bg']};
            color: white;
            border: none;
            border-radius: {BORDER_RADIUS['medium']}px;
            padding: {SPACING['s']}px {SPACING['l']}px;
            font-weight: 500;
            min-height: 32px;
            min-width: 80px;
        }}

        QPushButton:hover {{
            background-color: {colors['button_primary_hover']};
            margin-top: -1px;
        }}

        QPushButton:pressed {{
            background-color: {colors['button_primary_active']};
            margin-top: 0px;
        }}

        QPushButton:disabled {{
            background-color: {colors['bg_disabled']};
            color: {colors['text_disabled']};
        }}

        /* Ghost Button Variant */
        QPushButton[ghost="true"] {{
            background-color: transparent;
            color: {colors['accent_primary']};
            border: 1px solid {colors['accent_primary']};
        }}

        QPushButton[ghost="true"]:hover {{
            background-color: {colors['accent_primary']};
            color: white;
        }}

        /* Icon-only Buttons */
        QPushButton[icon-only="true"] {{
            background-color: transparent;
            border: none;
            border-radius: {BORDER_RADIUS['large']}px;
            padding: {SPACING['s']}px;
            min-width: 44px;
            min-height: 44px;
        }}

        QPushButton[icon-only="true"]:hover {{
            background-color: {colors['bg_hover']};
        }}

        /* ==================== Modern Tool Buttons ==================== */
        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: {BORDER_RADIUS['medium']}px;
            padding: {SPACING['s']}px;
            min-width: 44px;
            min-height: 44px;
        }}

        QToolButton:hover {{
            background-color: {colors['bg_hover']};
        }}

        QToolButton:pressed {{
            background-color: {colors['bg_selected']};
        }}

        QToolButton:checked {{
            background-color: {colors['accent_primary']};
            color: white;
        }}

        /* Timeline Tab Buttons */
        QToolButton#timelineTab {{
            background-color: {colors['bg_secondary']};
            border: 1px solid {colors['border_default']};
            border-radius: {BORDER_RADIUS['small']}px;
            color: {colors['text_primary']};
            font-weight: bold;
            min-width: 40px;
            min-height: 40px;
        }}

        QToolButton#timelineTab:hover {{
            background-color: {colors['bg_hover']};
            border-color: {colors['border_hover']};
        }}

        QToolButton#timelineTab:checked {{
            background-color: {colors['accent_primary']};
            border: 2px solid {colors['accent_secondary']};
            color: white;
        }}

        QToolButton#timelineTab:pressed {{
            background-color: {colors['button_primary_active']};
        }}

        /* ==================== Modern Input Fields ==================== */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {colors['bg_input']};
            border: 2px solid {colors['border_default']};
            border-radius: {BORDER_RADIUS['medium']}px;
            padding: {SPACING['s']}px {SPACING['m']}px;
            font-size: {FONT_SIZES['normal']}px;
            selection-background-color: {colors['accent_primary']};
            selection-color: white;
        }}

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {colors['border_focus']};
            outline: none;
            background-color: {colors['bg_elevated']};
        }}

        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
            border-color: {colors['border_hover']};
        }}

        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
            background-color: {colors['bg_disabled']};
            color: {colors['text_disabled']};
            border-color: {colors['border_default']};
        }}

        /* ==================== Modern Sliders ==================== */
        QSlider {{
            min-height: 30px;
        }}

        QSlider::groove:horizontal {{
            background: {colors['bg_secondary']};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background: {colors['accent_primary']};
            width: 20px;
            height: 20px;
            border-radius: 10px;
            margin: -7px 0;
        }}

        QSlider::handle:horizontal:hover {{
            background: {colors['button_primary_hover']};
            width: 24px;
            height: 24px;
            margin: -9px 0;
        }}

        QSlider::sub-page:horizontal {{
            background: {colors['accent_primary']};
            border-radius: 3px;
        }}

        /* ==================== Modern Checkboxes ==================== */
        QCheckBox {{
            spacing: {SPACING['s']}px;
            font-size: {FONT_SIZES['normal']}px;
        }}

        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: {BORDER_RADIUS['small']}px;
            border: 2px solid {colors['border_default']};
            background-color: {colors['bg_input']};
        }}

        QCheckBox::indicator:checked {{
            background-color: {colors['accent_primary']};
            border-color: {colors['accent_primary']};
        }}

        QCheckBox::indicator:checked:after {{
            content: "✓";
            color: white;
            font-size: 12px;
            font-weight: bold;
            position: absolute;
            left: 2px;
            top: -1px;
        }}

        QCheckBox::indicator:hover {{
            border-color: {colors['border_hover']};
        }}

        /* ==================== Modern Toolbar ==================== */
        QToolBar {{
            background: {colors['bg_elevated']};
            border: none;
            border-bottom: 1px solid {colors['border_default']};
            padding: {SPACING['s']}px;
            spacing: {SPACING['s']}px;
        }}

        QToolBar::separator {{
            background: {colors['border_default']};
            width: 1px;
            margin: {SPACING['s']}px;
        }}

        /* ==================== Modern Status Bar ==================== */
        QStatusBar {{
            background: {colors['bg_secondary']};
            border-top: 1px solid {colors['border_default']};
            font-size: {FONT_SIZES['small']}px;
            color: {colors['text_secondary']};
            padding: {SPACING['xs']}px;
        }}

        /* ==================== Modern Tabs ==================== */
        QTabWidget::pane {{
            background: {colors['bg_elevated']};
            border: 1px solid {colors['border_default']};
            border-radius: {BORDER_RADIUS['medium']}px;
        }}

        QTabBar::tab {{
            background: {colors['bg_secondary']};
            color: {colors['text_secondary']};
            padding: {SPACING['s']}px {SPACING['l']}px;
            margin-right: {SPACING['xs']}px;
            border-top-left-radius: {BORDER_RADIUS['medium']}px;
            border-top-right-radius: {BORDER_RADIUS['medium']}px;
            font-weight: 500;
        }}

        QTabBar::tab:selected {{
            background: {colors['bg_elevated']};
            color: {colors['text_primary']};
            border-bottom: 2px solid {colors['accent_primary']};
        }}

        QTabBar::tab:hover {{
            background: {colors['bg_hover']};
        }}

        /* ==================== Modern Scrollbars ==================== */
        QScrollBar:vertical {{
            background: {colors['bg_secondary']};
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background: {colors['border_default']};
            border-radius: 6px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {colors['border_hover']};
        }}

        QScrollBar:horizontal {{
            background: {colors['bg_secondary']};
            height: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:horizontal {{
            background: {colors['border_default']};
            border-radius: 6px;
            min-width: 30px;
        }}

        /* ==================== Modern Tooltips ==================== */
        QToolTip {{
            background-color: {colors['bg_elevated']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_default']};
            border-radius: {BORDER_RADIUS['medium']}px;
            padding: {SPACING['s']}px {SPACING['m']}px;
            font-size: {FONT_SIZES['small']}px;
        }}

        /* ==================== Modern Menu ==================== */
        QMenu {{
            background-color: {colors['bg_elevated']};
            border: 1px solid {colors['border_default']};
            border-radius: {BORDER_RADIUS['medium']}px;
            padding: {SPACING['s']}px 0;
        }}

        QMenu::item {{
            padding: {SPACING['s']}px {SPACING['xl']}px;
            color: {colors['text_primary']};
        }}

        QMenu::item:selected {{
            background-color: {colors['bg_hover']};
        }}

        QMenu::separator {{
            height: 1px;
            background: {colors['border_default']};
            margin: {SPACING['s']}px 0;
        }}

        /* ==================== Focus Indicators ==================== */
        *:focus {{
            outline: 2px solid {colors['accent_primary']};
            outline-offset: 2px;
        }}
        """

    def apply_card_shadow(self, widget: QWidget, intensity: str = "medium") -> None:
        """Apply modern card shadow effect to widget."""
        shadow = QGraphicsDropShadowEffect()

        shadow_configs = {
            "small": (10, 0, 1, QColor(0, 0, 0, 20)),
            "medium": (15, 0, 2, QColor(0, 0, 0, 30)),
            "large": (20, 0, 4, QColor(0, 0, 0, 40)),
        }

        config = shadow_configs.get(intensity, shadow_configs["medium"])
        shadow.setBlurRadius(config[0])
        shadow.setXOffset(config[1])
        shadow.setYOffset(config[2])
        shadow.setColor(config[3])

        widget.setGraphicsEffect(shadow)

    def create_hover_animation(self, widget: QWidget, property_name: bytes = b"geometry") -> QPropertyAnimation:
        """Create smooth hover animation for widget."""
        animation = QPropertyAnimation(widget, property_name)
        animation.setDuration(200)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        return animation

    def switch_theme(self, theme: str) -> None:
        """Switch between light and dark themes."""
        if theme in ["light", "dark"]:
            self.current_theme = theme
            self.theme_changed.emit(theme)
