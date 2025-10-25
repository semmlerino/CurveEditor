"""
Background file loading worker.

Handles asynchronous loading of tracking data and image sequences
using Qt threading (QThread) for proper Qt integration and thread safety.
"""

import logging
from pathlib import Path
from typing import ClassVar, override

from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal

from core.config import get_config
from core.coordinate_detector import detect_coordinate_system
from core.curve_data import CurveDataWithMetadata
from core.type_aliases import CurveDataList

logger = logging.getLogger(__name__)


class FileLoadWorker(QThread):
    """Worker class for loading files in a Qt background thread.

    Uses QThread for proper Qt integration and thread-safe signal emission.
    Signals are automatically marshaled across threads using Qt's event system.
    """

    # Qt signals as class attributes
    tracking_data_loaded: ClassVar[Signal] = Signal(str, object)  # file_path, CurveDataWithMetadata or list/dict
    image_sequence_loaded: ClassVar[Signal] = Signal(str, list)  # dir_path, file_list
    progress_updated: ClassVar[Signal] = Signal(int, str)  # progress%, message
    error_occurred: ClassVar[Signal] = Signal(str)  # error message
    # Note: finished signal is inherited from QThread, no need to redefine

    def __init__(self) -> None:
        """Initialize worker."""
        super().__init__()
        self.tracking_file_path: str | None = None
        self.image_dir_path: str | None = None
        self._work_ready: bool = False
        self._work_ready_mutex: QMutex = QMutex()

    def stop(self) -> None:
        """Request the worker to stop processing."""
        # Request thread interruption (Qt mechanism)
        self.requestInterruption()

        # Wait for thread to finish if it's running
        if self.isRunning():
            _ = self.wait(2000)  # Wait up to 2 seconds

    def start_work(self, tracking_file_path: str | None, image_dir_path: str | None) -> None:
        """Start new file loading work in Qt thread.

        Args:
            tracking_file_path: Path to tracking data file, or None
            image_dir_path: Path to image directory, or None
        """
        # Stop any existing work
        self.stop()

        # Set new work parameters
        self.tracking_file_path = tracking_file_path
        self.image_dir_path = image_dir_path

        with QMutexLocker(self._work_ready_mutex):
            self._work_ready = True

        # Start Qt thread (calls run() automatically)
        self.start()

    def _check_should_stop(self) -> bool:
        """Thread-safe check of interruption flag."""
        return self.isInterruptionRequested()

    @override
    def run(self) -> None:
        """Main worker method that runs in background Qt thread.

        This is called automatically by QThread.start().
        All signal emissions are thread-safe via Qt's event system.
        """
        # Check if there's work ready
        with QMutexLocker(self._work_ready_mutex):
            if not self._work_ready:
                return  # No work to do
            self._work_ready = False

        logger.info(f"[QTHREAD] Worker.run() starting in Qt thread: {self.objectName() or 'FileLoadWorker'}")

        try:
            total_tasks = 0
            current_task = 0

            # Count tasks to do
            if self.tracking_file_path:
                total_tasks += 1
            if self.image_dir_path:
                total_tasks += 1

            if total_tasks == 0:
                # QThread will automatically emit finished() when run() returns
                return

            # Load tracking data if requested
            if self.tracking_file_path and not self._check_should_stop():
                # Signal emission (Qt handles thread-safety)
                self.progress_updated.emit(0, "Loading tracking data...")

                try:
                    # Check if we should use metadata-aware loading
                    config = get_config()

                    if config.use_metadata_aware_data:
                        # New unified transformation approach - load raw data with metadata
                        logger.info("[COORD] Using metadata-aware data loading")
                        curve_data = self._load_2dtrack_data_metadata_aware(self.tracking_file_path)
                        # Emit the full metadata-aware data so coordinate transforms work correctly
                        data = curve_data
                    else:
                        # Legacy approach - apply flip_y to match manual loading behavior
                        # 3DEqualizer uses bottom-origin coordinates, flip to top-origin
                        data = self._load_2dtrack_data_direct(self.tracking_file_path, flip_y=True, image_height=720)

                    if data:
                        logger.info(
                            f"[QTHREAD] Emitting tracking_data_loaded from Qt thread: {self.objectName() or 'FileLoadWorker'}"
                        )

                    # Signal emission (Qt handles thread-safety) - include file path for session persistence
                    self.tracking_data_loaded.emit(self.tracking_file_path, data)
                    current_task += 1
                    progress = int((current_task / total_tasks) * 100)
                    # Handle different data types for length calculation
                    if isinstance(data, CurveDataWithMetadata):
                        data_len = len(data.data)
                    elif isinstance(data, dict):
                        data_len = sum(
                            len(v.data) if isinstance(v, CurveDataWithMetadata) else len(v) for v in data.values()
                        )
                    else:
                        # Must be a list at this point
                        data_len = len(data) if data else 0
                    msg = f"Loaded {data_len if data else 0} tracking points"
                    self.progress_updated.emit(progress, msg)

                except Exception as e:
                    # Signal emission (Qt handles thread-safety)
                    error_msg = f"Failed to load tracking data: {str(e)}"
                    self.error_occurred.emit(error_msg)

            # Load image sequence if requested
            if self.image_dir_path and not self._check_should_stop():
                # Signal emission (Qt handles thread-safety)
                progress_pct = int((current_task / total_tasks) * 100)
                self.progress_updated.emit(progress_pct, "Loading image sequence...")

                try:
                    # Directly scan for image files without creating DataService
                    image_files = self._scan_image_directory(self.image_dir_path)

                    if image_files:
                        logger.info(
                            f"[QTHREAD] Emitting image_sequence_loaded from Qt thread: {self.objectName() or 'FileLoadWorker'}"
                        )
                        # Signal emission (Qt handles thread-safety)
                        self.image_sequence_loaded.emit(self.image_dir_path, image_files)

                    current_task += 1
                    # Signal emission (Qt handles thread-safety)
                    msg = f"Loaded {len(image_files) if image_files else 0} images"
                    self.progress_updated.emit(100, msg)

                except Exception as e:
                    # Signal emission (Qt handles thread-safety)
                    error_msg = f"Failed to load image sequence: {str(e)}"
                    self.error_occurred.emit(error_msg)

        except Exception as e:
            # Signal emission (Qt handles thread-safety)
            error_msg = f"Unexpected error in file loading: {str(e)}"
            self.error_occurred.emit(error_msg)

        finally:
            # QThread will automatically emit finished() when run() returns
            logger.info(
                f"[QTHREAD] Exiting run() - Qt will emit finished signal automatically: {self.objectName() or 'FileLoadWorker'}"
            )

    def _load_2dtrack_data_direct(
        self, file_path: str, flip_y: bool = False, image_height: float = 720
    ) -> (
        list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | dict[str, list[tuple[int, float, float]]]
    ):
        """Load 2D tracking data directly without using DataService.

        Handles 2DTrackData.txt format with 4-line header:
        Line 1: Version
        Line 2: Identifier 1
        Line 3: Identifier 2
        Line 4: Number of points
        Lines 5+: frame_number x_coordinate y_coordinate [status]

        Args:
            file_path: Path to the tracking data file
            flip_y: If True, flip Y coordinates (image_height - y)
            image_height: Height for Y-flip calculation (default 720)

        Returns:
            For single-point data: List of tracking points as tuples (frame, x, y) or (frame, x, y, status)
            For multi-point data: Dict mapping point names to lists of tracking points
        """
        try:
            multi_point_data: dict[str, CurveDataList] = {}  # Dict for multi-point data

            with open(file_path) as f:
                lines = f.readlines()

            # Parse the header format for multi-point files
            line_idx = 0

            # Read number of tracking points
            num_points = 0
            if line_idx < len(lines):
                try:
                    num_points = int(lines[line_idx].strip())
                    line_idx += 1
                except (ValueError, IndexError):
                    logger.error(f"Invalid header in {file_path}")
                    return []

            # Process each tracking point
            for point_idx in range(num_points):
                if self._check_should_stop():
                    logger.info("File loading cancelled by user")
                    return []

                # Read point name
                if line_idx < len(lines):
                    point_name = lines[line_idx].strip()
                    line_idx += 1
                else:
                    break

                # Skip point type line
                if line_idx < len(lines):
                    line_idx += 1  # Skip point type (not used)
                else:
                    break

                # Read number of frames for this point
                if line_idx < len(lines):
                    try:
                        num_frames = int(lines[line_idx].strip())
                        line_idx += 1
                    except ValueError:
                        logger.error(f"Invalid frame count for point {point_name}")
                        continue
                else:
                    break

                logger.debug(f"Loading point {point_idx + 1}/{num_points}: {point_name} with {num_frames} frames")

                # Initialize list for this point's data
                point_data: CurveDataList = []

                # Read frame data for this point
                for _ in range(num_frames):
                    # Check if we should stop processing (make worker responsive)
                    if self._check_should_stop():
                        logger.info("File loading cancelled by user during frame processing")
                        return {}  # Return empty dict for multi-point

                    if line_idx >= len(lines):
                        break

                    parts = lines[line_idx].strip().split()
                    line_idx += 1

                    if len(parts) >= 3:
                        try:
                            frame = int(parts[0])
                            x = float(parts[1])

                            # Apply Y-flip if needed (for bottom-origin to top-origin conversion)
                            if flip_y:
                                y = image_height - float(parts[2])
                            else:
                                y = float(parts[2])

                            # Include status if present
                            if len(parts) > 3:
                                status = parts[3]
                                point_data.append((frame, x, y, status))
                            else:
                                point_data.append((frame, x, y))

                        except (ValueError, IndexError):
                            logger.warning(f"Skipping invalid data line: {lines[line_idx - 1].strip()}")
                            continue

                # Store point data in dict
                if point_data:
                    multi_point_data[point_name] = point_data

            # Return dict for multi-point data, list for single point
            if num_points > 1:
                total_frames = sum(len(points) for points in multi_point_data.values())
                logger.info(f"Loaded {num_points} points with {total_frames} total frames from {file_path}")
                return multi_point_data  # pyright: ignore[reportReturnType]
            elif num_points == 1 and multi_point_data:
                # For single point, return the list directly for backward compatibility
                point_name = list(multi_point_data.keys())[0]
                logger.info(
                    f"Loaded single point '{point_name}' with {len(multi_point_data[point_name])} frames from {file_path}"
                )
                return multi_point_data[point_name]  # pyright: ignore[reportReturnType]
            else:
                logger.info(f"No valid tracking points loaded from {file_path}")
                return []

        except Exception as e:
            logger.error(f"Error loading tracking data from {file_path}: {e}")
            raise  # Re-raise the exception so it can be handled properly

    def _load_2dtrack_data_metadata_aware(
        self, file_path: str
    ) -> CurveDataWithMetadata | dict[str, CurveDataWithMetadata]:
        """Load 2D tracking data with metadata for unified coordinate transformation.

        Args:
            file_path: Path to the tracking data file

        Returns:
            For single-point: CurveDataWithMetadata with coordinate system information
            For multi-point: Dict mapping point names to CurveDataWithMetadata
        """
        # First load the raw data - apply flip_y to match manual loading behavior
        # 3DEqualizer uses bottom-origin coordinates, flip to top-origin
        raw_data = self._load_2dtrack_data_direct(file_path, flip_y=True, image_height=720)

        # Detect coordinate system from file
        metadata = detect_coordinate_system(file_path)

        # Handle multi-point data
        if isinstance(raw_data, dict):
            # Create metadata-aware wrapper for each point
            result: dict[str, CurveDataWithMetadata] = {}
            for point_name, point_data in raw_data.items():
                # point_data is a list from dict values, compatible with CurveDataList at runtime
                result[point_name] = CurveDataWithMetadata(
                    data=point_data,
                    metadata=metadata,
                    is_normalized=False,
                )

            total_frames = sum(len(curve.data) for curve in result.values())
            logger.info(
                f"[COORD] Loaded {len(result)} points with {total_frames} total frames with metadata: "
                + f"system={metadata.system.value}, origin={metadata.origin.value}, "
                + f"dimensions={metadata.width}x{metadata.height}"
            )
            return result
        elif raw_data:
            # Single point data - backward compatibility (raw_data is a list at this point)
            # Type narrowing: raw_data is a list at this point, compatible with CurveDataList
            curve_data = CurveDataWithMetadata(data=raw_data, metadata=metadata)

            logger.info(
                f"[COORD] Loaded {len(raw_data)} points with metadata: "
                + f"system={metadata.system.value}, origin={metadata.origin.value}, "
                + f"dimensions={metadata.width}x{metadata.height}"
            )

            return curve_data
        else:
            # Empty data case
            return CurveDataWithMetadata(data=[], metadata=metadata)

    def _load_2dtrack_data_legacy_wrapper(
        self, file_path: str, flip_y: bool = False, image_height: float = 720
    ) -> (
        list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | dict[str, list[tuple[int, float, float]]]
    ):
        """Legacy wrapper that loads data and applies flip_y if needed.

        This method exists for backward compatibility with code that expects
        the flip_y parameter to work.

        Args:
            file_path: Path to the tracking data file
            flip_y: If True, flip Y coordinates
            image_height: Height for Y-flip calculation

        Returns:
            List of tracking points with Y optionally flipped, or dict for multi-point
        """
        # Check if we should use metadata-aware loading
        config = get_config()

        if config.use_metadata_aware_data:
            # Load with metadata
            curve_data = self._load_2dtrack_data_metadata_aware(file_path)

            # Handle dict case (multi-point data)
            if isinstance(curve_data, dict):
                # Return dict of legacy format for each point
                result_dict: dict[str, CurveDataList] = {}
                for point_name, point_curve in curve_data.items():
                    if flip_y and point_curve.needs_y_flip_for_display:
                        result_dict[point_name] = point_curve.to_normalized().to_legacy_format()
                    else:
                        result_dict[point_name] = point_curve.to_legacy_format()
                # Runtime type is compatible despite variance rules
                return result_dict  # pyright: ignore[reportReturnType]
            else:
                # Single point data (CurveDataWithMetadata) - to_legacy_format returns CurveDataList
                if flip_y and curve_data.needs_y_flip_for_display:
                    # Convert to normalized then back with flip
                    return curve_data.to_normalized().to_legacy_format()  # pyright: ignore[reportReturnType]
                else:
                    return curve_data.to_legacy_format()  # pyright: ignore[reportReturnType]
        else:
            # Use direct loading with flip_y parameter
            result = self._load_2dtrack_data_direct(file_path, flip_y, image_height)
            # Runtime type is compatible despite variance rules
            return result

    def _scan_image_directory(self, dir_path: str) -> list[str]:
        """Scan directory for image files without using DataService."""
        supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".exr"]
        image_files: list[str] = []

        try:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                # Get all image files
                for file_path in sorted(path.iterdir()):
                    if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                        image_files.append(file_path.name)

        except Exception as e:
            logger.error(f"Error scanning image directory: {e}")
            raise

        return sorted(image_files)  # Return sorted list of filenames


# Backward compatibility: Provide FileLoadSignals class that redirects to FileLoadWorker
class FileLoadSignals(FileLoadWorker):
    """Legacy compatibility class.

    DEPRECATED: Use FileLoadWorker directly instead.
    This class exists only for backward compatibility with existing code.
    """

    def __init__(self) -> None:
        """Initialize as FileLoadWorker."""
        super().__init__()
        logger.warning(

                "FileLoadSignals is deprecated. Use FileLoadWorker directly. "
                "FileLoadWorker now inherits from QThread with signals as class attributes."

        )
