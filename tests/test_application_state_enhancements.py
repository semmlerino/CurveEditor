#!/usr/bin/env python
"""
Tests for ApplicationState P0/P1 enhancement methods.

Tests the new point manipulation and selection methods added for
CurveDataStore deprecation (Phase 4).

P0 Methods (Critical):
- add_point()
- remove_point()
- set_point_status()

P1 Methods (High Value):
- select_all()
- select_range()
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Signal

from core.models import CurvePoint, PointStatus
from core.type_aliases import CurveDataList
from stores.application_state import get_application_state, reset_application_state


class SignalSpy:
    """Helper to track Qt signal emissions."""

    def __init__(self, signal: Signal):
        self.signal = signal
        self.emissions: list[tuple[object, ...]] = []
        self.signal.connect(self._on_emit)  # pyright: ignore[reportAttributeAccessIssue]

    def _on_emit(self, *args: object) -> None:
        self.emissions.append(args)

    def count(self) -> int:
        return len(self.emissions)

    def last_args(self) -> tuple[object, ...]:
        return self.emissions[-1] if self.emissions else ()

    def reset(self):
        self.emissions.clear()


@pytest.fixture
def app_state(qapp):
    """Fresh ApplicationState for each test."""
    reset_application_state()
    state = get_application_state()
    yield state
    reset_application_state()


@pytest.fixture
def sample_curve_data() -> CurveDataList:
    """Sample curve data for testing."""
    return [
        (1, 100.0, 200.0, "keyframe"),
        (2, 110.0, 210.0, "normal"),
        (3, 120.0, 220.0, "interpolated"),
        (5, 140.0, 240.0, "endframe"),
    ]


# ==================== P0 Tests: add_point() ====================


def test_add_point_to_empty_curve(app_state):
    """Test adding point to non-existent curve creates it."""
    point = CurvePoint(frame=1, x=100.0, y=200.0, status=PointStatus.KEYFRAME)

    # Add to non-existent curve
    index = app_state.add_point("new_curve", point)

    assert index == 0
    data = app_state.get_curve_data("new_curve")
    assert len(data) == 1
    assert data[0] == (1, 100.0, 200.0, "keyframe")


def test_add_point_to_existing_curve(app_state, sample_curve_data):
    """Test adding point appends to end of existing curve."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    point = CurvePoint(frame=10, x=200.0, y=300.0, status=PointStatus.TRACKED)
    index = app_state.add_point("test_curve", point)

    assert index == 4  # Appended after 4 existing points
    data = app_state.get_curve_data("test_curve")
    assert len(data) == 5
    assert data[4] == (10, 200.0, 300.0, "tracked")


def test_add_point_emits_curves_changed_signal(app_state):
    """Test add_point emits curves_changed signal."""
    spy = SignalSpy(app_state.curves_changed)
    point = CurvePoint(frame=1, x=100.0, y=200.0)

    app_state.add_point("test_curve", point)

    assert spy.count() == 1
    emitted_data = spy.last_args()[0]
    assert isinstance(emitted_data, dict)
    assert "test_curve" in emitted_data
    assert len(emitted_data["test_curve"]) == 1


def test_add_point_initializes_metadata(app_state):
    """Test add_point creates metadata for new curve."""
    point = CurvePoint(frame=1, x=100.0, y=200.0)
    app_state.add_point("new_curve", point)

    metadata = app_state.get_curve_metadata("new_curve")
    assert metadata["visible"] is True


def test_add_point_preserves_immutability(app_state):
    """Test add_point doesn't affect original data."""
    initial_data: CurveDataList = [(1, 100.0, 200.0)]
    app_state.set_curve_data("test_curve", initial_data)

    point = CurvePoint(frame=2, x=110.0, y=210.0)
    app_state.add_point("test_curve", point)

    # Original data unchanged
    assert len(initial_data) == 1


# ==================== P0 Tests: remove_point() ====================


def test_remove_point_success(app_state, sample_curve_data):
    """Test removing valid point."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    result = app_state.remove_point("test_curve", 1)

    assert result is True
    data = app_state.get_curve_data("test_curve")
    assert len(data) == 3
    # Point at index 1 removed, so index 2 is now at index 1
    assert data[1] == (3, 120.0, 220.0, "interpolated")


def test_remove_point_invalid_curve(app_state):
    """Test removing point from non-existent curve returns False."""
    result = app_state.remove_point("nonexistent", 0)
    assert result is False


def test_remove_point_invalid_index(app_state, sample_curve_data):
    """Test removing point with invalid index returns False."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    # Negative index
    assert app_state.remove_point("test_curve", -1) is False

    # Index too large
    assert app_state.remove_point("test_curve", 100) is False


def test_remove_point_shifts_selection_indices(app_state, sample_curve_data):
    """Test remove_point shifts selection indices correctly."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    # Select indices 1, 2, 3
    app_state.set_selection("test_curve", {1, 2, 3})

    # Remove index 1
    app_state.remove_point("test_curve", 1)

    # Index 1 removed, indices 2 and 3 shifted down to 1 and 2
    selection = app_state.get_selection("test_curve")
    assert selection == {1, 2}


def test_remove_point_removes_deleted_index_from_selection(app_state, sample_curve_data):
    """Test remove_point removes the deleted index from selection."""
    app_state.set_curve_data("test_curve", sample_curve_data)
    app_state.set_selection("test_curve", {0, 1, 2})

    # Remove index 1
    app_state.remove_point("test_curve", 1)

    # Index 1 removed, index 2 shifted to 1, index 0 unchanged
    selection = app_state.get_selection("test_curve")
    assert selection == {0, 1}


def test_remove_point_emits_signals(app_state, sample_curve_data):
    """Test remove_point emits both curves_changed and selection_changed if needed."""
    app_state.set_curve_data("test_curve", sample_curve_data)
    app_state.set_selection("test_curve", {1})

    curves_spy = SignalSpy(app_state.curves_changed)
    selection_spy = SignalSpy(app_state.selection_changed)

    app_state.remove_point("test_curve", 1)

    # Both signals emitted
    assert curves_spy.count() == 1
    assert selection_spy.count() == 1


def test_remove_point_no_selection_change_if_empty(app_state, sample_curve_data):
    """Test remove_point doesn't emit selection_changed if no selection."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    curves_spy = SignalSpy(app_state.curves_changed)
    selection_spy = SignalSpy(app_state.selection_changed)

    app_state.remove_point("test_curve", 1)

    # Only curves_changed emitted
    assert curves_spy.count() == 1
    assert selection_spy.count() == 0


# ==================== P0 Tests: set_point_status() ====================


def test_set_point_status_with_enum(app_state, sample_curve_data):
    """Test set_point_status with PointStatus enum."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    result = app_state.set_point_status("test_curve", 1, PointStatus.KEYFRAME)

    assert result is True
    data = app_state.get_curve_data("test_curve")
    assert data[1] == (2, 110.0, 210.0, "keyframe")


def test_set_point_status_with_string(app_state, sample_curve_data):
    """Test set_point_status with string status."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    result = app_state.set_point_status("test_curve", 1, "endframe")

    assert result is True
    data = app_state.get_curve_data("test_curve")
    assert data[1] == (2, 110.0, 210.0, "endframe")


def test_set_point_status_preserves_coordinates(app_state, sample_curve_data):
    """Test set_point_status only changes status, not coordinates."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    original_point = sample_curve_data[2]
    app_state.set_point_status("test_curve", 2, PointStatus.TRACKED)

    data = app_state.get_curve_data("test_curve")
    # Frame and coordinates unchanged, only status changed
    assert data[2][0] == original_point[0]  # frame
    assert data[2][1] == original_point[1]  # x
    assert data[2][2] == original_point[2]  # y
    assert data[2][3] == "tracked"  # status changed


def test_set_point_status_invalid_curve(app_state):
    """Test set_point_status with non-existent curve returns False."""
    result = app_state.set_point_status("nonexistent", 0, PointStatus.KEYFRAME)
    assert result is False


def test_set_point_status_invalid_index(app_state, sample_curve_data):
    """Test set_point_status with invalid index returns False."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    assert app_state.set_point_status("test_curve", -1, PointStatus.KEYFRAME) is False
    assert app_state.set_point_status("test_curve", 100, PointStatus.KEYFRAME) is False


def test_set_point_status_emits_curves_changed(app_state, sample_curve_data):
    """Test set_point_status emits curves_changed signal."""
    app_state.set_curve_data("test_curve", sample_curve_data)
    spy = SignalSpy(app_state.curves_changed)

    app_state.set_point_status("test_curve", 1, PointStatus.KEYFRAME)

    assert spy.count() == 1


def test_set_point_status_all_status_types(app_state, sample_curve_data):
    """Test set_point_status with all PointStatus types."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    status_types = [
        PointStatus.NORMAL,
        PointStatus.KEYFRAME,
        PointStatus.INTERPOLATED,
        PointStatus.TRACKED,
        PointStatus.ENDFRAME,
    ]

    for i, status in enumerate(status_types):
        if i < len(sample_curve_data):
            result = app_state.set_point_status("test_curve", i, status)
            assert result is True

            data = app_state.get_curve_data("test_curve")
            assert data[i][3] == status.value


# ==================== P1 Tests: select_all() ====================


def test_select_all_with_explicit_curve(app_state, sample_curve_data):
    """Test select_all with explicit curve name."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    app_state.select_all("test_curve")

    selection = app_state.get_selection("test_curve")
    assert selection == {0, 1, 2, 3}


def test_select_all_with_active_curve(app_state, sample_curve_data):
    """Test select_all defaults to active curve."""
    app_state.set_curve_data("test_curve", sample_curve_data)
    app_state.set_active_curve("test_curve")

    app_state.select_all()  # No curve_name argument

    selection = app_state.get_selection("test_curve")
    assert selection == {0, 1, 2, 3}


def test_select_all_no_active_curve(app_state):
    """Test select_all with no active curve does nothing."""
    app_state.select_all()  # Should log warning but not crash
    # No assertion needed - just verify no exception


def test_select_all_nonexistent_curve(app_state):
    """Test select_all with non-existent curve does nothing."""
    app_state.select_all("nonexistent")  # Should log warning
    # No assertion needed - just verify no exception


def test_select_all_empty_curve(app_state):
    """Test select_all on empty curve."""
    app_state.set_curve_data("empty_curve", [])
    app_state.select_all("empty_curve")

    selection = app_state.get_selection("empty_curve")
    assert selection == set()


def test_select_all_emits_selection_changed(app_state, sample_curve_data):
    """Test select_all emits selection_changed signal."""
    app_state.set_curve_data("test_curve", sample_curve_data)
    spy = SignalSpy(app_state.selection_changed)

    app_state.select_all("test_curve")

    assert spy.count() == 1
    emitted_selection, emitted_curve = spy.last_args()
    assert emitted_selection == {0, 1, 2, 3}
    assert emitted_curve == "test_curve"


# ==================== P1 Tests: select_range() ====================


def test_select_range_normal(app_state, sample_curve_data):
    """Test select_range with valid range."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    app_state.select_range("test_curve", 1, 3)

    selection = app_state.get_selection("test_curve")
    assert selection == {1, 2, 3}


def test_select_range_single_point(app_state, sample_curve_data):
    """Test select_range with start == end."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    app_state.select_range("test_curve", 2, 2)

    selection = app_state.get_selection("test_curve")
    assert selection == {2}


def test_select_range_reversed_indices(app_state, sample_curve_data):
    """Test select_range auto-swaps if start > end."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    app_state.select_range("test_curve", 3, 1)  # Reversed

    selection = app_state.get_selection("test_curve")
    assert selection == {1, 2, 3}


def test_select_range_clamps_to_valid_range(app_state, sample_curve_data):
    """Test select_range clamps indices to valid range."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    # Negative start, end beyond curve
    app_state.select_range("test_curve", -10, 100)

    selection = app_state.get_selection("test_curve")
    assert selection == {0, 1, 2, 3}  # Clamped to [0, 3]


def test_select_range_nonexistent_curve(app_state):
    """Test select_range with non-existent curve does nothing."""
    app_state.select_range("nonexistent", 0, 2)
    # No assertion needed - just verify no exception


def test_select_range_empty_curve(app_state):
    """Test select_range on empty curve does nothing."""
    app_state.set_curve_data("empty_curve", [])
    app_state.select_range("empty_curve", 0, 2)

    selection = app_state.get_selection("empty_curve")
    assert selection == set()


def test_select_range_emits_selection_changed(app_state, sample_curve_data):
    """Test select_range emits selection_changed signal."""
    app_state.set_curve_data("test_curve", sample_curve_data)
    spy = SignalSpy(app_state.selection_changed)

    app_state.select_range("test_curve", 1, 2)

    assert spy.count() == 1
    emitted_selection, emitted_curve = spy.last_args()
    assert emitted_selection == {1, 2}
    assert emitted_curve == "test_curve"


# ==================== Edge Cases & Integration Tests ====================


def test_add_remove_point_round_trip(app_state):
    """Test adding and removing points maintains consistency."""
    point1 = CurvePoint(1, 100.0, 200.0)
    point2 = CurvePoint(2, 110.0, 210.0)

    # Add two points
    idx1 = app_state.add_point("test_curve", point1)
    idx2 = app_state.add_point("test_curve", point2)

    assert idx1 == 0
    assert idx2 == 1

    # Remove first point
    result = app_state.remove_point("test_curve", 0)
    assert result is True

    # Only second point remains (now at index 0)
    data = app_state.get_curve_data("test_curve")
    assert len(data) == 1
    assert data[0] == (2, 110.0, 210.0, "normal")


def test_set_point_status_then_remove(app_state, sample_curve_data):
    """Test changing status then removing point."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    # Change status
    app_state.set_point_status("test_curve", 1, PointStatus.ENDFRAME)

    # Remove the point
    app_state.remove_point("test_curve", 1)

    data = app_state.get_curve_data("test_curve")
    assert len(data) == 3


def test_batch_operations_with_new_methods(app_state, sample_curve_data):
    """Test new methods work correctly in batch mode."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    curves_spy = SignalSpy(app_state.curves_changed)
    selection_spy = SignalSpy(app_state.selection_changed)

    with app_state.batch_updates():
        point = CurvePoint(10, 200.0, 300.0)
        app_state.add_point("test_curve", point)
        app_state.set_point_status("test_curve", 0, PointStatus.TRACKED)
        app_state.select_all("test_curve")

    # Only one signal emission per signal type (deduplicated)
    assert curves_spy.count() == 1
    assert selection_spy.count() == 1


def test_multiple_curves_independent_operations(app_state):
    """Test operations on different curves are independent."""
    data1: CurveDataList = [(1, 100.0, 200.0), (2, 110.0, 210.0)]
    data2: CurveDataList = [(1, 300.0, 400.0), (2, 310.0, 410.0)]

    app_state.set_curve_data("curve1", data1)
    app_state.set_curve_data("curve2", data2)

    # Operate on curve1
    app_state.select_all("curve1")
    app_state.remove_point("curve1", 0)

    # Operate on curve2
    app_state.select_range("curve2", 0, 1)
    point = CurvePoint(3, 320.0, 420.0)
    app_state.add_point("curve2", point)

    # Verify independence
    assert len(app_state.get_curve_data("curve1")) == 1
    assert len(app_state.get_curve_data("curve2")) == 3
    assert app_state.get_selection("curve1") == {0}  # Shifted after removal
    assert app_state.get_selection("curve2") == {0, 1}


def test_immutability_of_returned_data(app_state, sample_curve_data):
    """Test that modifying returned data doesn't affect state."""
    app_state.set_curve_data("test_curve", sample_curve_data)

    # Get data and modify it
    data = app_state.get_curve_data("test_curve")
    original_len = len(data)
    data.append((100, 999.0, 999.0))

    # State unchanged
    state_data = app_state.get_curve_data("test_curve")
    assert len(state_data) == original_len


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
