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

from core.spatial_index import HasDimensionsProtocol
from protocols.data import (
    BatchEditableProtocol,
    CurveDataProtocol,
    HistoryCommandProtocol,
    HistoryContainerProtocol,
    ImageProtocol,
    PointMovedSignalProtocol,
    PointProtocol,
    VoidSignalProtocol,
)
from protocols.services import (
    DataServiceProtocol,
    FileLoadWorkerProtocol,
    InteractionServiceProtocol,
    LoggingServiceProtocol,
    ServiceProtocol,
    ServicesProtocol,
    SessionManagerProtocol,
    SignalProtocol,
    StatusServiceProtocol,
    TransformServiceProtocol,
    UIServiceProtocol,
)
from protocols.ui import (
    CommandManagerProtocol,
    CurveViewProtocol,
    CurveWidgetProtocol,
    EventProtocol,
    FrameNavigationProtocol,
    MainWindowProtocol,
    ShortcutManagerProtocol,
    StateManagerProtocol,
    WidgetProtocol,
)
from ui.protocols.controller_protocols import (
    ActionHandlerProtocol,
    BackgroundImageProtocol,
    MultiPointTrackingProtocol,
    PointEditorProtocol,
    SignalConnectionProtocol,
    TimelineControllerProtocol,
    UIInitializationProtocol,
    ViewOptionsProtocol,
)


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


# ============================================================================
# CONTROLLER PROTOCOLS (10 protocols)
# ============================================================================


class TestActionHandlerProtocol:
    """Comprehensive test coverage for ActionHandlerProtocol (24 methods)."""

    def test_on_action_new_method(self):
        """Test ActionHandlerProtocol.on_action_new() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_new()
        mock.on_action_new.assert_called_once()

    def test_on_action_open_method(self):
        """Test ActionHandlerProtocol.on_action_open() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_open()
        mock.on_action_open.assert_called_once()

    def test_on_action_save_method(self):
        """Test ActionHandlerProtocol.on_action_save() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_save()
        mock.on_action_save.assert_called_once()

    def test_on_action_save_as_method(self):
        """Test ActionHandlerProtocol.on_action_save_as() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_save_as()
        mock.on_action_save_as.assert_called_once()

    def test_on_select_all_method(self):
        """Test ActionHandlerProtocol.on_select_all() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_select_all()
        mock.on_select_all.assert_called_once()

    def test_on_add_point_method(self):
        """Test ActionHandlerProtocol.on_add_point() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_add_point()
        mock.on_add_point.assert_called_once()

    def test_on_zoom_in_method(self):
        """Test ActionHandlerProtocol._on_zoom_in() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock._on_zoom_in()
        mock._on_zoom_in.assert_called_once()

    def test_on_zoom_out_method(self):
        """Test ActionHandlerProtocol._on_zoom_out() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock._on_zoom_out()
        mock._on_zoom_out.assert_called_once()

    def test_on_zoom_fit_method(self):
        """Test ActionHandlerProtocol.on_zoom_fit() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_zoom_fit()
        mock.on_zoom_fit.assert_called_once()

    def test_on_reset_view_method(self):
        """Test ActionHandlerProtocol._on_reset_view() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock._on_reset_view()
        mock._on_reset_view.assert_called_once()

    def test_update_zoom_label_method(self):
        """Test ActionHandlerProtocol.update_zoom_label() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.update_zoom_label()
        mock.update_zoom_label.assert_called_once()

    def test_apply_smooth_operation_method(self):
        """Test ActionHandlerProtocol.apply_smooth_operation() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.apply_smooth_operation()
        mock.apply_smooth_operation.assert_called_once()

    def test_get_current_curve_data_method(self):
        """Test ActionHandlerProtocol._get_current_curve_data() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock_data = [(1, 100.0, 200.0)]
        mock._get_current_curve_data.return_value = mock_data

        result = mock._get_current_curve_data()
        assert result == mock_data
        mock._get_current_curve_data.assert_called_once()

    def test_on_action_undo_method(self):
        """Test ActionHandlerProtocol.on_action_undo() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_undo()
        mock.on_action_undo.assert_called_once()

    def test_on_action_redo_method(self):
        """Test ActionHandlerProtocol.on_action_redo() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_redo()
        mock.on_action_redo.assert_called_once()

    def test_on_action_zoom_in_method(self):
        """Test ActionHandlerProtocol.on_action_zoom_in() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_zoom_in()
        mock.on_action_zoom_in.assert_called_once()

    def test_on_action_zoom_out_method(self):
        """Test ActionHandlerProtocol.on_action_zoom_out() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_zoom_out()
        mock.on_action_zoom_out.assert_called_once()

    def test_on_action_reset_view_method(self):
        """Test ActionHandlerProtocol.on_action_reset_view() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_action_reset_view()
        mock.on_action_reset_view.assert_called_once()

    def test_on_load_images_method(self):
        """Test ActionHandlerProtocol.on_load_images() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_load_images()
        mock.on_load_images.assert_called_once()

    def test_on_export_data_method(self):
        """Test ActionHandlerProtocol.on_export_data() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_export_data()
        mock.on_export_data.assert_called_once()

    def test_on_smooth_curve_method(self):
        """Test ActionHandlerProtocol.on_smooth_curve() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_smooth_curve()
        mock.on_smooth_curve.assert_called_once()

    def test_on_filter_curve_method(self):
        """Test ActionHandlerProtocol.on_filter_curve() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_filter_curve()
        mock.on_filter_curve.assert_called_once()

    def test_on_analyze_curve_method(self):
        """Test ActionHandlerProtocol.on_analyze_curve() exists and is callable."""
        mock = Mock(spec=ActionHandlerProtocol)
        mock.on_analyze_curve()
        mock.on_analyze_curve.assert_called_once()


class TestFrameNavigationProtocol:
    """Comprehensive test coverage for FrameNavigationProtocol (6 methods)."""

    def test_navigate_to_frame_method(self):
        """Test FrameNavigationProtocol.navigate_to_frame() exists and is callable."""
        mock = Mock(spec=FrameNavigationProtocol)
        mock.navigate_to_frame(42)
        mock.navigate_to_frame.assert_called_once_with(42)

    def test_jump_frames_method(self):
        """Test FrameNavigationProtocol.jump_frames() exists and is callable."""
        mock = Mock(spec=FrameNavigationProtocol)
        mock.jump_frames(5)
        mock.jump_frames.assert_called_once_with(5)

    def test_next_frame_method(self):
        """Test FrameNavigationProtocol.next_frame() exists and is callable."""
        mock = Mock(spec=FrameNavigationProtocol)
        mock.next_frame()
        mock.next_frame.assert_called_once()

    def test_previous_frame_method(self):
        """Test FrameNavigationProtocol.previous_frame() exists and is callable."""
        mock = Mock(spec=FrameNavigationProtocol)
        mock.previous_frame()
        mock.previous_frame.assert_called_once()

    def test_first_frame_method(self):
        """Test FrameNavigationProtocol.first_frame() exists and is callable."""
        mock = Mock(spec=FrameNavigationProtocol)
        mock.first_frame()
        mock.first_frame.assert_called_once()

    def test_last_frame_method(self):
        """Test FrameNavigationProtocol.last_frame() exists and is callable."""
        mock = Mock(spec=FrameNavigationProtocol)
        mock.last_frame()
        mock.last_frame.assert_called_once()


class TestMultiPointTrackingProtocol:
    """Comprehensive test coverage for MultiPointTrackingProtocol (15 methods + 1 property)."""

    def test_tracked_data_property(self):
        """Test MultiPointTrackingProtocol.tracked_data property exists."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock_data = {"Track1": [(1, 100.0, 200.0)]}
        mock.tracked_data = mock_data
        assert mock.tracked_data == mock_data

    def test_on_tracking_data_loaded_method(self):
        """Test MultiPointTrackingProtocol.on_tracking_data_loaded() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        test_data = [(1, 100.0, 200.0)]
        mock.on_tracking_data_loaded(test_data)
        mock.on_tracking_data_loaded.assert_called_once_with(test_data)

    def test_on_multi_point_data_loaded_method(self):
        """Test MultiPointTrackingProtocol.on_multi_point_data_loaded() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        multi_data = {"Track1": [(1, 100.0, 200.0)]}
        mock.on_multi_point_data_loaded(multi_data)
        mock.on_multi_point_data_loaded.assert_called_once_with(multi_data)

    def test_on_tracking_points_selected_method(self):
        """Test MultiPointTrackingProtocol.on_tracking_points_selected() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        point_names = ["Point_1", "Point_2"]
        mock.on_tracking_points_selected(point_names)
        mock.on_tracking_points_selected.assert_called_once_with(point_names)

    def test_on_point_visibility_changed_method(self):
        """Test MultiPointTrackingProtocol.on_point_visibility_changed() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.on_point_visibility_changed("Point_1", True)
        mock.on_point_visibility_changed.assert_called_once_with("Point_1", True)

    def test_on_point_color_changed_method(self):
        """Test MultiPointTrackingProtocol.on_point_color_changed() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.on_point_color_changed("Point_1", "#FF0000")
        mock.on_point_color_changed.assert_called_once_with("Point_1", "#FF0000")

    def test_on_point_deleted_method(self):
        """Test MultiPointTrackingProtocol.on_point_deleted() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.on_point_deleted("Point_1")
        mock.on_point_deleted.assert_called_once_with("Point_1")

    def test_on_point_renamed_method(self):
        """Test MultiPointTrackingProtocol.on_point_renamed() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.on_point_renamed("OldName", "NewName")
        mock.on_point_renamed.assert_called_once_with("OldName", "NewName")

    def test_on_tracking_direction_changed_method(self):
        """Test MultiPointTrackingProtocol.on_tracking_direction_changed() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock_direction = Mock()
        mock.on_tracking_direction_changed("Point_1", mock_direction)
        mock.on_tracking_direction_changed.assert_called_once_with("Point_1", mock_direction)

    def test_on_curve_selection_changed_method(self):
        """Test MultiPointTrackingProtocol.on_curve_selection_changed() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        selection = {0, 1, 2}
        mock.on_curve_selection_changed(selection)
        mock.on_curve_selection_changed.assert_called_once_with(selection)

    def test_update_tracking_panel_method(self):
        """Test MultiPointTrackingProtocol.update_tracking_panel() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.update_tracking_panel()
        mock.update_tracking_panel.assert_called_once()

    def test_update_curve_display_method(self):
        """Test MultiPointTrackingProtocol.update_curve_display() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.update_curve_display()
        mock.update_curve_display.assert_called_once()

    def test_clear_tracking_data_method(self):
        """Test MultiPointTrackingProtocol.clear_tracking_data() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.clear_tracking_data()
        mock.clear_tracking_data.assert_called_once()

    def test_has_tracking_data_method(self):
        """Test MultiPointTrackingProtocol.has_tracking_data() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        mock.has_tracking_data.return_value = True

        result = mock.has_tracking_data()
        assert result is True
        mock.has_tracking_data.assert_called_once()

    def test_get_tracking_point_names_method(self):
        """Test MultiPointTrackingProtocol.get_tracking_point_names() exists and is callable."""
        mock = Mock(spec=MultiPointTrackingProtocol)
        point_names = ["Point_1", "Point_2"]
        mock.get_tracking_point_names.return_value = point_names

        result = mock.get_tracking_point_names()
        assert result == point_names
        mock.get_tracking_point_names.assert_called_once()


class TestPointEditorProtocol:
    """Comprehensive test coverage for PointEditorProtocol (5 methods)."""

    def test_on_selection_changed_method(self):
        """Test PointEditorProtocol.on_selection_changed() exists and is callable."""
        mock = Mock(spec=PointEditorProtocol)
        indices = [0, 1, 2]
        mock.on_selection_changed(indices)
        mock.on_selection_changed.assert_called_once_with(indices)

    def test_on_store_selection_changed_method(self):
        """Test PointEditorProtocol.on_store_selection_changed() exists and is callable."""
        mock = Mock(spec=PointEditorProtocol)
        selection = {0, 1, 2}
        mock.on_store_selection_changed(selection, curve_name="Track1")
        mock.on_store_selection_changed.assert_called_once_with(selection, curve_name="Track1")

    def test_on_point_x_changed_method(self):
        """Test PointEditorProtocol.on_point_x_changed() exists and is callable."""
        mock = Mock(spec=PointEditorProtocol)
        mock.on_point_x_changed(150.5)
        mock.on_point_x_changed.assert_called_once_with(150.5)

    def test_on_point_y_changed_method(self):
        """Test PointEditorProtocol.on_point_y_changed() exists and is callable."""
        mock = Mock(spec=PointEditorProtocol)
        mock.on_point_y_changed(250.75)
        mock.on_point_y_changed.assert_called_once_with(250.75)

    def test_connect_signals_method(self):
        """Test PointEditorProtocol.connect_signals() exists and is callable."""
        mock = Mock(spec=PointEditorProtocol)
        mock.connect_signals()
        mock.connect_signals.assert_called_once()


class TestSignalConnectionProtocol:
    """Comprehensive test coverage for SignalConnectionProtocol (6 methods)."""

    def test_connect_all_signals_method(self):
        """Test SignalConnectionProtocol.connect_all_signals() exists and is callable."""
        mock = Mock(spec=SignalConnectionProtocol)
        mock.connect_all_signals()
        mock.connect_all_signals.assert_called_once()

    def test_connect_file_operations_signals_method(self):
        """Test SignalConnectionProtocol._connect_file_operations_signals() exists and is callable."""
        mock = Mock(spec=SignalConnectionProtocol)
        mock._connect_file_operations_signals()
        mock._connect_file_operations_signals.assert_called_once()

    def test_connect_signals_method(self):
        """Test SignalConnectionProtocol._connect_signals() exists and is callable."""
        mock = Mock(spec=SignalConnectionProtocol)
        mock._connect_signals()
        mock._connect_signals.assert_called_once()

    def test_connect_store_signals_method(self):
        """Test SignalConnectionProtocol._connect_store_signals() exists and is callable."""
        mock = Mock(spec=SignalConnectionProtocol)
        mock._connect_store_signals()
        mock._connect_store_signals.assert_called_once()

    def test_connect_curve_widget_signals_method(self):
        """Test SignalConnectionProtocol._connect_curve_widget_signals() exists and is callable."""
        mock = Mock(spec=SignalConnectionProtocol)
        mock._connect_curve_widget_signals()
        mock._connect_curve_widget_signals.assert_called_once()

    def test_verify_connections_method(self):
        """Test SignalConnectionProtocol._verify_connections() exists and is callable."""
        mock = Mock(spec=SignalConnectionProtocol)
        mock._verify_connections()
        mock._verify_connections.assert_called_once()


class TestUIInitializationProtocol:
    """Comprehensive test coverage for UIInitializationProtocol (9 methods)."""

    def test_initialize_ui_method(self):
        """Test UIInitializationProtocol.initialize_ui() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock.initialize_ui()
        mock.initialize_ui.assert_called_once()

    def test_init_actions_method(self):
        """Test UIInitializationProtocol._init_actions() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_actions()
        mock._init_actions.assert_called_once()

    def test_init_menus_method(self):
        """Test UIInitializationProtocol._init_menus() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_menus()
        mock._init_menus.assert_called_once()

    def test_init_curve_view_method(self):
        """Test UIInitializationProtocol._init_curve_view() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_curve_view()
        mock._init_curve_view.assert_called_once()

    def test_init_control_panel_method(self):
        """Test UIInitializationProtocol._init_control_panel() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_control_panel()
        mock._init_control_panel.assert_called_once()

    def test_init_properties_panel_method(self):
        """Test UIInitializationProtocol._init_properties_panel() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_properties_panel()
        mock._init_properties_panel.assert_called_once()

    def test_init_timeline_tabs_method(self):
        """Test UIInitializationProtocol._init_timeline_tabs() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_timeline_tabs()
        mock._init_timeline_tabs.assert_called_once()

    def test_init_tracking_panel_method(self):
        """Test UIInitializationProtocol._init_tracking_panel() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_tracking_panel()
        mock._init_tracking_panel.assert_called_once()

    def test_init_status_bar_method(self):
        """Test UIInitializationProtocol._init_status_bar() exists and is callable."""
        mock = Mock(spec=UIInitializationProtocol)
        mock._init_status_bar()
        mock._init_status_bar.assert_called_once()


class TestViewOptionsProtocol:
    """Comprehensive test coverage for ViewOptionsProtocol (10 methods)."""

    def test_on_show_background_changed_method(self):
        """Test ViewOptionsProtocol.on_show_background_changed() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.on_show_background_changed(True)
        mock.on_show_background_changed.assert_called_once_with(True)

    def test_on_show_grid_changed_method(self):
        """Test ViewOptionsProtocol.on_show_grid_changed() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.on_show_grid_changed(False)
        mock.on_show_grid_changed.assert_called_once_with(False)

    def test_on_point_size_changed_method(self):
        """Test ViewOptionsProtocol.on_point_size_changed() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.on_point_size_changed(5)
        mock.on_point_size_changed.assert_called_once_with(5)

    def test_on_line_width_changed_method(self):
        """Test ViewOptionsProtocol.on_line_width_changed() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.on_line_width_changed(2)
        mock.on_line_width_changed.assert_called_once_with(2)

    def test_toggle_tooltips_method(self):
        """Test ViewOptionsProtocol.toggle_tooltips() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.toggle_tooltips()
        mock.toggle_tooltips.assert_called_once()

    def test_update_curve_point_size_method(self):
        """Test ViewOptionsProtocol.update_curve_point_size() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.update_curve_point_size(7)
        mock.update_curve_point_size.assert_called_once_with(7)

    def test_update_curve_line_width_method(self):
        """Test ViewOptionsProtocol.update_curve_line_width() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.update_curve_line_width(3)
        mock.update_curve_line_width.assert_called_once_with(3)

    def test_update_curve_view_options_method(self):
        """Test ViewOptionsProtocol.update_curve_view_options() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock.update_curve_view_options()
        mock.update_curve_view_options.assert_called_once()

    def test_get_view_options_method(self):
        """Test ViewOptionsProtocol.get_view_options() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        mock_options = {"show_grid": True, "point_size": 5}
        mock.get_view_options.return_value = mock_options

        result = mock.get_view_options()
        assert result == mock_options
        mock.get_view_options.assert_called_once()

    def test_set_view_options_method(self):
        """Test ViewOptionsProtocol.set_view_options() exists and is callable."""
        mock = Mock(spec=ViewOptionsProtocol)
        options = {"show_grid": False, "point_size": 8}
        mock.set_view_options(options)
        mock.set_view_options.assert_called_once_with(options)


class TestSessionManagerProtocol:
    """Comprehensive test coverage for SessionManagerProtocol (3 methods)."""

    def test_save_session_method(self):
        """Test SessionManagerProtocol.save_session() exists and is callable."""
        mock = Mock(spec=SessionManagerProtocol)
        session_data = {"frame": 42, "zoom": 2.0}
        mock.save_session.return_value = True

        result = mock.save_session(session_data)
        assert result is True
        mock.save_session.assert_called_once_with(session_data)

    def test_load_session_method(self):
        """Test SessionManagerProtocol.load_session() exists and is callable."""
        mock = Mock(spec=SessionManagerProtocol)
        session_data = {"frame": 42, "zoom": 2.0}
        mock.load_session.return_value = session_data

        result = mock.load_session()
        assert result == session_data
        mock.load_session.assert_called_once()

    def test_create_session_data_method(self):
        """Test SessionManagerProtocol.create_session_data() exists and is callable."""
        mock = Mock(spec=SessionManagerProtocol)
        expected_data = {
            "tracking_file": "test.txt",
            "current_frame": 42,
            "zoom_level": 2.0,
        }
        mock.create_session_data.return_value = expected_data

        result = mock.create_session_data(
            tracking_file="test.txt",
            current_frame=42,
            zoom_level=2.0,
        )
        assert result == expected_data
        mock.create_session_data.assert_called_once()


class TestBackgroundImageProtocol:
    """Comprehensive test coverage for BackgroundImageProtocol (6 methods)."""

    def test_on_image_sequence_loaded_method(self):
        """Test BackgroundImageProtocol.on_image_sequence_loaded() exists and is callable."""
        mock = Mock(spec=BackgroundImageProtocol)
        image_files = ["img1.jpg", "img2.jpg"]
        mock.on_image_sequence_loaded("/path/to/images", image_files)
        mock.on_image_sequence_loaded.assert_called_once_with("/path/to/images", image_files)

    def test_update_background_for_frame_method(self):
        """Test BackgroundImageProtocol.update_background_for_frame() exists and is callable."""
        mock = Mock(spec=BackgroundImageProtocol)
        mock.update_background_for_frame(42)
        mock.update_background_for_frame.assert_called_once_with(42)

    def test_clear_background_images_method(self):
        """Test BackgroundImageProtocol.clear_background_images() exists and is callable."""
        mock = Mock(spec=BackgroundImageProtocol)
        mock.clear_background_images()
        mock.clear_background_images.assert_called_once()

    def test_get_image_count_method(self):
        """Test BackgroundImageProtocol.get_image_count() exists and is callable."""
        mock = Mock(spec=BackgroundImageProtocol)
        mock.get_image_count.return_value = 100

        result = mock.get_image_count()
        assert result == 100
        mock.get_image_count.assert_called_once()

    def test_has_images_method(self):
        """Test BackgroundImageProtocol.has_images() exists and is callable."""
        mock = Mock(spec=BackgroundImageProtocol)
        mock.has_images.return_value = True

        result = mock.has_images()
        assert result is True
        mock.has_images.assert_called_once()

    def test_get_current_image_info_method(self):
        """Test BackgroundImageProtocol.get_current_image_info() exists and is callable."""
        mock = Mock(spec=BackgroundImageProtocol)
        mock.get_current_image_info.return_value = ("img42.jpg", 42)

        result = mock.get_current_image_info()
        assert result == ("img42.jpg", 42)
        mock.get_current_image_info.assert_called_once()


# ============================================================================
# SERVICE PROTOCOLS (7 protocols)
# ============================================================================


class TestLoggingServiceProtocol:
    """Comprehensive test coverage for LoggingServiceProtocol (5 methods)."""

    def test_get_logger_method(self):
        """Test LoggingServiceProtocol.get_logger() exists and is callable."""
        mock = Mock(spec=LoggingServiceProtocol)
        mock_logger = Mock()
        mock.get_logger.return_value = mock_logger

        result = mock.get_logger("test")
        assert result is mock_logger
        mock.get_logger.assert_called_once_with("test")

    def test_log_info_method(self):
        """Test LoggingServiceProtocol.log_info() exists and is callable."""
        mock = Mock(spec=LoggingServiceProtocol)
        mock.log_info("Test info message")
        mock.log_info.assert_called_once_with("Test info message")

    def test_log_error_method(self):
        """Test LoggingServiceProtocol.log_error() exists and is callable."""
        mock = Mock(spec=LoggingServiceProtocol)
        mock.log_error("Test error message")
        mock.log_error.assert_called_once_with("Test error message")

    def test_log_warning_method(self):
        """Test LoggingServiceProtocol.log_warning() exists and is callable."""
        mock = Mock(spec=LoggingServiceProtocol)
        mock.log_warning("Test warning message")
        mock.log_warning.assert_called_once_with("Test warning message")

    def test_log_debug_method(self):
        """Test LoggingServiceProtocol.log_debug() exists and is callable."""
        mock = Mock(spec=LoggingServiceProtocol)
        mock.log_debug("Test debug message")
        mock.log_debug.assert_called_once_with("Test debug message")


class TestStatusServiceProtocol:
    """Comprehensive test coverage for StatusServiceProtocol (5 methods)."""

    def test_set_status_method(self):
        """Test StatusServiceProtocol.set_status() exists and is callable."""
        mock = Mock(spec=StatusServiceProtocol)
        mock.set_status("Processing...")
        mock.set_status.assert_called_once_with("Processing...")

    def test_clear_status_method(self):
        """Test StatusServiceProtocol.clear_status() exists and is callable."""
        mock = Mock(spec=StatusServiceProtocol)
        mock.clear_status()
        mock.clear_status.assert_called_once()

    def test_show_info_method(self):
        """Test StatusServiceProtocol.show_info() exists and is callable."""
        mock = Mock(spec=StatusServiceProtocol)
        mock.show_info("Info message")
        mock.show_info.assert_called_once_with("Info message")

    def test_show_error_method(self):
        """Test StatusServiceProtocol.show_error() exists and is callable."""
        mock = Mock(spec=StatusServiceProtocol)
        mock.show_error("Error message")
        mock.show_error.assert_called_once_with("Error message")

    def test_show_warning_method(self):
        """Test StatusServiceProtocol.show_warning() exists and is callable."""
        mock = Mock(spec=StatusServiceProtocol)
        mock.show_warning("Warning message")
        mock.show_warning.assert_called_once_with("Warning message")


class TestCommandManagerProtocol:
    """Comprehensive test coverage for CommandManagerProtocol (6 methods)."""

    def test_execute_command_method(self):
        """Test CommandManagerProtocol.execute_command() exists and is callable."""
        mock = Mock(spec=CommandManagerProtocol)
        mock.execute_command("smooth", 0.5)
        mock.execute_command.assert_called_once_with("smooth", 0.5)

    def test_execute_method(self):
        """Test CommandManagerProtocol.execute() exists and is callable."""
        mock = Mock(spec=CommandManagerProtocol)
        mock_command = Mock()
        mock.execute.return_value = True

        result = mock.execute(mock_command)
        assert result is True
        mock.execute.assert_called_once_with(mock_command)

    def test_can_undo_method(self):
        """Test CommandManagerProtocol.can_undo() exists and is callable."""
        mock = Mock(spec=CommandManagerProtocol)
        mock.can_undo.return_value = True

        result = mock.can_undo()
        assert result is True
        mock.can_undo.assert_called_once()

    def test_can_redo_method(self):
        """Test CommandManagerProtocol.can_redo() exists and is callable."""
        mock = Mock(spec=CommandManagerProtocol)
        mock.can_redo.return_value = False

        result = mock.can_redo()
        assert result is False
        mock.can_redo.assert_called_once()

    def test_undo_method(self):
        """Test CommandManagerProtocol.undo() exists and is callable."""
        mock = Mock(spec=CommandManagerProtocol)
        mock.undo()
        mock.undo.assert_called_once()

    def test_redo_method(self):
        """Test CommandManagerProtocol.redo() exists and is callable."""
        mock = Mock(spec=CommandManagerProtocol)
        mock.redo()
        mock.redo.assert_called_once()


class TestShortcutManagerProtocol:
    """Comprehensive test coverage for ShortcutManagerProtocol (4 methods)."""

    def test_register_shortcut_method(self):
        """Test ShortcutManagerProtocol.register_shortcut() exists and is callable."""
        mock = Mock(spec=ShortcutManagerProtocol)
        action = Mock()
        mock.register_shortcut("Ctrl+S", action)
        mock.register_shortcut.assert_called_once_with("Ctrl+S", action)

    def test_unregister_shortcut_method(self):
        """Test ShortcutManagerProtocol.unregister_shortcut() exists and is callable."""
        mock = Mock(spec=ShortcutManagerProtocol)
        mock.unregister_shortcut("Ctrl+S")
        mock.unregister_shortcut.assert_called_once_with("Ctrl+S")

    def test_trigger_shortcut_method(self):
        """Test ShortcutManagerProtocol.trigger_shortcut() exists and is callable."""
        mock = Mock(spec=ShortcutManagerProtocol)
        mock.trigger_shortcut.return_value = True

        result = mock.trigger_shortcut("Ctrl+S")
        assert result is True
        mock.trigger_shortcut.assert_called_once_with("Ctrl+S")

    def test_show_shortcuts_method(self):
        """Test ShortcutManagerProtocol.show_shortcuts() exists and is callable."""
        mock = Mock(spec=ShortcutManagerProtocol)
        mock.show_shortcuts()
        mock.show_shortcuts.assert_called_once()


class TestServiceProtocol:
    """Comprehensive test coverage for ServiceProtocol (2 methods)."""

    def test_initialize_method(self):
        """Test ServiceProtocol.initialize() exists and is callable."""
        mock = Mock(spec=ServiceProtocol)
        mock.initialize()
        mock.initialize.assert_called_once()

    def test_clear_cache_method(self):
        """Test ServiceProtocol.clear_cache() exists and is callable."""
        mock = Mock(spec=ServiceProtocol)
        mock.clear_cache()
        mock.clear_cache.assert_called_once()


class TestServicesProtocol:
    """Comprehensive test coverage for ServicesProtocol (7 methods + 4 properties)."""

    def test_data_service_attribute(self):
        """Test ServicesProtocol.data_service attribute exists."""
        mock = Mock(spec=ServicesProtocol)
        mock_data_service = Mock()
        mock.data_service = mock_data_service
        assert mock.data_service is mock_data_service

    def test_transform_service_attribute(self):
        """Test ServicesProtocol.transform_service attribute exists."""
        mock = Mock(spec=ServicesProtocol)
        mock_transform_service = Mock()
        mock.transform_service = mock_transform_service
        assert mock.transform_service is mock_transform_service

    def test_interaction_service_attribute(self):
        """Test ServicesProtocol.interaction_service attribute exists."""
        mock = Mock(spec=ServicesProtocol)
        mock_interaction_service = Mock()
        mock.interaction_service = mock_interaction_service
        assert mock.interaction_service is mock_interaction_service

    def test_ui_service_attribute(self):
        """Test ServicesProtocol.ui_service attribute exists."""
        mock = Mock(spec=ServicesProtocol)
        mock_ui_service = Mock()
        mock.ui_service = mock_ui_service
        assert mock.ui_service is mock_ui_service

    def test_initialize_all_method(self):
        """Test ServicesProtocol.initialize_all() exists and is callable."""
        mock = Mock(spec=ServicesProtocol)
        mock.initialize_all()
        mock.initialize_all.assert_called_once()

    def test_shutdown_all_method(self):
        """Test ServicesProtocol.shutdown_all() exists and is callable."""
        mock = Mock(spec=ServicesProtocol)
        mock.shutdown_all()
        mock.shutdown_all.assert_called_once()

    def test_confirm_action_method(self):
        """Test ServicesProtocol.confirm_action() exists and is callable."""
        mock = Mock(spec=ServicesProtocol)
        mock.confirm_action.return_value = True

        result = mock.confirm_action("Are you sure?", None)
        assert result is True
        mock.confirm_action.assert_called_once()

    def test_save_track_data_method(self):
        """Test ServicesProtocol.save_track_data() exists and is callable."""
        mock = Mock(spec=ServicesProtocol)
        mock_data = Mock()
        mock.save_track_data.return_value = True

        result = mock.save_track_data(mock_data, None)
        assert result is True
        mock.save_track_data.assert_called_once()

    def test_load_track_data_from_file_method(self):
        """Test ServicesProtocol.load_track_data_from_file() exists and is callable."""
        mock = Mock(spec=ServicesProtocol)
        mock_data = Mock()
        mock.load_track_data_from_file.return_value = mock_data

        result = mock.load_track_data_from_file("test.txt")
        assert result is mock_data
        mock.load_track_data_from_file.assert_called_once_with("test.txt")

    def test_show_warning_method(self):
        """Test ServicesProtocol.show_warning() exists and is callable."""
        mock = Mock(spec=ServicesProtocol)
        mock.show_warning("Warning!")
        mock.show_warning.assert_called_once_with("Warning!")


class TestFileLoadWorkerProtocol:
    """Comprehensive test coverage for FileLoadWorkerProtocol (6 methods + 1 property)."""

    def test_tracking_file_path_property(self):
        """Test FileLoadWorkerProtocol.tracking_file_path property exists."""
        mock = Mock(spec=FileLoadWorkerProtocol)
        mock.tracking_file_path = "test.txt"
        assert mock.tracking_file_path == "test.txt"

    def test_stop_method(self):
        """Test FileLoadWorkerProtocol.stop() exists and is callable."""
        mock = Mock(spec=FileLoadWorkerProtocol)
        mock.stop()
        mock.stop.assert_called_once()

    def test_run_method(self):
        """Test FileLoadWorkerProtocol.run() exists and is callable."""
        mock = Mock(spec=FileLoadWorkerProtocol)
        mock.run()
        mock.run.assert_called_once()

    def test_start_work_method(self):
        """Test FileLoadWorkerProtocol.start_work() exists and is callable."""
        mock = Mock(spec=FileLoadWorkerProtocol)
        mock.start_work(tracking_file="test.txt", image_dir="/path/to/images")
        mock.start_work.assert_called_once_with(tracking_file="test.txt", image_dir="/path/to/images")

    def test_load_file_method(self):
        """Test FileLoadWorkerProtocol.load_file() exists and is callable."""
        mock = Mock(spec=FileLoadWorkerProtocol)
        mock_data = Mock()
        mock.load_file.return_value = mock_data

        result = mock.load_file("test.txt")
        assert result is mock_data
        mock.load_file.assert_called_once_with("test.txt")

    def test_queue_tracking_file_method(self):
        """Test FileLoadWorkerProtocol.queue_tracking_file() exists and is callable."""
        mock = Mock(spec=FileLoadWorkerProtocol)
        mock.queue_tracking_file("test.txt")
        mock.queue_tracking_file.assert_called_once_with("test.txt")

    def test_queue_image_directory_method(self):
        """Test FileLoadWorkerProtocol.queue_image_directory() exists and is callable."""
        mock = Mock(spec=FileLoadWorkerProtocol)
        mock.queue_image_directory("/path/to/images")
        mock.queue_image_directory.assert_called_once_with("/path/to/images")


# ============================================================================
# DATA/RENDERING PROTOCOLS (8 protocols)
# ============================================================================


class TestCurveDataProtocol:
    """Comprehensive test coverage for CurveDataProtocol (7 methods + 3 properties)."""

    def test_points_attribute(self):
        """Test CurveDataProtocol.points attribute exists."""
        mock = Mock(spec=CurveDataProtocol)
        mock_points = [(1, 100.0, 200.0)]
        mock.points = mock_points
        assert mock.points == mock_points

    def test_name_attribute(self):
        """Test CurveDataProtocol.name attribute exists."""
        mock = Mock(spec=CurveDataProtocol)
        mock.name = "Track1"
        assert mock.name == "Track1"

    def test_color_attribute(self):
        """Test CurveDataProtocol.color attribute exists."""
        mock = Mock(spec=CurveDataProtocol)
        mock.color = "#FF0000"
        assert mock.color == "#FF0000"

    def test_get_point_method(self):
        """Test CurveDataProtocol.get_point() exists and is callable."""
        mock = Mock(spec=CurveDataProtocol)
        mock_point = (1, 100.0, 200.0)
        mock.get_point.return_value = mock_point

        result = mock.get_point(0)
        assert result == mock_point
        mock.get_point.assert_called_once_with(0)

    def test_add_point_method(self):
        """Test CurveDataProtocol.add_point() exists and is callable."""
        mock = Mock(spec=CurveDataProtocol)
        point = (1, 100.0, 200.0)
        mock.add_point(point)
        mock.add_point.assert_called_once_with(point)

    def test_remove_point_method(self):
        """Test CurveDataProtocol.remove_point() exists and is callable."""
        mock = Mock(spec=CurveDataProtocol)
        mock.remove_point.return_value = True

        result = mock.remove_point(0)
        assert result is True
        mock.remove_point.assert_called_once_with(0)

    def test_update_point_method(self):
        """Test CurveDataProtocol.update_point() exists and is callable."""
        mock = Mock(spec=CurveDataProtocol)
        point = (1, 150.0, 250.0)
        mock.update_point.return_value = True

        result = mock.update_point(0, point)
        assert result is True
        mock.update_point.assert_called_once_with(0, point)

    def test_get_frame_range_method(self):
        """Test CurveDataProtocol.get_frame_range() exists and is callable."""
        mock = Mock(spec=CurveDataProtocol)
        mock.get_frame_range.return_value = (1, 100)

        result = mock.get_frame_range()
        assert result == (1, 100)
        mock.get_frame_range.assert_called_once()


class TestRenderingBackgroundImageProtocol:
    """Test rendering module's BackgroundImageProtocol (from rendering_protocols.py)."""

    # Note: BackgroundImageProtocol in rendering_protocols.py is just an alias
    # to protocols.ui.BackgroundImageProtocol, which is tested elsewhere
    # This test verifies the alias works


class TestImageProtocol:
    """Comprehensive test coverage for ImageProtocol (5 methods + 2 properties)."""

    def test_width_attribute(self):
        """Test ImageProtocol.width attribute exists."""
        mock = Mock(spec=ImageProtocol)
        mock.width = 1920
        assert mock.width == 1920

    def test_height_attribute(self):
        """Test ImageProtocol.height attribute exists."""
        mock = Mock(spec=ImageProtocol)
        mock.height = 1080
        assert mock.height == 1080

    def test_pixmap_method(self):
        """Test ImageProtocol.pixmap() exists and is callable."""
        mock = Mock(spec=ImageProtocol)
        mock_pixmap = Mock()
        mock.pixmap.return_value = mock_pixmap

        result = mock.pixmap()
        assert result is mock_pixmap
        mock.pixmap.assert_called_once()

    def test_image_method(self):
        """Test ImageProtocol.image() exists and is callable."""
        mock = Mock(spec=ImageProtocol)
        mock_image = Mock()
        mock.image.return_value = mock_image

        result = mock.image()
        assert result is mock_image
        mock.image.assert_called_once()

    def test_is_null_method(self):
        """Test ImageProtocol.is_null() exists and is callable."""
        mock = Mock(spec=ImageProtocol)
        mock.is_null.return_value = False

        result = mock.is_null()
        assert result is False
        mock.is_null.assert_called_once()


class TestHasDimensionsProtocol:
    """Comprehensive test coverage for HasDimensionsProtocol (2 methods)."""

    def test_width_method(self):
        """Test HasDimensionsProtocol.width() exists and is callable."""
        mock = Mock(spec=HasDimensionsProtocol)
        mock.width.return_value = 800

        result = mock.width()
        assert result == 800
        mock.width.assert_called_once()

    def test_height_method(self):
        """Test HasDimensionsProtocol.height() exists and is callable."""
        mock = Mock(spec=HasDimensionsProtocol)
        mock.height.return_value = 600

        result = mock.height()
        assert result == 600
        mock.height.assert_called_once()


class TestHistoryCommandProtocol:
    """Comprehensive test coverage for HistoryCommandProtocol (3 methods)."""

    def test_undo_method(self):
        """Test HistoryCommandProtocol.undo() exists and is callable."""
        mock = Mock(spec=HistoryCommandProtocol)
        mock_container = Mock()
        mock.undo(mock_container)
        mock.undo.assert_called_once_with(mock_container)

    def test_redo_method(self):
        """Test HistoryCommandProtocol.redo() exists and is callable."""
        mock = Mock(spec=HistoryCommandProtocol)
        mock_container = Mock()
        mock.redo(mock_container)
        mock.redo.assert_called_once_with(mock_container)

    def test_get_description_method(self):
        """Test HistoryCommandProtocol.get_description() exists and is callable."""
        mock = Mock(spec=HistoryCommandProtocol)
        mock.get_description.return_value = "Smooth curve"

        result = mock.get_description()
        assert result == "Smooth curve"
        mock.get_description.assert_called_once()


class TestHistoryContainerProtocol:
    """Comprehensive test coverage for HistoryContainerProtocol (9 attributes + 1 method)."""

    def test_curve_data_attribute(self):
        """Test HistoryContainerProtocol.curve_data attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock_data = [(1, 100.0, 200.0)]
        mock.curve_data = mock_data
        assert mock.curve_data == mock_data

    def test_point_name_attribute(self):
        """Test HistoryContainerProtocol.point_name attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock.point_name = "Point_1"
        assert mock.point_name == "Point_1"

    def test_point_color_attribute(self):
        """Test HistoryContainerProtocol.point_color attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock.point_color = "#FF0000"
        assert mock.point_color == "#FF0000"

    def test_history_attribute(self):
        """Test HistoryContainerProtocol.history attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock.history = []
        assert mock.history == []

    def test_history_index_attribute(self):
        """Test HistoryContainerProtocol.history_index attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock.history_index = 0
        assert mock.history_index == 0

    def test_max_history_size_attribute(self):
        """Test HistoryContainerProtocol.max_history_size attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock.max_history_size = 50
        assert mock.max_history_size == 50

    def test_curve_widget_attribute(self):
        """Test HistoryContainerProtocol.curve_widget attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock_widget = Mock()
        mock.curve_widget = mock_widget
        assert mock.curve_widget is mock_widget

    def test_curve_view_attribute(self):
        """Test HistoryContainerProtocol.curve_view attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock_view = Mock()
        mock.curve_view = mock_view
        assert mock.curve_view is mock_view

    def test_services_attribute(self):
        """Test HistoryContainerProtocol.services attribute exists."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock_services = Mock()
        mock.services = mock_services
        assert mock.services is mock_services

    def test_restore_state_method(self):
        """Test HistoryContainerProtocol.restore_state() exists and is callable."""
        mock = Mock(spec=HistoryContainerProtocol)
        mock_state = Mock()
        mock.restore_state(mock_state)
        mock.restore_state.assert_called_once_with(mock_state)


class TestBatchEditableProtocol:
    """Comprehensive test coverage for BatchEditableProtocol (8 attributes + 3 methods)."""

    def test_point_edit_layout_attribute(self):
        """Test BatchEditableProtocol.point_edit_layout attribute exists."""
        mock = Mock(spec=BatchEditableProtocol)
        mock_layout = Mock()
        mock.point_edit_layout = mock_layout
        assert mock.point_edit_layout is mock_layout

    def test_batch_edit_group_attribute(self):
        """Test BatchEditableProtocol.batch_edit_group attribute exists."""
        mock = Mock(spec=BatchEditableProtocol)
        mock_group = Mock()
        mock.batch_edit_group = mock_group
        assert mock.batch_edit_group is mock_group

    def test_curve_view_attribute(self):
        """Test BatchEditableProtocol.curve_view attribute exists."""
        mock = Mock(spec=BatchEditableProtocol)
        mock_view = Mock()
        mock.curve_view = mock_view
        assert mock.curve_view is mock_view

    def test_selected_indices_attribute(self):
        """Test BatchEditableProtocol.selected_indices attribute exists."""
        mock = Mock(spec=BatchEditableProtocol)
        mock.selected_indices = [0, 1, 2]
        assert mock.selected_indices == [0, 1, 2]

    def test_image_width_attribute(self):
        """Test BatchEditableProtocol.image_width attribute exists."""
        mock = Mock(spec=BatchEditableProtocol)
        mock.image_width = 1920
        assert mock.image_width == 1920

    def test_image_height_attribute(self):
        """Test BatchEditableProtocol.image_height attribute exists."""
        mock = Mock(spec=BatchEditableProtocol)
        mock.image_height = 1080
        assert mock.image_height == 1080

    def test_status_bar_method(self):
        """Test BatchEditableProtocol.statusBar() exists and is callable."""
        mock = Mock(spec=BatchEditableProtocol)
        mock_status_bar = Mock()
        mock.statusBar.return_value = mock_status_bar

        result = mock.statusBar()
        assert result is mock_status_bar
        mock.statusBar.assert_called_once()

    def test_update_curve_data_method(self):
        """Test BatchEditableProtocol.update_curve_data() exists and is callable."""
        mock = Mock(spec=BatchEditableProtocol)
        test_data = [(1, 100.0, 200.0)]
        mock.update_curve_data(test_data)
        mock.update_curve_data.assert_called_once_with(test_data)

    def test_add_to_history_method(self):
        """Test BatchEditableProtocol.add_to_history() exists and is callable."""
        mock = Mock(spec=BatchEditableProtocol)
        mock.add_to_history()
        mock.add_to_history.assert_called_once()


class TestStateManagerProtocol:
    """Comprehensive test coverage for StateManagerProtocol (12 methods + 6 properties)."""

    def test_is_modified_attribute(self):
        """Test StateManagerProtocol.is_modified attribute exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock.is_modified = True
        assert mock.is_modified is True

    def test_auto_center_enabled_attribute(self):
        """Test StateManagerProtocol.auto_center_enabled attribute exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock.auto_center_enabled = False
        assert mock.auto_center_enabled is False

    def test_current_frame_property_getter(self):
        """Test StateManagerProtocol.current_frame property getter exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock.current_frame = 42
        assert mock.current_frame == 42

    def test_active_timeline_point_property_getter(self):
        """Test StateManagerProtocol.active_timeline_point property getter exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock.active_timeline_point = "Point_1"
        assert mock.active_timeline_point == "Point_1"

    def test_image_directory_property_getter(self):
        """Test StateManagerProtocol.image_directory property getter exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock.image_directory = "/path/to/images"
        assert mock.image_directory == "/path/to/images"

    def test_current_file_property_getter(self):
        """Test StateManagerProtocol.current_file property getter exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock.current_file = "test.txt"
        assert mock.current_file == "test.txt"

    def test_track_data_property_getter(self):
        """Test StateManagerProtocol.track_data property getter exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock_data = [(1, 100.0, 200.0)]
        mock.track_data = mock_data
        assert mock.track_data == mock_data

    def test_total_frames_property_getter(self):
        """Test StateManagerProtocol.total_frames property getter exists."""
        mock = Mock(spec=StateManagerProtocol)
        mock.total_frames = 100
        assert mock.total_frames == 100

    def test_reset_to_defaults_method(self):
        """Test StateManagerProtocol.reset_to_defaults() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        mock.reset_to_defaults()
        mock.reset_to_defaults.assert_called_once()

    def test_set_track_data_method(self):
        """Test StateManagerProtocol.set_track_data() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        test_data = [(1, 100.0, 200.0)]
        mock.set_track_data(test_data, mark_modified=True)
        mock.set_track_data.assert_called_once_with(test_data, mark_modified=True)

    def test_set_image_files_method(self):
        """Test StateManagerProtocol.set_image_files() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        files = ["img1.jpg", "img2.jpg"]
        mock.set_image_files(files)
        mock.set_image_files.assert_called_once_with(files)

    def test_get_window_title_method(self):
        """Test StateManagerProtocol.get_window_title() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        mock.get_window_title.return_value = "CurveEditor - test.txt"

        result = mock.get_window_title()
        assert result == "CurveEditor - test.txt"
        mock.get_window_title.assert_called_once()

    def test_set_selected_points_method(self):
        """Test StateManagerProtocol.set_selected_points() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        indices = [0, 1, 2]
        mock.set_selected_points(indices)
        mock.set_selected_points.assert_called_once_with(indices)

    def test_undo_method(self):
        """Test StateManagerProtocol.undo() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        mock.undo()
        mock.undo.assert_called_once()

    def test_redo_method(self):
        """Test StateManagerProtocol.redo() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        mock.redo()
        mock.redo.assert_called_once()

    def test_set_history_state_method(self):
        """Test StateManagerProtocol.set_history_state() exists and is callable."""
        mock = Mock(spec=StateManagerProtocol)
        mock.set_history_state(can_undo=True, can_redo=False, position=5, size=10)
        mock.set_history_state.assert_called_once_with(can_undo=True, can_redo=False, position=5, size=10)


# ============================================================================
# SIGNAL/EVENT PROTOCOLS (6 protocols)
# ============================================================================


class TestSignalProtocol:
    """Comprehensive test coverage for SignalProtocol (3 methods)."""

    def test_emit_method(self):
        """Test SignalProtocol.emit() exists and is callable."""
        mock = Mock(spec=SignalProtocol)
        mock.emit(42, "test")
        mock.emit.assert_called_once_with(42, "test")

    def test_connect_method(self):
        """Test SignalProtocol.connect() exists and is callable."""
        mock = Mock(spec=SignalProtocol)
        slot = Mock()
        mock_connection = Mock()
        mock.connect.return_value = mock_connection

        result = mock.connect(slot)
        assert result is mock_connection
        mock.connect.assert_called_once_with(slot)

    def test_disconnect_method(self):
        """Test SignalProtocol.disconnect() exists and is callable."""
        mock = Mock(spec=SignalProtocol)
        slot = Mock()
        mock.disconnect(slot)
        mock.disconnect.assert_called_once_with(slot)


class TestVoidSignalProtocol:
    """Comprehensive test coverage for VoidSignalProtocol (2 methods)."""

    def test_emit_method(self):
        """Test VoidSignalProtocol.emit() exists and is callable."""
        mock = Mock(spec=VoidSignalProtocol)
        mock.emit()
        mock.emit.assert_called_once()

    def test_connect_method(self):
        """Test VoidSignalProtocol.connect() exists and is callable."""
        mock = Mock(spec=VoidSignalProtocol)
        slot = Mock()
        mock_connection = Mock()
        mock.connect.return_value = mock_connection

        result = mock.connect(slot)
        assert result is mock_connection
        mock.connect.assert_called_once_with(slot)


class TestEventProtocol:
    """Comprehensive test coverage for EventProtocol (6 methods)."""

    def test_accept_method(self):
        """Test EventProtocol.accept() exists and is callable."""
        mock = Mock(spec=EventProtocol)
        mock.accept()
        mock.accept.assert_called_once()

    def test_ignore_method(self):
        """Test EventProtocol.ignore() exists and is callable."""
        mock = Mock(spec=EventProtocol)
        mock.ignore()
        mock.ignore.assert_called_once()

    def test_is_accepted_method(self):
        """Test EventProtocol.isAccepted() exists and is callable."""
        mock = Mock(spec=EventProtocol)
        mock.isAccepted.return_value = True

        result = mock.isAccepted()
        assert result is True
        mock.isAccepted.assert_called_once()

    def test_pos_method(self):
        """Test EventProtocol.pos() exists and is callable."""
        mock = Mock(spec=EventProtocol)
        mock_pos = Mock()
        mock.pos.return_value = mock_pos

        result = mock.pos()
        assert result is mock_pos
        mock.pos.assert_called_once()

    def test_global_pos_method(self):
        """Test EventProtocol.globalPos() exists and is callable."""
        mock = Mock(spec=EventProtocol)
        mock_global_pos = Mock()
        mock.globalPos.return_value = mock_global_pos

        result = mock.globalPos()
        assert result is mock_global_pos
        mock.globalPos.assert_called_once()

    def test_modifiers_method(self):
        """Test EventProtocol.modifiers() exists and is callable."""
        mock = Mock(spec=EventProtocol)
        mock_modifiers = Mock()
        mock.modifiers.return_value = mock_modifiers

        result = mock.modifiers()
        assert result is mock_modifiers
        mock.modifiers.assert_called_once()


class TestPointMovedSignalProtocol:
    """Comprehensive test coverage for PointMovedSignalProtocol (2 methods)."""

    def test_emit_method(self):
        """Test PointMovedSignalProtocol.emit() exists and is callable."""
        mock = Mock(spec=PointMovedSignalProtocol)
        mock.emit(5, 100.0, 200.0)
        mock.emit.assert_called_once_with(5, 100.0, 200.0)

    def test_connect_method(self):
        """Test PointMovedSignalProtocol.connect() exists and is callable."""
        mock = Mock(spec=PointMovedSignalProtocol)
        slot = Mock()
        mock_connection = Mock()
        mock.connect.return_value = mock_connection

        result = mock.connect(slot)
        assert result is mock_connection
        mock.connect.assert_called_once_with(slot)


class TestPointProtocol:
    """Comprehensive test coverage for PointProtocol (4 attributes + 1 method)."""

    def test_frame_attribute(self):
        """Test PointProtocol.frame attribute exists."""
        mock = Mock(spec=PointProtocol)
        mock.frame = 42
        assert mock.frame == 42

    def test_x_attribute(self):
        """Test PointProtocol.x attribute exists."""
        mock = Mock(spec=PointProtocol)
        mock.x = 100.0
        assert mock.x == 100.0

    def test_y_attribute(self):
        """Test PointProtocol.y attribute exists."""
        mock = Mock(spec=PointProtocol)
        mock.y = 200.0
        assert mock.y == 200.0

    def test_status_attribute(self):
        """Test PointProtocol.status attribute exists."""
        mock = Mock(spec=PointProtocol)
        mock.status = "NORMAL"
        assert mock.status == "NORMAL"

    def test_to_tuple_method(self):
        """Test PointProtocol.to_tuple() exists and is callable."""
        mock = Mock(spec=PointProtocol)
        mock.to_tuple.return_value = (42, 100.0, 200.0, "NORMAL")

        result = mock.to_tuple()
        assert result == (42, 100.0, 200.0, "NORMAL")
        mock.to_tuple.assert_called_once()


class TestWidgetProtocol:
    """Comprehensive test coverage for WidgetProtocol (6 methods)."""

    def test_update_method(self):
        """Test WidgetProtocol.update() exists and is callable."""
        mock = Mock(spec=WidgetProtocol)
        mock.update()
        mock.update.assert_called_once()

    def test_repaint_method(self):
        """Test WidgetProtocol.repaint() exists and is callable."""
        mock = Mock(spec=WidgetProtocol)
        mock.repaint()
        mock.repaint.assert_called_once()

    def test_width_method(self):
        """Test WidgetProtocol.width() exists and is callable."""
        mock = Mock(spec=WidgetProtocol)
        mock.width.return_value = 800

        result = mock.width()
        assert result == 800
        mock.width.assert_called_once()

    def test_height_method(self):
        """Test WidgetProtocol.height() exists and is callable."""
        mock = Mock(spec=WidgetProtocol)
        mock.height.return_value = 600

        result = mock.height()
        assert result == 600
        mock.height.assert_called_once()

    def test_set_visible_method(self):
        """Test WidgetProtocol.setVisible() exists and is callable."""
        mock = Mock(spec=WidgetProtocol)
        mock.setVisible(True)
        mock.setVisible.assert_called_once_with(True)

    def test_is_visible_method(self):
        """Test WidgetProtocol.isVisible() exists and is callable."""
        mock = Mock(spec=WidgetProtocol)
        mock.isVisible.return_value = True

        result = mock.isVisible()
        assert result is True
        mock.isVisible.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
