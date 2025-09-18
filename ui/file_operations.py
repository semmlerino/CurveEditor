#!/usr/bin/env python
"""
File Operations Manager for CurveEditor.

This module handles all file I/O operations including loading, saving,
and background file processing. Extracted from MainWindow to improve
maintainability and separation of concerns.
"""

import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from core.type_aliases import CurveDataList
from services import get_data_service

if TYPE_CHECKING:
    from .service_facade import ServiceFacade
    from .state_manager import StateManager

from core.logger_utils import get_logger

logger = get_logger("file_operations")


class FileLoadSignals(QObject):
    """Signal emitter for thread-safe communication from Python thread to Qt main thread."""

    # Signals for communicating with main thread
    tracking_data_loaded: Signal = Signal(list)  # Emits list of tracking data points
    multi_point_data_loaded: Signal = Signal(dict)  # Emits dict of multi-point tracking data
    image_sequence_loaded: Signal = Signal(str, list)  # Emits directory path and list of filenames
    progress_updated: Signal = Signal(int, str)  # Emits progress percentage and status message
    error_occurred: Signal = Signal(str)  # Emits error message
    finished: Signal = Signal()  # Emits when all loading is complete


class FileLoadWorker:
    """Worker class for loading files in a Python background thread (not QThread)."""

    def __init__(self, signals: FileLoadSignals):
        """Initialize worker with signal emitter."""
        self.signals: FileLoadSignals = signals  # QObject for emitting signals
        self.tracking_file_path: str | None = None
        self.image_dir_path: str | None = None
        self._should_stop: bool = False
        self._work_ready: bool = False
        self._work_ready_lock: threading.Lock = threading.Lock()
        self._stop_lock: threading.Lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def stop(self) -> None:
        """Request the worker to stop processing."""
        with self._stop_lock:
            self._should_stop = True
        # Wait for thread to finish if it's running
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def start_work(self, tracking_file_path: str | None, image_dir_path: str | None) -> None:
        """Start new file loading work in a Python thread."""
        # Stop any existing work
        self.stop()

        # Set new work parameters
        self.tracking_file_path = tracking_file_path
        self.image_dir_path = image_dir_path
        with self._work_ready_lock:
            self._work_ready = True
        self._should_stop = False

        # Start new thread
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def _check_should_stop(self) -> bool:
        """Thread-safe check of stop flag."""
        with self._stop_lock:
            return self._should_stop

    def run(self) -> None:
        """Main worker method that runs in background Python thread."""
        # Check if there's work ready
        with self._work_ready_lock:
            if not self._work_ready:
                return  # No work to do
            self._work_ready = False

        logger.info(f"[PYTHON-THREAD] Worker.run() starting in Python thread: {threading.current_thread().name}")
        try:
            total_tasks = 0
            current_task = 0

            # Count tasks to do
            if self.tracking_file_path:
                total_tasks += 1
            if self.image_dir_path:
                total_tasks += 1

            if total_tasks == 0:
                self.signals.finished.emit()
                return

            # Load tracking data if requested
            if self.tracking_file_path and not self._check_should_stop():
                self.signals.progress_updated.emit(0, "Loading tracking data...")
                try:
                    # Check if it's a multi-point file
                    is_multi_point = False
                    try:
                        with open(self.tracking_file_path) as f:
                            content = f.read(500)  # Read first 500 chars to detect format
                            # Multi-point files have "Point" followed by a name
                            is_multi_point = "Point" in content and ("Point1" in content or "Point01" in content)
                    except OSError:
                        pass

                    multi_data = {}
                    data = []

                    if is_multi_point:
                        # Load as multi-point data
                        multi_data = self._load_multi_point_data_direct(
                            self.tracking_file_path, flip_y=True, image_height=720
                        )
                        if multi_data:
                            # Emit multi-point data signal
                            self.signals.multi_point_data_loaded.emit(multi_data)

                            # Also emit first point's data for compatibility
                            first_point = list(multi_data.keys())[0] if multi_data else None
                            data = multi_data.get(first_point, []) if first_point else []

                            logger.info(
                                f"[PYTHON-THREAD] Loaded {len(multi_data)} tracking points from multi-point file"
                            )
                    else:
                        # Load as single-point data
                        data = self._load_2dtrack_data_direct(self.tracking_file_path, flip_y=True, image_height=720)
                        if data:
                            logger.info(
                                f"[PYTHON-THREAD] Emitting tracking_data_loaded from Python thread: {threading.current_thread().name}"
                            )
                            self.signals.tracking_data_loaded.emit(data)

                    current_task += 1
                    progress = int((current_task / total_tasks) * 100)

                    if is_multi_point and multi_data:
                        total_points = sum(len(traj) for traj in multi_data.values())
                        self.signals.progress_updated.emit(
                            progress, f"Loaded {len(multi_data)} trajectories, {total_points} total points"
                        )
                    else:
                        self.signals.progress_updated.emit(
                            progress, f"Loaded {len(data) if data else 0} tracking points"
                        )
                except Exception as e:
                    self.signals.error_occurred.emit(f"Failed to load tracking data: {str(e)}")

            # Load image sequence if requested
            if self.image_dir_path and not self._check_should_stop():
                self.signals.progress_updated.emit(int((current_task / total_tasks) * 100), "Loading image sequence...")
                try:
                    # Directly scan for image files without creating DataService
                    image_files = self._scan_image_directory(self.image_dir_path)
                    if image_files:
                        logger.info(
                            f"[PYTHON-THREAD] Emitting image_sequence_loaded from Python thread: {threading.current_thread().name}"
                        )
                        self.signals.image_sequence_loaded.emit(self.image_dir_path, image_files)
                    current_task += 1
                    self.signals.progress_updated.emit(100, f"Loaded {len(image_files) if image_files else 0} images")
                except Exception as e:
                    self.signals.error_occurred.emit(f"Failed to load image sequence: {str(e)}")

            # Emit finished signal
            self.signals.finished.emit()
            logger.info(f"[PYTHON-THREAD] Worker.run() finished in Python thread: {threading.current_thread().name}")

        except Exception as e:
            logger.error(f"[PYTHON-THREAD] Worker.run() error: {e}")
            self.signals.error_occurred.emit(str(e))
            self.signals.finished.emit()

    def _scan_image_directory(self, directory: str) -> list[str]:
        """Scan directory for image files."""
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
        image_files = []

        try:
            for file_name in sorted(os.listdir(directory)):
                if any(file_name.lower().endswith(ext) for ext in image_extensions):
                    image_files.append(file_name)
        except OSError as e:
            logger.error(f"Failed to scan image directory: {e}")

        return image_files

    def _load_2dtrack_data_direct(
        self, file_path: str, flip_y: bool = False, image_height: float = 720
    ) -> list[tuple[int, float, float] | tuple[int, float, float, str]]:
        """Load 2D tracking data directly."""
        data = []

        try:
            with open(file_path) as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            frame = int(parts[0])
                            x = float(parts[1])
                            y = float(parts[2])

                            if flip_y:
                                y = image_height - y

                            # Check for status field
                            if len(parts) >= 4:
                                status = parts[3]
                                data.append((frame, x, y, status))
                            else:
                                data.append((frame, x, y))

                        except ValueError as e:
                            logger.warning(f"Failed to parse line {line_num} in {file_path}: {e}")

        except OSError as e:
            logger.error(f"Failed to load tracking data from {file_path}: {e}")

        return data

    def _load_multi_point_data_direct(
        self, file_path: str, flip_y: bool = False, image_height: float = 720
    ) -> dict[str, CurveDataList]:
        """Load multi-point tracking data directly."""
        multi_data: dict[str, CurveDataList] = {}
        current_point = None

        try:
            with open(file_path) as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue

                    # Check for point marker
                    if line.startswith("Point"):
                        # Extract point name
                        parts = line.split()
                        if len(parts) >= 2:
                            current_point = parts[1]
                            multi_data[current_point] = []
                    elif current_point and not line.startswith("#"):
                        # Parse trajectory data
                        parts = line.split()
                        if len(parts) >= 3:
                            try:
                                frame = int(parts[0])
                                x = float(parts[1])
                                y = float(parts[2])

                                if flip_y:
                                    y = image_height - y

                                # Check for status field
                                if len(parts) >= 4:
                                    status = parts[3]
                                    multi_data[current_point].append((frame, x, y, status))
                                else:
                                    multi_data[current_point].append((frame, x, y))

                            except ValueError:
                                continue

        except OSError as e:
            logger.error(f"Failed to load multi-point data from {file_path}: {e}")

        return multi_data


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
        self.parent_widget = parent
        self.state_manager = state_manager
        self.services = services

        # Initialize file loading components
        self.file_load_signals = FileLoadSignals()
        self.file_load_worker = FileLoadWorker(self.file_load_signals)

        # Connect worker signals to our signals
        self._connect_worker_signals()

        logger.info("FileOperations initialized")

    def _connect_worker_signals(self) -> None:
        """Connect worker signals to FileOperations signals."""
        self.file_load_signals.tracking_data_loaded.connect(self.tracking_data_loaded.emit)
        self.file_load_signals.multi_point_data_loaded.connect(self.multi_point_data_loaded.emit)
        self.file_load_signals.image_sequence_loaded.connect(self.image_sequence_loaded.emit)
        self.file_load_signals.progress_updated.connect(self.progress_updated.emit)
        self.file_load_signals.error_occurred.connect(self.error_occurred.emit)
        self.file_load_signals.finished.connect(self.finished.emit)

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
        if self.state_manager and self.state_manager.is_modified:
            if self.services and not self.services.confirm_action(
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
        parent = parent_widget or self.parent_widget

        # Check for unsaved changes
        if self.state_manager and self.state_manager.is_modified:
            if self.services and not self.services.confirm_action(
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
                self.file_loaded.emit(file_path)
                if self.state_manager:
                    self.state_manager.current_file = file_path
                    self.state_manager.is_modified = False
                return tracked_data

        # Fall back to single curve loading
        if self.services:
            data = self.services.load_track_data_from_file(file_path)
            if data:
                self.file_loaded.emit(file_path)
                if self.state_manager:
                    self.state_manager.current_file = file_path
                    self.state_manager.is_modified = False
                return data

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

        # Save using services
        if self.services:
            if self.services.save_track_data_to_file(data, file_path):
                self.file_saved.emit(file_path)
                if self.state_manager:
                    self.state_manager.current_file = file_path
                    self.state_manager.is_modified = False
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
        Load background images (placeholder for future implementation).

        Args:
            parent_widget: Parent widget for dialogs

        Returns:
            True if loaded successfully
        """
        parent = parent_widget or self.parent_widget
        # TODO: Implement image loading dialog
        QMessageBox.information(parent, "Not Implemented", "Image loading will be implemented soon.")
        return False

    def export_data(self, data: CurveDataList, parent_widget: QWidget | None = None) -> bool:
        """
        Export curve data (placeholder for future implementation).

        Args:
            data: Data to export
            parent_widget: Parent widget for dialogs

        Returns:
            True if exported successfully
        """
        parent = parent_widget or self.parent_widget
        # TODO: Implement data export dialog
        QMessageBox.information(parent, "Not Implemented", "Data export will be implemented soon.")
        return False
