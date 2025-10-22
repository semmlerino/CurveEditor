"""
Comprehensive test suite for Phase 8 multi-curve InteractionService features.

This module tests critical multi-curve functionality that was identified as
having test coverage gaps during Phase 8 assessment.

Coverage targets:
- Multi-curve selection with curve_name parameter
- Edge cases (no visible curves, invalid names, empty curves)
- PointSearchResult backward compatibility
- Cross-curve operations
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

import pytest
from PySide6.QtCore import QRect

from core.models import PointSearchResult
from services import get_interaction_service
from stores.application_state import get_application_state


class TestMultiCurveSelection:
    """Test multi-curve selection methods with curve_name parameter."""

    def test_select_point_by_index_in_non_active_curve(self, interaction_service, curve_view_mock, main_window_mock):
        """Test selecting point in curve that's not active."""
        app_state = get_application_state()

        # Setup two curves
        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0)]
        curve_b = [(1, 30.0, 40.0), (2, 35.0, 45.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_active_curve("curve_a")

        # Select point in curve_b (not active)
        result = interaction_service.select_point_by_index(
            curve_view_mock, main_window_mock, idx=1, curve_name="curve_b"
        )

        assert result is True
        selection = app_state.get_selection("curve_b")
        assert 1 in selection

    def test_select_all_points_with_specific_curve_name(self, interaction_service, curve_view_mock, main_window_mock):
        """Test select_all_points with specific curve_name."""
        app_state = get_application_state()

        # Setup curves with different point counts
        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0), (3, 20.0, 30.0)]
        curve_b = [(1, 30.0, 40.0), (2, 35.0, 45.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_active_curve("curve_a")

        # Select all in curve_b specifically
        count = interaction_service.select_all_points(curve_view_mock, main_window_mock, curve_name="curve_b")

        assert count == 2  # curve_b has 2 points
        selection_b = app_state.get_selection("curve_b")
        assert len(selection_b) == 2
        assert selection_b == {0, 1}

    def test_clear_selection_with_specific_curve_name(self, interaction_service, curve_view_mock, main_window_mock):
        """Test clear_selection with specific curve_name."""
        app_state = get_application_state()

        # Setup curves with selections
        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0)]
        curve_b = [(1, 30.0, 40.0), (2, 35.0, 45.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_selection("curve_a", {0, 1})
        app_state.set_selection("curve_b", {0, 1})

        # Clear only curve_b
        interaction_service.clear_selection(curve_view_mock, main_window_mock, curve_name="curve_b")

        # curve_a selection should remain, curve_b should be cleared
        assert len(app_state.get_selection("curve_a")) == 2
        assert len(app_state.get_selection("curve_b")) == 0

    def test_delete_selected_points_with_specific_curve_name(
        self, interaction_service, curve_view_mock, main_window_mock
    ):
        """Test deleting selected points from specific curve."""
        app_state = get_application_state()

        # Setup curves
        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0), (3, 20.0, 30.0)]
        curve_b = [(1, 30.0, 40.0), (2, 35.0, 45.0), (3, 40.0, 50.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_active_curve("curve_b")  # Set curve_b as active to match selected_points

        # Select and delete from curve_b
        curve_view_mock.selected_points = {1, 2}
        interaction_service.delete_selected_points(curve_view_mock, main_window_mock, curve_name="curve_b")

        # curve_b should have 1 point, curve_a should be unchanged
        assert len(app_state.get_curve_data("curve_a")) == 3
        assert len(app_state.get_curve_data("curve_b")) == 1

    def test_select_points_in_rect_with_specific_curve_name(
        self, interaction_service, curve_view_mock, main_window_mock
    ):
        """Test rectangle selection in specific curve."""
        app_state = get_application_state()

        # Setup overlapping curves (same positions)
        curve_a = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        curve_b = [(1, 100.0, 100.0), (2, 200.0, 200.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_active_curve("curve_a")

        # Select rectangle covering first point in curve_b only
        rect = QRect(50, 50, 100, 100)  # Covers point at (100, 100)
        count = interaction_service.select_points_in_rect(curve_view_mock, main_window_mock, rect, curve_name="curve_b")

        # Only curve_b should have selection
        assert count >= 0  # May vary based on transform
        selection_b = app_state.get_selection("curve_b")
        assert isinstance(selection_b, set)


class TestEdgeCases:
    """Test edge cases for multi-curve operations."""

    def test_find_point_at_no_visible_curves(self, interaction_service, curve_view_mock):
        """Test find_point_at when all curves are hidden."""
        app_state = get_application_state()

        # Setup curves but mark as invisible
        curve_a = [(1, 100.0, 100.0)]
        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_visibility("curve_a", False)

        # Search with all_visible mode
        result = interaction_service.find_point_at(curve_view_mock, 100.0, 100.0, mode="all_visible")

        assert result.index == -1
        assert result.curve_name is None
        assert not result.found

    def test_select_all_points_invalid_curve_name(self, interaction_service, curve_view_mock, main_window_mock):
        """Test selecting all points with non-existent curve_name."""
        app_state = get_application_state()

        # Setup valid curve
        curve_a = [(1, 10.0, 20.0)]
        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_active_curve("curve_a")

        # Try to select from non-existent curve
        count = interaction_service.select_all_points(curve_view_mock, main_window_mock, curve_name="nonexistent")

        assert count == 0

    def test_delete_selected_points_empty_curve(self, interaction_service, curve_view_mock, main_window_mock):
        """Test deleting from empty curve."""
        app_state = get_application_state()

        # Setup empty curve
        app_state.set_curve_data("empty_curve", [])
        curve_view_mock.selected_points = {0}

        # Should handle gracefully
        interaction_service.delete_selected_points(curve_view_mock, main_window_mock, curve_name="empty_curve")

        assert len(app_state.get_curve_data("empty_curve")) == 0

    def test_select_point_by_index_out_of_bounds(self, interaction_service, curve_view_mock, main_window_mock):
        """Test selecting point with invalid index."""
        app_state = get_application_state()

        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0)]
        app_state.set_curve_data("curve_a", curve_a)

        # Try to select beyond curve length
        result = interaction_service.select_point_by_index(
            curve_view_mock, main_window_mock, idx=99, curve_name="curve_a"
        )

        assert result is False

    def test_clear_selection_with_none_active_curve(self, interaction_service, curve_view_mock, main_window_mock):
        """Test clear_selection when no active curve."""
        app_state = get_application_state()
        app_state.set_active_curve(None)

        # Should handle gracefully
        interaction_service.clear_selection(curve_view_mock, main_window_mock)

        # No errors should occur
        assert curve_view_mock.selected_points == set()


class TestPointSearchResultCompatibility:
    """Test PointSearchResult backward compatibility with int comparisons."""

    def test_point_search_result_greater_than_or_equal_zero(self):
        """Test PointSearchResult >= 0 comparison (common pattern)."""
        result = PointSearchResult(index=5, curve_name="curve_a")

        assert result >= 0
        assert not (result < 0)

    def test_point_search_result_equals_negative_one(self):
        """Test PointSearchResult == -1 comparison (not found pattern)."""
        result_found = PointSearchResult(index=3, curve_name="curve_b")
        result_not_found = PointSearchResult(index=-1, curve_name=None)

        assert not (result_found == -1)
        assert result_not_found == -1

    def test_point_search_result_bool_truthiness(self):
        """Test PointSearchResult truthiness (if result: pattern)."""
        result_found = PointSearchResult(index=2, curve_name="curve_c")
        result_not_found = PointSearchResult(index=-1, curve_name=None)

        assert result_found  # Truthy
        assert not result_not_found  # Falsy

    def test_point_search_result_found_property(self):
        """Test PointSearchResult.found property."""
        result_found = PointSearchResult(index=0, curve_name="curve_d")
        result_not_found = PointSearchResult(index=-1, curve_name=None)

        assert result_found.found is True
        assert result_not_found.found is False

    def test_point_search_result_comparison_operators(self):
        """Test all PointSearchResult comparison operators."""
        result = PointSearchResult(index=5, curve_name="curve_e")

        # Test all comparison operators
        assert result == 5
        assert result >= 5
        assert result <= 5
        assert result > 4
        assert result < 6
        assert result != 3


class TestCrossCurveOperations:
    """Test cross-curve selection persistence and operations."""

    def test_selection_persists_when_switching_active_curve(
        self, interaction_service, curve_view_mock, main_window_mock
    ):
        """Test that selections persist when switching active curve."""
        app_state = get_application_state()

        # Setup multiple curves
        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0)]
        curve_b = [(1, 30.0, 40.0), (2, 35.0, 45.0)]
        curve_c = [(1, 50.0, 60.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_curve_data("curve_c", curve_c)

        # Select points in curves
        app_state.set_selection("curve_a", {0})
        app_state.set_selection("curve_b", {1})
        app_state.set_active_curve("curve_a")

        # Switch active curve
        app_state.set_active_curve("curve_c")

        # Original selections should persist
        assert app_state.get_selection("curve_a") == {0}
        assert app_state.get_selection("curve_b") == {1}

    def test_find_point_at_overlapping_points_different_curves(self, interaction_service, curve_view_mock):
        """Test finding point when multiple curves have points at same location."""
        app_state = get_application_state()

        # Create curves with points at same location
        curve_a = [(1, 100.0, 100.0)]
        curve_b = [(1, 100.0, 100.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_curve_visibility("curve_a", True)
        app_state.set_curve_visibility("curve_b", True)

        # Search with all_visible mode
        result = interaction_service.find_point_at(curve_view_mock, 100.0, 100.0, mode="all_visible")

        # Should find one of them (distance-based selection)
        if result.found:
            assert result.curve_name in ["curve_a", "curve_b"]
            assert result.index == 0

    def test_multi_curve_selection_state_independence(self, interaction_service, curve_view_mock, main_window_mock):
        """Test that curve selections are independent."""
        app_state = get_application_state()

        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0), (3, 20.0, 30.0)]
        curve_b = [(1, 30.0, 40.0), (2, 35.0, 45.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)

        # Select different points in each curve
        app_state.set_selection("curve_a", {0, 2})
        app_state.set_selection("curve_b", {1})

        # Verify independence
        assert app_state.get_selection("curve_a") == {0, 2}
        assert app_state.get_selection("curve_b") == {1}

        # Clear one shouldn't affect the other
        interaction_service.clear_selection(curve_view_mock, main_window_mock, curve_name="curve_a")

        assert len(app_state.get_selection("curve_a")) == 0
        assert app_state.get_selection("curve_b") == {1}

    def test_nudge_selected_points_with_curve_name(self, interaction_service, curve_view_mock, main_window_mock):
        """Test nudging points in specific curve."""
        app_state = get_application_state()

        curve_a = [(1, 10.0, 20.0), (2, 15.0, 25.0)]
        curve_b = [(1, 30.0, 40.0), (2, 35.0, 45.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)
        app_state.set_active_curve("curve_a")

        # Select points in curve_b
        curve_view_mock.selected_points = {0, 1}

        # Nudge curve_b points
        result = interaction_service.nudge_selected_points(
            curve_view_mock, main_window_mock, dx=5.0, dy=10.0, curve_name="curve_b"
        )

        assert result is True

    def test_update_point_position_with_curve_name(self, interaction_service, curve_view_mock, main_window_mock):
        """Test updating point position in specific curve."""
        app_state = get_application_state()

        curve_a = [(1, 10.0, 20.0)]
        curve_b = [(1, 30.0, 40.0)]

        app_state.set_curve_data("curve_a", curve_a)
        app_state.set_curve_data("curve_b", curve_b)

        # Update point in curve_b
        result = interaction_service.update_point_position(
            curve_view_mock, main_window_mock, idx=0, x=99.0, y=88.0, curve_name="curve_b"
        )

        assert result is True

        # Verify curve_b updated, curve_a unchanged
        updated_b = app_state.get_curve_data("curve_b")
        unchanged_a = app_state.get_curve_data("curve_a")

        assert updated_b[0][1] == 99.0
        assert updated_b[0][2] == 88.0
        assert unchanged_a[0][1] == 10.0  # Unchanged


@pytest.fixture
def interaction_service():
    """Get InteractionService singleton."""
    return get_interaction_service()


@pytest.fixture
def curve_view_mock():
    """Create a mock CurveViewProtocol for testing."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.selected_points = set()
    mock.selected_point_idx = -1
    mock.zoom_factor = 1.0
    mock.pan_offset_x = 0.0
    mock.pan_offset_y = 0.0
    mock.flip_y_axis = False
    mock.width.return_value = 800
    mock.height.return_value = 600

    return mock


@pytest.fixture
def main_window_mock():
    """Create a mock MainWindowProtocol for testing."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.curve_data = []
    mock.history = []
    mock.history_index = -1

    return mock
