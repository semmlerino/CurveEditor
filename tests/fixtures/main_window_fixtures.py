"""
Fixtures for MainWindow testing.

Provides mock data, test helpers, and reusable components
for MainWindow characterization and refactoring tests.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import pytest
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from core.coordinate_system import CoordinateMetadata, CoordinateOrigin, CoordinateSystem
from core.curve_data import CurveDataWithMetadata
from core.type_aliases import CurveDataList
from tests.fixtures.qt_fixtures import _cleanup_main_window_event_filter
from ui.main_window import MainWindow

# --- Sample Data ---


def get_sample_tracking_data() -> list[tuple[int, float, float]]:
    """Get sample tracking data for testing."""
    return [
        (1, 682.29, 211.33),
        (2, 682.55, 212.54),
        (3, 682.71, 214.06),
        (4, 683.06, 215.83),
        (5, 683.32, 217.81),
        (10, 684.54, 230.60),
        (15, 686.36, 246.90),
        (20, 687.98, 264.22),
        (25, 690.15, 282.58),
        (30, 691.92, 302.25),
        (35, 694.02, 321.50),
        (37, 694.79, 328.93),
    ]


def get_sample_metadata() -> CoordinateMetadata:
    """Get sample 3DEqualizer metadata."""
    return CoordinateMetadata(
        system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
    )


def get_sample_curve_data() -> CurveDataWithMetadata:
    """Get sample curve data with metadata."""
    return CurveDataWithMetadata(data=cast(CurveDataList, get_sample_tracking_data()), metadata=get_sample_metadata())


def create_test_2dtrack_file(content: str | None = None) -> Path:
    """Create a temporary 2DTrackData file for testing."""
    if content is None:
        # Default content - single point with a few frames
        content = """1
Point1
0
5
1 682.291351786175937 211.331718165415879
2 682.545189161841108 212.540183990857656
3 682.713305139502836 214.057309384797804
4 683.064889159724544 215.828024768162948
5 683.318386159606803 217.806226221166156"""

    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    temp_file.write(content)
    temp_file.close()

    return Path(temp_file.name)


def create_test_image_sequence(num_images: int = 5) -> tuple[Path, list[str]]:
    """Create temporary test images."""
    temp_dir = Path(tempfile.mkdtemp())
    image_files = []

    for i in range(1, num_images + 1):
        image = QImage(1280, 720, QImage.Format_RGB32)
        image.fill(0x404040)  # Gray

        filename = f"test_image_{i:04d}.png"
        filepath = temp_dir / filename
        image.save(str(filepath))
        image_files.append(filename)

    return temp_dir, image_files


# --- Mock Classes ---


class MockCurveWidget:
    """Mock CurveViewWidget for testing."""

    def __init__(self):
        self.curve_data: CurveDataList = []
        self.background_image: QPixmap | None = None
        self.show_background: bool = False
        self.selected_indices: set[int] = set()
        self.flip_y_axis: bool = False
        self._data_metadata: CoordinateMetadata | None = None

        # Mock signals
        self.selection_changed: Mock = Mock()
        self.view_changed: Mock = Mock()
        self.point_moved: Mock = Mock()

    def set_curve_data(self, data):
        """Mock set_curve_data method."""
        if isinstance(data, CurveDataWithMetadata):
            self.curve_data = data.data
            self._data_metadata = data.metadata
        else:
            self.curve_data = data

    def set_background_image(self, pixmap):
        """Mock set_background_image method."""
        self.background_image = pixmap

    def setup_for_3dequalizer_data(self):
        """Mock setup method."""
        self.flip_y_axis = True

    def update(self):
        """Mock update method."""
        pass


class MockFileLoadWorker:
    """Mock FileLoadWorker for testing."""

    def __init__(self):
        # Signal mocks
        self.tracking_data_loaded: Mock = Mock()
        self.image_sequence_loaded: Mock = Mock()
        self.progress_updated: Mock = Mock()
        self.error_occurred: Mock = Mock()
        self.finished: Mock = Mock()

        # State
        self._running: bool = False

    def start_work(self, tracking_file: str | None = None, image_dir: str | None = None):
        """Mock start_work method."""
        self._running = True

        # Simulate immediate completion for testing
        if tracking_file:
            data = get_sample_tracking_data()
            self.tracking_data_loaded.emit(data)

        if image_dir:
            self.image_sequence_loaded.emit(image_dir, ["test1.png", "test2.png"])

        self.finished.emit()

    def stop(self):
        """Mock stop method."""
        self._running = False


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self):
        # State attributes
        self.is_modified: bool = False
        self.current_file: str | None = None
        self.total_frames: int = 1

        # Signal mocks
        self.file_changed: Mock = Mock()
        self.modified_changed: Mock = Mock()

    def set_track_data(self, data, mark_modified=True):
        """Mock set_track_data method."""
        if mark_modified:
            self.is_modified = True
            self.modified_changed.emit(True)

    def add_undo_state(self, description):
        """Mock undo state tracking."""
        pass


# --- Test Fixtures ---


@pytest.fixture
def mock_curve_widget() -> MockCurveWidget:
    """Provide a mock CurveViewWidget."""
    return MockCurveWidget()


@pytest.fixture
def mock_file_worker() -> MockFileLoadWorker:
    """Provide a mock FileLoadWorker."""
    return MockFileLoadWorker()


@pytest.fixture
def mock_state_manager() -> MockStateManager:
    """Provide a mock StateManager."""
    return MockStateManager()


@pytest.fixture
def main_window_with_mocks(qapp, qtbot, monkeypatch) -> Generator[MainWindow, None, None]:
    """Create MainWindow with mocked components.

    CRITICAL: Uses qtbot.addWidget() for automatic cleanup to prevent
    QObject accumulation and segfaults (see UNIFIED_TESTING_GUIDE).
    """
    # Prevent auto-loading
    monkeypatch.setattr(MainWindow, "_load_burger_tracking_data", Mock(return_value=None))

    window = MainWindow()

    # CRITICAL: Use qtbot.addWidget with before_close_func for automatic cleanup
    # including event filter removal (prevents accumulation after 1580+ tests)
    qtbot.addWidget(window, before_close_func=_cleanup_main_window_event_filter)

    # Replace components with mocks
    window.curve_widget = MockCurveWidget()
    window.file_load_worker = MockFileLoadWorker()
    window.state_manager = MockStateManager()

    window.show()
    qapp.processEvents()

    yield window

    # qtbot.addWidget handles cleanup automatically


@pytest.fixture
def temp_tracking_file() -> Generator[Path, None, None]:
    """Create a temporary tracking data file."""
    file_path = create_test_2dtrack_file()
    yield file_path
    file_path.unlink()  # Cleanup


@pytest.fixture
def temp_image_sequence() -> Generator[tuple[Path, list[str]], None, None]:
    """Create temporary test images."""
    dir_path, files = create_test_image_sequence()
    yield dir_path, files

    # Cleanup
    import shutil

    shutil.rmtree(dir_path)


# --- Test Helpers ---


class MainWindowTestHelper:
    """Helper methods for MainWindow testing."""

    @staticmethod
    def simulate_file_load(window: MainWindow, file_path: str):
        """Simulate loading a file through the UI."""
        with patch("ui.main_window.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (file_path, "")
            window.on_action_open()

    @staticmethod
    def simulate_image_load(window: MainWindow, image_dir: str):
        """Simulate loading images through the UI."""
        with patch("ui.main_window.QFileDialog.getExistingDirectory") as mock_dialog:
            mock_dialog.return_value = image_dir
            window._on_action_load_images()

    @staticmethod
    def simulate_playback(window: MainWindow, num_frames: int = 5):
        """Simulate playback for a number of frames."""
        window._on_play_pause(True)

        for _ in range(num_frames):
            window._on_playback_timer()
            QApplication.processEvents()

        window._on_play_pause(False)

    @staticmethod
    def set_frame_range(window: MainWindow, min_frame: int, max_frame: int):
        """Set the frame range for testing."""
        if window.frame_slider:
            window.frame_slider.setMinimum(min_frame)
            window.frame_slider.setMaximum(max_frame)
        if window.frame_spinbox:
            window.frame_spinbox.setMinimum(min_frame)
            window.frame_spinbox.setMaximum(max_frame)

    @staticmethod
    def verify_ui_state(window: MainWindow) -> dict[str, bool | int]:
        """Get current UI state for verification."""
        return {
            "current_frame": window.current_frame,
            "is_playing": window.playback_timer.isActive() if window.playback_timer else False,
            "has_data": bool(window.curve_widget.curve_data) if window.curve_widget else False,
            "has_background": bool(window.curve_widget.background_image) if window.curve_widget else False,
            "is_modified": window.state_manager.is_modified if window.state_manager else False,
            "undo_enabled": window.action_undo.isEnabled() if window.action_undo else False,
            "redo_enabled": window.action_redo.isEnabled() if window.action_redo else False,
        }


# --- Performance Test Helpers ---


class PerformanceMonitor:
    """Monitor performance during tests."""

    def __init__(self):
        self.measurements: list[dict[str, object]] = []

    def measure(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        import time

        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        self.measurements.append({"function": func.__name__, "time": elapsed})

        return result

    def report(self):
        """Generate performance report."""
        if not self.measurements:
            return "No measurements"

        total = sum(m["time"] for m in self.measurements)
        avg = total / len(self.measurements)

        return f"Total: {total:.3f}s, Average: {avg:.3f}s, Count: {len(self.measurements)}"


@pytest.fixture
def performance_monitor() -> PerformanceMonitor:
    """Provide performance monitoring for tests."""
    return PerformanceMonitor()


# --- Assertion Helpers ---


def assert_frame_synchronized(window: MainWindow, expected_frame: int):
    """Assert all frame controls are synchronized."""
    assert window.current_frame == expected_frame
    if window.frame_spinbox:
        assert window.frame_spinbox.value() == expected_frame
    if window.frame_slider:
        assert window.frame_slider.value() == expected_frame

    if window.timeline_tabs:
        # Timeline might have different representation
        pass  # Add timeline-specific checks if needed


def assert_data_loaded(window: MainWindow, expected_points: int | None = None):
    """Assert data is properly loaded."""
    assert window.curve_widget is not None
    assert window.curve_widget.curve_data is not None

    if expected_points is not None:
        assert len(window.curve_widget.curve_data) == expected_points


def assert_clean_state(window: MainWindow):
    """Assert window is in clean, unmodified state."""
    assert not window.state_manager.is_modified
    if window.action_undo:
        assert not window.action_undo.isEnabled()
    if window.action_redo:
        assert not window.action_redo.isEnabled()
    if window.playback_timer:
        assert not window.playback_timer.isActive()
