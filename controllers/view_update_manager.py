"""ViewUpdateManager - Handles UI update coordination for MainWindow.

This class consolidates all UI update logic from MainWindow, including:
- Timeline and frame display updates
- Point coordinate spinbox updates
- Status bar updates
- Zoom label updates
- Cursor position display
- General UI state synchronization
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import contextmanager
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QSignalBlocker
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QLabel, QSlider, QSpinBox

if TYPE_CHECKING:
    from typing import Protocol

    class MainWindowProtocol(Protocol):
        """Protocol for MainWindow to avoid circular imports."""

        # UI components - Core
        frame_spinbox: QSpinBox | None
        frame_slider: QSlider | None
        point_x_spinbox: QDoubleSpinBox | None
        point_y_spinbox: QDoubleSpinBox | None

        # UI components - Labels
        zoom_label: QLabel | None
        position_label: QLabel | None  # MainWindow uses position_label, not cursor_label
        status_label: QLabel | None
        total_frames_label: QLabel | None
        selected_count_label: QLabel | None
        selected_point_label: QLabel | None
        point_count_label: QLabel | None
        bounds_label: QLabel | None
        point_size_label: QLabel | None
        line_width_label: QLabel | None

        # UI components - Actions
        action_undo: QAction | None
        action_redo: QAction | None

        # UI components - Checkboxes
        show_background_cb: QCheckBox | None

        # Properties
        @property
        def current_frame(self) -> int: ...
        @property
        def curve_widget(self): ...
        @property
        def state_manager(self): ...

        # Methods
        def _update_background_image_for_frame(self, frame: int) -> None: ...


logger = logging.getLogger(__name__)


@contextmanager
def safe_signal_blocker(widget):
    """Context manager that safely blocks signals, handling Mock objects in tests."""
    if widget is None:
        yield
        return

    # Check if this is a real Qt object that supports signal blocking
    if hasattr(widget, "blockSignals") and isinstance(widget, QObject):
        # Use proper QSignalBlocker for real Qt objects
        with QSignalBlocker(widget):
            yield
    else:
        # For Mock objects or non-Qt objects, just yield without blocking
        yield


class ViewUpdateManager:
    """Manages UI updates for MainWindow."""

    def __init__(self, main_window: MainWindowProtocol):
        """Initialize ViewUpdateManager.

        Args:
            main_window: Reference to MainWindow instance
        """
        self.main_window: MainWindowProtocol = main_window
        self._point_spinbox_connected: bool = False
        # Store handler references for proper disconnection
        self._x_handler: Callable[[float], None] | None = None
        self._y_handler: Callable[[float], None] | None = None

    def update_frame_display(self, frame: int, update_state_manager: bool = True) -> None:
        """Update all frame-related UI elements.

        Args:
            frame: Frame number to display
            update_state_manager: Whether to update state manager
        """
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            if self.main_window.frame_spinbox:
                # Use QSignalBlocker for exception-safe signal blocking
                with safe_signal_blocker(self.main_window.frame_spinbox):
                    self.main_window.frame_spinbox.setValue(frame)
        except RuntimeError as e:
            logger.warning(f"Widget destroyed during frame update: {e}")
            return

        # Update state manager if requested
        if update_state_manager and self.main_window.state_manager:
            try:
                self.main_window.state_manager.current_frame = frame
            except RuntimeError as e:
                logger.warning(f"State manager update failed: {e}")

        # Update background image for new frame
        try:
            self.main_window._update_background_image_for_frame(frame)
        except Exception as e:
            logger.error(f"Failed to update background image for frame {frame}: {e}")
            # Continue with other updates rather than failing entirely

        logger.debug(f"Updated frame display to {frame}")

    def update_point_spinboxes(
        self,
        x: float | None = None,
        y: float | None = None,
        enabled: bool = True,
    ) -> None:
        """Update point coordinate spinboxes.

        Args:
            x: X coordinate value (None to keep current)
            y: Y coordinate value (None to keep current)
            enabled: Whether spinboxes should be enabled
        """
        # Check application is still running
        if not QApplication.instance():
            return

        if not (self.main_window.point_x_spinbox and self.main_window.point_y_spinbox):
            return

        try:
            # Use QSignalBlocker for exception-safe signal blocking
            with (
                safe_signal_blocker(self.main_window.point_x_spinbox),
                QSignalBlocker(self.main_window.point_y_spinbox),
            ):
                # Update values if provided
                if x is not None:
                    self.main_window.point_x_spinbox.setValue(x)
                if y is not None:
                    self.main_window.point_y_spinbox.setValue(y)

                # Update enabled state
                self.main_window.point_x_spinbox.setEnabled(enabled)
                self.main_window.point_y_spinbox.setEnabled(enabled)
        except RuntimeError as e:
            logger.warning(f"Widget destroyed during spinbox update: {e}")
            return
        except (ValueError, OverflowError) as e:
            logger.error(f"Invalid value for spinbox: {e}")
            return

        logger.debug(f"Updated point spinboxes: x={x}, y={y}, enabled={enabled}")

    def update_status(self, message: str) -> None:
        """Update status bar message.

        Args:
            message: Status message to display
        """
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            if hasattr(self.main_window, "statusBar"):
                # Use runtime check for statusBar method
                status_bar = getattr(self.main_window, "statusBar")()
                status_bar.showMessage(message, 3000)
            elif self.main_window.status_label:
                self.main_window.status_label.setText(message)
        except RuntimeError as e:
            logger.warning(f"Failed to update status: {e}")
            return

        logger.debug(f"Status updated: {message}")

    def update_zoom_label(self) -> None:
        """Update zoom level display."""
        # Check application is still running
        if not QApplication.instance():
            return

        if not self.main_window.zoom_label or not self.main_window.curve_widget:
            return

        try:
            zoom = self.main_window.curve_widget.zoom_factor
            zoom_percent = int(zoom * 100)
            self.main_window.zoom_label.setText(f"Zoom: {zoom_percent}%")
            logger.debug(f"Zoom label updated: {zoom_percent}%")
        except RuntimeError as e:
            logger.warning(f"Failed to update zoom label: {e}")

    def update_cursor_position(self, x: float, y: float) -> None:
        """Update cursor position display.

        Args:
            x: X coordinate in data space
            y: Y coordinate in data space
        """
        # Check application is still running
        if not QApplication.instance():
            return

        if not self.main_window.position_label:
            return

        try:
            # Format position with appropriate precision (match MainWindow format)
            self.main_window.position_label.setText(f"X: {x:.3f}, Y: {y:.3f}")
            logger.debug(f"Cursor position updated: ({x:.2f}, {y:.2f})")
        except RuntimeError as e:
            logger.warning(f"Failed to update cursor position: {e}")

    def update_ui_state(self) -> None:
        """Synchronize UI state with application state."""
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            # Get current state
            curve_widget = self.main_window.curve_widget
            state_manager = self.main_window.state_manager

            if not curve_widget or not state_manager:
                return

            # Update zoom display
            self.update_zoom_label()

            # Update point spinboxes based on selection
            selected_points = state_manager.selected_points
            if selected_points:
                # Get coordinates of first selected point
                point_data = curve_widget.get_selected_point_data()
                if point_data:
                    x, y = point_data[1], point_data[2]  # (frame, x, y)
                    self.update_point_spinboxes(x, y, enabled=True)
            else:
                # Disable spinboxes when nothing selected
                self.update_point_spinboxes(enabled=False)

            # Update frame display
            current_frame = self.main_window.current_frame
            if current_frame > 0:
                self.update_frame_display(current_frame, update_state_manager=False)

            logger.debug("UI state synchronized")
        except RuntimeError as e:
            logger.warning(f"Failed to synchronize UI state: {e}")

    def update_selection_labels(self, selected_indices: list[int]) -> None:
        """Update selection-related labels.

        Args:
            selected_indices: List of selected point indices
        """
        # Check application is still running
        if not QApplication.instance():
            return

        count = len(selected_indices)

        try:
            # Update selected count label
            if self.main_window.selected_count_label:
                self.main_window.selected_count_label.setText(f"Selected: {count}")

            # Update selected point label
            if self.main_window.selected_point_label:
                if count == 0:
                    self.main_window.selected_point_label.setText("No point selected")
                elif count == 1:
                    self.main_window.selected_point_label.setText(f"Point #{selected_indices[0]}")
                else:
                    self.main_window.selected_point_label.setText(f"{count} points selected")
        except RuntimeError as e:
            logger.warning(f"Failed to update selection labels: {e}")

    def update_frame_range(self, max_frame: int) -> None:
        """Update frame range controls.

        Args:
            max_frame: Maximum frame number
        """
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            # Update frame spinbox maximum
            if self.main_window.frame_spinbox:
                with safe_signal_blocker(self.main_window.frame_spinbox):
                    self.main_window.frame_spinbox.setMaximum(max_frame)

            # Update frame slider maximum
            if self.main_window.frame_slider:
                with safe_signal_blocker(self.main_window.frame_slider):
                    self.main_window.frame_slider.setMaximum(max_frame)

            # Update total frames label
            if self.main_window.total_frames_label:
                self.main_window.total_frames_label.setText(str(max_frame))

            logger.debug(f"Frame range updated to 1-{max_frame}")
        except RuntimeError as e:
            logger.warning(f"Failed to update frame range: {e}")

    def update_point_statistics(
        self, point_count: int, bounds: tuple[float, float, float, float] | None = None
    ) -> None:
        """Update point count and bounds labels.

        Args:
            point_count: Number of points
            bounds: Optional (min_x, min_y, max_x, max_y) bounds
        """
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            # Update point count label
            if self.main_window.point_count_label:
                self.main_window.point_count_label.setText(f"Points: {point_count}")

            # Update bounds label
            if self.main_window.bounds_label:
                if bounds and len(bounds) == 4:
                    min_x, min_y, max_x, max_y = bounds
                    self.main_window.bounds_label.setText(
                        f"Bounds:\nX: [{min_x:.2f}, {max_x:.2f}]\nY: [{min_y:.2f}, {max_y:.2f}]"
                    )
                else:
                    self.main_window.bounds_label.setText("Bounds: N/A")
        except RuntimeError as e:
            logger.warning(f"Failed to update point statistics: {e}")

    def update_visualization_labels(self, point_size: int | None = None, line_width: int | None = None) -> None:
        """Update visualization setting labels.

        Args:
            point_size: Point size value (optional)
            line_width: Line width value (optional)
        """
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            if point_size is not None and self.main_window.point_size_label:
                self.main_window.point_size_label.setText(str(point_size))

            if line_width is not None and self.main_window.line_width_label:
                self.main_window.line_width_label.setText(str(line_width))
        except RuntimeError as e:
            logger.warning(f"Failed to update visualization labels: {e}")

    def update_undo_redo_state(self, can_undo: bool, can_redo: bool) -> None:
        """Update undo/redo action states.

        Args:
            can_undo: Whether undo is available
            can_redo: Whether redo is available
        """
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            if self.main_window.action_undo:
                self.main_window.action_undo.setEnabled(can_undo)

            if self.main_window.action_redo:
                self.main_window.action_redo.setEnabled(can_redo)

            logger.debug(f"Undo/redo state updated: undo={can_undo}, redo={can_redo}")
        except RuntimeError as e:
            logger.warning(f"Failed to update undo/redo state: {e}")

    def update_background_checkbox(self, checked: bool) -> None:
        """Update background checkbox state.

        Args:
            checked: Whether checkbox should be checked
        """
        # Check application is still running
        if not QApplication.instance():
            return

        try:
            if self.main_window.show_background_cb:
                with safe_signal_blocker(self.main_window.show_background_cb):
                    self.main_window.show_background_cb.setChecked(checked)

            logger.debug(f"Background checkbox updated: {checked}")
        except RuntimeError as e:
            logger.warning(f"Failed to update background checkbox: {e}")

    def connect_point_spinbox_handlers(
        self, x_handler: Callable[[float], None], y_handler: Callable[[float], None]
    ) -> None:
        """Connect spinbox value change handlers.

        Args:
            x_handler: Handler for X spinbox changes
            y_handler: Handler for Y spinbox changes
        """
        if self._point_spinbox_connected:
            return

        # Check application is still running
        if not QApplication.instance():
            return

        # Store handler references for proper disconnection
        self._x_handler = x_handler
        self._y_handler = y_handler

        try:
            if self.main_window.point_x_spinbox:
                self.main_window.point_x_spinbox.valueChanged.connect(x_handler)

            if self.main_window.point_y_spinbox:
                self.main_window.point_y_spinbox.valueChanged.connect(y_handler)

            self._point_spinbox_connected = True
            logger.debug("Point spinbox handlers connected")
        except RuntimeError as e:
            logger.warning(f"Failed to connect spinbox handlers: {e}")
            self._x_handler = None
            self._y_handler = None

    def disconnect_point_spinbox_handlers(self) -> None:
        """Disconnect specific spinbox handlers."""
        if not self._point_spinbox_connected:
            return

        # Check application is still running
        if not QApplication.instance():
            return

        # Disconnect only the specific handlers we connected
        if self.main_window.point_x_spinbox and self._x_handler:
            try:
                self.main_window.point_x_spinbox.valueChanged.disconnect(self._x_handler)
            except RuntimeError:
                pass  # Already disconnected

        if self.main_window.point_y_spinbox and self._y_handler:
            try:
                self.main_window.point_y_spinbox.valueChanged.disconnect(self._y_handler)
            except RuntimeError:
                pass  # Already disconnected

        # Clear handler references
        self._x_handler = None
        self._y_handler = None
        self._point_spinbox_connected = False
        logger.debug("Point spinbox handlers disconnected")
