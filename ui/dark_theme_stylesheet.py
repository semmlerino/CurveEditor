#!/usr/bin/env python
"""
Dark Theme Stylesheet for CurveEditor.

Comprehensive Qt stylesheet providing consistent dark theme styling
for all widgets in the application.
"""

from .ui_constants import COLORS_DARK


def get_dark_theme_stylesheet() -> str:
    """Get the complete dark theme stylesheet for the application.

    Returns a comprehensive Qt stylesheet using colors from COLORS_DARK.
    Covers all standard Qt widgets with consistent dark theme styling.
    """
    colors = COLORS_DARK

    return f"""
    /* ========================================================================
       BASE STYLES - Applied to all widgets
       ======================================================================== */

    * {{
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }}

    QWidget {{
        background-color: {colors['bg_primary']};
        color: {colors['text_primary']};
    }}

    /* ========================================================================
       MAIN CONTAINERS
       ======================================================================== */

    QMainWindow {{
        background-color: {colors['bg_primary']};
    }}

    QDialog {{
        background-color: {colors['bg_primary']};
        color: {colors['text_primary']};
    }}

    QFrame {{
        background-color: {colors['bg_primary']};
        color: {colors['text_primary']};
        border: none;
    }}

    /* ========================================================================
       MENUS AND TOOLBARS
       ======================================================================== */

    QMenuBar {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        border-bottom: 1px solid {colors['border_default']};
        padding: 3px;
    }}

    QMenuBar::item {{
        padding: 4px 8px;
        background: transparent;
    }}

    QMenuBar::item:selected {{
        background-color: {colors['bg_hover']};
    }}

    QMenu {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        padding: 4px;
    }}

    QMenu::item {{
        padding: 5px 25px 5px 20px;
        margin: 2px;
    }}

    QMenu::item:selected {{
        background-color: {colors['accent_primary']};
    }}

    QMenu::item:disabled {{
        color: {colors['text_disabled']};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {colors['border_default']};
        margin: 4px 10px;
    }}

    QToolBar {{
        background-color: {colors['bg_secondary']};
        border: none;
        spacing: 3px;
        padding: 4px;
    }}

    QToolButton {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 3px;
        padding: 4px;
        color: {colors['text_primary']};
    }}

    QToolButton:hover {{
        background-color: {colors['bg_hover']};
        border: 1px solid {colors['border_hover']};
    }}

    QToolButton:pressed {{
        background-color: {colors['accent_primary']};
    }}

    QToolButton:checked {{
        background-color: {colors['accent_primary']};
        border: 1px solid {colors['accent_primary']};
    }}

    /* ========================================================================
       BUTTONS
       ======================================================================== */

    QPushButton {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        border-radius: 3px;
        padding: 5px 12px;
        min-width: 60px;
    }}

    QPushButton:hover {{
        background-color: {colors['bg_hover']};
        border: 1px solid {colors['border_hover']};
    }}

    QPushButton:pressed {{
        background-color: {colors['accent_primary']};
    }}

    QPushButton:disabled {{
        color: {colors['text_disabled']};
        background-color: {colors['bg_disabled']};
        border: 1px solid {colors['bg_disabled']};
    }}

    QPushButton:default {{
        border: 2px solid {colors['accent_primary']};
    }}

    /* ========================================================================
       INPUT FIELDS
       ======================================================================== */

    QLineEdit {{
        background-color: {colors['bg_input']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        border-radius: 3px;
        padding: 4px;
        selection-background-color: {colors['accent_primary']};
    }}

    QLineEdit:focus {{
        border: 1px solid {colors['border_focus']};
    }}

    QLineEdit:disabled {{
        background-color: {colors['bg_disabled']};
        color: {colors['text_disabled']};
    }}

    QSpinBox, QDoubleSpinBox {{
        background-color: {colors['bg_input']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        border-radius: 3px;
        padding: 4px;
        selection-background-color: {colors['accent_primary']};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {colors['border_focus']};
    }}

    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: {colors['bg_disabled']};
        color: {colors['text_disabled']};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        background-color: {colors['bg_secondary']};
        border-left: 1px solid {colors['border_default']};
    }}

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
        background-color: {colors['bg_hover']};
    }}

    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background-color: {colors['bg_secondary']};
        border-left: 1px solid {colors['border_default']};
    }}

    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {colors['bg_hover']};
    }}

    QComboBox {{
        background-color: {colors['bg_input']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        border-radius: 3px;
        padding: 4px;
        min-width: 75px;
    }}

    QComboBox:hover {{
        border: 1px solid {colors['border_hover']};
    }}

    QComboBox:focus {{
        border: 1px solid {colors['border_focus']};
    }}

    QComboBox::drop-down {{
        border: none;
        background-color: {colors['bg_secondary']};
    }}

    QComboBox::down-arrow {{
        width: 12px;
        height: 12px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        selection-background-color: {colors['accent_primary']};
        border: 1px solid {colors['border_default']};
    }}

    /* ========================================================================
       CHECKBOXES AND RADIO BUTTONS
       ======================================================================== */

    QCheckBox {{
        color: {colors['text_primary']};
        spacing: 5px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {colors['border_default']};
        border-radius: 3px;
        background-color: {colors['bg_input']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {colors['accent_primary']};
        border: 1px solid {colors['accent_primary']};
    }}

    QCheckBox::indicator:disabled {{
        background-color: {colors['bg_disabled']};
        border: 1px solid {colors['bg_disabled']};
    }}

    QRadioButton {{
        color: {colors['text_primary']};
        spacing: 5px;
    }}

    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {colors['border_default']};
        border-radius: 8px;
        background-color: {colors['bg_input']};
    }}

    QRadioButton::indicator:checked {{
        background-color: {colors['accent_primary']};
        border: 1px solid {colors['accent_primary']};
    }}

    QRadioButton::indicator:disabled {{
        background-color: {colors['bg_disabled']};
        border: 1px solid {colors['bg_disabled']};
    }}

    /* ========================================================================
       LABELS AND TEXT
       ======================================================================== */

    QLabel {{
        color: {colors['text_primary']};
        background-color: transparent;
    }}

    QLabel:disabled {{
        color: {colors['text_disabled']};
    }}

    /* ========================================================================
       GROUP BOXES
       ======================================================================== */

    QGroupBox {{
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        border-radius: 4px;
        margin-top: 7px;
        padding-top: 7px;
        font-weight: bold;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        background-color: {colors['bg_primary']};
    }}

    /* ========================================================================
       TABS
       ======================================================================== */

    QTabWidget::pane {{
        background-color: {colors['bg_primary']};
        border: 1px solid {colors['border_default']};
    }}

    QTabBar::tab {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_secondary']};
        padding: 6px 12px;
        margin-right: 2px;
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
    }}

    QTabBar::tab:selected {{
        background-color: {colors['bg_primary']};
        color: {colors['text_primary']};
        border-bottom: 2px solid {colors['accent_primary']};
    }}

    QTabBar::tab:hover {{
        background-color: {colors['bg_hover']};
    }}

    /* ========================================================================
       SLIDERS
       ======================================================================== */

    QSlider::groove:horizontal {{
        height: 4px;
        background-color: {colors['bg_secondary']};
        border-radius: 2px;
    }}

    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        background-color: {colors['accent_primary']};
        border-radius: 7px;
        margin: -5px 0;
    }}

    QSlider::handle:horizontal:hover {{
        background-color: {colors['accent_primary']};
        border: 2px solid {colors['text_primary']};
    }}

    QSlider::groove:vertical {{
        width: 4px;
        background-color: {colors['bg_secondary']};
        border-radius: 2px;
    }}

    QSlider::handle:vertical {{
        width: 14px;
        height: 14px;
        background-color: {colors['accent_primary']};
        border-radius: 7px;
        margin: 0 -5px;
    }}

    /* ========================================================================
       PROGRESS BARS
       ======================================================================== */

    QProgressBar {{
        background-color: {colors['bg_secondary']};
        border: 1px solid {colors['border_default']};
        border-radius: 3px;
        text-align: center;
        color: {colors['text_primary']};
        min-height: 20px;
    }}

    QProgressBar::chunk {{
        background-color: {colors['accent_primary']};
        border-radius: 2px;
    }}

    /* ========================================================================
       SCROLL BARS
       ======================================================================== */

    QScrollBar:vertical {{
        background-color: {colors['bg_secondary']};
        width: 12px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {colors['border_default']};
        border-radius: 6px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {colors['border_hover']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {colors['bg_secondary']};
        height: 12px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {colors['border_default']};
        border-radius: 6px;
        min-width: 20px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {colors['border_hover']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        border: none;
        background: none;
        width: 0px;
    }}

    /* ========================================================================
       TABLE WIDGETS
       ======================================================================== */

    QTableWidget {{
        background-color: {colors['bg_primary']};
        alternate-background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        gridline-color: {colors['border_default']};
        border: 1px solid {colors['border_default']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
    }}

    QTableView {{
        background-color: {colors['bg_primary']};
        alternate-background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        gridline-color: {colors['border_default']};
        border: 1px solid {colors['border_default']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
    }}

    QHeaderView {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        border: none;
    }}

    QHeaderView::section {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        padding: 5px;
        border: none;
        border-right: 1px solid {colors['border_default']};
        border-bottom: 1px solid {colors['border_default']};
    }}

    QHeaderView::section:hover {{
        background-color: {colors['bg_hover']};
    }}

    QTableWidget::item {{
        padding: 4px;
        border: none;
    }}

    QTableWidget::item:selected {{
        background-color: {colors['accent_primary']};
    }}

    QTableWidget::item:hover {{
        background-color: {colors['bg_hover']};
    }}

    QTableCornerButton::section {{
        background-color: {colors['bg_secondary']};
        border: none;
    }}

    /* ========================================================================
       LIST WIDGETS
       ======================================================================== */

    QListWidget {{
        background-color: {colors['bg_primary']};
        alternate-background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
        outline: none;
    }}

    QListView {{
        background-color: {colors['bg_primary']};
        alternate-background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
        outline: none;
    }}

    QListWidget::item {{
        padding: 4px;
    }}

    QListWidget::item:selected {{
        background-color: {colors['accent_primary']};
    }}

    QListWidget::item:hover {{
        background-color: {colors['bg_hover']};
    }}

    /* ========================================================================
       TREE WIDGETS
       ======================================================================== */

    QTreeWidget {{
        background-color: {colors['bg_primary']};
        alternate-background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        outline: none;
    }}

    QTreeView {{
        background-color: {colors['bg_primary']};
        alternate-background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        outline: none;
    }}

    QTreeWidget::item {{
        padding: 2px;
    }}

    QTreeWidget::item:selected {{
        background-color: {colors['accent_primary']};
    }}

    QTreeWidget::item:hover {{
        background-color: {colors['bg_hover']};
    }}

    QTreeWidget::branch {{
        background-color: {colors['bg_primary']};
    }}

    QTreeWidget::branch:selected {{
        background-color: {colors['accent_primary']};
    }}

    /* ========================================================================
       TEXT EDITORS
       ======================================================================== */

    QTextEdit {{
        background-color: {colors['bg_input']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
    }}

    QTextEdit:focus {{
        border: 1px solid {colors['border_focus']};
    }}

    QPlainTextEdit {{
        background-color: {colors['bg_input']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        selection-background-color: {colors['accent_primary']};
        selection-color: {colors['text_primary']};
    }}

    QPlainTextEdit:focus {{
        border: 1px solid {colors['border_focus']};
    }}

    /* ========================================================================
       SCROLL AREAS
       ======================================================================== */

    QScrollArea {{
        background-color: {colors['bg_primary']};
        border: none;
    }}

    QScrollArea > QWidget > QWidget {{
        background-color: {colors['bg_primary']};
    }}

    /* ========================================================================
       SPLITTERS
       ======================================================================== */

    QSplitter::handle {{
        background-color: {colors['border_default']};
    }}

    QSplitter::handle:hover {{
        background-color: {colors['border_hover']};
    }}

    QSplitter::handle:horizontal {{
        width: 4px;
    }}

    QSplitter::handle:vertical {{
        height: 4px;
    }}

    /* ========================================================================
       STATUS BAR
       ======================================================================== */

    QStatusBar {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_secondary']};
        border-top: 1px solid {colors['border_default']};
    }}

    QStatusBar::item {{
        border: none;
    }}

    QSizeGrip {{
        background-color: transparent;
        width: 12px;
        height: 12px;
    }}

    /* ========================================================================
       DOCK WIDGETS
       ======================================================================== */

    QDockWidget {{
        color: {colors['text_primary']};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}

    QDockWidget::title {{
        background-color: {colors['bg_secondary']};
        color: {colors['text_primary']};
        padding: 5px;
        border-bottom: 1px solid {colors['border_default']};
    }}

    QDockWidget::close-button, QDockWidget::float-button {{
        background-color: transparent;
        border: none;
        padding: 2px;
    }}

    QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
        background-color: {colors['bg_hover']};
    }}

    /* ========================================================================
       TOOLTIPS
       ======================================================================== */

    QToolTip {{
        background-color: {colors['bg_elevated']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border_default']};
        padding: 4px;
    }}

    /* ========================================================================
       MESSAGE BOXES
       ======================================================================== */

    QMessageBox {{
        background-color: {colors['bg_primary']};
        color: {colors['text_primary']};
    }}

    QMessageBox QPushButton {{
        min-width: 75px;
        min-height: 25px;
    }}

    /* ========================================================================
       FILE DIALOGS
       ======================================================================== */

    QFileDialog {{
        background-color: {colors['bg_primary']};
        color: {colors['text_primary']};
    }}

    /* ========================================================================
       SPECIAL FIXES
       ======================================================================== */

    /* Fix for white corners in some widgets */
    QWidget:window {{
        background-color: {colors['bg_primary']};
    }}

    /* Ensure context menus are styled */
    QMenu::right-arrow {{
        width: 10px;
        height: 10px;
    }}

    /* Disabled text for all widgets */
    *:disabled {{
        color: {colors['text_disabled']};
    }}
    """
