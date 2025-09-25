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
        curve_widget._curve_store.select(1)
        curve_widget._curve_store.select(2, add_to_selection=True)

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
        curve_widget._curve_store.clear_selection()

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
        curve_widget._curve_store.select(1)
        curve_widget._curve_store.select(2, add_to_selection=True)
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
        curve_widget._curve_store.select(0)
        curve_widget._curve_store.select(1, add_to_selection=True)
        curve_widget._curve_store.select(2, add_to_selection=True)

        # Press Escape key
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify selection was cleared
        assert len(curve_widget.selected_indices) == 0

    def test_ctrl_a_selects_all(self, curve_widget: CurveViewWidget):
        """Test that Ctrl+A selects all points."""
        # Clear selection first
        curve_widget._curve_store.clear_selection()

        # Press Ctrl+A
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        curve_widget.keyPressEvent(event)

        # Verify all points are selected
        assert len(curve_widget.selected_indices) == len(curve_widget.curve_data)

    def test_numpad_keys_nudge_selected(self, curve_widget: CurveViewWidget):
        """Test that numpad keys nudge selected points."""
        # Select a point
        curve_widget._curve_store.select(0)

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

    def test_regular_number_keys_nudge_selected(self, curve_widget: CurveViewWidget):
        """Test that regular number keys (non-numpad) also nudge selected points."""
        # Select a point
        curve_widget._curve_store.select(0)

        # Get original position
        _, original_x, original_y, _ = safe_extract_point(curve_widget.curve_data[0])

        # Press regular 6 (right) - without KeypadModifier
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_6, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify X position changed
        _, new_x, new_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert new_x > original_x, "Regular key 6 should nudge right"
        assert new_y == original_y

        # Press regular 8 (up) - without KeypadModifier
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_8, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify Y position changed
        _, final_x, final_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert final_x == new_x
        assert final_y < new_y, "Regular key 8 should nudge up"

        # Test with modifiers - regular 4 with Shift (10x left)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_4, Qt.KeyboardModifier.ShiftModifier)
        curve_widget.keyPressEvent(event)

        _, shifted_x, shifted_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert shifted_x == final_x - 10.0, "Shift+4 should nudge left by 10"
        assert shifted_y == final_y

        # Test with Ctrl modifier - regular 2 with Ctrl (0.1x down)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
        curve_widget.keyPressEvent(event)

        _, ctrl_x, ctrl_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert ctrl_x == shifted_x
        assert ctrl_y == pytest.approx(shifted_y + 0.1, rel=1e-5), "Ctrl+2 should nudge down by 0.1"

    def test_arrow_keys_pass_through_for_frame_navigation(self, curve_widget: CurveViewWidget):
        # Select a point to confirm they don't get nudged
        curve_widget._curve_store.select(0)

        # Get original position
        _, original_x, original_y, _ = safe_extract_point(curve_widget.curve_data[0])

        # Press Right arrow - should NOT nudge the point
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify point position did NOT change (arrow keys don't nudge anymore)
        _, new_x, new_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert new_x == original_x
        assert new_y == original_y

    def test_nudge_current_frame_point_without_selection(self, curve_widget: CurveViewWidget, monkeypatch):
        """Test that nudging works on current frame point when no points are selected."""
        # Mock the main_window to provide current frame
        from unittest.mock import MagicMock

        mock_main_window = MagicMock()
        mock_main_window.current_frame = 2  # Frame 2 (index 1 in 0-based)
        curve_widget.main_window = mock_main_window

        # Clear any selection
        curve_widget.clear_selection()
        assert len(curve_widget.selected_indices) == 0

        # Get original position of point at frame 2 (index 1)
        _, original_x, original_y, _ = safe_extract_point(curve_widget.curve_data[1])

        # Press key 6 (right) - should nudge current frame point
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_6, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify the point at frame 2 moved right
        _, new_x, new_y, _ = safe_extract_point(curve_widget.curve_data[1])
        assert new_x == original_x + 1.0  # Default nudge amount
        assert new_y == original_y

    def test_nudge_prefers_selected_over_current_frame(self, curve_widget: CurveViewWidget):
        """Test that selected points take precedence over current frame."""
        from unittest.mock import MagicMock

        mock_main_window = MagicMock()
        mock_main_window.current_frame = 2  # Frame 2 (index 1)
        curve_widget.main_window = mock_main_window

        # Select point at index 0 (not the current frame)
        curve_widget._curve_store.select(0)

        # Get original positions
        _, sel_orig_x, sel_orig_y, _ = safe_extract_point(curve_widget.curve_data[0])
        _, curr_orig_x, curr_orig_y, _ = safe_extract_point(curve_widget.curve_data[1])

        # Press key 8 (up) - should nudge selected point, not current frame
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_8, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Selected point should move
        _, sel_new_x, sel_new_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert sel_new_x == sel_orig_x
        assert sel_new_y < sel_orig_y  # Moved up

        # Current frame point should NOT move
        _, curr_new_x, curr_new_y, _ = safe_extract_point(curve_widget.curve_data[1])
        assert curr_new_x == curr_orig_x
        assert curr_new_y == curr_orig_y

    def test_nudge_with_modifiers_on_current_frame(self, curve_widget: CurveViewWidget):
        """Test that modifiers work when nudging current frame point."""
        from unittest.mock import MagicMock

        mock_main_window = MagicMock()
        mock_main_window.current_frame = 1  # Frame 1 (index 0)
        curve_widget.main_window = mock_main_window

        # Clear selection
        curve_widget.clear_selection()

        # Get original position
        _, original_x, original_y, _ = safe_extract_point(curve_widget.curve_data[0])

        # Test Shift modifier (10x)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_4, Qt.KeyboardModifier.ShiftModifier)
        curve_widget.keyPressEvent(event)

        _, new_x, new_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert new_x == original_x - 10.0  # 10x left
        assert new_y == original_y

        # Test Ctrl modifier (0.1x)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
        curve_widget.keyPressEvent(event)

        _, final_x, final_y, _ = safe_extract_point(curve_widget.curve_data[0])
        assert final_x == new_x
        assert final_y == pytest.approx(new_y + 0.1, rel=1e-5)  # 0.1x down

    def test_no_nudge_when_no_selection_and_no_current_frame(self, curve_widget: CurveViewWidget):
        """Test that nudging does nothing when no selection and no current frame."""
        # No main_window means no current frame
        curve_widget.main_window = None

        # Clear selection
        curve_widget.clear_selection()

        # Get original positions
        original_positions = [safe_extract_point(p) for p in curve_widget.curve_data]

        # Try to nudge - should do nothing
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_6, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify nothing moved
        new_positions = [safe_extract_point(p) for p in curve_widget.curve_data]
        for orig, new in zip(original_positions, new_positions):
            assert orig == new

    def test_no_nudge_when_current_frame_out_of_range(self, curve_widget: CurveViewWidget):
        """Test that nudging handles out-of-range current frame gracefully."""
        from unittest.mock import MagicMock

        mock_main_window = MagicMock()
        mock_main_window.current_frame = 10  # Out of range (only 3 points)
        curve_widget.main_window = mock_main_window

        # Clear selection
        curve_widget.clear_selection()

        # Get original positions
        original_positions = [safe_extract_point(p) for p in curve_widget.curve_data]

        # Try to nudge - should do nothing
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_8, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify nothing moved
        new_positions = [safe_extract_point(p) for p in curve_widget.curve_data]
        for orig, new in zip(original_positions, new_positions):
            assert orig == new

    def test_nudge_converts_to_keyframe_status(self, curve_widget: CurveViewWidget):
        """Test that nudging a point converts it to KEYFRAME status."""
        from core.models import PointStatus

        # Start with a point that's not a keyframe (e.g., NORMAL status)
        test_data = [(1, 100.0, 200.0, PointStatus.NORMAL.value)]
        curve_widget.set_curve_data(test_data)
        curve_widget._curve_store.select(0)

        # Verify initial status is NORMAL
        _, _, _, status = safe_extract_point(curve_widget.curve_data[0])
        assert status == PointStatus.NORMAL.value

        # Nudge the point
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_6, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify status changed to KEYFRAME
        _, _, _, new_status = safe_extract_point(curve_widget.curve_data[0])
        assert new_status == PointStatus.KEYFRAME.value

    def test_nudge_current_frame_converts_to_keyframe(self, curve_widget: CurveViewWidget):
        """Test that nudging current frame point converts it to KEYFRAME status."""
        from unittest.mock import MagicMock

        from core.models import PointStatus

        # Set up test data with INTERPOLATED status
        test_data = [(1, 100.0, 200.0, PointStatus.INTERPOLATED.value), (2, 150.0, 250.0, PointStatus.NORMAL.value)]
        curve_widget.set_curve_data(test_data)

        # Mock current frame
        mock_main_window = MagicMock()
        mock_main_window.current_frame = 1  # Frame 1 (index 0)
        curve_widget.main_window = mock_main_window

        # Clear selection
        curve_widget.clear_selection()

        # Verify initial status
        _, _, _, status = safe_extract_point(curve_widget.curve_data[0])
        assert status == PointStatus.INTERPOLATED.value

        # Nudge using key 8 (up)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_8, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify status changed to KEYFRAME
        _, _, _, new_status = safe_extract_point(curve_widget.curve_data[0])
        assert new_status == PointStatus.KEYFRAME.value

    def test_nudge_multiple_points_all_become_keyframes(self, curve_widget: CurveViewWidget):
        """Test that nudging multiple selected points converts all to KEYFRAME status."""
        from core.models import PointStatus

        # Set up test data with mixed statuses
        test_data = [
            (1, 100.0, 200.0, PointStatus.NORMAL.value),
            (2, 150.0, 250.0, PointStatus.INTERPOLATED.value),
            (3, 200.0, 300.0, PointStatus.TRACKED.value),
        ]
        curve_widget.set_curve_data(test_data)

        # Select all points
        curve_widget.select_all()

        # Nudge all points
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_4, Qt.KeyboardModifier.NoModifier)
        curve_widget.keyPressEvent(event)

        # Verify all points became KEYFRAME
        for i in range(3):
            _, _, _, status = safe_extract_point(curve_widget.curve_data[i])
            assert status == PointStatus.KEYFRAME.value, f"Point {i} should be KEYFRAME"
