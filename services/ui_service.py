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

import logging
from typing import Any

from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

logger = logging.getLogger("ui_service")


class UIService:
    """
    Consolidated service for all UI operations.
    
    This service handles:
    - Dialog operations (input dialogs, message boxes, confirmations)
    - Status bar updates
    - UI component state management
    - User notifications
    """
    
    def __init__(self):
        """Initialize the UIService."""
        pass
    
    # ==================== Dialog Methods (from dialog_service) ====================
    
    def get_smooth_window_size(self, parent: QWidget) -> int | None:
        """Get smoothing window size from user.
        
        Args:
            parent: Parent widget for the dialog
        
        Returns:
            Window size or None if cancelled
        """
        value, ok = QInputDialog.getInt(
            parent, "Smooth Curve", "Window size:", 5, 3, 20
        )
        return value if ok else None
    
    def get_filter_params(self, parent: QWidget) -> tuple[str, int] | None:
        """Get filter type and parameters from user.
        
        Args:
            parent: Parent widget for the dialog
        
        Returns:
            Tuple of (filter_type, parameter) or None if cancelled
        """
        filter_types = ["Median", "Butterworth"]
        filter_type, ok = QInputDialog.getItem(
            parent, "Filter Curve", "Filter type:", filter_types, 0, False
        )
        if not ok:
            return None
        
        if filter_type == "Median":
            window, ok = QInputDialog.getInt(
                parent, "Median Filter", "Window size:", 5, 3, 20
            )
            return (filter_type, window) if ok else None
        else:  # Butterworth
            cutoff, ok = QInputDialog.getDouble(
                parent, "Butterworth Filter", "Cutoff frequency:", 0.1, 0.01, 1.0, 2
            )
            return (filter_type, int(cutoff * 100)) if ok else None
    
    def get_offset_values(self, parent: QWidget) -> tuple[float, float] | None:
        """Get X and Y offset values from user.
        
        Args:
            parent: Parent widget for the dialog
        
        Returns:
            Tuple of (x_offset, y_offset) or None if cancelled
        """
        x_offset, ok = QInputDialog.getDouble(
            parent, "Offset Curve", "X offset:", 0.0, -1000.0, 1000.0, 2
        )
        if not ok:
            return None
        
        y_offset, ok = QInputDialog.getDouble(
            parent, "Offset Curve", "Y offset:", 0.0, -1000.0, 1000.0, 2
        )
        return (x_offset, y_offset) if ok else None
    
    def get_fill_gaps_size(self, parent: QWidget) -> int | None:
        """Get maximum gap size to fill from user.
        
        Args:
            parent: Parent widget for the dialog
        
        Returns:
            Maximum gap size or None if cancelled
        """
        value, ok = QInputDialog.getInt(
            parent, "Fill Gaps", "Maximum gap size:", 10, 1, 100
        )
        return value if ok else None
    
    def get_scale_values(self, parent: QWidget) -> tuple[float, float] | None:
        """Get X and Y scale values from user.
        
        Args:
            parent: Parent widget for the dialog
        
        Returns:
            Tuple of (x_scale, y_scale) or None if cancelled
        """
        x_scale, ok = QInputDialog.getDouble(
            parent, "Scale Curve", "X scale:", 1.0, 0.01, 100.0, 2
        )
        if not ok:
            return None
        
        y_scale, ok = QInputDialog.getDouble(
            parent, "Scale Curve", "Y scale:", 1.0, 0.01, 100.0, 2
        )
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
    
    def get_integer_input(self, parent: QWidget, title: str, label: str, 
                         default: int = 0, min_val: int = -2147483647, 
                         max_val: int = 2147483647) -> int | None:
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
    
    def get_float_input(self, parent: QWidget, title: str, label: str,
                       default: float = 0.0, min_val: float = -2147483647.0,
                       max_val: float = 2147483647.0, decimals: int = 2) -> float | None:
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
    
    def get_choice(self, parent: QWidget, title: str, label: str, 
                  choices: list[str], current: int = 0) -> str | None:
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
        QMessageBox.critical(parent, title, message)
        logger.error(f"Error shown to user: {message}")
    
    def show_warning(self, parent: QWidget, message: str, title: str = "Warning") -> None:
        """Show warning message dialog.
        
        Args:
            parent: Parent widget for the dialog
            message: Warning message to display
            title: Dialog title
        """
        QMessageBox.warning(parent, title, message)
        logger.warning(f"Warning shown to user: {message}")
    
    def show_info(self, parent: QWidget, message: str, title: str = "Information") -> None:
        """Show information message dialog.
        
        Args:
            parent: Parent widget for the dialog
            message: Information message to display
            title: Dialog title
        """
        QMessageBox.information(parent, title, message)
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
    
    def set_status(self, main_window: Any, message: str, timeout: int = 0) -> None:
        """Set status bar message.
        
        Args:
            main_window: Main window with status bar
            message: Status message to display
            timeout: Timeout in milliseconds (0 = permanent)
        """
        if hasattr(main_window, "statusBar"):
            main_window.statusBar().showMessage(message, timeout)
            logger.debug(f"Status bar updated: {message}")
    
    def clear_status(self, main_window: Any) -> None:
        """Clear status bar message.
        
        Args:
            main_window: Main window with status bar
        """
        if hasattr(main_window, "statusBar"):
            main_window.statusBar().clearMessage()
    
    def set_permanent_status(self, main_window: Any, message: str) -> None:
        """Set a permanent status message.
        
        Args:
            main_window: Main window with status bar
            message: Status message to display permanently
        """
        self.set_status(main_window, message, 0)
    
    def set_temporary_status(self, main_window: Any, message: str, timeout: int = 3000) -> None:
        """Set a temporary status message.
        
        Args:
            main_window: Main window with status bar
            message: Status message to display
            timeout: Timeout in milliseconds (default 3 seconds)
        """
        self.set_status(main_window, message, timeout)
    
    # ==================== UI State Management ====================
    
    def enable_ui_components(self, main_window: Any, components: list[str], enabled: bool = True) -> None:
        """Enable or disable UI components.
        
        Args:
            main_window: Main window containing the components
            components: List of component attribute names
            enabled: Whether to enable (True) or disable (False)
        """
        for component_name in components:
            component = getattr(main_window, component_name, None)
            if component and hasattr(component, "setEnabled"):
                component.setEnabled(enabled)
    
    def update_button_states(self, main_window: Any) -> None:
        """Update the enabled state of various buttons based on application state.
        
        Args:
            main_window: Main window containing the buttons
        """
        # Update undo/redo buttons
        if hasattr(main_window, "undo_button") and hasattr(main_window, "history_index"):
            main_window.undo_button.setEnabled(main_window.history_index > 0)
        
        if hasattr(main_window, "redo_button") and hasattr(main_window, "history"):
            main_window.redo_button.setEnabled(
                main_window.history_index < len(main_window.history) - 1
            )
        
        # Update save button
        if hasattr(main_window, "save_button") and hasattr(main_window, "curve_data"):
            main_window.save_button.setEnabled(len(main_window.curve_data) > 0)
        
        # Update selection-dependent buttons
        has_selection = False
        if hasattr(main_window, "selected_indices"):
            has_selection = len(main_window.selected_indices) > 0
        
        selection_buttons = ["delete_button", "update_point_button", "duplicate_button"]
        for button_name in selection_buttons:
            button = getattr(main_window, button_name, None)
            if button:
                button.setEnabled(has_selection)
    
    def update_window_title(self, main_window: Any, title: str = None, modified: bool = False) -> None:
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
        
        if hasattr(main_window, "setWindowTitle"):
            main_window.setWindowTitle(title)
    
    def show_progress(self, main_window: Any, message: str, value: int = -1, maximum: int = 100) -> None:
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
    
    def update_ui_from_data(self, main_window: Any) -> None:
        """Update all UI components based on current data state.
        
        Args:
            main_window: Main window to update
        """
        # Update button states
        self.update_button_states(main_window)
        
        # Update status bar with data info
        if hasattr(main_window, "curve_data"):
            point_count = len(main_window.curve_data)
            self.set_status(main_window, f"{point_count} points loaded")
        
        # Update window title if modified
        if hasattr(main_window, "is_modified") and main_window.is_modified:
            self.update_window_title(main_window, modified=True)
    
    def create_context_menu(self, parent: QWidget, actions: dict[str, callable]) -> "QMenu":
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
                menu.addSeparator()
            else:
                action = menu.addAction(action_name)
                if callback:
                    action.triggered.connect(callback)
        
        return menu


# Module-level singleton instance
_instance = UIService()

def get_ui_service() -> UIService:
    """Get the singleton instance of UIService."""
    return _instance