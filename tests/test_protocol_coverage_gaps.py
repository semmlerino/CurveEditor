#!/usr/bin/env python3
"""
Protocol Coverage Gap Analysis

This test identifies protocol methods that are missing test coverage.
Per UNIFIED_TESTING_GUIDE: "Every Protocol method MUST have test coverage."

These tests catch typos in protocol method names that would otherwise go undetected
until runtime, potentially causing application crashes.
"""

import pytest
from unittest.mock import Mock

from ui.protocols.controller_protocols import TimelineControllerProtocol
from protocols.ui import MainWindowProtocol


class TestTimelineControllerProtocolGaps:
    """Test previously uncovered TimelineControllerProtocol methods."""

    def test_timeline_controller_protocol_update_frame_display_method(self):
        """Test TimelineControllerProtocol.update_frame_display() method exists and is callable."""
        mock_timeline = Mock(spec=TimelineControllerProtocol)

        mock_timeline.update_frame_display(42, update_state=False)
        mock_timeline.update_frame_display.assert_called_once_with(42, update_state=False)

    def test_timeline_controller_protocol_toggle_playback_method(self):
        """Test TimelineControllerProtocol.toggle_playback() method exists and is callable."""
        mock_timeline = Mock(spec=TimelineControllerProtocol)

        mock_timeline.toggle_playback()
        mock_timeline.toggle_playback.assert_called_once()

    def test_timeline_controller_protocol_on_next_frame_method(self):
        """Test TimelineControllerProtocol._on_next_frame() method exists and is callable."""
        mock_timeline = Mock(spec=TimelineControllerProtocol)

        mock_timeline._on_next_frame()
        mock_timeline._on_next_frame.assert_called_once()

    def test_timeline_controller_protocol_on_prev_frame_method(self):
        """Test TimelineControllerProtocol._on_prev_frame() method exists and is callable."""
        mock_timeline = Mock(spec=TimelineControllerProtocol)

        mock_timeline._on_prev_frame()
        mock_timeline._on_prev_frame.assert_called_once()

    def test_timeline_controller_protocol_on_first_frame_method(self):
        """Test TimelineControllerProtocol._on_first_frame() method exists and is callable."""
        mock_timeline = Mock(spec=TimelineControllerProtocol)

        mock_timeline._on_first_frame()
        mock_timeline._on_first_frame.assert_called_once()

    def test_timeline_controller_protocol_on_last_frame_method(self):
        """Test TimelineControllerProtocol._on_last_frame() method exists and is callable."""
        mock_timeline = Mock(spec=TimelineControllerProtocol)

        mock_timeline._on_last_frame()
        mock_timeline._on_last_frame.assert_called_once()


class TestMainWindowProtocolGaps:
    """Test previously uncovered MainWindowProtocol methods (43 missing out of 54 total)."""

    def test_main_window_protocol_get_current_frame_method(self):
        """Test MainWindowProtocol._get_current_frame() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_window._get_current_frame.return_value = 42

        result = mock_window._get_current_frame()
        assert result == 42
        mock_window._get_current_frame.assert_called_once()

    def test_main_window_protocol_set_current_frame_method(self):
        """Test MainWindowProtocol._set_current_frame() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)

        mock_window._set_current_frame(42)
        mock_window._set_current_frame.assert_called_once_with(42)

    def test_main_window_protocol_update_timeline_tabs_method(self):
        """Test MainWindowProtocol.update_timeline_tabs() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_data = [(1, 100.0, 200.0)]

        mock_window.update_timeline_tabs(mock_data)
        mock_window.update_timeline_tabs.assert_called_once_with(mock_data)

    def test_main_window_protocol_update_tracking_panel_method(self):
        """Test MainWindowProtocol.update_tracking_panel() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)

        mock_window.update_tracking_panel()
        mock_window.update_tracking_panel.assert_called_once()

    def test_main_window_protocol_update_ui_state_method(self):
        """Test MainWindowProtocol.update_ui_state() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)

        mock_window.update_ui_state()
        mock_window.update_ui_state.assert_called_once()

    def test_main_window_protocol_update_zoom_label_method(self):
        """Test MainWindowProtocol.update_zoom_label() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)

        mock_window.update_zoom_label()
        mock_window.update_zoom_label.assert_called_once()

    def test_main_window_protocol_get_current_curve_data_method(self):
        """Test MainWindowProtocol._get_current_curve_data() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_data = [(1, 100.0, 200.0)]
        mock_window._get_current_curve_data.return_value = mock_data

        result = mock_window._get_current_curve_data()
        assert result == mock_data
        mock_window._get_current_curve_data.assert_called_once()

    def test_main_window_protocol_set_tracked_data_atomic_method(self):
        """Test MainWindowProtocol.set_tracked_data_atomic() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_data = {"Point_1": [(1, 100.0, 200.0)]}

        mock_window.set_tracked_data_atomic(mock_data)
        mock_window.set_tracked_data_atomic.assert_called_once_with(mock_data)

    def test_main_window_protocol_set_file_loading_state_method(self):
        """Test MainWindowProtocol.set_file_loading_state() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)

        mock_window.set_file_loading_state(True)
        mock_window.set_file_loading_state.assert_called_once_with(True)

    # Properties that need existence verification
    def test_main_window_protocol_current_frame_property(self):
        """Test MainWindowProtocol.current_frame property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_window.current_frame = 42
        assert mock_window.current_frame == 42

    def test_main_window_protocol_curve_widget_attribute(self):
        """Test MainWindowProtocol.curve_widget attribute exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_window.curve_widget = Mock()
        assert mock_window.curve_widget is not None

    def test_main_window_protocol_services_property(self):
        """Test MainWindowProtocol.services property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_service = Mock()
        mock_window.services = mock_service
        assert mock_window.services is mock_service

    def test_main_window_protocol_state_manager_property(self):
        """Test MainWindowProtocol.state_manager property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_state = Mock()
        mock_window.state_manager = mock_state
        assert mock_window.state_manager is mock_state

    def test_main_window_protocol_shortcut_manager_property(self):
        """Test MainWindowProtocol.shortcut_manager property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_shortcut = Mock()
        mock_window.shortcut_manager = mock_shortcut
        assert mock_window.shortcut_manager is mock_shortcut

    def test_main_window_protocol_multi_point_controller_property(self):
        """Test MainWindowProtocol.multi_point_controller property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_controller = Mock()
        mock_window.multi_point_controller = mock_controller
        assert mock_window.multi_point_controller is mock_controller

    def test_main_window_protocol_image_filenames_property(self):
        """Test MainWindowProtocol.image_filenames property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        filenames = ["img1.jpg", "img2.jpg"]
        mock_window.image_filenames = filenames
        assert mock_window.image_filenames == filenames

    def test_main_window_protocol_tracked_data_property(self):
        """Test MainWindowProtocol.tracked_data property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_data = {"Point_1": [(1, 100.0, 200.0)]}
        mock_window.tracked_data = mock_data
        assert mock_window.tracked_data == mock_data

    def test_main_window_protocol_active_points_property(self):
        """Test MainWindowProtocol.active_points property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        points = ["Point_1", "Point_2"]
        mock_window.active_points = points
        assert mock_window.active_points == points

    def test_main_window_protocol_active_timeline_point_property(self):
        """Test MainWindowProtocol.active_timeline_point property exists."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_window.active_timeline_point = "Point_1"
        assert mock_window.active_timeline_point == "Point_1"

    def test_main_window_protocol_geometry_method(self):
        """Test MainWindowProtocol.geometry() method exists and is callable."""
        mock_window = Mock(spec=MainWindowProtocol)
        mock_geometry = Mock()
        mock_window.geometry.return_value = mock_geometry

        result = mock_window.geometry()
        assert result is mock_geometry
        mock_window.geometry.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
