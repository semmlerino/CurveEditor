#!/usr/bin/env python

"""
Integration tests for critical user workflows.

These tests exercise complete workflows that users actually perform,
testing multiple services and components together to maximize coverage
of important code paths.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from core.protocols import PointsList
from services.analysis_service import AnalysisService
from services.centering_zoom_service import CenteringZoomService
from services.curve_service import CurveService

# Real imports - use actual services
from services.file_service import FileService
from services.history_service import HistoryService
from services.image_service import ImageService
from services.visualization_service import VisualizationService
from ui.application_state import ApplicationState
from ui.service_facade import ServiceFacade
from ui.state_manager import StateManager


class SimpleCurveView:
    """Minimal real curve view implementation for testing."""

    def __init__(self):
        # Data attributes
        self.points: PointsList = []
        self.selected_points: set = set()
        self.selected_point_idx = -1
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.x_offset = 0  # Alternative naming
        self.y_offset = 0  # Alternative naming
        self.flip_y_axis = True
        self.scale_to_image = False
        self.image_width = 1920
        self.image_height = 1080

        # Display attributes
        self.show_grid = False
        self.show_velocity_vectors = False
        self.show_crosshair = False
        self.show_background = True
        self.background_opacity = 1.0
        self.point_radius = 5

        # Image sequence attributes
        self.image_filenames: list[str] = []
        self.image_sequence_path = ""
        self.current_image_idx = -1

    def width(self) -> int:
        return 800

    def height(self) -> int:
        return 600

    def setPoints(self, points: PointsList, width: int = 0, height: int = 0, preserve_view: bool = False):
        """Set points data."""
        self.points = points
        if width > 0:
            self.image_width = width
        if height > 0:
            self.image_height = height

    def setCurrentImageByIndex(self, index: int):
        """Set current image by index."""
        if 0 <= index < len(self.image_filenames):
            self.current_image_idx = index

    def setImageSequence(self, path: str, filenames: list[str]):
        """Set image sequence."""
        self.image_sequence_path = path
        self.image_filenames = filenames
        self.current_image_idx = 0 if filenames else -1

    def update(self):
        """Update view - no-op for testing."""
        pass

    def centerOnSelectedPoint(self, preserve_zoom: bool = False):
        """Simulate centering by changing offsets."""
        # For testing, just change the offsets to simulate centering
        if self.selected_point_idx >= 0:
            self.offset_x += 100  # Simulate view change
            self.offset_y += 50  # Simulate view change
            return True
        return False


class MockMainWindowForWorkflow:
    """Minimal mock MainWindow that uses real services and data objects."""

    def __init__(self):
        # Core state - use real objects
        self.state = ApplicationState()
        self.curve_data: PointsList = []
        self.image_filenames: list[str] = []
        self.image_sequence_path = ""
        self.current_frame = 0
        self.selected_indices: list[int] = []

        # Mock only Qt widget (for dialogs)
        self.qwidget = None  # Pass None to Qt dialogs instead of Mock
        self._status_bar = Mock()
        self._status_bar.showMessage = Mock()

        # History tracking - real implementation
        self.history: list[dict] = []
        self.history_index = -1
        self.max_history_size = 50

        # Image dimensions
        self.image_width = 1920
        self.image_height = 1080

        # File tracking
        self.default_directory = tempfile.gettempdir()
        self.last_opened_file = ""
        self.track_data_loaded = False

        # Point properties
        self.point_name = "Track Point"
        self.point_color = "red"

        # Use real curve view implementation
        self.curve_view = SimpleCurveView()

        # Set up bidirectional reference between curve_view and main_window
        # This is needed for services that require access to main_window through curve_view
        self.curve_view.main_window = self

        # UI elements for history
        self.undo_button = Mock()
        self.redo_button = Mock()
        self.info_label = Mock()

        # Services - use real implementations
        self.services = ServiceFacade(self)
        self.state_manager = StateManager(self)

    def statusBar(self):
        return self._status_bar

    def add_to_history(self):
        """Add current state to history - real implementation."""
        state = {
            "curve_data": self.curve_data.copy() if self.curve_data else [],
            "point_name": self.point_name,
            "point_color": self.point_color,
            "current_frame": self.current_frame,
        }

        if self.history_index < len(self.history) - 1:
            self.history = self.history[: self.history_index + 1]

        self.history.append(state)
        self.history_index += 1

        if len(self.history) > self.max_history_size:
            self.history.pop(0)
            self.history_index -= 1

    def setup_timeline(self):
        """Setup timeline - minimal implementation for testing."""
        pass

    def update_image_label(self):
        """Update image label - minimal implementation for testing."""
        pass


class TestLoadEditSaveWorkflow:
    """Test the complete workflow: Load track data -> Edit points -> Save."""

    @pytest.fixture
    def mock_window(self):
        return MockMainWindowForWorkflow()

    @pytest.fixture
    def sample_track_data(self):
        """Create sample 3DE track data."""
        data = """# 3DE4 Track Data
# Point: TestPoint
1 100.0 200.0
2 150.0 250.0
3 200.0 300.0
4 250.0 350.0
5 300.0 400.0
"""
        return data

    def test_complete_load_edit_save_workflow(self, mock_window, sample_track_data):
        """Test loading a file, editing points, and saving."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".3de", delete=False) as f:
            f.write(sample_track_data)
            temp_file = f.name

        try:
            # Step 1: Load track data
            with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
                mock_dialog.return_value = (temp_file, "3DE Files (*.3de)")

                # Use real FileService
                FileService.load_track_data(mock_window)

                # Verify data was loaded
                assert len(mock_window.curve_data) == 5
                # Check first point (includes status field from fallback loader)
                assert mock_window.curve_data[0][:3] == (1, 100.0, 200.0)
                assert mock_window.track_data_loaded is True
                assert mock_window.last_opened_file == temp_file

            # Step 2: Edit a point using CurveService
            # Select a point
            CurveService.select_point_by_index(mock_window.curve_view, mock_window, 2)
            assert mock_window.curve_view.selected_point_idx == 2

            # Move the selected point
            CurveService.update_point_position(mock_window.curve_view, mock_window, 2, 220.0, 320.0)
            # Check first 3 elements (frame, x, y) - ignoring status field
            assert mock_window.curve_data[2][:3] == (3, 220.0, 320.0)

            # Step 3: Analyze the curve
            analysis = AnalysisService(mock_window.curve_data)
            # Check basic properties
            assert len(analysis.get_data()) == 5
            # Get frame range from data
            frames = [point[0] for point in analysis.get_data()]
            assert min(frames) == 1
            assert max(frames) == 5

            # Step 4: Save the modified data
            with tempfile.NamedTemporaryFile(mode="w", suffix=".3de", delete=False) as f:
                save_file = f.name

            with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName") as mock_save:
                mock_save.return_value = (save_file, "3DE Files (*.3de)")

                FileService.save_track_data(mock_window)

                # Verify file was saved
                assert os.path.exists(save_file)
                with open(save_file) as f:
                    content = f.read()
                    assert "220.000000 320.000000" in content  # Modified point

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            if "save_file" in locals() and os.path.exists(save_file):
                os.unlink(save_file)


class TestImageSequenceWorkflow:
    """Test image sequence loading and navigation."""

    @pytest.fixture
    def mock_window(self):
        return MockMainWindowForWorkflow()

    @pytest.fixture
    def mock_image_files(self):
        """Create mock image files."""
        return ["frame_0001.jpg", "frame_0002.jpg", "frame_0003.jpg", "frame_0004.jpg", "frame_0005.jpg"]

    def test_load_and_navigate_image_sequence(self, mock_window, mock_image_files):
        """Test loading image sequence and navigating frames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy image files
            for img in mock_image_files:
                path = os.path.join(tmpdir, img)
                with open(path, "wb") as f:
                    f.write(b"dummy image data")

            # Load image sequence
            with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory") as mock_dialog:
                mock_dialog.return_value = tmpdir

                # Use real ImageService
                ImageService.load_image_sequence(mock_window)

                # Verify sequence was loaded
                assert len(mock_window.image_filenames) == 5
                assert mock_window.image_sequence_path == tmpdir

            # Navigate frames
            ImageService.next_image(mock_window)
            assert mock_window.current_frame == 1

            ImageService.prev_image(mock_window)
            assert mock_window.current_frame == 0

            ImageService.go_to_frame(mock_window, 3)
            assert mock_window.current_frame == 3

            # Test frame bounds
            ImageService.go_to_frame(mock_window, 10)  # Beyond max
            assert mock_window.current_frame == 4  # Should clamp to max


class TestVisualizationWorkflow:
    """Test visualization settings and display options."""

    @pytest.fixture
    def mock_window(self):
        window = MockMainWindowForWorkflow()
        # Add visualization attributes
        window.curve_view.show_grid = False
        window.curve_view.show_velocity_vectors = False
        window.curve_view.show_crosshair = False
        window.curve_view.show_background = True
        window.curve_view.background_opacity = 1.0
        window.curve_view.point_radius = 5
        return window

    def test_visualization_options_workflow(self, mock_window):
        """Test toggling various visualization options."""
        # Toggle grid
        VisualizationService.toggle_grid(mock_window.curve_view)
        assert mock_window.curve_view.show_grid is True

        # Toggle velocity vectors
        VisualizationService.toggle_velocity_vectors(mock_window.curve_view)
        assert mock_window.curve_view.show_velocity_vectors is True

        # Toggle crosshair
        VisualizationService.toggle_crosshair(mock_window.curve_view)
        assert mock_window.curve_view.show_crosshair is True

        # Set point size
        VisualizationService.set_point_radius(mock_window.curve_view, 10)
        assert mock_window.curve_view.point_radius == 10

        # Set background opacity
        VisualizationService.set_background_opacity(mock_window.curve_view, 0.5)
        assert mock_window.curve_view.background_opacity == 0.5


class TestTransformationWorkflow:
    """Test coordinate transformation and view manipulation."""

    @pytest.fixture
    def mock_window(self):
        return MockMainWindowForWorkflow()

    def test_centering_and_zoom_workflow(self, mock_window):
        """Test centering on points and zoom operations."""
        # Add some curve data
        mock_window.curve_data = [(1, 100.0, 200.0), (2, 300.0, 400.0), (3, 500.0, 600.0)]
        mock_window.curve_view.points = mock_window.curve_data
        # Set the selected point index before centering
        mock_window.curve_view.selected_point_idx = 1

        # Get initial offsets
        initial_offset_x = mock_window.curve_view.offset_x
        initial_offset_y = mock_window.curve_view.offset_y

        # Center on middle point (index 1)
        result = CenteringZoomService.center_on_point(
            mock_window.curve_view,
            1,  # point index
        )

        # Verify centering was successful and offsets changed
        assert result is True
        assert mock_window.curve_view.offset_x != initial_offset_x
        assert mock_window.curve_view.offset_y != initial_offset_y

        # Test zoom to fit
        CenteringZoomService.zoom_to_fit(mock_window.curve_view)

        # Should have updated zoom
        assert mock_window.curve_view.zoom_factor != 1.0


class TestHistoryWorkflow:
    """Test undo/redo functionality."""

    @pytest.fixture
    def mock_window(self):
        window = MockMainWindowForWorkflow()
        # Add UI elements for history
        window.undo_button = Mock()
        window.redo_button = Mock()
        window.info_label = Mock()
        return window

    def test_undo_redo_workflow(self, mock_window):
        """Test making changes and undoing/redoing them."""
        # Initial state
        mock_window.curve_data = [(1, 100.0, 200.0)]
        mock_window.add_to_history()

        # Make change 1
        mock_window.curve_data = [(1, 150.0, 250.0)]
        mock_window.add_to_history()

        # Make change 2
        mock_window.curve_data = [(1, 200.0, 300.0)]
        mock_window.add_to_history()

        assert len(mock_window.history) == 3
        assert mock_window.history_index == 2

        # Undo once
        HistoryService.undo(mock_window)
        assert mock_window.curve_data == [(1, 150.0, 250.0)]
        assert mock_window.history_index == 1

        # Undo again
        HistoryService.undo(mock_window)
        assert mock_window.curve_data == [(1, 100.0, 200.0)]
        assert mock_window.history_index == 0

        # Redo
        HistoryService.redo(mock_window)
        assert mock_window.curve_data == [(1, 150.0, 250.0)]
        assert mock_window.history_index == 1

        # Make new change (should truncate history)
        mock_window.curve_data = [(1, 175.0, 275.0)]
        mock_window.add_to_history()
        assert len(mock_window.history) == 3  # Old future was discarded
        assert mock_window.history_index == 2
