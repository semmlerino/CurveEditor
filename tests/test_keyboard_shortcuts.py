#!/usr/bin/env python
"""Tests for keyboard shortcuts in CurveViewWidget."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.point_types import safe_extract_point
from tests.qt_test_helpers import ThreadSafeTestImage
from ui.curve_view_widget import CurveViewWidget


class TestKeyboardShortcuts:
    """Test keyboard shortcuts functionality."""

    @pytest.fixture
    def curve_widget(self, qapp: QApplication) -> CurveViewWidget:
        """Create a CurveViewWidget for testing."""
        widget = CurveViewWidget()
        widget.resize(800, 600)

        # Add test data
        test_data = [
            (1, 100.0, 200.0),
            (2, 300.0, 400.0),
            (3, 500.0, 600.0),
            (4, 700.0, 800.0),
        ]
        widget.set_curve_data(test_data)

        return widget

    def test_c_key_centers_on_selected(self, curve_widget: CurveViewWidget):
        """Test that C key centers view on selected points."""
        # Select some points
        curve_widget.selected_indices = {1, 2}

        # Store original offsets
        original_offset_x = curve_widget.pan_offset_x
        original_offset_y = curve_widget.pan_offset_y

        # Press C key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify offsets changed (centering occurred)
        assert curve_widget.pan_offset_x != original_offset_x or curve_widget.pan_offset_y != original_offset_y

    def test_c_key_no_action_without_selection(self, curve_widget: CurveViewWidget):
        """Test that C key does nothing when no points are selected."""
        # No selection
        curve_widget.selected_indices = set()

        # Store original offsets
        original_offset_x = curve_widget.pan_offset_x
        original_offset_y = curve_widget.pan_offset_y

        # Press C key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify offsets didn't change
        assert curve_widget.pan_offset_x == original_offset_x
        assert curve_widget.pan_offset_y == original_offset_y

    def test_f_key_fits_background_image(self, curve_widget: CurveViewWidget):
        """Test that F key fits background image to view."""
        # Create a background image
        pixmap = ThreadSafeTestImage(1920, 1080)
        curve_widget.background_image = pixmap
        curve_widget.image_width = 1920
        curve_widget.image_height = 1080
        curve_widget.show_background = True

        # Store original zoom
        original_zoom = curve_widget.zoom_factor

        # Press F key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify zoom changed to fit image
        assert curve_widget.zoom_factor != original_zoom
        # The zoom factor should have been adjusted to fit the image
        # (actual value depends on widget and image dimensions)

    def test_f_key_no_action_without_background(self, curve_widget: CurveViewWidget):
        """Test that F key does nothing when no background image is set."""
        # No background image
        curve_widget.background_image = None

        # Store original values
        original_zoom = curve_widget.zoom_factor
        original_offset_x = curve_widget.pan_offset_x
        original_offset_y = curve_widget.pan_offset_y

        # Press F key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify nothing changed
        assert curve_widget.zoom_factor == original_zoom
        assert curve_widget.pan_offset_x == original_offset_x
        assert curve_widget.pan_offset_y == original_offset_y

    def test_delete_key_removes_selected(self, curve_widget: CurveViewWidget):
        """Test that Delete key removes selected points."""
        # Select points
        curve_widget.selected_indices = {1, 2}
        original_count = len(curve_widget.curve_data)

        # Press Delete key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify points were deleted
        assert len(curve_widget.curve_data) == original_count - 2
        assert len(curve_widget.selected_indices) == 0

    def test_escape_key_clears_selection(self, curve_widget: CurveViewWidget):
        """Test that Escape key clears selection."""
        # Select points
        curve_widget.selected_indices = {0, 1, 2}

        # Press Escape key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify selection was cleared
        assert len(curve_widget.selected_indices) == 0

    def test_ctrl_a_selects_all(self, curve_widget: CurveViewWidget):
        """Test that Ctrl+A selects all points."""
        # Clear selection first
        curve_widget.selected_indices = set()

        # Press Ctrl+A
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        curve_widget.keyPressEvent(event)

        # Verify all points are selected
        assert len(curve_widget.selected_indices) == len(curve_widget.curve_data)

    def test_numpad_keys_nudge_selected(self, curve_widget: CurveViewWidget):
        """Test that numpad keys nudge selected points."""
        # Select a point
        curve_widget.selected_indices = {0}

        # Get original position
        _, original_x, original_y, _ = safe_extract_point(curve_widget.curve_data[0])

        # Press Numpad 6 (right)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_6, Qt.KeyboardModifier.KeypadModifier)
        curve_widget.keyPressEvent(event)

        # Verify X position changed
        _, new_x, new_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert new_x > original_x
        assert new_y == original_y

        # Press Numpad 8 (up)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_8, Qt.KeyboardModifier.KeypadModifier)
        curve_widget.keyPressEvent(event)

        # Verify Y position changed
        _, final_x, final_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert final_x == new_x
        assert final_y < new_y  # Y decreases when going up

    def test_arrow_keys_pass_through_for_frame_navigation(self, curve_widget: CurveViewWidget):
        """Test that arrow keys are passed through to parent for frame navigation."""
        # Select a point to confirm they don't get nudged
        curve_widget.selected_indices = {0}

        # Get original position
        _, original_x, original_y, _ = safe_extract_point(curve_widget.curve_data[0])

        # Press Right arrow - should NOT nudge the point
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify point position did NOT change (arrow keys don't nudge anymore)
        _, new_x, new_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert new_x == original_x
        assert new_y == original_y
