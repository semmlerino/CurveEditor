#!/usr/bin/env python
"""
Tests for TrackingPointsPanel tracking direction functionality.

Following UNIFIED_TESTING_GUIDE principles:
- Use real Qt components with QSignalSpy
- Mock only external dependencies
- Test behavior, not implementation
- Ensure proper widget cleanup with qtbot.addWidget()
"""

from typing import Any, cast
from core.type_aliases import PointTuple4Str

import pytest
from PySide6.QtWidgets import QComboBox
from pytestqt.qt_compat import qt_api
from pytestqt.qtbot import QtBot

from core.models import TrackingDirection
from core.type_aliases import CurveDataList
from ui.tracking_points_panel import TrackingPointsPanel


class TestTrackingPointsPanelDirection:
    """Test suite for tracking direction functionality in TrackingPointsPanel."""

    @pytest.fixture
    def tracking_panel(self, qtbot: QtBot) -> TrackingPointsPanel:
        """TrackingPointsPanel with proper cleanup."""
        panel = TrackingPointsPanel()
        qtbot.addWidget(panel)  # CRITICAL: Auto cleanup
        return panel

    @pytest.fixture
    def sample_tracking_data(self) -> dict[str, CurveDataList]:
        """Sample tracking data for tests."""
        return {
            "Track1": [(1, 100.0, 200.0), (2, 105.0, 210.0), (3, 110.0, 220.0)],
            "Track2": [(5, 300.0, 400.0), (6, 305.0, 410.0)],
            "Track3": [(10, 500.0, 600.0), (11, 510.0, 610.0), (12, 520.0, 620.0)],
        }

    @pytest.fixture
    def populated_panel(
        self, tracking_panel: TrackingPointsPanel, sample_tracking_data: dict[str, CurveDataList]
    ) -> TrackingPointsPanel:
        """TrackingPointsPanel with sample data loaded."""
        tracking_panel.set_tracked_data(sample_tracking_data)  # pyright: ignore[reportArgumentType]
        return tracking_panel

    # ==================== Basic Setup and Metadata Tests ====================

    def test_default_tracking_direction_on_new_data(
        self, tracking_panel: TrackingPointsPanel, sample_tracking_data: dict[str, CurveDataList]
    ):
        """Test that new tracking data gets default direction FW+BW."""
        tracking_panel.set_tracked_data(sample_tracking_data)  # pyright: ignore[reportArgumentType]

        for point_name in sample_tracking_data.keys():
            direction = tracking_panel.get_tracking_direction(point_name)
            assert direction == TrackingDirection.TRACKING_FW_BW

    def test_direction_column_exists_in_table(self, populated_panel: TrackingPointsPanel):
        """Test that Direction column is present in table headers."""
        table = populated_panel.table
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]

        assert "Direction" in headers
        direction_column = headers.index("Direction")
        assert direction_column == 3  # Should be column 3 (after Visible, Name, Frames)

    def test_direction_dropdown_created_for_each_point(self, populated_panel: TrackingPointsPanel):
        """Test that each tracking point has a direction dropdown."""
        table = populated_panel.table

        for row in range(table.rowCount()):
            direction_widget = table.cellWidget(row, 3)  # Direction column
            assert isinstance(direction_widget, QComboBox)

            # Check dropdown has correct options
            items = [direction_widget.itemText(i) for i in range(direction_widget.count())]
            assert items == ["FW", "BW", "FW+BW"]

    def test_get_tracking_direction_helper_method(self, populated_panel: TrackingPointsPanel):
        """Test get_tracking_direction helper method."""
        # Test existing point
        direction = populated_panel.get_tracking_direction("Track1")
        assert direction == TrackingDirection.TRACKING_FW_BW

        # Test non-existent point returns default
        direction = populated_panel.get_tracking_direction("NonExistent")
        assert direction == TrackingDirection.TRACKING_FW_BW

    # ==================== Signal Emission Tests ====================

    def test_tracking_direction_changed_signal_exists(self, tracking_panel: TrackingPointsPanel):
        """Test that tracking_direction_changed signal exists and is properly defined."""
        assert hasattr(tracking_panel, "tracking_direction_changed")
        # Signal should be defined in class with proper signature
        signal = tracking_panel.tracking_direction_changed
        assert signal is not None

    def test_direction_change_via_dropdown_emits_signal(self, populated_panel: TrackingPointsPanel, qtbot: QtBot):
        """Test that changing direction via dropdown emits tracking_direction_changed signal."""
        table = populated_panel.table

        # Create signal spy for tracking_direction_changed
        direction_spy = qt_api.QtTest.QSignalSpy(populated_panel.tracking_direction_changed)

        # Get the direction dropdown for first point
        direction_combo = table.cellWidget(0, 3)
        assert isinstance(direction_combo, QComboBox)

        # Change from default "FW+BW" to "FW"
        direction_combo.setCurrentText("FW")

        # Verify signal was emitted
        assert direction_spy.count() == 1
        signal_args = direction_spy.at(0)
        assert signal_args[0] == "Track1"  # Point name
        assert signal_args[1] == TrackingDirection.TRACKING_FW  # New direction

    def test_direction_change_updates_metadata(self, populated_panel: TrackingPointsPanel):
        """Test that changing direction updates internal metadata."""
        table = populated_panel.table

        # Change direction for Track1
        direction_combo = cast(QComboBox, table.cellWidget(0, 3))
        direction_combo.setCurrentText("BW")

        # Verify metadata was updated
        new_direction = populated_panel.get_tracking_direction("Track1")
        assert new_direction == TrackingDirection.TRACKING_BW

    # ==================== Context Menu Tests ====================

    def test_context_menu_has_direction_submenu(self, populated_panel: TrackingPointsPanel, qtbot: QtBot):
        """Test that context menu direction functionality works via helper methods."""
        table = populated_panel.table

        # Select first row
        table.selectRow(0)

        # Test that the direction submenu functionality exists by testing the helper method
        # This avoids the blocking menu.exec() call while still testing the core functionality
        selected_points = populated_panel.get_selected_points()
        assert len(selected_points) > 0

        # Test that _set_direction_for_points method exists and works
        # This is the core functionality that the context menu would call
        original_direction = populated_panel.get_tracking_direction(selected_points[0])
        populated_panel._set_direction_for_points(selected_points, TrackingDirection.TRACKING_FW)
        new_direction = populated_panel.get_tracking_direction(selected_points[0])

        assert new_direction == TrackingDirection.TRACKING_FW
        assert new_direction != original_direction

    def test_context_menu_direction_actions_exist(self, populated_panel: TrackingPointsPanel):
        """Test that direction submenu has correct actions."""
        # Select first row
        populated_panel.table.selectRow(0)

        # Get selected points to trigger menu creation logic
        selected_points = populated_panel.get_selected_points()
        assert "Track1" in selected_points

        # The _show_context_menu method should create direction actions
        # We test the underlying helper method instead
        original_direction = populated_panel.get_tracking_direction("Track1")

        # Test the helper method directly
        populated_panel._set_direction_for_points(["Track1"], TrackingDirection.TRACKING_FW)

        new_direction = populated_panel.get_tracking_direction("Track1")
        assert new_direction == TrackingDirection.TRACKING_FW
        assert new_direction != original_direction

    def test_bulk_direction_setting_via_context_menu(self, populated_panel: TrackingPointsPanel, qtbot: QtBot):
        """Test setting direction for multiple selected points."""
        table = populated_panel.table

        # Create signal spy
        direction_spy = qt_api.QtTest.QSignalSpy(populated_panel.tracking_direction_changed)

        # Select multiple rows using QTableWidget selection API
        selection_model = table.selectionModel()

        # Select rows 0, 1, and 2
        for row in range(3):
            index = table.model().index(row, 1)  # Column 1 contains the point name
            selection_model.select(index, selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows)

        selected_points = populated_panel.get_selected_points()
        assert len(selected_points) == 3

        # Set direction for all selected points
        populated_panel._set_direction_for_points(selected_points, TrackingDirection.TRACKING_BW)

        # Verify all points were updated
        for point_name in selected_points:
            direction = populated_panel.get_tracking_direction(point_name)
            assert direction == TrackingDirection.TRACKING_BW

        # Verify signals were emitted (could be more than 3 due to UI updates)
        # At minimum, we should have 3 signals for the 3 points
        assert direction_spy.count() >= 3

    def test_bulk_direction_setting_updates_ui_dropdowns(self, populated_panel: TrackingPointsPanel):
        """Test that bulk direction setting updates UI dropdowns."""
        table = populated_panel.table

        # Get all point names
        all_points = ["Track1", "Track2", "Track3"]

        # Set direction for all points
        populated_panel._set_direction_for_points(all_points, TrackingDirection.TRACKING_FW)

        # Verify UI dropdowns were updated
        for row in range(table.rowCount()):
            direction_combo = table.cellWidget(row, 3)
            assert isinstance(direction_combo, QComboBox)
            assert direction_combo.currentText() == "FW"

    # ==================== Edge Cases and Error Handling ====================

    def test_direction_change_with_empty_data(self, tracking_panel: TrackingPointsPanel):
        """Test direction operations with no tracking data."""
        # Should not crash
        direction = tracking_panel.get_tracking_direction("NonExistent")
        assert direction == TrackingDirection.TRACKING_FW_BW

        # Should handle empty point list gracefully
        tracking_panel._set_direction_for_points([], TrackingDirection.TRACKING_FW)

    def test_direction_change_with_invalid_point_name(self, populated_panel: TrackingPointsPanel):
        """Test direction operations with invalid point names."""
        # Should not crash and should not emit signals
        direction_spy = qt_api.QtTest.QSignalSpy(populated_panel.tracking_direction_changed)

        populated_panel._set_direction_for_points(["InvalidPoint"], TrackingDirection.TRACKING_FW)

        # No signal should be emitted for invalid point
        assert direction_spy.count() == 0

    def test_direction_dropdown_prevents_recursive_updates(self, populated_panel: TrackingPointsPanel):
        """Test that direction changes don't cause recursive updates."""
        # Set updating flag manually to simulate ongoing update
        populated_panel._updating = True

        direction_spy = qt_api.QtTest.QSignalSpy(populated_panel.tracking_direction_changed)

        # Try to change direction - should be blocked
        populated_panel._on_direction_changed("Track1", "FW")

        # No signal should be emitted when updating flag is set
        assert direction_spy.count() == 0

        # Reset flag
        populated_panel._updating = False

    def test_direction_persistence_across_data_reload(
        self, tracking_panel: TrackingPointsPanel, sample_tracking_data: dict[str, CurveDataList]
    ):
        """Test that direction settings persist when data is reloaded."""
        # Load data first time
        # Cast dict to satisfy invariant type parameter (CurveDataList is a Sequence subtype)
        tracking_panel.set_tracked_data(cast(Any, sample_tracking_data))

        # Change direction for Track1
        tracking_panel._set_direction_for_points(["Track1"], TrackingDirection.TRACKING_FW)
        assert tracking_panel.get_tracking_direction("Track1") == TrackingDirection.TRACKING_FW

        # Reload same data (simulating refresh)
        tracking_panel.set_tracked_data(cast(Any, sample_tracking_data))

        # Direction should persist
        assert tracking_panel.get_tracking_direction("Track1") == TrackingDirection.TRACKING_FW

    # ==================== Integration Tests ====================

    def test_direction_column_width_and_layout(self, populated_panel: TrackingPointsPanel):
        """Test that direction column has appropriate width and layout."""
        table = populated_panel.table
        header = table.horizontalHeader()

        # Direction column should have fixed width
        direction_column = 3
        resize_mode = header.sectionResizeMode(direction_column)
        assert resize_mode == header.ResizeMode.Fixed

        # Should have reasonable width
        width = table.columnWidth(direction_column)
        assert width == 80  # As set in the code

    def test_direction_dropdown_tooltip_or_accessibility(self, populated_panel: TrackingPointsPanel):
        """Test direction dropdown accessibility features."""
        table = populated_panel.table

        # Get direction dropdown for first point
        direction_combo = table.cellWidget(0, 3)
        assert isinstance(direction_combo, QComboBox)

        # Should have proper items
        assert direction_combo.count() == 3
        assert direction_combo.itemText(0) == "FW"
        assert direction_combo.itemText(1) == "BW"
        assert direction_combo.itemText(2) == "FW+BW"

    def test_all_direction_enum_values_supported(self, populated_panel: TrackingPointsPanel):
        """Test that all TrackingDirection enum values are supported in UI."""
        # Test each enum value can be set and retrieved
        for direction in TrackingDirection:
            populated_panel._set_direction_for_points(["Track1"], direction)
            retrieved_direction = populated_panel.get_tracking_direction("Track1")
            assert retrieved_direction == direction

            # Verify UI shows correct abbreviation
            table = populated_panel.table
            direction_combo = cast(QComboBox, table.cellWidget(0, 3))
            assert direction_combo.currentText() == direction.abbreviation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
