#!/usr/bin/env python
"""
Quick modernization script for existing MainWindow
Apply this to instantly modernize the UI without major refactoring
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from ui.modern_theme import ModernTheme
from ui.modern_widgets import ModernToast


def apply_modern_theme_to_window(window):
    """Apply modern theme to existing MainWindow with minimal changes."""

    # Initialize theme
    theme = ModernTheme()

    # Apply comprehensive stylesheet
    window.setStyleSheet(theme.get_stylesheet())

    # Apply shadows to existing cards/panels
    for widget in window.findChildren(QWidget):
        if widget.objectName() in ["searchCard", "modernCard"]:
            theme.apply_card_shadow(widget, "medium")

        # Update GroupBox to card style
        if widget.__class__.__name__ == "QGroupBox":
            widget.setObjectName("modernCard")
            theme.apply_card_shadow(widget, "small")

    # Enhance timeline tabs with better styling
    if hasattr(window, "frame_tabs"):
        for tab in window.frame_tabs:
            tab.setStyleSheet("""
                QToolButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #495057, stop:1 #343a40);
                    border: 1px solid #495057;
                    border-radius: 6px;
                    color: white;
                    font-weight: 600;
                    min-width: 44px;
                    min-height: 44px;
                }
                QToolButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6c757d, stop:1 #495057);
                    transform: translateY(-2px);
                }
                QToolButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #007bff, stop:1 #0056b3);
                    border: 2px solid #66b3ff;
                    box-shadow: 0 0 10px rgba(0, 123, 255, 0.5);
                }
            """)

    # Add smooth transitions to existing widgets
    window.setStyleSheet(window.styleSheet() + """
        * {
            transition: all 0.2s ease;
        }

        QPushButton, QToolButton {
            transition: all 0.15s ease;
        }

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
        }
    """)

    # Show welcome notification
    def show_welcome():
        toast = ModernToast(
            "UI Modernization Applied Successfully!",
            "success",
            3000,
            window
        )
        toast.move(window.width() - toast.width() - 20, 60)
        toast.show_toast()

    QTimer.singleShot(500, show_welcome)

    return theme


def enhance_existing_ui(window):
    """Enhance existing UI with modern patterns without breaking functionality."""

    # Add hover effects to all buttons
    for btn in window.findChildren(QPushButton):
        if not btn.property("enhanced"):
            btn.setProperty("enhanced", True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

    # Improve status bar appearance
    if hasattr(window, "status_bar"):
        window.status_bar.setStyleSheet("""
            QStatusBar {
                background: linear-gradient(to right, #f8f9fa, #e9ecef);
                border-top: 1px solid #dee2e6;
                padding: 6px;
                font-size: 13px;
            }
            QStatusBar::item {
                border: none;
            }
        """)

    # Add subtle animations to curve widget
    if hasattr(window, "curve_widget"):
        window.curve_widget.setStyleSheet("""
            CurveViewWidget {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background: white;
            }
            CurveViewWidget:focus {
                border-color: #007bff;
                box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
            }
        """)


# Usage in main.py:
# from ui.apply_modern_theme import apply_modern_theme_to_window
# theme = apply_modern_theme_to_window(window)
# enhance_existing_ui(window)
