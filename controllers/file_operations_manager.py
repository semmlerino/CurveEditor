"""
File operations manager for the Curve Editor application.

Manages file operations including new, open, save, save as,
and loading image sequences.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from PySide6.QtCore import QObject, QRect, Signal
from PySide6.QtWidgets import QFileDialog, QLabel, QSlider, QSpinBox, QWidget

from core.type_aliases import CurveDataList

if TYPE_CHECKING:
    from core.curve_data import CurveDataWithMetadata

logger = logging.getLogger(__name__)


class FileLoadWorkerProtocol(Protocol):
    """Protocol for FileLoadWorker interface."""

    def start_work(self, tracking_file: str | None, image_dir: str | None) -> None: ...
    def stop(self) -> None: ...


class SessionManagerProtocol(Protocol):
    """Protocol for SessionManager interface."""

    def create_session_data(
        self,
        tracking_file: str | None = None,
        image_directory: str | None = None,
        current_frame: int = 1,
        zoom_level: float = 1.0,
        pan_offset: tuple[float, float] = (0.0, 0.0),
        window_geometry: tuple[int, int, int, int] | None = None,
        active_points: list[str] | None = None,
    ) -> dict[str, str | int | float | tuple[float, float] | list[str] | None]: ...

    def save_session(
        self, session_data: dict[str, str | int | float | tuple[float, float] | list[str] | None]
    ) -> bool: ...


class CurveWidgetProtocol(Protocol):
    """Protocol for CurveWidget interface."""

    def set_curve_data(self, data: "CurveDataList | CurveDataWithMetadata") -> None: ...
    def setup_for_pixel_tracking(self) -> None: ...
    def setup_for_3dequalizer_data(self) -> None: ...
    def fit_to_view(self) -> None: ...
    @property
    def curve_data(self) -> "CurveDataList | CurveDataWithMetadata | None": ...


class StateManagerProtocol(Protocol):
    """Protocol for StateManager interface."""

    @property
    def is_modified(self) -> bool: ...
    @is_modified.setter
    def is_modified(self, value: bool) -> None: ...
    @property
    def current_file(self) -> str | None: ...
    @current_file.setter
    def current_file(self, value: str | None) -> None: ...
    @property
    def image_directory(self) -> str | None: ...
    @property
    def current_frame(self) -> int: ...
    @property
    def track_data(self) -> "CurveDataList | CurveDataWithMetadata | None": ...
    @property
    def total_frames(self) -> int: ...
    @total_frames.setter
    def total_frames(self, value: int) -> None: ...
    def reset_to_defaults(self) -> None: ...
    def set_track_data(self, data: "CurveDataList | CurveDataWithMetadata", mark_modified: bool) -> None: ...


class ServicesProtocol(Protocol):
    """Protocol for Services interface."""

    def confirm_action(self, message: str, parent: QWidget | None) -> bool: ...
    def save_track_data(self, data: "CurveDataList | CurveDataWithMetadata", parent: QWidget | None) -> bool: ...
    def load_track_data_from_file(self, file_path: str) -> "CurveDataList | CurveDataWithMetadata | None": ...
    def show_warning(self, message: str) -> None: ...


class MainWindowProtocol(Protocol):
    """Protocol for MainWindow interface needed by FileOperationsManager."""

    @property
    def curve_widget(self) -> CurveWidgetProtocol | None: ...
    @property
    def state_manager(self) -> StateManagerProtocol: ...
    @property
    def services(self) -> ServicesProtocol: ...
    @property
    def file_load_worker(self) -> FileLoadWorkerProtocol | None: ...
    @property
    def frame_slider(self) -> QSlider | None: ...
    @property
    def frame_spinbox(self) -> QSpinBox | None: ...
    @property
    def total_frames_label(self) -> QLabel | None: ...
    @property
    def tracked_data(self) -> dict[str, "CurveDataList"]: ...
    @tracked_data.setter
    def tracked_data(self, value: dict[str, "CurveDataList"]) -> None: ...
    @property
    def active_points(self) -> list[str]: ...
    @active_points.setter
    def active_points(self, value: list[str]) -> None: ...
    @property
    def session_manager(self) -> SessionManagerProtocol: ...
    def geometry(self) -> QRect: ...
    def _update_tracking_panel(self) -> None: ...
    def _update_curve_display(self) -> None: ...
    def _update_ui_state(self) -> None: ...
    def _update_timeline_tabs(self, data: "CurveDataList | CurveDataWithMetadata") -> None: ...
    def update_status(self, message: str) -> None: ...


class FileOperationsManager(QObject):
    """Manager for file operations."""

    # Signals
    file_new: Signal = Signal()
    file_opened: Signal = Signal(str)
    file_saved: Signal = Signal(str)
    images_loaded: Signal = Signal(str)

    def __init__(self, main_window: MainWindowProtocol, parent: QObject | None = None):
        """Initialize the file operations manager.

        Args:
            main_window: Reference to the main window
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.main_window: MainWindowProtocol = main_window

    def new_file(self) -> None:
        """Create a new file, clearing current data."""
        if self.main_window.state_manager.is_modified:
            if not self.main_window.services.confirm_action(
                "Current curve has unsaved changes. Continue?", cast(QWidget, cast(object, self.main_window))
            ):
                return

        # Clear curve widget data
        if self.main_window.curve_widget:
            self.main_window.curve_widget.set_curve_data([])
            self.main_window._update_tracking_panel()

        self.main_window.state_manager.reset_to_defaults()
        self.main_window._update_ui_state()
        self.main_window.update_status("New curve created")

        self.file_new.emit()

    def open_file(self) -> None:
        """Open a tracking data file."""
        # Check for unsaved changes
        if self.main_window.state_manager.is_modified:
            if not self.main_window.services.confirm_action(
                "Current curve has unsaved changes. Continue?", cast(QWidget, cast(object, self.main_window))
            ):
                return

        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            cast(QWidget, cast(object, self.main_window)),  # Cast through object for type safety
            "Open Tracking Data",
            "",
            "Text Files (*.txt);;JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)",
        )

        if not file_path:
            return

        # Check if it's a multi-point file
        if file_path.endswith(".txt"):
            # Try loading as multi-point format
            from services import get_data_service

            data_service = get_data_service()
            tracked_data = data_service.load_tracked_data(file_path)

            if tracked_data:
                # Successfully loaded multi-point data
                self.main_window.tracked_data = tracked_data
                self.main_window.active_points = list(tracked_data.keys())[:1]  # Select first point

                # Detect coordinate system and set up view BEFORE displaying
                if self.main_window.curve_widget:
                    # Detect if this is 3DE data based on file characteristics
                    # .txt files with multi-point tracking are typically 3DE exports
                    is_3de_data = file_path.endswith(".txt") and tracked_data and len(tracked_data) > 0

                    # Check for high-precision decimals characteristic of 3DE exports
                    if is_3de_data and tracked_data:
                        first_point_name = list(tracked_data.keys())[0]
                        first_trajectory = tracked_data[first_point_name]
                        if first_trajectory and len(first_trajectory) > 0:
                            # Check if coordinates have high precision (more than 3 decimal places)
                            x_coord = first_trajectory[0][1] if len(first_trajectory[0]) > 1 else 0
                            has_high_precision = len(str(x_coord).split(".")[-1]) > 3 if "." in str(x_coord) else False
                            is_3de_data = has_high_precision

                    if is_3de_data:
                        logger.info(f"[COORD] Detected 3DEqualizer data format for {file_path}")
                        self.main_window.curve_widget.setup_for_3dequalizer_data()
                    else:
                        logger.info(f"[COORD] Detected pixel tracking data format for {file_path}")
                        self.main_window.curve_widget.setup_for_pixel_tracking()

                self.main_window._update_tracking_panel()
                self.main_window._update_curve_display()

                # CRITICAL: Don't fit to view for 3DE/pixel tracking data
                # The data is already in pixel coordinates and should display at 1:1
                # Note: Multi-point tracking data is typically screen/pixel coordinates
                logger.info("[TRACKING] Skipping fit_to_view for pixel tracking data - displaying at 1:1")

                # Update frame range based on first trajectory
                if (
                    self.main_window.active_points
                    and self.main_window.active_points[0] in self.main_window.tracked_data
                ):
                    trajectory = self.main_window.tracked_data[self.main_window.active_points[0]]
                    if trajectory:
                        max_frame = max(point[0] for point in trajectory)
                        if self.main_window.frame_slider:
                            self.main_window.frame_slider.setMaximum(max_frame)
                        if self.main_window.frame_spinbox:
                            self.main_window.frame_spinbox.setMaximum(max_frame)
                        if self.main_window.total_frames_label:
                            self.main_window.total_frames_label.setText(str(max_frame))
                        self.main_window.state_manager.total_frames = max_frame

                # Update state manager so session saves the file path
                self.main_window.state_manager.current_file = file_path
                self.file_opened.emit(file_path)

                # Save session after successful multi-point file loading
                self.save_current_session()
                return

        # Fall back to single curve loading
        # Load data using data service directly
        from services import get_data_service

        data_service = get_data_service()
        data = data_service.load_tracked_data(file_path) if file_path else []
        if not data and file_path:
            # Try direct loading
            from services import get_data_service

            data_service = get_data_service()
            if file_path.endswith(".json"):
                data = data_service._load_json(file_path)
            elif file_path.endswith(".csv"):
                data = data_service._load_csv(file_path)
            elif file_path.endswith(".txt"):
                data = data_service._load_2dtrack_data(file_path)

        if data:
            # Handle both dictionary (multi-point) and list (single curve) formats
            if isinstance(data, dict):
                # Dictionary format - extract first point's data
                if data:
                    first_point_name = list(data.keys())[0]
                    curve_data: CurveDataList = data[first_point_name]
                else:
                    curve_data = []
            else:
                # List format (single curve)
                curve_data = data

            # Update curve widget with new data
            if self.main_window.curve_widget:
                self.main_window.curve_widget.set_curve_data(curve_data)

                # CRITICAL: Only fit to view for non-3DE data
                # 3DE data is already in pixel coordinates and should display at 1:1
                from core.coordinate_system import CoordinateSystem
                from core.curve_data import CurveDataWithMetadata

                should_fit = True
                if isinstance(data, CurveDataWithMetadata):
                    if data.metadata and data.metadata.system == CoordinateSystem.THREE_DE_EQUALIZER:
                        logger.info("[3DE] Skipping fit_to_view - data should display at 1:1 pixel mapping")
                        should_fit = False

                if should_fit:
                    # Fit the loaded data to view so it's visible
                    self.main_window.curve_widget.fit_to_view()

                self.main_window._update_tracking_panel()

            # Update state manager
            self.main_window.state_manager.set_track_data(curve_data, mark_modified=False)

            # Update frame range based on loaded data
            if curve_data:
                # Ensure frame numbers are integers
                try:
                    max_frame = max(int(point[0]) for point in curve_data if len(point) > 0)
                except (ValueError, TypeError, IndexError) as e:
                    logger.warning(f"Error parsing frame data for UI update: {e}. Using default max_frame=100")
                    max_frame = 100
                if self.main_window.frame_slider:
                    self.main_window.frame_slider.setMaximum(max_frame)
                if self.main_window.frame_spinbox:
                    self.main_window.frame_spinbox.setMaximum(max_frame)
                if self.main_window.total_frames_label:
                    self.main_window.total_frames_label.setText(str(max_frame))
                # CRITICAL: Update state manager's total frames!
                self.main_window.state_manager.total_frames = max_frame

                # Update timeline tabs with frame range and point data
                self.main_window._update_timeline_tabs(curve_data)

            self.main_window._update_ui_state()
            self.main_window.update_status("File loaded successfully")

            # Update state manager so session saves the file path
            self.main_window.state_manager.current_file = file_path
            self.file_opened.emit(file_path)

            # Save session after successful file loading
            self.save_current_session()

    def save_file(self) -> None:
        """Save the current file."""
        # Check if there's data to save
        data = self.get_current_curve_data()
        if not data:
            self.main_window.services.show_warning("No curve data to save")
            return

        if not self.main_window.state_manager.current_file:
            self.save_file_as()
        else:
            if self.main_window.services.save_track_data(data, cast(QWidget, cast(object, self.main_window))):
                self.main_window.state_manager.is_modified = False
                self.main_window.update_status("File saved successfully")
                self.file_saved.emit(self.main_window.state_manager.current_file)

    def save_file_as(self) -> None:
        """Save the current file with a new name."""
        # Get current data from curve widget
        data = self.get_current_curve_data()
        if not data:
            self.main_window.services.show_warning("No curve data to save")
            return

        if self.main_window.services.save_track_data(data, cast(QWidget, cast(object, self.main_window))):
            self.main_window.state_manager.is_modified = False
            self.main_window.update_status("File saved successfully")
            if self.main_window.state_manager.current_file:
                self.file_saved.emit(self.main_window.state_manager.current_file)

    def load_image_sequence(self) -> None:
        """Load an image sequence."""
        # Open directory selection dialog
        image_dir = QFileDialog.getExistingDirectory(
            cast(QWidget, cast(object, self.main_window)),  # Cast through object for type safety
            "Select Image Sequence Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if image_dir:
            # Use the file load worker to load only images (no tracking data)
            if self.main_window.file_load_worker:
                logger.info(f"Loading image sequence from: {image_dir}")
                self.main_window.update_status(f"Loading images from {image_dir}...")
                # Pass None for tracking file to load only images
                self.main_window.file_load_worker.start_work(None, image_dir)
                self.images_loaded.emit(image_dir)

                # Save session after successful image loading
                self.save_current_session()
            else:
                logger.error("File load worker not available")
                self.main_window.update_status("Error: Unable to load images")

    def load_burger_tracking_data(self) -> None:
        """Auto-load burger footage and tracking data if available using background thread."""
        # Get the current working directory
        base_dir = Path(__file__).parent.parent.parent  # Go up to project root

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
                if dir_path.exists() and dir_path.is_dir():
                    image_dir_path = str(dir_path)
                    logger.info(f"Found burger footage at: {image_dir_path}")
                    break

        # Always proceed with loading if we have at least the image directory
        if not image_dir_path:
            logger.warning("No burger footage found in any expected location")
            logger.debug(f"Checked: {base_dir}/footage/Burger, {base_dir}/Data/burger, {base_dir}/Burger")
            # Still continue to attempt loading from default location
            image_dir_path = str(footage_dir)  # Use default even if it doesn't exist

        # Start new work in Python thread
        if not self.main_window.file_load_worker:
            logger.error("[PYTHON-THREAD] Worker not initialized! This should not happen.")
            return

        logger.info("[PYTHON-THREAD] Starting file loading in Python thread")

        # Start work in new Python thread
        self.main_window.file_load_worker.start_work(tracking_file_path, image_dir_path)

        logger.info("[PYTHON-THREAD] File loading started in Python thread")

    def get_current_curve_data(self) -> "CurveDataList | CurveDataWithMetadata | None":
        """Get current curve data from curve widget or state manager.

        Returns:
            Current curve data
        """
        if self.main_window.curve_widget:
            return self.main_window.curve_widget.curve_data
        return self.main_window.state_manager.track_data

    def cleanup_file_load_thread(self) -> None:
        """Clean up file loading thread - stops Python thread if running."""
        logger.info("[PYTHON-THREAD] cleanup_file_load_thread called - stopping Python thread if running")
        if self.main_window.file_load_worker:
            self.main_window.file_load_worker.stop()

    def save_current_session(self) -> None:
        """Save the current application state to session."""
        try:
            # Check if session manager is available
            if not hasattr(self.main_window, "session_manager"):
                logger.warning("SessionManager not available, skipping session save")
                return

            # Get current state from various components
            current_file = self.main_window.state_manager.current_file
            image_directory = self.main_window.state_manager.image_directory
            current_frame = self.main_window.state_manager.current_frame

            # Get view state from curve widget if available
            zoom_level = 1.0
            pan_offset = (0.0, 0.0)
            if self.main_window.curve_widget:
                zoom_level = getattr(self.main_window.curve_widget, "zoom_factor", 1.0)
                pan_offset = (
                    getattr(self.main_window.curve_widget, "pan_offset_x", 0.0),
                    getattr(self.main_window.curve_widget, "pan_offset_y", 0.0),
                )

            # Get active points for multi-point tracking
            active_points = getattr(self.main_window, "active_points", [])

            # Get window geometry
            window_geometry = None
            try:
                geometry = self.main_window.geometry()
                window_geometry = (geometry.x(), geometry.y(), geometry.width(), geometry.height())
            except Exception as e:
                logger.debug(f"Could not get window geometry: {e}")

            # Create session data
            session_data = self.main_window.session_manager.create_session_data(
                tracking_file=current_file,
                image_directory=image_directory,
                current_frame=current_frame,
                zoom_level=zoom_level,
                pan_offset=pan_offset,
                window_geometry=window_geometry,
                active_points=active_points,
            )

            # Save session data
            success = self.main_window.session_manager.save_session(session_data)
            if success:
                logger.debug("Session saved successfully")
            else:
                logger.warning("Failed to save session")

        except Exception as e:
            logger.error(f"Error saving session: {e}")
