#!/usr/bin/env python3
"""
Comprehensive tests for the ServiceFacade pattern.

This test module validates the facade pattern implementation that provides
a unified interface to all application services using the consolidated
4-service architecture.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from core.image_state import ImageState
from protocols.ui import CurveViewProtocol, MainWindowProtocol
from ui.service_facade import ServiceFacade, get_service_facade, reset_service_facade


@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication for all tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def mock_main_window():
    """Create a mock main window."""
    return Mock(spec=MainWindowProtocol)


@pytest.fixture
def mock_curve_view():
    """Create a mock curve view."""
    return Mock(spec=CurveViewProtocol)


@pytest.fixture
def sample_curve_data():
    """Sample curve data for testing."""
    return [(1, 100.0, 200.0, "normal"), (2, 150.0, 250.0, "keyframe")]


@pytest.fixture
def service_facade(mock_main_window):
    """Create a ServiceFacade instance."""
    return ServiceFacade(mock_main_window)


class TestServiceFacadeInitialization:
    """Test ServiceFacade initialization and basic properties."""

    def test_initialization_with_main_window(self, mock_main_window):
        """Test ServiceFacade initialization with main window."""
        facade = ServiceFacade(mock_main_window)

        assert facade.main_window is mock_main_window
        assert isinstance(facade.image_state, ImageState)
        assert facade.logger.name == "service_facade"

    def test_initialization_without_main_window(self):
        """Test ServiceFacade initialization without main window."""
        facade = ServiceFacade()

        assert facade.main_window is None
        assert isinstance(facade.image_state, ImageState)
        assert facade.logger.name == "service_facade"

    @patch("ui.service_facade.get_transform_service")
    def test_transform_service_property(self, mock_get_service, service_facade):
        """Test _transform_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade._transform_service
        assert result is mock_service
        mock_get_service.assert_called_once()

    @patch("ui.service_facade.get_data_service")
    def test_data_service_property(self, mock_get_service, service_facade):
        """Test _data_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade._data_service
        assert result is mock_service
        mock_get_service.assert_called_once()

    @patch("ui.service_facade.get_interaction_service")
    def test_interaction_service_property(self, mock_get_service, service_facade):
        """Test _interaction_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade._interaction_service
        assert result is mock_service
        mock_get_service.assert_called_once()

    @patch("ui.service_facade.get_ui_service")
    def test_ui_service_property(self, mock_get_service, service_facade):
        """Test _ui_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade._ui_service
        assert result is mock_service
        mock_get_service.assert_called_once()

    def test_legacy_service_properties(self, service_facade):
        """Test legacy service property aliases."""
        with patch("ui.service_facade.get_data_service") as mock_get_data:
            mock_data = Mock()
            mock_get_data.return_value = mock_data
            assert service_facade._file_service is mock_data

        with patch("ui.service_facade.get_interaction_service") as mock_get_interaction:
            mock_interaction = Mock()
            mock_get_interaction.return_value = mock_interaction
            assert service_facade._history_service is mock_interaction


class TestTransformServiceMethods:
    """Test transform service facade methods."""

    @patch("ui.service_facade.get_transform_service")
    def test_transform_service_property_access(self, mock_get_service, service_facade):
        """Test public transform_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade.transform_service
        assert result is mock_service

    @patch("ui.service_facade.get_transform_service")
    def test_create_view_state_with_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test create_view_state when service is available."""
        mock_service = Mock()
        mock_view_state = Mock()
        mock_service.create_view_state.return_value = mock_view_state
        mock_get_service.return_value = mock_service

        result = service_facade.create_view_state(mock_curve_view)

        assert result is mock_view_state
        mock_service.create_view_state.assert_called_once_with(mock_curve_view)

    @patch("ui.service_facade.get_transform_service")
    def test_create_view_state_without_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test create_view_state when service is not available."""
        mock_get_service.return_value = None

        result = service_facade.create_view_state(mock_curve_view)

        assert result is None

    @patch("ui.service_facade.get_transform_service")
    def test_create_transform_with_service(self, mock_get_service, service_facade):
        """Test create_transform when service is available."""
        mock_service = Mock()
        mock_transform = Mock()
        mock_view_state = Mock()
        mock_service.create_transform_from_view_state.return_value = mock_transform
        mock_get_service.return_value = mock_service

        result = service_facade.create_transform(mock_view_state)

        assert result is mock_transform
        mock_service.create_transform_from_view_state.assert_called_once_with(mock_view_state)

    @patch("ui.service_facade.get_transform_service")
    def test_create_transform_without_service(self, mock_get_service, service_facade):
        """Test create_transform when service is not available."""
        mock_get_service.return_value = None
        mock_view_state = Mock()

        result = service_facade.create_transform(mock_view_state)

        assert result is None

    def test_transform_to_screen_with_transform(self, service_facade):
        """Test transform_to_screen with valid transform."""
        mock_transform = Mock()
        mock_transform.data_to_screen.return_value = (800.0, 600.0)

        result = service_facade.transform_to_screen(mock_transform, 100.0, 200.0)

        assert result == (800.0, 600.0)
        mock_transform.data_to_screen.assert_called_once_with(100.0, 200.0)

    def test_transform_to_screen_without_transform(self, service_facade):
        """Test transform_to_screen without transform returns input coordinates."""
        result = service_facade.transform_to_screen(None, 100.0, 200.0)

        assert result == (100.0, 200.0)

    def test_transform_to_data_with_transform(self, service_facade):
        """Test transform_to_data with valid transform."""
        mock_transform = Mock()
        mock_transform.screen_to_data.return_value = (100.0, 200.0)

        result = service_facade.transform_to_data(mock_transform, 800.0, 600.0)

        assert result == (100.0, 200.0)
        mock_transform.screen_to_data.assert_called_once_with(800.0, 600.0)

    def test_transform_to_data_without_transform(self, service_facade):
        """Test transform_to_data without transform returns input coordinates."""
        result = service_facade.transform_to_data(None, 800.0, 600.0)

        assert result == (800.0, 600.0)


class TestDataServiceMethods:
    """Test data service facade methods."""

    @patch("ui.service_facade.get_data_service")
    def test_data_service_property_access(self, mock_get_service, service_facade):
        """Test public data_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade.data_service
        assert result is mock_service

    @patch("ui.service_facade.get_data_service")
    def test_smooth_curve_with_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test smooth_curve when service is available."""
        mock_service = Mock()
        smoothed_data = [(1, 105.0, 205.0, "normal"), (2, 145.0, 245.0, "keyframe")]
        mock_service.smooth_moving_average.return_value = smoothed_data
        mock_get_service.return_value = mock_service

        result = service_facade.smooth_curve(sample_curve_data, 3)

        assert result == smoothed_data
        mock_service.smooth_moving_average.assert_called_once_with(sample_curve_data, 3)

    @patch("ui.service_facade.get_data_service")
    def test_smooth_curve_without_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test smooth_curve when service is not available returns original data."""
        mock_get_service.return_value = None

        result = service_facade.smooth_curve(sample_curve_data)

        assert result == sample_curve_data

    @patch("ui.service_facade.get_data_service")
    def test_filter_curve_median_with_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test filter_curve with median filter when service is available."""
        mock_service = Mock()
        filtered_data = [(1, 102.0, 202.0, "normal"), (2, 148.0, 248.0, "keyframe")]
        mock_service.filter_median.return_value = filtered_data
        mock_get_service.return_value = mock_service

        result = service_facade.filter_curve(sample_curve_data, "median", 5)

        assert result == filtered_data
        mock_service.filter_median.assert_called_once_with(sample_curve_data, 5)

    @patch("ui.service_facade.get_data_service")
    def test_filter_curve_butterworth_with_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test filter_curve with butterworth filter when service is available."""
        mock_service = Mock()
        filtered_data = [(1, 101.0, 201.0, "normal"), (2, 149.0, 249.0, "keyframe")]
        mock_service.filter_butterworth.return_value = filtered_data
        mock_get_service.return_value = mock_service

        result = service_facade.filter_curve(sample_curve_data, "butterworth", 50)

        assert result == filtered_data
        mock_service.filter_butterworth.assert_called_once_with(sample_curve_data, 0.5)  # 50/100.0

    @patch("ui.service_facade.get_data_service")
    def test_filter_curve_unknown_type(self, mock_get_service, service_facade, sample_curve_data):
        """Test filter_curve with unknown filter type returns original data."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade.filter_curve(sample_curve_data, "unknown", 5)

        assert result == sample_curve_data
        # Service methods should not be called for unknown filter type
        assert not mock_service.filter_median.called
        assert not mock_service.filter_butterworth.called

    @patch("ui.service_facade.get_data_service")
    def test_filter_curve_without_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test filter_curve when service is not available returns original data."""
        mock_get_service.return_value = None

        result = service_facade.filter_curve(sample_curve_data, "median", 5)

        assert result == sample_curve_data

    @patch("ui.service_facade.get_data_service")
    def test_fill_gaps_with_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test fill_gaps when service is available."""
        mock_service = Mock()
        filled_data = [(1, 100.0, 200.0, "normal"), (2, 150.0, 250.0, "keyframe"), (3, 175.0, 275.0, "interpolated")]
        mock_service.fill_gaps.return_value = filled_data
        mock_get_service.return_value = mock_service

        result = service_facade.fill_gaps(sample_curve_data, 5)

        assert result == filled_data
        mock_service.fill_gaps.assert_called_once_with(sample_curve_data, 5)

    @patch("ui.service_facade.get_data_service")
    def test_fill_gaps_without_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test fill_gaps when service is not available returns original data."""
        mock_get_service.return_value = None

        result = service_facade.fill_gaps(sample_curve_data)

        assert result == sample_curve_data

    @patch("ui.service_facade.get_data_service")
    def test_detect_outliers_with_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test detect_outliers when service is available."""
        mock_service = Mock()
        outlier_indices = [1, 5, 10]
        mock_service.detect_outliers.return_value = outlier_indices
        mock_get_service.return_value = mock_service

        result = service_facade.detect_outliers(sample_curve_data, 2.5)

        assert result == outlier_indices
        mock_service.detect_outliers.assert_called_once_with(sample_curve_data, 2.5)

    @patch("ui.service_facade.get_data_service")
    def test_detect_outliers_without_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test detect_outliers when service is not available returns empty list."""
        mock_get_service.return_value = None

        result = service_facade.detect_outliers(sample_curve_data)

        assert result == []

    @patch("ui.service_facade.get_data_service")
    def test_analyze_curve_bounds_with_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test analyze_curve_bounds when service is available."""
        mock_service = Mock()
        analysis_result = {
            "count": 2,
            "min_frame": 1,
            "max_frame": 2,
            "bounds": {"min_x": 100.0, "max_x": 150.0, "min_y": 200.0, "max_y": 250.0},
        }
        mock_service.analyze_points.return_value = analysis_result
        mock_get_service.return_value = mock_service

        result = service_facade.analyze_curve_bounds(sample_curve_data)

        assert result == analysis_result
        mock_service.analyze_points.assert_called_once_with(sample_curve_data)

    @patch("ui.service_facade.get_data_service")
    def test_analyze_curve_bounds_without_service(self, mock_get_service, service_facade, sample_curve_data):
        """Test analyze_curve_bounds when service is not available returns default values."""
        mock_get_service.return_value = None

        result = service_facade.analyze_curve_bounds(sample_curve_data)

        expected_default = {
            "count": 0,
            "min_frame": 0,
            "max_frame": 0,
            "bounds": {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0},
        }
        assert result == expected_default

    @patch("ui.service_facade.get_data_service")
    def test_load_track_data_with_service(self, mock_get_service, service_facade):
        """Test load_track_data when service is available."""
        mock_service = Mock()
        track_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        mock_service.load_track_data.return_value = track_data
        mock_get_service.return_value = mock_service
        mock_widget = Mock()

        result = service_facade.load_track_data(mock_widget)

        assert result == track_data
        mock_service.load_track_data.assert_called_once()

    @patch("ui.service_facade.get_data_service")
    def test_load_track_data_without_service_or_widget(self, mock_get_service, service_facade):
        """Test load_track_data when service or widget is not available."""
        mock_get_service.return_value = None

        result = service_facade.load_track_data()

        assert result is None

    @patch("ui.service_facade.get_data_service")
    def test_load_track_data_from_file_json(self, mock_get_service, service_facade):
        """Test load_track_data_from_file with JSON file."""
        mock_service = Mock()
        track_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        mock_service.load_json.return_value = track_data
        mock_get_service.return_value = mock_service

        result = service_facade.load_track_data_from_file("test.json")

        assert result == track_data
        mock_service.load_json.assert_called_once_with("test.json")

    @patch("ui.service_facade.get_data_service")
    def test_load_track_data_from_file_csv(self, mock_get_service, service_facade):
        """Test load_track_data_from_file with CSV file."""
        mock_service = Mock()
        track_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        mock_service.load_csv.return_value = track_data
        mock_get_service.return_value = mock_service

        result = service_facade.load_track_data_from_file("test.csv")

        assert result == track_data
        mock_service.load_csv.assert_called_once_with("test.csv")

    @patch("ui.service_facade.get_data_service")
    def test_load_track_data_from_file_txt(self, mock_get_service, service_facade):
        """Test load_track_data_from_file with TXT file."""
        mock_service = Mock()
        track_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        mock_service.load_2dtrack_data.return_value = track_data
        mock_get_service.return_value = mock_service

        result = service_facade.load_track_data_from_file("test.txt")

        assert result == track_data
        mock_service.load_2dtrack_data.assert_called_once_with("test.txt")

    @patch("ui.service_facade.get_data_service")
    def test_load_track_data_from_file_unknown_type(self, mock_get_service, service_facade):
        """Test load_track_data_from_file with unknown file type."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade.load_track_data_from_file("test.xyz")

        assert result is None
        # No service methods should be called for unknown file type
        assert not mock_service.load_json.called
        assert not mock_service.load_csv.called
        assert not mock_service.load_2dtrack_data.called

    @patch("ui.service_facade.get_data_service")
    def test_load_track_data_from_file_without_service(self, mock_get_service, service_facade):
        """Test load_track_data_from_file when service is not available."""
        mock_get_service.return_value = None

        result = service_facade.load_track_data_from_file("test.json")

        assert result is None


class TestInteractionServiceMethods:
    """Test interaction service facade methods."""

    @patch("ui.service_facade.get_interaction_service")
    def test_interaction_service_property_access(self, mock_get_service, service_facade):
        """Test public interaction_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade.interaction_service
        assert result is mock_service

    @patch("ui.service_facade.get_interaction_service")
    def test_on_point_moved_with_service(self, mock_get_service, service_facade, mock_main_window):
        """Test on_point_moved when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        service_facade.main_window = mock_main_window

        service_facade.on_point_moved(5, 123.45, 678.90)

        mock_service.on_point_moved.assert_called_once_with(mock_main_window, 5, 123.45, 678.90)

    @patch("ui.service_facade.get_interaction_service")
    def test_on_point_moved_without_service(self, mock_get_service, service_facade):
        """Test on_point_moved when service is not available."""
        mock_get_service.return_value = None

        # Should not raise exception when service is not available
        service_facade.on_point_moved(5, 123.45, 678.90)

    @patch("ui.service_facade.get_interaction_service")
    def test_on_point_selected_with_service(self, mock_get_service, service_facade, mock_curve_view, mock_main_window):
        """Test on_point_selected when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        service_facade.main_window = mock_main_window

        service_facade.on_point_selected(mock_curve_view, 3)

        mock_service.on_point_selected.assert_called_once_with(mock_curve_view, mock_main_window, 3)

    @patch("ui.service_facade.get_interaction_service")
    def test_on_point_selected_without_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test on_point_selected when service is not available."""
        mock_get_service.return_value = None

        # Should not raise exception when service is not available
        service_facade.on_point_selected(mock_curve_view, 3)

    @patch("ui.service_facade.get_interaction_service")
    def test_handle_mouse_press_with_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test handle_mouse_press when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_event = Mock()

        service_facade.handle_mouse_press(mock_curve_view, mock_event)

        mock_service.handle_mouse_press.assert_called_once_with(mock_curve_view, mock_event)

    @patch("ui.service_facade.get_interaction_service")
    def test_handle_mouse_move_with_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test handle_mouse_move when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_event = Mock()

        service_facade.handle_mouse_move(mock_curve_view, mock_event)

        mock_service.handle_mouse_move.assert_called_once_with(mock_curve_view, mock_event)

    @patch("ui.service_facade.get_interaction_service")
    def test_handle_mouse_release_with_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test handle_mouse_release when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_event = Mock()

        service_facade.handle_mouse_release(mock_curve_view, mock_event)

        mock_service.handle_mouse_release.assert_called_once_with(mock_curve_view, mock_event)

    @patch("ui.service_facade.get_interaction_service")
    def test_handle_wheel_event_with_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test handle_wheel_event when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_event = Mock()

        service_facade.handle_wheel_event(mock_curve_view, mock_event)

        mock_service.handle_wheel_event.assert_called_once_with(mock_curve_view, mock_event)

    @patch("ui.service_facade.get_interaction_service")
    def test_handle_key_press_with_service(self, mock_get_service, service_facade, mock_curve_view):
        """Test handle_key_press when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_event = Mock()

        service_facade.handle_key_press(mock_curve_view, mock_event)

        mock_service.handle_key_press.assert_called_once_with(mock_curve_view, mock_event)

    @patch("ui.service_facade.get_interaction_service")
    def test_add_to_history_with_service(self, mock_get_service, service_facade):
        """Test add_to_history when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        service_facade.add_to_history()

        mock_service.add_to_history.assert_called_once()

    @patch("ui.service_facade.get_interaction_service")
    def test_add_to_history_without_service(self, mock_get_service, service_facade, mock_main_window):
        """Test add_to_history when service is not available."""
        mock_get_service.return_value = None
        service_facade.main_window = mock_main_window

        # Should not raise exception when service is not available
        service_facade.add_to_history()

    @patch("ui.service_facade.get_interaction_service")
    def test_undo_with_service(self, mock_get_service, service_facade, mock_main_window):
        """Test undo when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        service_facade.main_window = mock_main_window

        service_facade.undo()

        mock_service.undo.assert_called_once_with(mock_main_window)

    @patch("ui.service_facade.get_interaction_service")
    def test_undo_without_service(self, mock_get_service, service_facade):
        """Test undo when service is not available."""
        mock_get_service.return_value = None

        # Should not raise exception when service is not available
        service_facade.undo()

    @patch("ui.service_facade.get_interaction_service")
    def test_redo_with_service(self, mock_get_service, service_facade, mock_main_window):
        """Test redo when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        service_facade.main_window = mock_main_window

        service_facade.redo()

        mock_service.redo.assert_called_once_with(mock_main_window)

    @patch("ui.service_facade.get_interaction_service")
    def test_redo_without_service(self, mock_get_service, service_facade):
        """Test redo when service is not available."""
        mock_get_service.return_value = None

        # Should not raise exception when service is not available
        service_facade.redo()


class TestUIServiceMethods:
    """Test UI service facade methods."""

    @patch("ui.service_facade.get_ui_service")
    def test_ui_service_property_access(self, mock_get_service, service_facade):
        """Test public ui_service property."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        result = service_facade.ui_service
        assert result is mock_service

    @patch("ui.service_facade.get_ui_service")
    def test_show_error_with_service(self, mock_get_service, service_facade):
        """Test show_error when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_parent = Mock()

        service_facade.show_error("Test error", mock_parent)

        mock_service.show_error.assert_called_once_with(mock_parent, "Test error")

    @patch("ui.service_facade.get_ui_service")
    def test_show_error_without_service(self, mock_get_service, service_facade):
        """Test show_error when service is not available."""
        mock_get_service.return_value = None

        # Should not raise exception when service is not available
        service_facade.show_error("Test error")

    @patch("ui.service_facade.get_ui_service")
    def test_show_warning_with_service(self, mock_get_service, service_facade):
        """Test show_warning when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_parent = Mock()

        service_facade.show_warning("Test warning", mock_parent)

        mock_service.show_warning.assert_called_once_with(mock_parent, "Test warning")

    @patch("ui.service_facade.get_ui_service")
    def test_show_info_with_service(self, mock_get_service, service_facade):
        """Test show_info when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_parent = Mock()

        service_facade.show_info("Test info", mock_parent)

        mock_service.show_info.assert_called_once_with(mock_parent, "Test info")

    @patch("ui.service_facade.get_ui_service")
    def test_confirm_action_with_service(self, mock_get_service, service_facade):
        """Test confirm_action when service is available."""
        mock_service = Mock()
        mock_service.confirm_action.return_value = True
        mock_get_service.return_value = mock_service
        mock_parent = Mock()

        result = service_facade.confirm_action("Confirm test?", mock_parent)

        assert result is True
        mock_service.confirm_action.assert_called_once_with(mock_parent, "Confirm test?")

    @patch("ui.service_facade.get_ui_service")
    def test_confirm_action_without_service(self, mock_get_service, service_facade):
        """Test confirm_action when service is not available returns False."""
        mock_get_service.return_value = None

        result = service_facade.confirm_action("Confirm test?")

        assert result is False

    @patch("ui.service_facade.get_ui_service")
    def test_get_smooth_window_size_with_service(self, mock_get_service, service_facade):
        """Test get_smooth_window_size when service is available."""
        mock_service = Mock()
        mock_service.get_smooth_window_size.return_value = 5
        mock_get_service.return_value = mock_service
        mock_parent = Mock()

        result = service_facade.get_smooth_window_size(mock_parent)

        assert result == 5
        mock_service.get_smooth_window_size.assert_called_once_with(mock_parent)

    @patch("ui.service_facade.get_ui_service")
    def test_get_smooth_window_size_without_service(self, mock_get_service, service_facade):
        """Test get_smooth_window_size when service is not available returns None."""
        mock_get_service.return_value = None

        result = service_facade.get_smooth_window_size()

        assert result is None

    @patch("ui.service_facade.get_ui_service")
    def test_get_filter_params_with_service(self, mock_get_service, service_facade):
        """Test get_filter_params when service is available."""
        mock_service = Mock()
        mock_service.get_filter_params.return_value = ("median", 5)
        mock_get_service.return_value = mock_service
        mock_parent = Mock()

        result = service_facade.get_filter_params(mock_parent)

        assert result == ("median", 5)
        mock_service.get_filter_params.assert_called_once_with(mock_parent)

    @patch("ui.service_facade.get_ui_service")
    def test_get_filter_params_without_service(self, mock_get_service, service_facade):
        """Test get_filter_params when service is not available returns None."""
        mock_get_service.return_value = None

        result = service_facade.get_filter_params()

        assert result is None

    @patch("ui.service_facade.get_ui_service")
    def test_set_status_with_service(self, mock_get_service, service_facade, mock_main_window):
        """Test set_status when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        service_facade.main_window = mock_main_window

        service_facade.set_status("Test status", 5000)

        mock_service.set_status.assert_called_once_with(mock_main_window, "Test status", 5000)

    @patch("ui.service_facade.get_ui_service")
    def test_clear_status_with_service(self, mock_get_service, service_facade):
        """Test clear_status when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        service_facade.clear_status()

        mock_service.clear_status.assert_called_once()

    @patch("ui.service_facade.get_ui_service")
    def test_update_ui_from_data_with_service(self, mock_get_service, service_facade):
        """Test update_ui_from_data when service is available."""
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        service_facade.update_ui_from_data()

        mock_service.update_ui_from_data.assert_called_once()


class TestUtilityMethods:
    """Test utility methods of ServiceFacade."""

    def test_is_service_available_transform(self, service_facade):
        """Test is_service_available for transform service."""
        with patch("ui.service_facade.get_transform_service") as mock_get:
            mock_get.return_value = Mock()
            assert service_facade.is_service_available("transform") is True

        with patch("ui.service_facade.get_transform_service") as mock_get:
            mock_get.return_value = None
            assert service_facade.is_service_available("transform") is False

    def test_is_service_available_data(self, service_facade):
        """Test is_service_available for data service."""
        with patch("ui.service_facade.get_data_service") as mock_get:
            mock_get.return_value = Mock()
            assert service_facade.is_service_available("data") is True

        with patch("ui.service_facade.get_data_service") as mock_get:
            mock_get.return_value = None
            assert service_facade.is_service_available("data") is False

    def test_is_service_available_interaction(self, service_facade):
        """Test is_service_available for interaction service."""
        with patch("ui.service_facade.get_interaction_service") as mock_get:
            mock_get.return_value = Mock()
            assert service_facade.is_service_available("interaction") is True

        with patch("ui.service_facade.get_interaction_service") as mock_get:
            mock_get.return_value = None
            assert service_facade.is_service_available("interaction") is False

    def test_is_service_available_ui(self, service_facade):
        """Test is_service_available for ui service."""
        with patch("ui.service_facade.get_ui_service") as mock_get:
            mock_get.return_value = Mock()
            assert service_facade.is_service_available("ui") is True

        with patch("ui.service_facade.get_ui_service") as mock_get:
            mock_get.return_value = None
            assert service_facade.is_service_available("ui") is False

    def test_is_service_available_legacy_file(self, service_facade):
        """Test is_service_available for legacy file service."""
        with patch("ui.service_facade.get_data_service") as mock_get:
            mock_get.return_value = Mock()
            assert service_facade.is_service_available("file") is True

        with patch("ui.service_facade.get_data_service") as mock_get:
            mock_get.return_value = None
            assert service_facade.is_service_available("file") is False

    def test_is_service_available_legacy_history(self, service_facade):
        """Test is_service_available for legacy history service."""
        with patch("ui.service_facade.get_interaction_service") as mock_get:
            mock_get.return_value = Mock()
            assert service_facade.is_service_available("history") is True

        with patch("ui.service_facade.get_interaction_service") as mock_get:
            mock_get.return_value = None
            assert service_facade.is_service_available("history") is False

    def test_is_service_available_unknown(self, service_facade):
        """Test is_service_available for unknown service returns False."""
        assert service_facade.is_service_available("unknown") is False

    def test_get_available_services(self, service_facade):
        """Test get_available_services returns list of available services."""
        with (
            patch("ui.service_facade.get_transform_service") as mock_transform,
            patch("ui.service_facade.get_data_service") as mock_data,
            patch("ui.service_facade.get_interaction_service") as mock_interaction,
            patch("ui.service_facade.get_ui_service") as mock_ui,
        ):
            mock_transform.return_value = Mock()
            mock_data.return_value = Mock()
            mock_interaction.return_value = None
            mock_ui.return_value = None

            available = service_facade.get_available_services()

            assert "transform" in available
            assert "data" in available
            assert "interaction" not in available
            assert "ui" not in available
            # get_available_services only returns main names, not legacy aliases
            assert len(available) == 2

    def test_refresh_services(self, service_facade):
        """Test refresh_services method."""
        # This method doesn't do anything concrete in the facade pattern
        # but should not raise exceptions
        service_facade.refresh_services()

    @patch("ui.service_facade.get_data_service")
    def test_load_image_sequence(self, mock_get_service, service_facade):
        """Test load_image_sequence method."""
        mock_service = Mock()
        image_files = ["img1.jpg", "img2.jpg", "img3.jpg"]
        mock_service.load_image_sequence.return_value = image_files
        mock_get_service.return_value = mock_service

        result = service_facade.load_image_sequence("/path/to/images")

        assert result == image_files
        mock_service.load_image_sequence.assert_called_once_with("/path/to/images")


class TestModuleLevelFunctions:
    """Test module-level facade functions."""

    def test_get_service_facade_without_main_window(self):
        """Test get_service_facade without main window."""
        facade = get_service_facade()

        assert isinstance(facade, ServiceFacade)
        assert facade.main_window is None

    def test_get_service_facade_with_main_window(self, mock_main_window):
        """Test get_service_facade with main window."""
        facade = get_service_facade(mock_main_window)

        assert isinstance(facade, ServiceFacade)
        assert facade.main_window is mock_main_window

    def test_get_service_facade_singleton_behavior(self, mock_main_window):
        """Test that get_service_facade returns the same instance."""
        facade1 = get_service_facade(mock_main_window)
        facade2 = get_service_facade()

        # Should return the same instance (singleton behavior)
        assert facade1 is facade2

    def test_reset_service_facade(self, mock_main_window):
        """Test reset_service_facade clears the singleton."""
        facade1 = get_service_facade(mock_main_window)
        reset_service_facade()
        facade2 = get_service_facade()

        # Should return a new instance after reset
        assert facade1 is not facade2
        assert facade2.main_window is None  # New instance with no main window


class TestFacadePattern:
    """Test the facade pattern implementation."""

    def test_facade_provides_unified_interface(self, service_facade):
        """Test that facade provides unified interface to all services."""
        # Verify facade has methods from all service types
        assert hasattr(service_facade, "transform_service")  # Transform
        assert hasattr(service_facade, "data_service")  # Data
        assert hasattr(service_facade, "interaction_service")  # Interaction
        assert hasattr(service_facade, "ui_service")  # UI

        # Verify facade has high-level operations
        assert hasattr(service_facade, "smooth_curve")
        assert hasattr(service_facade, "filter_curve")
        assert hasattr(service_facade, "handle_mouse_press")
        assert hasattr(service_facade, "show_error")

    def test_facade_handles_service_unavailability_gracefully(self, service_facade):
        """Test that facade handles missing services gracefully."""
        # Mock all services as None
        with (
            patch("ui.service_facade.get_transform_service") as mock_transform,
            patch("ui.service_facade.get_data_service") as mock_data,
            patch("ui.service_facade.get_interaction_service") as mock_interaction,
            patch("ui.service_facade.get_ui_service") as mock_ui,
        ):
            mock_transform.return_value = None
            mock_data.return_value = None
            mock_interaction.return_value = None
            mock_ui.return_value = None

            # These should not raise exceptions
            assert service_facade.transform_service is None
            assert service_facade.data_service is None
            assert service_facade.interaction_service is None
            assert service_facade.ui_service is None

            # High-level operations should handle missing services gracefully
            assert service_facade.create_view_state(Mock()) is None
            assert service_facade.smooth_curve([]) == []
            assert service_facade.detect_outliers([]) == []
            service_facade.show_error("test")  # Should not crash

    def test_facade_delegation_pattern(self, service_facade, sample_curve_data):
        """Test that facade properly delegates to underlying services."""
        mock_data_service = Mock()
        mock_data_service.smooth_moving_average.return_value = sample_curve_data

        with patch("ui.service_facade.get_data_service") as mock_get:
            mock_get.return_value = mock_data_service
            result = service_facade.smooth_curve(sample_curve_data, 5)

            # Verify delegation occurred
            mock_data_service.smooth_moving_average.assert_called_once_with(sample_curve_data, 5)
            assert result == sample_curve_data

    def test_facade_legacy_service_compatibility(self, service_facade):
        """Test that facade maintains compatibility with legacy service names."""
        mock_data_service = Mock()
        mock_interaction_service = Mock()

        with (
            patch("ui.service_facade.get_data_service") as mock_get_data,
            patch("ui.service_facade.get_interaction_service") as mock_get_interaction,
        ):
            mock_get_data.return_value = mock_data_service
            mock_get_interaction.return_value = mock_interaction_service

            # Legacy aliases should work
            assert service_facade._file_service is mock_data_service
            assert service_facade._history_service is mock_interaction_service

            # Legacy service availability checks should work
            assert service_facade.is_service_available("file") is True
            assert service_facade.is_service_available("history") is True
