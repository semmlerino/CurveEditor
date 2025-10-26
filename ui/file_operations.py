#!/usr/bin/env python
"""
File Operations Manager for CurveEditor.

This module handles all file I/O operations including loading, saving,
and background file processing. Extracted from MainWindow to improve
maintainability and separation of concerns.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from core.type_aliases import CurveDataList
from io_utils.file_load_worker import FileLoadWorker
from services import get_data_service

if TYPE_CHECKING:
    from .service_facade import ServiceFacade
    from .state_manager import StateManager

from core.logger_utils import get_logger

logger = get_logger("file_operations")


# FileLoadWorker is now imported from io_utils.file_load_worker
# It uses QThread for proper Qt threading instead of Python threading


class FileOperations(QObject):
    """
    Manages all file operations for the CurveEditor application.

    This class handles file loading, saving, and background processing,
    extracted from MainWindow for better separation of concerns.
    """

    # Signals for communication with MainWindow
    tracking_data_loaded: Signal = Signal(list)
    multi_point_data_loaded: Signal = Signal(dict)
    image_sequence_loaded: Signal = Signal(str, list)
    progress_updated: Signal = Signal(int, str)
    error_occurred: Signal = Signal(str)
    file_loaded: Signal = Signal(str)  # Emits file path when loaded
    file_saved: Signal = Signal(str)  # Emits file path when saved
    finished: Signal = Signal()  # Loading finished

    def __init__(
        self,
        parent: QWidget | None = None,
        state_manager: "StateManager | None" = None,
        services: "ServiceFacade | None" = None,
    ) -> None:
        """
        Initialize the file operations manager.

        Args:
            parent: Parent widget for dialogs
            state_manager: Application state manager
            services: Service facade for I/O operations
        """
        super().__init__(parent)
        self.parent_widget: QWidget | None = parent
        self.state_manager: StateManager | None = state_manager
        self.services: ServiceFacade | None = services

        # Initialize file loading components
        # FileLoadWorker now inherits from QThread with signals as class attributes
        self.file_load_worker: FileLoadWorker = FileLoadWorker()

        # Connect worker signals to our signals
        self._connect_worker_signals()

        logger.info("FileOperations initialized")

    def _connect_worker_signals(self) -> None:
        """Connect worker signals to FileOperations signals."""
        # FileLoadWorker now has signals as class attributes (QThread pattern)
        # tracking_data_loaded can emit either single curve or dict of curves
        _ = self.file_load_worker.tracking_data_loaded.connect(self._on_tracking_data_loaded)
        _ = self.file_load_worker.image_sequence_loaded.connect(self.image_sequence_loaded.emit)
        _ = self.file_load_worker.progress_updated.connect(self.progress_updated.emit)
        _ = self.file_load_worker.error_occurred.connect(self.error_occurred.emit)
        _ = self.file_load_worker.finished.connect(self.finished.emit)

    def _on_tracking_data_loaded(self, file_path: str, data: object) -> None:
        """Handle tracking data loaded from worker.

        The new FileLoadWorker emits file path and data.
        This handler updates state and splits the signal for backward compatibility.

        Args:
            file_path: Path to the loaded file
            data: Loaded data (single curve or multi-point dict)
        """
        # Set state BEFORE emitting signals (for session persistence)
        if self.state_manager:
            self.state_manager.current_file = file_path
            self.state_manager.is_modified = False
            logger.debug(f"[FILE-LOAD] Set current_file to: {file_path}")

        if isinstance(data, dict):
            # Multi-point data
            self.multi_point_data_loaded.emit(data)
        else:
            # Single curve data
            self.tracking_data_loaded.emit(data)

    def cleanup_threads(self) -> None:
        """Clean up background threads."""
        if self.file_load_worker:
            self.file_load_worker.stop()

    def new_file(self) -> bool:
        """
        Create a new file, prompting to save if needed.

        Returns:
            True if new file was created, False if cancelled
        """
        # Check for unsaved changes
        if self.state_manager and self.state_manager.is_modified and self.services and not self.services.confirm_action(
            "Current curve has unsaved changes. Continue?", self.parent_widget
        ):
            return False

        # Clear state
        if self.state_manager:
            self.state_manager.current_file = None
            self.state_manager.is_modified = False

        return True

    def open_file(self, parent_widget: QWidget | None = None) -> CurveDataList | dict[str, CurveDataList] | None:
        """
        Open a file dialog and load the selected file.

        Args:
            parent_widget: Parent widget for the dialog

        Returns:
            Loaded data (single curve or multi-point dict), or None if cancelled
        """
        from typing import cast

        parent = parent_widget or self.parent_widget

        # Check for unsaved changes
        if self.state_manager and self.state_manager.is_modified and self.services and not self.services.confirm_action(
            "Current curve has unsaved changes. Continue?", parent
        ):
            return None

        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Open Tracking Data",
            "",
            "Text Files (*.txt);;JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)",
        )

        if not file_path:
            return None

        # Check if it's a multi-point file
        if file_path.endswith(".txt"):
            # Try loading as multi-point format
            data_service = get_data_service()
            tracked_data = data_service.load_tracked_data(file_path)

            if tracked_data:
                # Successfully loaded multi-point data
                # Set state BEFORE emitting signal (for session persistence)
                if self.state_manager:
                    self.state_manager.current_file = file_path
                    self.state_manager.is_modified = False
                self.file_loaded.emit(file_path)
                return tracked_data

        # Fall back to single curve loading
        if self.services:
            data = self.services.load_track_data_from_file(file_path)
            if data:
                # Set state BEFORE emitting signal (for session persistence)
                if self.state_manager:
                    self.state_manager.current_file = file_path
                    self.state_manager.is_modified = False
                self.file_loaded.emit(file_path)
                # Cast to proper return type
                return cast(CurveDataList, data)

        return None

    def save_file(self, data: CurveDataList, file_path: str | None = None) -> bool:
        """
        Save data to a file.

        Args:
            data: Curve data to save
            file_path: Path to save to (uses current file if None)

        Returns:
            True if saved successfully, False otherwise
        """
        # Use current file if no path specified
        if file_path is None and self.state_manager:
            file_path = self.state_manager.current_file

        if not file_path:
            return self.save_file_as(data)

        # Save directly using DataService
        data_service = get_data_service()
        success = data_service.save_json(file_path, data)

        if success:
            # Set state BEFORE emitting signal (for session persistence)
            if self.state_manager:
                self.state_manager.current_file = file_path
                self.state_manager.is_modified = False
            self.file_saved.emit(file_path)
            return True

        return False

    def save_file_as(self, data: CurveDataList, parent_widget: QWidget | None = None) -> bool:
        """
        Show save dialog and save data to selected file.

        Args:
            data: Curve data to save
            parent_widget: Parent widget for the dialog

        Returns:
            True if saved successfully, False if cancelled or failed
        """
        parent = parent_widget or self.parent_widget

        # Show save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Save Tracking Data",
            "",
            "Text Files (*.txt);;JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)",
        )

        if not file_path:
            return False

        return self.save_file(data, file_path)

    def load_burger_data_async(self) -> None:
        """Auto-load burger footage and tracking data if available using background thread."""
        # Get the current working directory
        base_dir = Path(__file__).parent.parent

        # Check for tracking data file - try v2 first, then v1
        tracking_file = base_dir / "2DTrackDatav2.txt"
        if not tracking_file.exists():
            tracking_file = base_dir / "2DTrackData.txt"
            if not tracking_file.exists():
                # Also check in footage directory
                tracking_file = base_dir / "footage" / "Burger" / "2DTrackDatav2.txt"
                if not tracking_file.exists():
                    tracking_file = base_dir / "footage" / "Burger" / "2DTrackData.txt"

        # Check for burger footage directory
        footage_dir = base_dir / "footage" / "Burger"

        # Determine what files need to be loaded
        tracking_file_path = str(tracking_file) if tracking_file.exists() else None
        image_dir_path = str(footage_dir) if footage_dir.exists() else None

        # For debugging: Always try to load burger sequence
        if not image_dir_path:
            # Try to find it in different locations
            possible_dirs = [base_dir / "footage" / "Burger", base_dir / "Data" / "burger", base_dir / "Burger"]
            for dir_path in possible_dirs:
                if dir_path.exists():
                    image_dir_path = str(dir_path)
                    logger.info(f"[FILE-OPS] Found burger footage at: {image_dir_path}")
                    break

        if tracking_file_path or image_dir_path:
            logger.info(
                f"[FILE-OPS] Starting background load - tracking: {bool(tracking_file_path)}, images: {bool(image_dir_path)}"
            )
            self.file_load_worker.start_work(tracking_file_path, image_dir_path)
        else:
            logger.info("[FILE-OPS] No burger data found to auto-load")

    def load_images(self, parent_widget: QWidget | None = None) -> bool:
        """
        Load background image sequence using visual browser dialog.

        Args:
            parent_widget: Parent widget for dialogs

        Returns:
            True if loading started successfully
        """
        from ui.image_sequence_browser import ImageSequenceBrowserDialog

        parent = parent_widget or self.parent_widget

        # Get last used directory from state manager
        last_dir: str | None = None
        if self.state_manager is not None:
            # Use getattr with default to avoid type safety issues
            last_dir = getattr(self.state_manager, "image_directory", None)

        # Show image sequence browser dialog with last directory
        dialog = ImageSequenceBrowserDialog(parent, start_directory=last_dir)
        if dialog.exec() != ImageSequenceBrowserDialog.DialogCode.Accepted:
            return False

        selected_directory = dialog.get_selected_directory()
        if not selected_directory:
            return False

        # Remember the selected directory for next time
        if self.state_manager is not None:
            # StateManager always has image_directory property
            self.state_manager.image_directory = selected_directory
            # StateManager always has add_recent_directory method
            self.state_manager.add_recent_directory(selected_directory)

        # Start background loading of image sequence
        self.file_load_worker.start_work(tracking_file_path=None, image_dir_path=selected_directory)

        return True

    def export_data(self, data: CurveDataList, parent_widget: QWidget | None = None) -> bool:
        """
        Export curve data (placeholder for future implementation).

        Args:
            data: Data to export
            parent_widget: Parent widget for dialogs

        Returns:
            True if exported successfully
        """
        _ = data  # Unused for now - placeholder for future implementation
        parent = parent_widget or self.parent_widget
        # TODO: Implement data export dialog
        _ = QMessageBox.information(parent, "Not Implemented", "Data export will be implemented soon.")
        return False
