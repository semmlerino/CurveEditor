#!/usr/bin/env python
"""
Progressive Disclosure Controller for CurveEditor.

Manages transitions between simple and advanced interface modes with smooth animations
and state preservation.
"""

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Signal
from PySide6.QtWidgets import QSplitter, QWidget

from core.logger_utils import get_logger

if TYPE_CHECKING:
    from ui.state_manager import StateManager

logger = get_logger("progressive_disclosure_controller")


class ProgressiveDisclosureController(QObject):
    """
    Controller for managing progressive disclosure between simple and advanced modes.

    Handles:
    - Mode switching with smooth animations
    - State preservation across mode changes
    - User preference persistence
    - Layout management
    """

    # Signals
    mode_changed: Signal = Signal(str)  # Emits "simple" or "advanced"

    # Instance attributes (initialized in __init__)
    simple_widget: QWidget
    advanced_widget: QWidget
    splitter: QSplitter | None
    state_manager: "StateManager | None"
    _current_mode: str
    _animation_duration: int
    _is_animating: bool

    def __init__(self,
                 simple_widget: QWidget,
                 advanced_widget: QWidget,
                 splitter: QSplitter | None = None,
                 state_manager: "StateManager | None" = None):
        """
        Initialize progressive disclosure controller.

        Args:
            simple_widget: Widget containing simple mode interface
            advanced_widget: Widget containing advanced mode interface
            splitter: Optional splitter for advanced mode layout
            state_manager: State manager for preferences
        """
        super().__init__()
        self.simple_widget = simple_widget
        self.advanced_widget = advanced_widget
        self.splitter = splitter
        self.state_manager = state_manager

        self._current_mode = "simple"
        self._animation_duration = 300  # milliseconds
        self._is_animating = False
        self._fade_out_animation: QPropertyAnimation | None = None
        self._fade_in_animation: QPropertyAnimation | None = None

        # Store original sizes for restoration
        self._simple_size: tuple[int, int] | None = None
        self._advanced_size: tuple[int, int] | None = None
        self._splitter_sizes: list[int] | None = None

        self._setup_initial_state()

    def _setup_initial_state(self) -> None:
        """Set up initial state based on user preferences."""
        # Get user preference for interface mode
        if self.state_manager:
            preferences = self.state_manager.get_user_preferences()
            self._current_mode = preferences.interface_mode

        # Set initial visibility
        if self._current_mode == "simple":
            self.simple_widget.setVisible(True)
            self.advanced_widget.setVisible(False)
        else:
            self.simple_widget.setVisible(False)
            self.advanced_widget.setVisible(True)

        logger.debug(f"Initialized in {self._current_mode} mode")

    def get_current_mode(self) -> str:
        """
        Get the current interface mode.

        Returns:
            Current mode ("simple" or "advanced")
        """
        return self._current_mode

    def set_mode(self, mode: str, animate: bool = True) -> None:
        """
        Set the interface mode.

        Args:
            mode: Target mode ("simple" or "advanced")
            animate: Whether to animate the transition
        """
        if mode not in ("simple", "advanced"):
            logger.warning(f"Invalid mode: {mode}")
            return

        if mode == self._current_mode:
            return

        if self._is_animating:
            logger.debug("Animation in progress, ignoring mode change request")
            return

        logger.debug(f"Switching from {self._current_mode} to {mode} mode")

        if animate:
            self._animate_mode_change(mode)
        else:
            self._switch_mode_immediate(mode)

    def toggle_mode(self, animate: bool = True) -> None:
        """
        Toggle between simple and advanced modes.

        Args:
            animate: Whether to animate the transition
        """
        new_mode = "advanced" if self._current_mode == "simple" else "simple"
        self.set_mode(new_mode, animate)

    def _animate_mode_change(self, target_mode: str) -> None:
        """
        Animate transition between modes.

        Args:
            target_mode: Target mode to transition to
        """
        self._is_animating = True

        # Store current sizes
        if self._current_mode == "simple":
            self._simple_size = (self.simple_widget.width(), self.simple_widget.height())
        else:
            self._advanced_size = (self.advanced_widget.width(), self.advanced_widget.height())
            if self.splitter:
                self._splitter_sizes = self.splitter.sizes()

        # Get parent widget for animation
        parent = self.simple_widget.parent()
        if not parent:
            # Fallback to immediate switch if no parent
            self._switch_mode_immediate(target_mode)
            return

        # Create fade out animation for current widget
        current_widget = self.simple_widget if self._current_mode == "simple" else self.advanced_widget
        target_widget = self.advanced_widget if target_mode == "advanced" else self.simple_widget

        # Prepare target widget (hidden initially)
        target_widget.setVisible(True)
        target_widget.setGraphicsEffect(None)  # Clear any existing effects  # pyright: ignore[reportArgumentType]

        # Create opacity animations
        self._fade_out_animation = QPropertyAnimation(current_widget, b"windowOpacity")
        self._fade_out_animation.setDuration(self._animation_duration // 2)
        self._fade_out_animation.setStartValue(1.0)
        self._fade_out_animation.setEndValue(0.0)
        self._fade_out_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_in_animation = QPropertyAnimation(target_widget, b"windowOpacity")
        self._fade_in_animation.setDuration(self._animation_duration // 2)
        self._fade_in_animation.setStartValue(0.0)
        self._fade_in_animation.setEndValue(1.0)
        self._fade_in_animation.setEasingCurve(QEasingCurve.Type.InCubic)

        # Connect animation finished signals
        self._fade_out_animation.finished.connect(
            lambda: self._on_fade_out_finished(current_widget, target_widget, target_mode)
        )
        self._fade_in_animation.finished.connect(
            lambda: self._on_animation_finished(target_mode)
        )

        # Start fade out
        self._fade_out_animation.start()

    def _on_fade_out_finished(self, current_widget: QWidget, target_widget: QWidget, target_mode: str) -> None:
        """Handle fade out animation finished."""
        # Hide current widget
        current_widget.setVisible(False)
        current_widget.setWindowOpacity(1.0)  # Reset opacity

        # Show target widget and start fade in
        target_widget.setVisible(True)
        target_widget.setWindowOpacity(0.0)

        # Restore sizes if available
        if target_mode == "simple" and self._simple_size:
            target_widget.resize(*self._simple_size)
        elif target_mode == "advanced" and self._advanced_size:
            target_widget.resize(*self._advanced_size)
            if self.splitter and self._splitter_sizes:
                self.splitter.setSizes(self._splitter_sizes)

        if self._fade_in_animation is not None:
            self._fade_in_animation.start()

    def _on_animation_finished(self, target_mode: str) -> None:
        """Handle animation completion."""
        self._is_animating = False
        self._current_mode = target_mode

        # Reset opacity
        target_widget = self.advanced_widget if target_mode == "advanced" else self.simple_widget
        target_widget.setWindowOpacity(1.0)

        # Save preference
        self._save_mode_preference()

        # Emit signal
        self.mode_changed.emit(target_mode)

        logger.debug(f"Mode change animation completed: {target_mode}")

    def _switch_mode_immediate(self, target_mode: str) -> None:
        """
        Switch modes immediately without animation.

        Args:
            target_mode: Target mode to switch to
        """
        # Store current sizes
        if self._current_mode == "simple":
            self._simple_size = (self.simple_widget.width(), self.simple_widget.height())
        else:
            self._advanced_size = (self.advanced_widget.width(), self.advanced_widget.height())
            if self.splitter:
                self._splitter_sizes = self.splitter.sizes()

        # Hide current widget
        if self._current_mode == "simple":
            self.simple_widget.setVisible(False)
        else:
            self.advanced_widget.setVisible(False)

        # Show target widget
        if target_mode == "simple":
            self.simple_widget.setVisible(True)
            if self._simple_size:
                self.simple_widget.resize(*self._simple_size)
        else:
            self.advanced_widget.setVisible(True)
            if self._advanced_size:
                self.advanced_widget.resize(*self._advanced_size)
            if self.splitter and self._splitter_sizes:
                self.splitter.setSizes(self._splitter_sizes)

        self._current_mode = target_mode

        # Save preference
        self._save_mode_preference()

        # Emit signal
        self.mode_changed.emit(target_mode)

        logger.debug(f"Mode switched immediately to: {target_mode}")

    def _save_mode_preference(self) -> None:
        """Save current mode to user preferences."""
        if self.state_manager:
            preferences = self.state_manager.get_user_preferences()
            preferences.interface_mode = self._current_mode
            self.state_manager.save_user_preferences(preferences)
            logger.debug(f"Saved mode preference: {self._current_mode}")

    def preserve_state(self) -> dict[str, Any]:
        """
        Preserve current state for restoration.

        Returns:
            Dictionary containing current state
        """
        state = {
            "mode": self._current_mode,
            "simple_size": self._simple_size,
            "advanced_size": self._advanced_size,
            "splitter_sizes": self._splitter_sizes,
        }

        # Get current widget sizes
        if self._current_mode == "simple":
            state["current_size"] = (self.simple_widget.width(), self.simple_widget.height())
        else:
            state["current_size"] = (self.advanced_widget.width(), self.advanced_widget.height())
            if self.splitter:
                state["current_splitter_sizes"] = self.splitter.sizes()

        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        """
        Restore state from preserved data.

        Args:
            state: State dictionary from preserve_state()
        """
        # Restore sizes
        self._simple_size = state.get("simple_size")
        self._advanced_size = state.get("advanced_size")
        self._splitter_sizes = state.get("splitter_sizes")

        # Restore mode
        target_mode = state.get("mode", "simple")
        if target_mode != self._current_mode:
            self.set_mode(target_mode, animate=False)

        # Restore current sizes
        current_size = state.get("current_size")
        if current_size:
            if self._current_mode == "simple":
                self.simple_widget.resize(*current_size)
            else:
                self.advanced_widget.resize(*current_size)

        current_splitter_sizes = state.get("current_splitter_sizes")
        if current_splitter_sizes and self.splitter and self._current_mode == "advanced":
            self.splitter.setSizes(current_splitter_sizes)

        logger.debug(f"Restored state: mode={target_mode}")

    def set_animation_duration(self, duration_ms: int) -> None:
        """
        Set animation duration.

        Args:
            duration_ms: Animation duration in milliseconds
        """
        self._animation_duration = max(100, min(duration_ms, 1000))  # Clamp between 100ms and 1s

    def is_animating(self) -> bool:
        """
        Check if currently animating.

        Returns:
            True if animation is in progress
        """
        return self._is_animating

    def get_recommended_mode_for_context(self, sequence_count: int, has_recent_dirs: bool) -> str:
        """
        Get recommended mode based on context.

        Args:
            sequence_count: Number of sequences in current directory
            has_recent_dirs: Whether user has recent directories

        Returns:
            Recommended mode ("simple" or "advanced")
        """
        # Use simple mode for straightforward cases
        if sequence_count <= 5 and has_recent_dirs:
            return "simple"

        # Use advanced mode for complex scenarios
        if sequence_count > 20:
            return "advanced"

        # Default to user preference
        if self.state_manager:
            preferences = self.state_manager.get_user_preferences()
            return preferences.interface_mode

        return "simple"
