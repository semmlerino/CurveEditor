"""Smoothing controller for managing curve smoothing operations.

This controller handles the smoothing dialog, parameter collection,
and command execution for curve smoothing operations.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QInputDialog, QMessageBox

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class SmoothingController:
    """Controller for smoothing operations."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the smoothing controller.

        Args:
            main_window: Reference to the main window
        """
        self.main_window: MainWindow = main_window

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to selected points in the curve using Command pattern.

        Shows a dialog to get smoothing parameters and applies smoothing
        to the currently selected points or all points if none selected.
        """
        try:
            # Check if curve widget is available
            if self.main_window.curve_widget is None:
                logger.warning("No curve widget available for smoothing")
                return

            # Get the current curve data
            curve_data = self.main_window.curve_widget.curve_data  # pyright: ignore[reportAttributeAccessIssue]
            if not curve_data:
                QMessageBox.information(self.main_window, "No Data", "No curve data to smooth.")  # pyright: ignore
                return

            # Get selected points or use all points
            selected_indices = self.main_window.curve_widget.selected_indices  # pyright: ignore[reportAttributeAccessIssue]
            if not selected_indices:
                # Ask if user wants to smooth all points
                reply = QMessageBox.question(
                    self.main_window,  # pyright: ignore
                    "No Selection",
                    "No points selected. Apply smoothing to all points?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                selected_indices = list(range(len(curve_data)))

            # Get smoothing window size from user
            window_size = self._get_smoothing_window_size()
            if window_size is None:
                return  # User cancelled

            # Create and execute smooth command
            from core.commands.curve_commands import SmoothCommand
            from services import get_interaction_service

            smooth_command = SmoothCommand(
                description=f"Smooth {len(selected_indices)} points",
                indices=list(selected_indices),
                filter_type="moving_average",
                window_size=window_size,
            )

            # Execute through command manager for undo/redo support
            interaction_service = get_interaction_service()
            success = False
            if interaction_service and interaction_service.command_manager is not None:
                success = interaction_service.command_manager.execute_command(smooth_command, self.main_window)

            if success:
                # Update status
                self.main_window.statusBar().showMessage(  # pyright: ignore
                    f"Applied smoothing to {len(selected_indices)} points (window size: {window_size})", 3000
                )
                logger.info(f"Smoothing applied to {len(selected_indices)} points")
            else:
                QMessageBox.warning(self.main_window, "Smoothing Failed", "Failed to apply smoothing operation.")  # pyright: ignore

        except Exception as e:
            logger.error(f"Error in smooth operation: {e}")
            QMessageBox.critical(self.main_window, "Error", f"An error occurred during smoothing: {str(e)}")  # pyright: ignore

    def _get_smoothing_window_size(self) -> int | None:
        """Get smoothing window size from user.

        Returns:
            Window size or None if cancelled
        """
        try:
            # Try to use UI service first
            from services import get_ui_service

            ui_service = get_ui_service()
            if ui_service:
                return ui_service.get_smooth_window_size(self.main_window)  # pyright: ignore
        except Exception:
            pass  # Fall back to simple dialog

        # Fallback to simple input dialog
        window_size, ok = QInputDialog.getInt(
            self.main_window,  # pyright: ignore
            "Smoothing Window Size",
            "Enter window size (3-15):",
            5,
            3,
            15,
        )
        return window_size if ok else None
