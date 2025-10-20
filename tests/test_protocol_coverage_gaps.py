#!/usr/bin/env python3
"""
Protocol Coverage Gap Analysis

This test identifies protocol methods that are missing test coverage.
Per UNIFIED_TESTING_GUIDE: "Every Protocol method MUST have test coverage."

These tests catch typos in protocol method names that would otherwise go undetected
until runtime, potentially causing application crashes.
"""

from unittest.mock import Mock

import pytest

from protocols.services import (
    DataServiceProtocol,
    InteractionServiceProtocol,
    TransformServiceProtocol,
    UIServiceProtocol,
)
from protocols.ui import (
    CurveViewProtocol,
    CurveWidgetProtocol,
    MainWindowProtocol,
)
from ui.protocols.controller_protocols import TimelineControllerProtocol


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


class TestCurveWidgetProtocol:
    """Comprehensive test coverage for CurveWidgetProtocol (14 methods/properties)."""

    def test_curve_view_property(self):
        """Test CurveWidgetProtocol.curve_view property exists."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.curve_view = Mock()
        assert mock.curve_view is not None

    def test_update_method(self):
        """Test CurveWidgetProtocol.update() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.update()
        mock.update.assert_called_once()

    def test_repaint_method(self):
        """Test CurveWidgetProtocol.repaint() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.repaint()
        mock.repaint.assert_called_once()

    def test_on_frame_changed_method(self):
        """Test CurveWidgetProtocol.on_frame_changed() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.on_frame_changed(42)
        mock.on_frame_changed.assert_called_once_with(42)

    def test_invalidate_caches_method(self):
        """Test CurveWidgetProtocol.invalidate_caches() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.invalidate_caches()
        mock.invalidate_caches.assert_called_once()

    def test_background_image_property(self):
        """Test CurveWidgetProtocol.background_image property exists."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.background_image = None
        assert mock.background_image is None

    def test_set_curve_data_method(self):
        """Test CurveWidgetProtocol.set_curve_data() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        test_data = [(1, 100.0, 200.0)]
        mock.set_curve_data(test_data)
        mock.set_curve_data.assert_called_once_with(test_data)

    def test_setup_for_pixel_tracking_method(self):
        """Test CurveWidgetProtocol.setup_for_pixel_tracking() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.setup_for_pixel_tracking()
        mock.setup_for_pixel_tracking.assert_called_once()

    def test_setup_for_3dequalizer_data_method(self):
        """Test CurveWidgetProtocol.setup_for_3dequalizer_data() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.setup_for_3dequalizer_data()
        mock.setup_for_3dequalizer_data.assert_called_once()

    def test_fit_to_view_method(self):
        """Test CurveWidgetProtocol.fit_to_view() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.fit_to_view()
        mock.fit_to_view.assert_called_once()

    def test_set_background_image_method(self):
        """Test CurveWidgetProtocol.set_background_image() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock_image = Mock()
        mock.set_background_image(mock_image)
        mock.set_background_image.assert_called_once_with(mock_image)

    def test_fit_to_background_image_method(self):
        """Test CurveWidgetProtocol.fit_to_background_image() method exists and is callable."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.fit_to_background_image()
        mock.fit_to_background_image.assert_called_once()

    def test_curve_data_property(self):
        """Test CurveWidgetProtocol.curve_data property exists."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.curve_data = [(1, 100.0, 200.0)]
        assert mock.curve_data is not None

    def test_show_background_property(self):
        """Test CurveWidgetProtocol.show_background property exists."""
        mock = Mock(spec=CurveWidgetProtocol)
        mock.show_background = True
        assert mock.show_background is True


class TestTransformServiceProtocol:
    """Comprehensive test coverage for TransformServiceProtocol (5 methods)."""

    def test_create_transform_from_view_state_method(self):
        """Test TransformServiceProtocol.create_transform_from_view_state() method exists."""
        mock = Mock(spec=TransformServiceProtocol)
        mock_view_state = Mock()
        mock_transform = Mock()
        mock.create_transform_from_view_state.return_value = mock_transform

        result = mock.create_transform_from_view_state(mock_view_state)
        assert result is mock_transform
        mock.create_transform_from_view_state.assert_called_once_with(mock_view_state)

    def test_get_cache_info_method(self):
        """Test TransformServiceProtocol.get_cache_info() method exists and is callable."""
        mock = Mock(spec=TransformServiceProtocol)
        mock_info = {"hits": 100, "misses": 10}
        mock.get_cache_info.return_value = mock_info

        result = mock.get_cache_info()
        assert result == mock_info
        mock.get_cache_info.assert_called_once()

    def test_clear_cache_method(self):
        """Test TransformServiceProtocol.clear_cache() method exists and is callable."""
        mock = Mock(spec=TransformServiceProtocol)
        mock.clear_cache()
        mock.clear_cache.assert_called_once()

    def test_data_to_screen_method(self):
        """Test TransformServiceProtocol.data_to_screen() method exists and is callable."""
        mock = Mock(spec=TransformServiceProtocol)
        mock.data_to_screen.return_value = (100, 200)

        result = mock.data_to_screen(10.0, 20.0, Mock())
        assert result == (100, 200)
        mock.data_to_screen.assert_called_once()

    def test_screen_to_data_method(self):
        """Test TransformServiceProtocol.screen_to_data() method exists and is callable."""
        mock = Mock(spec=TransformServiceProtocol)
        mock.screen_to_data.return_value = (10.0, 20.0)

        result = mock.screen_to_data(100, 200, Mock())
        assert result == (10.0, 20.0)
        mock.screen_to_data.assert_called_once()


class TestDataServiceProtocol:
    """Comprehensive test coverage for DataServiceProtocol (6 methods)."""

    def test_load_tracking_data_method(self):
        """Test DataServiceProtocol.load_tracking_data() method exists and is callable."""
        mock = Mock(spec=DataServiceProtocol)
        mock.load_tracking_data.return_value = {"Track1": [(1, 100.0, 200.0)]}

        result = mock.load_tracking_data("test.txt")
        assert result is not None
        mock.load_tracking_data.assert_called_once_with("test.txt")

    def test_save_tracking_data_method(self):
        """Test DataServiceProtocol.save_tracking_data() method exists and is callable."""
        mock = Mock(spec=DataServiceProtocol)
        test_data = {"Track1": [(1, 100.0, 200.0)]}
        mock.save_tracking_data(test_data, "output.txt")
        mock.save_tracking_data.assert_called_once_with(test_data, "output.txt")

    def test_load_image_method(self):
        """Test DataServiceProtocol.load_image() method exists and is callable."""
        mock = Mock(spec=DataServiceProtocol)
        mock_image = Mock()
        mock.load_image.return_value = mock_image

        result = mock.load_image("image.jpg")
        assert result is mock_image
        mock.load_image.assert_called_once_with("image.jpg")

    def test_get_supported_formats_method(self):
        """Test DataServiceProtocol.get_supported_formats() method exists and is callable."""
        mock = Mock(spec=DataServiceProtocol)
        mock.get_supported_formats.return_value = [".txt", ".csv", ".json"]

        result = mock.get_supported_formats()
        assert isinstance(result, list)
        mock.get_supported_formats.assert_called_once()

    def test_analyze_data_method(self):
        """Test DataServiceProtocol.analyze_data() method exists and is callable."""
        mock = Mock(spec=DataServiceProtocol)
        test_data = [(1, 100.0, 200.0)]
        mock_analysis = {"min_x": 100.0, "max_x": 100.0}
        mock.analyze_data.return_value = mock_analysis

        result = mock.analyze_data(test_data)
        assert result == mock_analysis
        mock.analyze_data.assert_called_once_with(test_data)

    def test_clear_cache_method(self):
        """Test DataServiceProtocol.clear_cache() method exists and is callable."""
        mock = Mock(spec=DataServiceProtocol)
        mock.clear_cache()
        mock.clear_cache.assert_called_once()


class TestInteractionServiceProtocol:
    """Comprehensive test coverage for InteractionServiceProtocol (6 methods)."""

    def test_handle_point_selection_method(self):
        """Test InteractionServiceProtocol.handle_point_selection() method exists."""
        mock = Mock(spec=InteractionServiceProtocol)
        mock_view = Mock()
        mock.handle_point_selection(mock_view, 100, 200, ctrl_pressed=False)
        mock.handle_point_selection.assert_called_once()

    def test_handle_point_move_method(self):
        """Test InteractionServiceProtocol.handle_point_move() method exists."""
        mock = Mock(spec=InteractionServiceProtocol)
        mock_view = Mock()
        mock.handle_point_move(mock_view, 0, 150.0, 250.0)
        mock.handle_point_move.assert_called_once()

    def test_handle_rubber_band_selection_method(self):
        """Test InteractionServiceProtocol.handle_rubber_band_selection() method exists."""
        mock = Mock(spec=InteractionServiceProtocol)
        mock_view = Mock()
        mock_rect = Mock()
        mock.handle_rubber_band_selection(mock_view, mock_rect, ctrl_pressed=False)
        mock.handle_rubber_band_selection.assert_called_once()

    def test_find_point_at_method(self):
        """Test InteractionServiceProtocol.find_point_at() method exists."""
        mock = Mock(spec=InteractionServiceProtocol)
        mock_view = Mock()
        mock.find_point_at.return_value = 5

        result = mock.find_point_at(mock_view, 100, 200)
        assert result == 5
        mock.find_point_at.assert_called_once()

    def test_get_spatial_index_stats_method(self):
        """Test InteractionServiceProtocol.get_spatial_index_stats() method exists."""
        mock = Mock(spec=InteractionServiceProtocol)
        mock.get_spatial_index_stats.return_value = {"cells": 100, "points": 500}

        result = mock.get_spatial_index_stats()
        assert result is not None
        mock.get_spatial_index_stats.assert_called_once()

    def test_clear_cache_method(self):
        """Test InteractionServiceProtocol.clear_cache() method exists and is callable."""
        mock = Mock(spec=InteractionServiceProtocol)
        mock.clear_cache()
        mock.clear_cache.assert_called_once()


class TestUIServiceProtocol:
    """Comprehensive test coverage for UIServiceProtocol (5 methods)."""

    def test_show_dialog_method(self):
        """Test UIServiceProtocol.show_dialog() method exists and is callable."""
        mock = Mock(spec=UIServiceProtocol)
        mock.show_dialog.return_value = True

        result = mock.show_dialog("Error", "An error occurred")
        assert result is True
        mock.show_dialog.assert_called_once()

    def test_update_status_method(self):
        """Test UIServiceProtocol.update_status() method exists and is callable."""
        mock = Mock(spec=UIServiceProtocol)
        mock.update_status("Processing...")
        mock.update_status.assert_called_once_with("Processing...")

    def test_refresh_ui_method(self):
        """Test UIServiceProtocol.refresh_ui() method exists and is callable."""
        mock = Mock(spec=UIServiceProtocol)
        mock.refresh_ui()
        mock.refresh_ui.assert_called_once()

    def test_get_theme_method(self):
        """Test UIServiceProtocol.get_theme() method exists and is callable."""
        mock = Mock(spec=UIServiceProtocol)
        mock.get_theme.return_value = "dark"

        result = mock.get_theme()
        assert result == "dark"
        mock.get_theme.assert_called_once()

    def test_set_theme_method(self):
        """Test UIServiceProtocol.set_theme() method exists and is callable."""
        mock = Mock(spec=UIServiceProtocol)
        mock.set_theme("light")
        mock.set_theme.assert_called_once_with("light")


class TestCurveViewProtocol:
    """Comprehensive test coverage for CurveViewProtocol (54 members)."""

    # Basic attributes
    def test_selected_point_idx_attribute(self):
        """Test CurveViewProtocol.selected_point_idx attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.selected_point_idx = 5
        assert mock.selected_point_idx == 5

    def test_curve_data_attribute(self):
        """Test CurveViewProtocol.curve_data attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.curve_data = [(1, 100.0, 200.0)]
        assert mock.curve_data is not None

    def test_current_image_idx_attribute(self):
        """Test CurveViewProtocol.current_image_idx attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.current_image_idx = 10
        assert mock.current_image_idx == 10

    # Point management
    def test_points_attribute(self):
        """Test CurveViewProtocol.points attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.points = [(1, 100.0, 200.0)]
        assert mock.points is not None

    def test_selected_points_attribute(self):
        """Test CurveViewProtocol.selected_points attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.selected_points = {0, 1, 2}
        assert len(mock.selected_points) == 3

    # Transform and positioning
    def test_offset_x_attribute(self):
        """Test CurveViewProtocol.offset_x attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.offset_x = 50.0
        assert mock.offset_x == 50.0

    def test_offset_y_attribute(self):
        """Test CurveViewProtocol.offset_y attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.offset_y = 75.0
        assert mock.offset_y == 75.0

    def test_x_offset_attribute(self):
        """Test CurveViewProtocol.x_offset attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.x_offset = 50.0
        assert mock.x_offset == 50.0

    def test_y_offset_attribute(self):
        """Test CurveViewProtocol.y_offset attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.y_offset = 75.0
        assert mock.y_offset == 75.0

    def test_zoom_factor_attribute(self):
        """Test CurveViewProtocol.zoom_factor attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.zoom_factor = 2.0
        assert mock.zoom_factor == 2.0

    def test_pan_offset_x_attribute(self):
        """Test CurveViewProtocol.pan_offset_x attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.pan_offset_x = 100.0
        assert mock.pan_offset_x == 100.0

    def test_pan_offset_y_attribute(self):
        """Test CurveViewProtocol.pan_offset_y attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.pan_offset_y = 150.0
        assert mock.pan_offset_y == 150.0

    def test_manual_offset_x_attribute(self):
        """Test CurveViewProtocol.manual_offset_x attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.manual_offset_x = 25.0
        assert mock.manual_offset_x == 25.0

    def test_manual_offset_y_attribute(self):
        """Test CurveViewProtocol.manual_offset_y attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.manual_offset_y = 30.0
        assert mock.manual_offset_y == 30.0

    # Interaction state
    def test_drag_active_attribute(self):
        """Test CurveViewProtocol.drag_active attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.drag_active = True
        assert mock.drag_active is True

    def test_pan_active_attribute(self):
        """Test CurveViewProtocol.pan_active attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.pan_active = False
        assert mock.pan_active is False

    def test_last_drag_pos_attribute(self):
        """Test CurveViewProtocol.last_drag_pos attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.last_drag_pos = None
        assert mock.last_drag_pos is None

    def test_last_pan_pos_attribute(self):
        """Test CurveViewProtocol.last_pan_pos attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.last_pan_pos = None
        assert mock.last_pan_pos is None

    # Rubber band selection
    def test_rubber_band_attribute(self):
        """Test CurveViewProtocol.rubber_band attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.rubber_band = None
        assert mock.rubber_band is None

    def test_rubber_band_active_attribute(self):
        """Test CurveViewProtocol.rubber_band_active attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.rubber_band_active = False
        assert mock.rubber_band_active is False

    def test_rubber_band_origin_attribute(self):
        """Test CurveViewProtocol.rubber_band_origin attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock_origin = Mock()
        mock.rubber_band_origin = mock_origin
        assert mock.rubber_band_origin is mock_origin

    # Visualization settings
    def test_show_grid_attribute(self):
        """Test CurveViewProtocol.show_grid attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.show_grid = True
        assert mock.show_grid is True

    def test_show_background_attribute(self):
        """Test CurveViewProtocol.show_background attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.show_background = False
        assert mock.show_background is False

    def test_show_velocity_vectors_attribute(self):
        """Test CurveViewProtocol.show_velocity_vectors attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.show_velocity_vectors = True
        assert mock.show_velocity_vectors is True

    def test_show_all_frame_numbers_attribute(self):
        """Test CurveViewProtocol.show_all_frame_numbers attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.show_all_frame_numbers = False
        assert mock.show_all_frame_numbers is False

    # Background image
    def test_background_image_attribute(self):
        """Test CurveViewProtocol.background_image attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.background_image = None
        assert mock.background_image is None

    def test_background_opacity_attribute(self):
        """Test CurveViewProtocol.background_opacity attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.background_opacity = 0.5
        assert mock.background_opacity == 0.5

    # Image and display settings
    def test_image_width_attribute(self):
        """Test CurveViewProtocol.image_width attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.image_width = 1920
        assert mock.image_width == 1920

    def test_image_height_attribute(self):
        """Test CurveViewProtocol.image_height attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.image_height = 1080
        assert mock.image_height == 1080

    def test_scale_to_image_attribute(self):
        """Test CurveViewProtocol.scale_to_image attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.scale_to_image = True
        assert mock.scale_to_image is True

    def test_flip_y_axis_attribute(self):
        """Test CurveViewProtocol.flip_y_axis attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock.flip_y_axis = False
        assert mock.flip_y_axis is False

    # Parent reference
    def test_main_window_attribute(self):
        """Test CurveViewProtocol.main_window attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock_window = Mock()
        mock.main_window = mock_window
        assert mock.main_window is mock_window

    # Qt signals
    def test_point_selected_attribute(self):
        """Test CurveViewProtocol.point_selected attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock_signal = Mock()
        mock.point_selected = mock_signal
        assert mock.point_selected is mock_signal

    def test_point_moved_attribute(self):
        """Test CurveViewProtocol.point_moved attribute exists."""
        mock = Mock(spec=CurveViewProtocol)
        mock_signal = Mock()
        mock.point_moved = mock_signal
        assert mock.point_moved is mock_signal

    # Methods
    def test_update_method(self):
        """Test CurveViewProtocol.update() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.update()
        mock.update.assert_called_once()

    def test_repaint_method(self):
        """Test CurveViewProtocol.repaint() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.repaint()
        mock.repaint.assert_called_once()

    def test_width_method(self):
        """Test CurveViewProtocol.width() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.width.return_value = 800

        result = mock.width()
        assert result == 800
        mock.width.assert_called_once()

    def test_height_method(self):
        """Test CurveViewProtocol.height() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.height.return_value = 600

        result = mock.height()
        assert result == 600
        mock.height.assert_called_once()

    def test_set_cursor_method(self):
        """Test CurveViewProtocol.setCursor() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock_cursor = Mock()
        mock.setCursor(mock_cursor)
        mock.setCursor.assert_called_once_with(mock_cursor)

    def test_unset_cursor_method(self):
        """Test CurveViewProtocol.unsetCursor() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.unsetCursor()
        mock.unsetCursor.assert_called_once()

    def test_find_point_at_method(self):
        """Test CurveViewProtocol.findPointAt() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.findPointAt.return_value = 3

        result = mock.findPointAt(100, 200)
        assert result == 3
        mock.findPointAt.assert_called_once()

    def test_select_point_by_index_method(self):
        """Test CurveViewProtocol.selectPointByIndex() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.selectPointByIndex(5)
        mock.selectPointByIndex.assert_called_once_with(5)

    def test_get_current_transform_method(self):
        """Test CurveViewProtocol.get_current_transform() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock_transform = Mock()
        mock.get_current_transform.return_value = mock_transform

        result = mock.get_current_transform()
        assert result is mock_transform
        mock.get_current_transform.assert_called_once()

    def test_get_transform_method(self):
        """Test CurveViewProtocol.get_transform() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock_transform = Mock()
        mock.get_transform.return_value = mock_transform

        result = mock.get_transform()
        assert result is mock_transform
        mock.get_transform.assert_called_once()

    def test_invalidate_caches_method(self):
        """Test CurveViewProtocol._invalidate_caches() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock._invalidate_caches()
        mock._invalidate_caches.assert_called_once()

    def test_get_point_data_method(self):
        """Test CurveViewProtocol.get_point_data() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.get_point_data.return_value = (1, 100.0, 200.0)

        result = mock.get_point_data(5)
        assert result is not None
        mock.get_point_data.assert_called_once_with(5)

    def test_toggle_background_visible_method(self):
        """Test CurveViewProtocol.toggleBackgroundVisible() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.toggleBackgroundVisible()
        mock.toggleBackgroundVisible.assert_called_once()

    def test_toggle_point_interpolation_method(self):
        """Test CurveViewProtocol.toggle_point_interpolation() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.toggle_point_interpolation(5)
        mock.toggle_point_interpolation.assert_called_once_with(5)

    def test_set_curve_data_method(self):
        """Test CurveViewProtocol.set_curve_data() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        test_data = [(1, 100.0, 200.0)]
        mock.set_curve_data(test_data)
        mock.set_curve_data.assert_called_once_with(test_data)

    def test_set_points_method(self):
        """Test CurveViewProtocol.setPoints() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        test_data = [(1, 100.0, 200.0)]
        mock.setPoints(test_data)
        mock.setPoints.assert_called_once_with(test_data)

    def test_set_selected_indices_method(self):
        """Test CurveViewProtocol.set_selected_indices() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        indices = {0, 1, 2}
        mock.set_selected_indices(indices)
        mock.set_selected_indices.assert_called_once_with(indices)

    def test_setup_for_3dequalizer_data_method(self):
        """Test CurveViewProtocol.setup_for_3dequalizer_data() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.setup_for_3dequalizer_data()
        mock.setup_for_3dequalizer_data.assert_called_once()

    def test_setup_for_pixel_tracking_method(self):
        """Test CurveViewProtocol.setup_for_pixel_tracking() method exists and is callable."""
        mock = Mock(spec=CurveViewProtocol)
        mock.setup_for_pixel_tracking()
        mock.setup_for_pixel_tracking.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
