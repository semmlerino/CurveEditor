#!/usr/bin/env python
"""
Modernized Main Window for CurveEditor
Extends the base MainWindow with comprehensive modern UI/UX enhancements
"""

import logging

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QToolBar,
    QWidget,
)

from .main_window import MainWindow
from .modern_theme import ModernTheme
from .modern_widgets import (
    ModernLoadingSpinner,
    ModernProgressBar,
    ModernToast,
)
from .ui_constants import ANIMATION, COLORS_DARK, COLORS_LIGHT

logger = logging.getLogger("modernized_main_window")


class ModernizedMainWindow(MainWindow):
    """Enhanced main window with comprehensive modern UI/UX features."""

    # Additional signals for modern features
    theme_changed = Signal(str)
    animation_toggled = Signal(bool)
    keyboard_hints_toggled = Signal(bool)

    def __init__(self, parent=None):
        """Initialize the modernized main window."""
        # Initialize theme manager before parent init
        self.theme_manager = ModernTheme()
        self.animations_enabled = True
        self.current_theme = "dark"  # Default to dark theme
        self.keyboard_hints_visible = False

        # Initialize parent (MainWindow)
        super().__init__(parent)

        # Apply modern enhancements after parent initialization
        self._apply_modern_theme()
        self._enhance_ui_components()
        self._setup_animations()
        self._add_keyboard_hints()
        self._setup_loading_indicators()
        self._add_theme_switcher()
        self._enhance_timeline()
        self._enhance_toolbar()
        self._add_welcome_animation()

        # Setup keyboard shortcuts for modern features
        self._setup_modern_shortcuts()

        logger.info("ModernizedMainWindow initialized with enhanced UI/UX")

    def _apply_modern_theme(self):
        """Apply the modern theme to the application."""
        # Set dark theme as default
        self.theme_manager.current_theme = self.current_theme

        # Apply comprehensive stylesheet
        stylesheet = self.theme_manager.get_stylesheet()
        self.setStyleSheet(stylesheet)

        # Apply window-specific dark theme enhancements
        if self.current_theme == "dark":
            self.setStyleSheet(
                self.styleSheet()
                + """
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2b3035, stop:1 #212529);
                }

                QToolBar {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #343a40, stop:1 #2b3035);
                    border-bottom: 1px solid #495057;
                }

                QStatusBar {
                    background: qlineargradient(x1:0, y1:1, x2:0, y2:0,
                        stop:0 #212529, stop:1 #2b3035);
                    border-top: 1px solid #495057;
                    color: #adb5bd;
                }

                /* Enhanced timeline tabs */
                QToolButton {
                    /* Transition effect handled by animations */
                }

                QToolButton:hover {
                    margin-top: -2px;
                }
            """
            )

    def _enhance_ui_components(self):
        """Enhance existing UI components with modern features."""
        # Apply card shadows to GroupBoxes
        for group_box in self.findChildren(QWidget):
            if group_box.__class__.__name__ == "QGroupBox":
                self._apply_card_effect(group_box)

        # Enhance buttons with hover effects
        for button in self.findChildren(QPushButton):
            self._enhance_button(button)

        # Enhance the curve widget
        if hasattr(self, "curve_widget") and self.curve_widget:
            self._enhance_curve_widget()

    def _apply_card_effect(self, widget: QWidget):
        """Apply modern card effect with shadow to widget."""
        # Create drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 40 if self.current_theme == "light" else 60))
        widget.setGraphicsEffect(shadow)

        # Add hover animation capability
        widget.setProperty("card_shadow", shadow)

    def _enhance_button(self, button: QPushButton):
        """Enhance button with modern hover effects."""
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("enhanced", True)

        # Install event filter for hover animations
        button.installEventFilter(self)

    def _enhance_curve_widget(self):
        """Enhance the curve widget with modern styling."""
        colors = COLORS_DARK if self.current_theme == "dark" else COLORS_LIGHT

        self.curve_widget.setStyleSheet(f"""
            CurveViewWidget {{
                border: 2px solid {colors['border_default']};
                border-radius: 8px;
                background: {colors['bg_elevated']};
            }}
            CurveViewWidget:focus {{
                border: 2px solid {colors['accent_primary']};
                /* Shadow effect handled by QGraphicsDropShadowEffect */
            }}
        """)

    def _enhance_toolbar(self):
        """Enhance the existing toolbar with modern styling."""
        # Find existing toolbar
        toolbar = self.findChild(QToolBar, "mainToolBar")
        if not toolbar:
            return

        # Apply modern styling to toolbar actions
        colors = COLORS_DARK if self.current_theme == "dark" else COLORS_LIGHT
        toolbar.setStyleSheet(f"""
            QToolBar {{
                spacing: 4px;
                padding: 4px;
            }}
            QToolButton {{
                border-radius: 4px;
                padding: 6px;
                margin: 2px;
            }}
            QToolButton:hover {{
                background: {colors['bg_hover']};
            }}
        """)

    def _setup_animations(self):
        """Setup animation controllers for smooth transitions."""
        self.animation_group = QParallelAnimationGroup()
        self.fade_animations = {}

        # Setup opacity effects for smooth transitions
        # Only animate the curve container (side panels removed)
        for widget_name in ["curve_container"]:
            widget = getattr(self, widget_name, None)
            if widget and isinstance(widget, QWidget):
                opacity_effect = QGraphicsOpacityEffect()
                opacity_effect.setOpacity(1.0)  # Set initial opacity
                widget.setGraphicsEffect(opacity_effect)

                fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
                fade_anim.setDuration(ANIMATION["duration_normal"])
                fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                self.fade_animations[widget] = fade_anim

    def _add_keyboard_hints(self):
        """Add visual keyboard navigation hints."""
        self.keyboard_hints = []

        # Create keyboard hint overlays for important controls
        hint_configs = [
            (self.frame_spinbox, "↑↓", "Adjust frame"),
            (self.btn_play_pause, "Space", "Play/Pause"),
            (self.point_x_spinbox, "Tab", "Navigate"),
        ]

        for widget, key, description in hint_configs:
            if widget:
                hint = self._create_keyboard_hint(widget, key, description)
                self.keyboard_hints.append(hint)

    def _create_keyboard_hint(self, target_widget: QWidget, key: str, description: str) -> QWidget:
        """Create a keyboard hint overlay for a widget."""
        hint = QLabel(f"{key}", target_widget.parent() if target_widget.parent() else self)
        hint.setStyleSheet("""
            QLabel {
                background: rgba(0, 123, 255, 0.9);
                color: white;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        hint.setToolTip(description)
        # Store reference to target widget for positioning
        hint.setProperty("target_widget", target_widget)
        hint.setProperty("description", description)
        hint.hide()
        hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return hint

    def _setup_loading_indicators(self):
        """Setup loading indicators for async operations."""
        # Create loading spinner
        self.loading_spinner = ModernLoadingSpinner(self)
        self.loading_spinner.move(self.width() // 2 - 20, self.height() // 2 - 20)
        self.loading_spinner.hide()

        # Create progress bar for file operations
        self.progress_bar_modern = ModernProgressBar(self)
        self.progress_bar_modern.setFixedWidth(300)
        self.progress_bar_modern.move(self.width() // 2 - 150, self.height() - 100)
        self.progress_bar_modern.hide()

    def _add_theme_switcher(self):
        """Add theme switching capability to toolbar."""
        toolbar = self.findChild(QToolBar, "mainToolBar")
        if toolbar:
            # Add separator before theme toggle
            toolbar.addSeparator()

            # Create theme switcher action
            theme_action = QAction("🌙" if self.current_theme == "light" else "☀️", self)
            theme_action.setToolTip("Switch theme (Ctrl+T)")
            theme_action.setShortcut(QKeySequence("Ctrl+T"))
            theme_action.triggered.connect(self._toggle_theme)
            toolbar.addAction(theme_action)
            self.theme_action = theme_action

            # Add performance mode toggle
            perf_action = QAction("🚀 Performance Mode", self)
            perf_action.setCheckable(True)
            perf_action.setToolTip("Toggle performance mode (Ctrl+P)")
            perf_action.setShortcut(QKeySequence("Ctrl+P"))
            perf_action.triggered.connect(self._toggle_performance_mode)
            toolbar.addAction(perf_action)
            self.perf_action = perf_action

    def _enhance_timeline(self):
        """Enhance the timeline with modern styling and animations."""
        if hasattr(self, "frame_tabs") and self.frame_tabs:
            colors = COLORS_DARK if self.current_theme == "dark" else COLORS_LIGHT

            for i, tab in enumerate(self.frame_tabs):
                # Apply modern styling with gradient
                tab.setStyleSheet(f"""
                    QToolButton {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {colors['bg_elevated']}, stop:1 {colors['bg_secondary']});
                        border: 1px solid {colors['border_default']};
                        border-radius: 6px;
                        color: {colors['text_primary']};
                        font-weight: 600;
                        min-width: 44px;
                        min-height: 44px;
                        /* Transition effect handled by animations */
                    }}
                    QToolButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {colors['bg_hover']}, stop:1 {colors['bg_selected']});
                        margin-top: -2px;
                        border-color: {colors['accent_primary']};
                    }}
                    QToolButton:checked {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {colors['accent_primary']}, stop:1 {colors['button_primary_hover']});
                        border: 2px solid {colors['accent_primary']};
                        color: white;
                        /* Glow effect handled programmatically */
                    }}
                """)

                # Add pulse animation for first frame
                if i == 0:
                    self._add_pulse_animation(tab)

    def _add_pulse_animation(self, widget: QWidget):
        """Add subtle pulse animation to widget."""
        if not widget or not isinstance(widget, QWidget):
            return

        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(1.0)  # Set initial opacity
        widget.setGraphicsEffect(opacity_effect)

        pulse_anim = QPropertyAnimation(opacity_effect, b"opacity")
        pulse_anim.setDuration(1000)
        pulse_anim.setStartValue(1.0)
        pulse_anim.setKeyValueAt(0.5, 0.7)
        pulse_anim.setEndValue(1.0)
        pulse_anim.setLoopCount(-1)  # Infinite loop
        pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        # Store animation reference to prevent garbage collection
        if not hasattr(self, "_pulse_animations"):
            self._pulse_animations = []
        self._pulse_animations.append(pulse_anim)

        pulse_anim.start()
        widget.setProperty("pulse_animation", pulse_anim)

    def _add_welcome_animation(self):
        """Show welcome animation on startup."""

        def show_welcome():
            # Create welcome toast
            toast = ModernToast("Welcome to CurveEditor! Press F1 for keyboard shortcuts.", "info", 4000, self)
            toast.move(self.width() - toast.width() - 20, 60)
            toast.show_toast()

            # Animate main panel with fade-in (only curve container now)
            for widget_name in ["curve_container"]:
                widget = getattr(self, widget_name, None)
                if widget and widget in self.fade_animations:
                    try:
                        fade_anim = self.fade_animations[widget]
                        fade_anim.setStartValue(0.0)
                        fade_anim.setEndValue(1.0)
                        fade_anim.start()
                    except RuntimeError:
                        # Animation object may have been deleted during teardown
                        pass

        # Delay welcome animation slightly
        QTimer.singleShot(500, show_welcome)

    def _setup_modern_shortcuts(self):
        """Setup keyboard shortcuts for modern features."""
        # F1 - Toggle keyboard hints
        # F2 - Toggle animations
        # Ctrl+T - Toggle theme
        pass  # Shortcuts are connected via actions

    @Slot()
    def _toggle_theme(self):
        """Toggle between light and dark themes."""
        # Switch theme
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.theme_manager.switch_theme(self.current_theme)

        # Apply new theme
        self._apply_modern_theme()
        self._enhance_ui_components()
        self._enhance_timeline()

        # Update theme button icon
        if hasattr(self, "theme_action"):
            self.theme_action.setText("🌙" if self.current_theme == "light" else "☀️")

        # Show theme change notification
        self._show_notification(f"Switched to {self.current_theme.title()} Theme", "success")

        # Emit theme changed signal
        self.theme_changed.emit(self.current_theme)

        logger.info(f"Theme switched to: {self.current_theme}")

    def _show_notification(self, message: str, variant: str = "info", duration: int = 3000):
        """Show a modern toast notification."""
        toast = ModernToast(message, variant, duration, self)
        toast.move(self.width() - toast.width() - 20, 60)
        toast.show_toast()

    @Slot(bool)
    def _toggle_performance_mode(self, enabled: bool):
        """Toggle performance mode for better responsiveness.

        Args:
            enabled: True to enable performance mode
        """
        if enabled:
            # Disable expensive visual effects
            self.animations_enabled = False

            # Disable graphics effects on widgets
            for widget in self.findChildren(QWidget):
                if widget.graphicsEffect():
                    widget.graphicsEffect().setEnabled(False)

            # Stop all animations
            for widget, anim in self.fade_animations.items():
                anim.stop()

            # Use faster rendering in curve widget if available
            if hasattr(self, "curve_widget") and self.curve_widget:
                if hasattr(self.curve_widget, "renderer"):
                    from rendering.optimized_curve_renderer import RenderQuality

                    self.curve_widget.renderer.set_render_quality(RenderQuality.DRAFT)

            self._show_notification("Performance mode enabled - animations disabled", "success", 2000)
        else:
            # Re-enable visual effects
            self.animations_enabled = True

            # Re-enable graphics effects
            for widget in self.findChildren(QWidget):
                if widget.graphicsEffect():
                    widget.graphicsEffect().setEnabled(True)

            # Restore normal rendering
            if hasattr(self, "curve_widget") and self.curve_widget:
                if hasattr(self.curve_widget, "renderer"):
                    from rendering.optimized_curve_renderer import RenderQuality

                    self.curve_widget.renderer.set_render_quality(RenderQuality.NORMAL)

            self._show_notification("Performance mode disabled - animations enabled", "info", 2000)

    def toggle_keyboard_hints(self):
        """Toggle visibility of keyboard hints."""
        self.keyboard_hints_visible = not self.keyboard_hints_visible

        for hint in self.keyboard_hints:
            if self.keyboard_hints_visible:
                hint.show()
                # Position hint near its target widget
                self._position_keyboard_hint(hint)
            else:
                hint.hide()

        self._show_notification(f"Keyboard hints {'shown' if self.keyboard_hints_visible else 'hidden'}", "info", 2000)

        self.keyboard_hints_toggled.emit(self.keyboard_hints_visible)

    def _position_keyboard_hint(self, hint: QLabel):
        """Position keyboard hint near its target widget."""
        target_widget = hint.property("target_widget")
        if target_widget and target_widget.isVisible():
            # Get target widget's geometry
            target_rect = target_widget.rect()

            # Map to main window coordinates
            if target_widget.parent():
                pos = target_widget.mapTo(self, target_rect.topRight())
            else:
                pos = target_widget.pos() + target_rect.topRight()

            # Position hint at top-right corner, slightly offset
            hint_x = pos.x() - hint.width() - 5
            hint_y = pos.y() - hint.height() + 5

            # Ensure hint stays within window bounds
            hint_x = max(5, min(hint_x, self.width() - hint.width() - 5))
            hint_y = max(5, hint_y)

            hint.move(hint_x, hint_y)
            hint.raise_()  # Ensure hint is on top

    def keyPressEvent(self, event):
        """Enhanced key press handling with visual feedback."""
        # Toggle keyboard hints with F1
        if event.key() == Qt.Key.Key_F1:
            self.toggle_keyboard_hints()
            return

        # Toggle animations with F2
        if event.key() == Qt.Key.Key_F2:
            self.animations_enabled = not self.animations_enabled
            self._show_notification(f"Animations {'enabled' if self.animations_enabled else 'disabled'}", "info", 2000)
            self.animation_toggled.emit(self.animations_enabled)
            return

        # Call parent key press handler
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)

        # Reposition keyboard hints if they're visible
        if self.keyboard_hints_visible:
            for hint in self.keyboard_hints:
                self._position_keyboard_hint(hint)

        # Reposition loading indicators
        if hasattr(self, "loading_spinner"):
            self.loading_spinner.move(self.width() // 2 - 20, self.height() // 2 - 20)

        if hasattr(self, "progress_bar_modern"):
            self.progress_bar_modern.move(self.width() // 2 - 150, self.height() - 100)

    def closeEvent(self, event):
        """Clean up animations and resources."""
        # Stop and clean up fade animations
        for widget, anim in self.fade_animations.items():
            if anim and anim.state() == QPropertyAnimation.State.Running:
                anim.stop()
            anim.deleteLater()

        # Stop and clean up pulse animations
        if hasattr(self, "_pulse_animations"):
            for anim in self._pulse_animations:
                if anim and anim.state() == QPropertyAnimation.State.Running:
                    anim.stop()
                anim.deleteLater()

        # Stop and clean up button animations
        if hasattr(self, "_button_animations"):
            for key, obj in self._button_animations.items():
                if isinstance(obj, QPropertyAnimation):
                    if obj.state() == QPropertyAnimation.State.Running:
                        obj.stop()
                    obj.deleteLater()

        # Stop pulse animations on timeline tabs
        if hasattr(self, "ui_components") and hasattr(self.ui_components, "timeline"):
            timeline_widget = self.ui_components.timeline.timeline_widget
            if timeline_widget:
                for i in range(timeline_widget.count()):
                    tab = timeline_widget.widget(i)
                    if tab and tab.property("pulse_animation"):
                        pulse_anim = tab.property("pulse_animation")
                        pulse_anim.stop()
                        pulse_anim.deleteLater()

        # Stop any running toast notifications
        for child in self.findChildren(QWidget):
            if isinstance(child, QWidget) and child.property("is_toast"):
                child.close()
                child.deleteLater()

        # Call parent close event with error handling
        try:
            super().closeEvent(event)
        except RuntimeError as e:
            # Handle case where parent resources are already deleted
            if "already deleted" in str(e):
                # Resources already cleaned up, just accept the event
                event.accept()
            else:
                # Re-raise other runtime errors
                raise

    def eventFilter(self, obj, event):
        """Enhanced event filter with hover animations."""
        # Handle button hover animations
        if isinstance(obj, QPushButton) and obj.property("enhanced"):
            if event.type() == event.Type.Enter:
                self._animate_button_hover(obj, True)
            elif event.type() == event.Type.Leave:
                self._animate_button_hover(obj, False)

        # Call parent event filter
        return super().eventFilter(obj, event)

    def _animate_button_hover(self, button: QPushButton, hovering: bool):
        """Animate button on hover with opacity effect."""
        if not self.animations_enabled:
            return

        # Get or create animation objects
        anim_id = f"hover_anim_{id(button)}"
        effect_id = f"opacity_effect_{id(button)}"

        if not hasattr(self, "_button_animations"):
            self._button_animations = {}

        if anim_id not in self._button_animations:
            # Create new opacity effect and animation
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(0.9)  # Initial opacity
            button.setGraphicsEffect(opacity_effect)

            anim = QPropertyAnimation(opacity_effect, b"opacity")
            anim.setDuration(ANIMATION["duration_fast"])
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            # Store in our dictionary instead of as widget properties
            self._button_animations[anim_id] = anim
            self._button_animations[effect_id] = opacity_effect

        # Get animation and effect from our storage
        anim = self._button_animations[anim_id]
        opacity_effect = self._button_animations[effect_id]

        # Stop any running animation
        if anim.state() == QPropertyAnimation.State.Running:
            anim.stop()

        if hovering:
            # Brighten button on hover
            anim.setStartValue(opacity_effect.opacity())
            anim.setEndValue(1.0)

            # Also update style for visual feedback
            current_style = button.styleSheet()
            if "background-color" not in current_style:
                button.setStyleSheet(
                    current_style
                    + """
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.1);
                    }
                """
                )
        else:
            # Return to normal opacity
            anim.setStartValue(opacity_effect.opacity())
            anim.setEndValue(0.9)

            # Remove hover style
            current_style = button.styleSheet()
            button.setStyleSheet(current_style.replace("background-color: rgba(255, 255, 255, 0.1);", ""))

        anim.start()

    # Override file operations to show loading indicators
    def _on_action_open(self):
        """Enhanced open file action with loading indicator."""
        self.loading_spinner.start()
        super()._on_action_open()
        self.loading_spinner.stop()

    def _on_file_load_progress(self, progress: int, message: str):
        """Enhanced file loading progress display."""
        super()._on_file_load_progress(progress, message)

        # Show modern progress bar
        if progress == 0:
            self.progress_bar_modern.show()

        self.progress_bar_modern.setValue(progress)
        self.progress_bar_modern.setText(message)

        if progress >= 100:
            QTimer.singleShot(1000, self.progress_bar_modern.hide)

    def _on_file_load_finished(self):
        """Enhanced file loading completion."""
        super()._on_file_load_finished()

        # Hide loading indicators
        self.loading_spinner.stop()
        self.progress_bar_modern.hide()

        # Show success notification
        self._show_notification("Files loaded successfully!", "success")

    def _on_file_load_error(self, error_message: str):
        """Enhanced error handling with notifications."""
        super()._on_file_load_error(error_message)

        # Hide loading indicators
        self.loading_spinner.stop()
        self.progress_bar_modern.hide()

        # Show error notification
        self._show_notification(f"Error: {error_message}", "error", 5000)
