#!/usr/bin/env python
"""
Consolidated UIService for CurveEditor.

This service merges functionality from:
- dialog_service.py: All dialog operations
- UI update methods from curve_service.py
- Any remaining UI helper functionality

Provides a unified interface for all UI operations including dialogs,
status updates, and UI component management.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QWidget

from core.defaults import DEFAULT_STATUS_TIMEOUT

if TYPE_CHECKING:
    from protocols.ui import MainWindowProtocol

from core.logger_utils import get_logger
from stores.application_state import get_application_state

logger = get_logger("ui_service")


class UIService:
    """
    Consolidated service for all UI operations.

    This service handles:
    - Dialog operations (input dialogs, message boxes, confirmations)
    - Status bar updates
    - UI component state management
    - User notifications
    """

    def __init__(self) -> None:
        """Initialize the UIService."""

    # ==================== Dialog Methods (from dialog_service) ====================

    def get_smooth_window_size(self, parent: QWidget) -> int | None:
        """Get smoothing window size from user.

        Args:
            parent: Parent widget for the dialog

        Returns:
            Window size or None if cancelled
        """
        value, ok = QInputDialog.getInt(parent, "Smooth Curve", "Window size:", 5, 3, 20)
        return value if ok else None

    def get_filter_params(self, parent: QWidget) -> tuple[str, int] | None:
        """Get filter type and parameters from user.

        Args:
            parent: Parent widget for the dialog

        Returns:
            Tuple of (filter_type, parameter) or None if cancelled
        """
        filter_types = ["Median", "Butterworth"]
        filter_type, ok = QInputDialog.getItem(parent, "Filter Curve", "Filter type:", filter_types, 0, False)
        if not ok:
            return None

        if filter_type == "Median":
            window, ok = QInputDialog.getInt(parent, "Median Filter", "Window size:", 5, 3, 20)
            return (filter_type, window) if ok else None
        # Butterworth
        cutoff, ok = QInputDialog.getDouble(parent, "Butterworth Filter", "Cutoff frequency:", 0.1, 0.01, 1.0, 2)
        return (filter_type, int(cutoff * 100)) if ok else None

    def get_offset_values(self, parent: QWidget) -> tuple[float, float] | None:
        """Get X and Y offset values from user.

        Args:
            parent: Parent widget for the dialog

        Returns:
            Tuple of (x_offset, y_offset) or None if cancelled
        """
        x_offset, ok = QInputDialog.getDouble(parent, "Offset Curve", "X offset:", 0.0, -1000.0, 1000.0, 2)
        if not ok:
            return None

        y_offset, ok = QInputDialog.getDouble(parent, "Offset Curve", "Y offset:", 0.0, -1000.0, 1000.0, 2)
        return (x_offset, y_offset) if ok else None

    def get_fill_gaps_size(self, parent: QWidget) -> int | None:
        """Get maximum gap size to fill from user.

        Args:
            parent: Parent widget for the dialog

        Returns:
            Maximum gap size or None if cancelled
        """
        value, ok = QInputDialog.getInt(parent, "Fill Gaps", "Maximum gap size:", 10, 1, 100)
        return value if ok else None

    def get_scale_values(self, parent: QWidget) -> tuple[float, float] | None:
        """Get X and Y scale values from user.

        Args:
            parent: Parent widget for the dialog

        Returns:
            Tuple of (x_scale, y_scale) or None if cancelled
        """
        x_scale, ok = QInputDialog.getDouble(parent, "Scale Curve", "X scale:", 1.0, 0.01, 100.0, 2)
        if not ok:
            return None

        y_scale, ok = QInputDialog.getDouble(parent, "Scale Curve", "Y scale:", 1.0, 0.01, 100.0, 2)
        return (x_scale, y_scale) if ok else None

    def get_text_input(self, parent: QWidget, title: str, label: str, default: str = "") -> str | None:
        """Get text input from user.

        Args:
            parent: Parent widget for the dialog
            title: Dialog title
            label: Input label
            default: Default value

        Returns:
            User input or None if cancelled
        """
        text, ok = QInputDialog.getText(parent, title, label, text=default)
        return text if ok else None

    def get_integer_input(
        self,
        parent: QWidget,
        title: str,
        label: str,
        default: int = 0,
        min_val: int = -2147483647,
        max_val: int = 2147483647,
    ) -> int | None:
        """Get integer input from user.

        Args:
            parent: Parent widget for the dialog
            title: Dialog title
            label: Input label
            default: Default value
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            User input or None if cancelled
        """
        value, ok = QInputDialog.getInt(parent, title, label, default, min_val, max_val)
        return value if ok else None

    def get_float_input(
        self,
        parent: QWidget,
        title: str,
        label: str,
        default: float = 0.0,
        min_val: float = -2147483647.0,
        max_val: float = 2147483647.0,
        decimals: int = 2,
    ) -> float | None:
        """Get float input from user.

        Args:
            parent: Parent widget for the dialog
            title: Dialog title
            label: Input label
            default: Default value
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            decimals: Number of decimal places

        Returns:
            User input or None if cancelled
        """
        value, ok = QInputDialog.getDouble(parent, title, label, default, min_val, max_val, decimals)
        return value if ok else None

    def get_choice(self, parent: QWidget, title: str, label: str, choices: list[str], current: int = 0) -> str | None:
        """Get a choice from a list of options.

        Args:
            parent: Parent widget for the dialog
            title: Dialog title
            label: Choice label
            choices: List of choices
            current: Index of current/default choice

        Returns:
            Selected choice or None if cancelled
        """
        choice, ok = QInputDialog.getItem(parent, title, label, choices, current, False)
        return choice if ok else None

    # ==================== Message Box Methods ====================

    def show_error(self, parent: QWidget, message: str, title: str = "Error") -> None:
        """Show error message dialog.

        Args:
            parent: Parent widget for the dialog
            message: Error message to display
            title: Dialog title
        """
        _ = QMessageBox.critical(parent, title, message)
        logger.error(f"Error shown to user: {message}")

    def show_warning(self, parent: QWidget, message: str, title: str = "Warning") -> None:
        """Show warning message dialog.

        Args:
            parent: Parent widget for the dialog
            message: Warning message to display
            title: Dialog title
        """
        _ = QMessageBox.warning(parent, title, message)
        logger.warning(f"Warning shown to user: {message}")

    def show_info(self, parent: QWidget, message: str, title: str = "Information") -> None:
        """Show information message dialog.

        Args:
            parent: Parent widget for the dialog
            message: Information message to display
            title: Dialog title
        """
        _ = QMessageBox.information(parent, title, message)
        logger.info(f"Info shown to user: {message}")

    def confirm_action(self, parent: QWidget, message: str, title: str = "Confirm") -> bool:
        """Ask for confirmation from user.

        Args:
            parent: Parent widget for the dialog
            message: Confirmation message
            title: Dialog title

        Returns:
            True if user confirmed, False otherwise
        """
        result = QMessageBox.question(parent, title, message)
        confirmed = result == QMessageBox.StandardButton.Yes
        logger.info(f"Confirmation requested: {message} - Result: {confirmed}")
        return confirmed

    def show_about(self, parent: QWidget, title: str = "About", message: str = "") -> None:
        """Show about dialog.

        Args:
            parent: Parent widget for the dialog
            title: Dialog title
            message: About message
        """
        if not message:
            message = "CurveEditor Application\nVersion 1.0.0\n\nA professional curve editing tool."
        QMessageBox.about(parent, title, message)

    # ==================== Status Bar Methods ====================

    def show_status_message(
        self, main_window: "MainWindowProtocol", message: str, timeout: int = DEFAULT_STATUS_TIMEOUT
    ) -> None:
        """Show status message (alias for set_temporary_status).

        Args:
            main_window: Main window with status bar
            message: Status message to display
            timeout: Timeout in milliseconds (default 3 seconds)
        """
        self.set_temporary_status(main_window, message, timeout)

    def set_status(self, main_window: "MainWindowProtocol", message: str, timeout: int = 0) -> None:
        """Set status bar message.

        Args:
            main_window: Main window with status bar
            message: Status message to display
            timeout: Timeout in milliseconds (0 = permanent)
        """
        # statusBar() is defined in MainWindowProtocol
        main_window.statusBar().showMessage(message, timeout)
        logger.debug(f"Status bar updated: {message}")

    def clear_status(self, main_window: "MainWindowProtocol") -> None:
        """Clear status bar message.

        Args:
            main_window: Main window with status bar
        """
        # statusBar() is defined in MainWindowProtocol
        main_window.statusBar().clearMessage()

    def set_permanent_status(self, main_window: "MainWindowProtocol", message: str) -> None:
        """Set a permanent status message.

        Args:
            main_window: Main window with status bar
            message: Status message to display permanently
        """
        self.set_status(main_window, message, 0)

    def set_temporary_status(
        self, main_window: "MainWindowProtocol", message: str, timeout: int = DEFAULT_STATUS_TIMEOUT
    ) -> None:
        """Set a temporary status message.

        Args:
            main_window: Main window with status bar
            message: Status message to display
            timeout: Timeout in milliseconds (default 3 seconds)
        """
        self.set_status(main_window, message, timeout)

    # ==================== UI State Management ====================

    def enable_ui_components(
        self, main_window: "MainWindowProtocol", components: list[str], enabled: bool = True
    ) -> None:
        """Enable or disable UI components.

        Args:
            main_window: Main window containing the components
            components: List of component attribute names
            enabled: Whether to enable (True) or disable (False)
        """
        for component_name in components:
            # Skip empty component names
            if not component_name:
                continue

            component = getattr(main_window, component_name, None)
            if component is not None and callable(getattr(component, "setEnabled", None)):
                component.setEnabled(enabled)

    def update_button_states(self, main_window: "MainWindowProtocol") -> None:
        """Update the enabled state of various buttons based on application state.

        Args:
            main_window: Main window containing the buttons
        """
        # Update undo/redo buttons
        # undo_button, history_index are Optional in MainWindowProtocol
        if main_window.undo_button is not None and main_window.history_index is not None:
            main_window.undo_button.setEnabled(main_window.history_index > 0)

        # redo_button, history_index, history are Optional in MainWindowProtocol
        if (
            main_window.redo_button is not None
            and main_window.history_index is not None
            and main_window.history is not None
        ):
            main_window.redo_button.setEnabled(main_window.history_index < len(main_window.history) - 1)

        # Update save button
        # save_button is Optional
        if main_window.save_button is not None:
            app_state = get_application_state()
            if (cd := app_state.active_curve_data) is None:
                has_data = False
            else:
                _, data = cd
                has_data = len(data) > 0
            main_window.save_button.setEnabled(has_data)

        # Update selection-dependent buttons
        has_selection = False
        # selected_indices is defined in MainWindowProtocol
        has_selection = len(main_window.selected_indices) > 0

        selection_buttons = ["delete_button", "update_point_button", "duplicate_button"]
        for button_name in selection_buttons:
            button = getattr(main_window, button_name, None)
            if button:
                button.setEnabled(has_selection)

    def update_window_title(
        self, main_window: "MainWindowProtocol", title: str | None = None, modified: bool = False
    ) -> None:
        """Update the main window title.

        Args:
            main_window: Main window to update
            title: New title (if None, uses default)
            modified: Whether to show modified indicator
        """
        if title is None:
            title = "CurveEditor"

        if modified:
            title = f"*{title}"

        # setWindowTitle is defined in MainWindowProtocol
        main_window.setWindowTitle(title)

    def show_progress(
        self, main_window: "MainWindowProtocol", message: str, value: int = -1, maximum: int = 100
    ) -> None:
        """Show progress in status bar or progress dialog.

        Args:
            main_window: Main window
            message: Progress message
            value: Current progress value (-1 for indeterminate)
            maximum: Maximum progress value
        """
        # For now, just update status bar
        # Could be extended to show progress dialog for long operations
        if value < 0:
            self.set_status(main_window, f"{message}...")
        else:
            percentage = int((value / maximum) * 100) if maximum > 0 else 0
            self.set_status(main_window, f"{message} ({percentage}%)")

    def update_ui_from_data(self, main_window: "MainWindowProtocol") -> None:
        """Update all UI components based on current data state.

        Args:
            main_window: Main window to update
        """
        # Update button states
        self.update_button_states(main_window)

        # Update status bar with data info
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            point_count = 0
        else:
            _, data = cd
            point_count = len(data)
        self.set_status(main_window, f"{point_count} points loaded")

        # Update window title if modified
        # is_modified is a property in MainWindowProtocol
        if main_window.is_modified:
            self.update_window_title(main_window, modified=True)

    def create_context_menu(self, parent: QWidget, actions: dict[str, Callable[[], None] | None]) -> QMenu:
        """Create a context menu with the given actions.

        Args:
            parent: Parent widget for the menu
            actions: Dictionary of action names to callbacks

        Returns:
            Created QMenu instance
        """
        from PySide6.QtWidgets import QMenu

        menu = QMenu(parent)
        for action_name, callback in actions.items():
            if action_name == "-":
                # Add separator
                _ = menu.addSeparator()
            else:
                action = menu.addAction(action_name)
                if callback:
                    _ = action.triggered.connect(callback)

        return menu

    def show_filter_dialog(
        self, parent: QWidget, data: list[tuple[float, float, float]], indices: list[int]
    ) -> tuple[list[tuple[float, float, float]], list[int]] | None:
        """Show dialog for filtering curve data.

        Args:
            parent: Parent widget for the dialog
            data: Current curve data
            indices: Selected point indices

        Returns:
            Tuple of (filtered_data, filtered_indices) or None if cancelled
        """
        # TODO: Implement proper filter dialog
        # For now, just show a placeholder message
        _ = data  # Mark as intentionally unused
        _ = indices  # Mark as intentionally unused
        self.show_info(parent, "Filter dialog not yet implemented")
        return None

    def show_fill_gaps_dialog(
        self, parent: QWidget, data: list[tuple[float, float, float]], gaps: list[tuple[int, int]]
    ) -> list[tuple[float, float, float]] | None:
        """Show dialog for filling gaps in curve data.

        Args:
            parent: Parent widget for the dialog
            data: Current curve data
            gaps: List of gap ranges to fill

        Returns:
            Updated data with filled gaps or None if cancelled
        """
        # TODO: Implement proper fill gaps dialog
        # For now, just show a placeholder message
        _ = data  # Mark as intentionally unused
        _ = gaps  # Mark as intentionally unused
        self.show_info(parent, "Fill gaps dialog not yet implemented")
        return None

    def show_extrapolate_dialog(
        self, parent: QWidget, data: list[tuple[float, float, float]]
    ) -> list[tuple[float, float, float]] | None:
        """Show dialog for extrapolating curve data.

        Args:
            parent: Parent widget for the dialog
            data: Current curve data

        Returns:
            Extrapolated data or None if cancelled
        """
        # TODO: Implement proper extrapolate dialog
        # For now, just show a placeholder message
        _ = data  # Mark as intentionally unused
        self.show_info(parent, "Extrapolate dialog not yet implemented")
        return None

    def show_shortcuts_dialog(self, parent: object) -> None:
        """Show keyboard shortcuts dialog.

        Args:
            parent: Parent widget for the dialog (usually MainWindow)
        """
        from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout

        dialog = QDialog(parent if isinstance(parent, QWidget) else None)
        dialog.setWindowTitle("Keyboard Shortcuts")
        dialog.resize(600, 400)

        layout = QVBoxLayout()

        # Create text edit for shortcuts
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h3>Keyboard Shortcuts</h3>
        <table>
        <tr><td><b>Ctrl+O</b></td><td>Open track file</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>Save track file</td></tr>
        <tr><td><b>Ctrl+E</b></td><td>Smooth selected points</td></tr>
        <tr><td><b>Ctrl+Shift+E</b></td><td>Export to CSV</td></tr>
        <tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
        <tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
        <tr><td><b>Ctrl+A</b></td><td>Select all points</td></tr>
        <tr><td><b>Ctrl+D</b></td><td>Deselect all</td></tr>
        <tr><td><b>Delete</b></td><td>Delete selected points</td></tr>
        <tr><td><b>Space</b></td><td>Play/Pause</td></tr>
        <tr><td><b>Left/Right</b></td><td>Previous/Next frame</td></tr>
        <tr><td><b>Home/End</b></td><td>First/Last frame</td></tr>
        <tr><td><b>C</b></td><td>Center view on selected</td></tr>
        <tr><td><b>R</b></td><td>Reset view</td></tr>
        <tr><td><b>G</b></td><td>Toggle grid</td></tr>
        <tr><td><b>B</b></td><td>Toggle background</td></tr>
        <tr><td><b>+/-</b></td><td>Zoom in/out</td></tr>
        </table>
        """)
        layout.addWidget(text_edit)

        # Add close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("Close")
        _ = close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        _ = dialog.exec()
