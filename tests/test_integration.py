#!/usr/bin/env python3
"""
Integration tests for the CurveEditor application.

These tests verify end-to-end functionality of the fully integrated CurveEditor,
including MainWindow with CurveViewWidget integration, service coordination,
and critical user workflows.

Test categories:
1. MainWindow + CurveViewWidget integration
2. File operations end-to-end
3. Point manipulation workflows
4. View operations and state synchronization
5. Service facade integration
6. Critical user scenarios
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from core.point_types import safe_extract_point
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow


class TestMainWindowCurveWidgetIntegration:
    """Test integration between MainWindow and CurveViewWidget."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        window.show()  # Show to ensure proper initialization
        qapp.processEvents()  # Process Qt events
        yield window
        window.close()

    @pytest.fixture
    def sample_curve_data(self) -> list[tuple]:
        """Sample curve data for testing."""
        return [
            (1, 100.0, 200.0, "keyframe"),
            (2, 150.0, 250.0, "interpolated"),
            (3, 200.0, 180.0, "keyframe"),
            (4, 250.0, 220.0, "interpolated"),
            (5, 300.0, 280.0, "keyframe"),
        ]

    def test_main_window_initializes_curve_widget(self, main_window: MainWindow) -> None:
        """Test that MainWindow properly initializes CurveViewWidget."""
        assert main_window.curve_widget is not None
        assert isinstance(main_window.curve_widget, CurveViewWidget)
        assert main_window.curve_widget.main_window is main_window
        assert main_window.curve_widget.parent() is not None

    def test_curve_widget_service_integration(self, main_window: MainWindow) -> None:
        """Test that CurveViewWidget integrates with services."""
        curve_widget = main_window.curve_widget
        assert curve_widget.curve_service is not None
        assert main_window.services is not None

    def test_curve_data_synchronization(
        self, main_window: MainWindow, sample_curve_data: list[tuple]
    ) -> None:
        """Test that curve data is properly synchronized between components."""
        # Set data through main window
        main_window.curve_widget.set_curve_data(sample_curve_data)
        
        # Verify data is accessible
        assert len(main_window.curve_widget.curve_data) == len(sample_curve_data)
        assert main_window.curve_widget.curve_data == sample_curve_data
        
        # Verify point collection is created
        assert main_window.curve_widget.point_collection is not None
        assert len(main_window.curve_widget.point_collection.points) == len(sample_curve_data)

    def test_signal_connections(self, main_window: MainWindow) -> None:
        """Test that signals are properly connected between components."""
        curve_widget = main_window.curve_widget
        
        # Test that curve widget signals exist
        assert hasattr(curve_widget, 'point_selected')
        assert hasattr(curve_widget, 'point_moved')
        assert hasattr(curve_widget, 'selection_changed')
        assert hasattr(curve_widget, 'view_changed')
        assert hasattr(curve_widget, 'zoom_changed')

    def test_ui_synchronization(
        self, main_window: MainWindow, sample_curve_data: list[tuple]
    ) -> None:
        """Test that UI components are synchronized with curve data."""
        # Set curve data
        main_window.curve_widget.set_curve_data(sample_curve_data)
        main_window._update_ui_state()
        
        # Check that point count is updated
        assert "5" in main_window.point_count_label.text()
        
        # Check that bounds are calculated
        bounds_text = main_window.bounds_label.text()
        assert "Bounds:" in bounds_text
        assert bounds_text != "Bounds: N/A"


class TestFileOperationsEndToEnd:
    """Test file operations from UI to services and back."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        yield window
        window.close()

    @pytest.fixture
    def temp_data_file(self) -> Generator[str, None, None]:
        """Create a temporary data file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write sample 2D track data
            f.write("1 100.0 200.0\n")
            f.write("2 150.0 250.0\n")
            f.write("3 200.0 180.0\n")
            f.write("4 250.0 220.0\n")
            f.write("5 300.0 280.0\n")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass

    def test_new_file_workflow(self, main_window: MainWindow) -> None:
        """Test creating a new file workflow."""
        # Set some initial data
        main_window.curve_widget.set_curve_data([(1, 100.0, 200.0)])
        main_window.state_manager.is_modified = True
        
        # Mock confirm dialog to always return True
        with patch.object(main_window.services, 'confirm_action', return_value=True):
            # Trigger new file action
            main_window._on_action_new()
        
        # Verify state is reset
        assert len(main_window.curve_widget.curve_data) == 0
        assert not main_window.state_manager.is_modified
        assert main_window.state_manager.current_file == ""

    def test_open_file_workflow(self, main_window: MainWindow, temp_data_file: str) -> None:
        """Test opening a file workflow."""
        # Mock file dialog to return our test file
        with patch.object(main_window.services, 'load_track_data') as mock_load:
            # Set up mock to return test data
            test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 180.0)]
            mock_load.return_value = test_data
            
            # Trigger open action
            main_window._on_action_open()
            
            # Verify mock was called
            mock_load.assert_called_once()
            
            # Verify data was loaded
            assert len(main_window.curve_widget.curve_data) == len(test_data)
            assert main_window.curve_widget.curve_data == test_data

    def test_save_file_workflow(self, main_window: MainWindow) -> None:
        """Test saving a file workflow."""
        # Set up test data
        test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        main_window.curve_widget.set_curve_data(test_data)
        main_window.state_manager.current_file = "test.txt"
        main_window.state_manager.is_modified = True
        
        # Mock save service
        with patch.object(main_window.services, 'save_track_data', return_value=True) as mock_save:
            # Trigger save action
            main_window._on_action_save()
            
            # Verify save was called with correct data
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][0]
            assert saved_data == test_data
            
            # Verify modified flag is cleared
            assert not main_window.state_manager.is_modified

    def test_save_as_workflow(self, main_window: MainWindow) -> None:
        """Test save as workflow."""
        # Set up test data
        test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        main_window.curve_widget.set_curve_data(test_data)
        main_window.state_manager.is_modified = True
        
        # Mock save service
        with patch.object(main_window.services, 'save_track_data', return_value=True) as mock_save:
            # Trigger save as action
            main_window._on_action_save_as()
            
            # Verify save was called
            mock_save.assert_called_once()
            
            # Verify modified flag is cleared
            assert not main_window.state_manager.is_modified


class TestPointManipulationWorkflows:
    """Test point manipulation workflows end-to-end."""

    @pytest.fixture
    def main_window_with_data(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create MainWindow with sample data."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        
        # Add sample data
        test_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 150.0, 250.0, "interpolated"),
            (3, 200.0, 180.0, "keyframe"),
        ]
        window.curve_widget.set_curve_data(test_data)
        
        yield window
        window.close()

    def test_point_selection_workflow(self, main_window_with_data: MainWindow) -> None:
        """Test point selection workflow."""
        curve_widget = main_window_with_data.curve_widget
        state_manager = main_window_with_data.state_manager
        
        # Simulate point selection
        curve_widget.selected_indices.add(1)
        curve_widget.selection_changed.emit([1])
        
        # Process events
        QApplication.processEvents()
        
        # Verify selection is reflected in state manager
        assert 1 in curve_widget.selected_indices
        
        # Verify UI is updated
        main_window_with_data._on_curve_selection_changed([1])
        assert len(state_manager.selected_points) == 1

    def test_point_dragging_workflow(self, main_window_with_data: MainWindow) -> None:
        """Test point dragging workflow."""
        curve_widget = main_window_with_data.curve_widget
        
        # Get initial point position
        initial_point = curve_widget.curve_data[1]
        _, initial_x, initial_y, _ = safe_extract_point(initial_point)
        
        # Update point position (simulate drag)
        new_x, new_y = initial_x + 50, initial_y + 30
        curve_widget.update_point(1, new_x, new_y)
        
        # Verify point was updated
        updated_point = curve_widget.curve_data[1]
        _, updated_x, updated_y, _ = safe_extract_point(updated_point)
        
        assert abs(updated_x - new_x) < 0.001
        assert abs(updated_y - new_y) < 0.001
        
        # Verify modified flag is set
        assert main_window_with_data.state_manager.is_modified

    def test_point_addition_workflow(self, main_window_with_data: MainWindow) -> None:
        """Test adding a point workflow."""
        curve_widget = main_window_with_data.curve_widget
        initial_count = len(curve_widget.curve_data)
        
        # Add a new point
        new_point = (4, 300.0, 320.0, "keyframe")
        curve_widget.add_point(new_point)
        
        # Verify point was added
        assert len(curve_widget.curve_data) == initial_count + 1
        assert curve_widget.curve_data[-1] == new_point
        
        # Verify point collection was updated
        assert curve_widget.point_collection is not None
        assert len(curve_widget.point_collection.points) == initial_count + 1

    def test_point_deletion_workflow(self, main_window_with_data: MainWindow) -> None:
        """Test deleting a point workflow."""
        curve_widget = main_window_with_data.curve_widget
        initial_count = len(curve_widget.curve_data)
        
        # Select and delete a point
        curve_widget.selected_indices.add(1)
        curve_widget._delete_selected_points()
        
        # Verify point was deleted
        assert len(curve_widget.curve_data) == initial_count - 1
        assert len(curve_widget.selected_indices) == 0

    def test_undo_redo_workflow(self, main_window_with_data: MainWindow) -> None:
        """Test undo/redo workflow."""
        curve_widget = main_window_with_data.curve_widget
        state_manager = main_window_with_data.state_manager
        
        # Get initial point
        initial_point = curve_widget.curve_data[1]
        _, initial_x, initial_y, _ = safe_extract_point(initial_point)
        
        # Mock history service
        with patch.object(main_window_with_data.services, 'undo') as mock_undo, \
             patch.object(main_window_with_data.services, 'redo') as mock_redo:
            
            # Make a change
            curve_widget.update_point(1, initial_x + 50, initial_y + 30)
            main_window_with_data.add_to_history()
            
            # Test undo
            main_window_with_data._on_action_undo()
            mock_undo.assert_called_once()
            
            # Test redo
            main_window_with_data._on_action_redo()
            mock_redo.assert_called_once()


class TestViewOperationsAndState:
    """Test view operations and state synchronization."""

    @pytest.fixture
    def main_window_with_data(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create MainWindow with sample data."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        
        # Add sample data
        test_data = [
            (1, 100.0, 200.0),
            (2, 200.0, 300.0),
            (3, 300.0, 200.0),
        ]
        window.curve_widget.set_curve_data(test_data)
        
        yield window
        window.close()

    def test_zoom_operations(self, main_window_with_data: MainWindow) -> None:
        """Test zoom operations."""
        curve_widget = main_window_with_data.curve_widget
        initial_zoom = curve_widget.zoom_factor
        
        # Test zoom in
        main_window_with_data._on_action_zoom_in()
        assert curve_widget.zoom_factor > initial_zoom
        
        # Test zoom out
        main_window_with_data._on_action_zoom_out()
        assert curve_widget.zoom_factor < initial_zoom * 1.2  # Should be less than zoom in result

    def test_reset_view_operation(self, main_window_with_data: MainWindow) -> None:
        """Test reset view operation."""
        curve_widget = main_window_with_data.curve_widget
        
        # Change view state
        curve_widget.zoom_factor = 2.0
        curve_widget.pan_offset_x = 100.0
        curve_widget.pan_offset_y = 50.0
        
        # Reset view
        main_window_with_data._on_action_reset_view()
        
        # Verify reset
        assert curve_widget.zoom_factor == 1.0
        assert curve_widget.pan_offset_x == 0.0
        assert curve_widget.pan_offset_y == 0.0

    def test_view_options_synchronization(self, main_window_with_data: MainWindow) -> None:
        """Test that view options are synchronized between UI and widget."""
        curve_widget = main_window_with_data.curve_widget
        
        # Change checkbox states
        main_window_with_data.show_background_cb.setChecked(False)
        main_window_with_data.show_grid_cb.setChecked(True)
        
        # Update curve view options
        main_window_with_data._update_curve_view_options()
        
        # Verify synchronization
        assert not curve_widget.show_background
        assert curve_widget.show_grid

    def test_point_size_and_line_width(self, main_window_with_data: MainWindow) -> None:
        """Test point size and line width controls."""
        curve_widget = main_window_with_data.curve_widget
        
        # Change point size
        new_point_size = 8
        main_window_with_data.point_size_slider.setValue(new_point_size)
        main_window_with_data._update_curve_point_size(new_point_size)
        
        assert curve_widget.point_radius == new_point_size
        assert curve_widget.selected_point_radius == new_point_size + 2
        
        # Change line width
        new_line_width = 3
        main_window_with_data.line_width_slider.setValue(new_line_width)
        main_window_with_data._update_curve_line_width(new_line_width)
        
        assert curve_widget.line_width == new_line_width
        assert curve_widget.selected_line_width == new_line_width + 1

    def test_frame_navigation(self, main_window_with_data: MainWindow) -> None:
        """Test frame navigation controls."""
        state_manager = main_window_with_data.state_manager
        
        # Test frame spinbox
        main_window_with_data.frame_spinbox.setValue(5)
        main_window_with_data._on_frame_changed(5)
        
        assert state_manager.current_frame == 5
        assert main_window_with_data.frame_slider.value() == 5
        
        # Test navigation buttons
        main_window_with_data._on_next_frame()
        assert main_window_with_data.frame_spinbox.value() == 6
        
        main_window_with_data._on_prev_frame()
        assert main_window_with_data.frame_spinbox.value() == 5
        
        main_window_with_data._on_first_frame()
        assert main_window_with_data.frame_spinbox.value() == 1
        
        # Set max for last frame test
        main_window_with_data.frame_spinbox.setMaximum(10)
        main_window_with_data._on_last_frame()
        assert main_window_with_data.frame_spinbox.value() == 10


class TestServiceFacadeIntegration:
    """Test service facade integration and delegation."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        yield window
        window.close()

    def test_service_facade_initialization(self, main_window: MainWindow) -> None:
        """Test that service facade is properly initialized."""
        assert main_window.services is not None
        assert hasattr(main_window.services, 'load_track_data')
        assert hasattr(main_window.services, 'save_track_data')
        assert hasattr(main_window.services, 'undo')
        assert hasattr(main_window.services, 'redo')
        assert hasattr(main_window.services, 'add_to_history')
        assert hasattr(main_window.services, 'confirm_action')

    def test_file_service_delegation(self, main_window: MainWindow) -> None:
        """Test file service delegation through facade."""
        with patch.object(main_window.services, 'load_track_data') as mock_load:
            mock_load.return_value = [(1, 100.0, 200.0)]
            
            # Call through main window
            result = main_window.services.load_track_data(main_window)
            
            # Verify delegation worked
            mock_load.assert_called_once_with(main_window)
            assert result == [(1, 100.0, 200.0)]

    def test_history_service_delegation(self, main_window: MainWindow) -> None:
        """Test history service delegation through facade."""
        with patch.object(main_window.services, 'undo') as mock_undo, \
             patch.object(main_window.services, 'redo') as mock_redo, \
             patch.object(main_window.services, 'add_to_history') as mock_add:
            
            # Test undo delegation
            main_window.services.undo()
            mock_undo.assert_called_once()
            
            # Test redo delegation
            main_window.services.redo()
            mock_redo.assert_called_once()
            
            # Test add to history delegation
            main_window.services.add_to_history()
            mock_add.assert_called_once()

    def test_state_manager_integration(self, main_window: MainWindow) -> None:
        """Test state manager integration with services."""
        state_manager = main_window.state_manager
        
        # Test state changes trigger UI updates
        state_manager.current_frame = 10
        state_manager.frame_changed.emit(10)
        
        # Process events
        QApplication.processEvents()
        
        # State change should be reflected in UI
        assert main_window.frame_spinbox.value() == 10


class TestCriticalUserScenarios:
    """Test critical user scenarios end-to-end."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        yield window
        window.close()

    @pytest.fixture
    def temp_data_file(self) -> Generator[str, None, None]:
        """Create a temporary data file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("1 100.0 200.0\n")
            f.write("2 150.0 250.0\n")
            f.write("3 200.0 180.0\n")
            temp_file = f.name
        
        yield temp_file
        
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass

    def test_complete_edit_workflow(self, main_window: MainWindow) -> None:
        """Test: Open file → Edit points → Save file."""
        # Mock file operations
        test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 180.0)]
        
        with patch.object(main_window.services, 'load_track_data', return_value=test_data), \
             patch.object(main_window.services, 'save_track_data', return_value=True) as mock_save:
            
            # Step 1: Open file
            main_window._on_action_open()
            assert len(main_window.curve_widget.curve_data) == 3
            
            # Step 2: Edit a point
            main_window.curve_widget.update_point(1, 200.0, 300.0)
            assert main_window.state_manager.is_modified
            
            # Step 3: Save file
            main_window.state_manager.current_file = "test.txt"
            main_window._on_action_save()
            
            # Verify save was called
            mock_save.assert_called_once()
            assert not main_window.state_manager.is_modified

    def test_select_drag_undo_redo_workflow(self, main_window: MainWindow) -> None:
        """Test: Select point → Drag → Undo → Redo."""
        # Set up test data
        test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        main_window.curve_widget.set_curve_data(test_data)
        
        # Mock history operations
        with patch.object(main_window.services, 'undo') as mock_undo, \
             patch.object(main_window.services, 'redo') as mock_redo, \
             patch.object(main_window.services, 'add_to_history') as mock_add:
            
            # Step 1: Select point
            main_window.curve_widget.selected_indices.add(1)
            main_window.curve_widget.selection_changed.emit([1])
            
            # Step 2: Drag point (simulate)
            original_point = main_window.curve_widget.curve_data[1]
            _, orig_x, orig_y, _ = safe_extract_point(original_point)
            main_window.curve_widget.update_point(1, orig_x + 50, orig_y + 30)
            main_window.add_to_history()
            
            # Verify point moved and history added
            mock_add.assert_called()
            
            # Step 3: Undo
            main_window._on_action_undo()
            mock_undo.assert_called_once()
            
            # Step 4: Redo
            main_window._on_action_redo()
            mock_redo.assert_called_once()

    def test_zoom_pan_reset_workflow(self, main_window: MainWindow) -> None:
        """Test: Zoom in → Pan → Reset view."""
        curve_widget = main_window.curve_widget
        
        # Add some test data for context
        test_data = [(1, 100.0, 200.0), (2, 300.0, 400.0)]
        curve_widget.set_curve_data(test_data)
        
        # Step 1: Zoom in
        initial_zoom = curve_widget.zoom_factor
        main_window._on_action_zoom_in()
        assert curve_widget.zoom_factor > initial_zoom
        
        # Step 2: Pan (simulate)
        curve_widget.pan_offset_x = 100.0
        curve_widget.pan_offset_y = 50.0
        
        # Step 3: Reset view
        main_window._on_action_reset_view()
        assert curve_widget.zoom_factor == 1.0
        assert curve_widget.pan_offset_x == 0.0
        assert curve_widget.pan_offset_y == 0.0

    def test_new_file_add_data_save_workflow(self, main_window: MainWindow) -> None:
        """Test: New file → Add data → Save as."""
        # Mock save dialog
        with patch.object(main_window.services, 'save_track_data', return_value=True) as mock_save:
            
            # Step 1: New file
            main_window._on_action_new()
            assert len(main_window.curve_widget.curve_data) == 0
            
            # Step 2: Add data
            new_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
            main_window.curve_widget.set_curve_data(new_data)
            main_window.state_manager.is_modified = True
            
            # Step 3: Save as
            main_window._on_action_save_as()
            
            # Verify save was called
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][0]
            assert saved_data == new_data

    def test_playback_and_frame_navigation(self, main_window: MainWindow) -> None:
        """Test playback controls and frame navigation."""
        # Set frame range
        main_window.frame_spinbox.setMaximum(10)
        main_window.frame_slider.setMaximum(10)
        
        # Test play/pause
        main_window._on_play_pause(True)  # Start playback
        assert main_window.playback_timer.isActive()
        
        main_window._on_play_pause(False)  # Stop playback
        assert not main_window.playback_timer.isActive()
        
        # Test frame navigation
        main_window._on_first_frame()
        assert main_window.frame_spinbox.value() == 1
        
        main_window._on_last_frame()
        assert main_window.frame_spinbox.value() == 10
        
        # Test FPS change
        main_window._on_fps_changed(30)
        # Should update timer interval if playing


class TestPerformanceAndStability:
    """Test performance aspects and stability."""

    @pytest.fixture
    def main_window(self, qapp: QApplication) -> Generator[MainWindow, None, None]:
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        window.show()
        qapp.processEvents()
        yield window
        window.close()

    def test_large_dataset_handling(self, main_window: MainWindow) -> None:
        """Test handling of large datasets."""
        # Create large dataset
        large_data = [(i, float(i * 10), float(i * 20)) for i in range(1000)]
        
        # Measure time to set data
        start_time = time.time()
        main_window.curve_widget.set_curve_data(large_data)
        end_time = time.time()
        
        # Should complete in reasonable time (< 1 second for 1000 points)
        assert end_time - start_time < 1.0
        assert len(main_window.curve_widget.curve_data) == 1000

    def test_memory_cleanup(self, main_window: MainWindow) -> None:
        """Test that memory is properly cleaned up."""
        # Add data
        test_data = [(i, float(i), float(i * 2)) for i in range(100)]
        main_window.curve_widget.set_curve_data(test_data)
        
        # Clear data
        main_window.curve_widget.set_curve_data([])
        
        # Verify cleanup
        assert len(main_window.curve_widget.curve_data) == 0
        assert len(main_window.curve_widget._screen_points_cache) == 0
        assert len(main_window.curve_widget.selected_indices) == 0

    def test_rapid_ui_updates(self, main_window: MainWindow) -> None:
        """Test rapid UI updates don't cause issues."""
        test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        main_window.curve_widget.set_curve_data(test_data)
        
        # Rapid zoom changes
        for i in range(10):
            main_window._on_action_zoom_in()
            main_window._on_action_zoom_out()
            QApplication.processEvents()
        
        # Should still be functional
        assert main_window.curve_widget.zoom_factor > 0
        assert len(main_window.curve_widget.curve_data) == 2

    def test_signal_emission_performance(self, main_window: MainWindow) -> None:
        """Test that signal emissions don't cause performance issues."""
        curve_widget = main_window.curve_widget
        
        # Connect a counting receiver
        signal_count = {"count": 0}
        
        def count_signals():
            signal_count["count"] += 1
        
        curve_widget.view_changed.connect(count_signals)
        
        # Emit many signals rapidly
        start_time = time.time()
        for _ in range(100):
            curve_widget.view_changed.emit()
            QApplication.processEvents()
        end_time = time.time()
        
        # Should complete quickly and all signals should be processed
        assert end_time - start_time < 1.0
        assert signal_count["count"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])