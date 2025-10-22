"""
Comprehensive tests for ApplicationState.

Test Coverage:
- State operations (CRUD)
- Immutability guarantees
- Signal emission
- Batch operations
- Memory efficiency
- Performance benchmarks
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

from collections.abc import Generator

import pytest
from PySide6.QtTest import QSignalSpy

from core.models import CurvePoint, PointStatus
from core.type_aliases import CurveDataInput
from stores.application_state import get_application_state, reset_application_state


class TestApplicationState:
    """Test ApplicationState functionality."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> Generator[None, None, None]:
        """Reset state before each test."""
        reset_application_state()
        yield
        reset_application_state()

    # ==================== Singleton Tests ====================

    def test_singleton_pattern(self) -> None:
        """Verify singleton returns same instance."""
        state1 = get_application_state()
        state2 = get_application_state()
        assert state1 is state2

    def test_reset_creates_new_instance(self) -> None:
        """Verify reset creates new instance."""
        state1 = get_application_state()
        reset_application_state()
        state2 = get_application_state()
        assert state1 is not state2

    # ==================== Curve Data Tests ====================

    def test_set_and_get_curve_data(self) -> None:
        """Test basic curve data storage."""
        state = get_application_state()
        test_data = [(1, 10.0, 20.0, "normal"), (2, 30.0, 40.0, "keyframe")]

        state.set_curve_data("test_curve", test_data)
        retrieved = state.get_curve_data("test_curve")

        assert retrieved == test_data

    def test_curve_data_immutability(self) -> None:
        """Verify returned data is copy."""
        state = get_application_state()
        original = [(1, 10.0, 20.0, "normal")]

        state.set_curve_data("test", original)
        retrieved = state.get_curve_data("test")
        retrieved.append((2, 30.0, 40.0, "normal"))

        # Original should be unchanged
        assert state.get_curve_data("test") == original

    def test_update_single_point(self) -> None:
        """Test updating single point."""
        state = get_application_state()
        state.set_curve_data("test", [(1, 10.0, 20.0, "normal")])

        new_point = CurvePoint(frame=1, x=15.0, y=25.0, status=PointStatus.KEYFRAME)
        state.update_point("test", 0, new_point)

        result = state.get_curve_data("test")
        assert len(result[0]) == 4  # PointTuple4
        point = result[0]
        assert point[1] == 15.0
        assert point[2] == 25.0
        # Access index 3 safely for PointTuple4
        if len(point) == 4:
            assert point[3] == "keyframe"

    def test_multi_curve_support(self) -> None:
        """Test native multi-curve handling."""
        state = get_application_state()

        state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])
        state.set_curve_data("curve2", [(1, 30.0, 40.0, "normal")])
        state.set_curve_data("curve3", [(1, 50.0, 60.0, "normal")])

        names = state.get_all_curve_names()
        assert set(names) == {"curve1", "curve2", "curve3"}

    def test_get_all_curves_returns_copy(self) -> None:
        """Verify get_all_curves returns independent copy."""
        state = get_application_state()

        # Set up multiple curves
        state.set_curve_data("Track1", [(1, 1.0, 1.0, "normal")])
        state.set_curve_data("Track2", [(2, 2.0, 2.0, "keyframe"), (3, 3.0, 3.0, "normal")])
        state.set_curve_data("Track3", [(4, 4.0, 4.0, "normal")])

        # Get all curves
        all_curves = state.get_all_curves()

        # Verify structure
        assert len(all_curves) == 3
        assert "Track1" in all_curves
        assert "Track2" in all_curves
        assert "Track3" in all_curves

        # Verify data integrity
        assert len(all_curves["Track1"]) == 1
        assert len(all_curves["Track2"]) == 2
        assert len(all_curves["Track3"]) == 1

        # Verify immutability - modifying returned dict should not affect state
        all_curves["Track1"].append((5, 5.0, 5.0, "normal"))
        assert len(state.get_curve_data("Track1")) == 1  # Unchanged

        # Verify immutability - adding new key should not affect state
        all_curves["NewCurve"] = [(6, 6.0, 6.0, "normal")]
        assert "NewCurve" not in state.get_all_curve_names()

    def test_get_all_curves_empty_state(self) -> None:
        """Verify get_all_curves works with empty state."""
        state = get_application_state()
        all_curves = state.get_all_curves()

        assert isinstance(all_curves, dict)
        assert len(all_curves) == 0

    # ==================== Selection Tests ====================

    def test_per_curve_selection(self) -> None:
        """Verify selection tracked independently per curve."""
        state = get_application_state()

        state.set_selection("curve1", {0, 1, 2})
        state.set_selection("curve2", {5, 6})
        state.set_selection("curve3", {10})

        assert state.get_selection("curve1") == {0, 1, 2}
        assert state.get_selection("curve2") == {5, 6}
        assert state.get_selection("curve3") == {10}

    def test_selection_immutability(self) -> None:
        """Verify selection returns copy."""
        state = get_application_state()
        original = {0, 1, 2}

        state.set_selection("test", original)
        retrieved = state.get_selection("test")
        retrieved.add(999)

        assert state.get_selection("test") == original

    # ==================== Signal Tests ====================

    def test_curves_changed_signal(self) -> None:
        """Test curves_changed signal emission."""
        state = get_application_state()
        spy = QSignalSpy(state.curves_changed)

        state.set_curve_data("test", [(1, 10.0, 20.0, "normal")])

        assert spy.count() == 1

    def test_selection_changed_signal(self) -> None:
        """Test selection_changed includes curve name."""
        state = get_application_state()
        spy = QSignalSpy(state.selection_changed)

        state.set_selection("test", {0, 1, 2})

        assert spy.count() == 1
        # QSignalSpy stores args in list, access via at() method
        args = spy.at(0)
        assert args[0] == {0, 1, 2}
        assert args[1] == "test"

    # ==================== Batch Operation Tests ====================

    def test_batch_mode_defers_signals(self) -> None:
        """Test batch mode prevents signal storm."""
        state = get_application_state()
        spy = QSignalSpy(state.curves_changed)

        with state.batch_updates():
            state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])
            state.set_curve_data("curve2", [(1, 30.0, 40.0, "normal")])
            state.set_curve_data("curve3", [(1, 50.0, 60.0, "normal")])

            # No signals yet (still in batch)
            assert spy.count() == 0

        # After batch completes, signals emitted
        assert spy.count() > 0

    def test_batch_mode_eliminates_duplicates(self) -> None:
        """Test duplicate signals eliminated in batch mode."""
        state = get_application_state()
        spy = QSignalSpy(state.curves_changed)

        with state.batch_updates():
            # Modify same curve 10 times
            for i in range(10):
                state.set_curve_data("test", [(i, float(i), float(i * 2), "normal")])

        # Should emit only once (last state wins)
        assert spy.count() == 1

    def test_batch_mode_exception_handling(self) -> None:
        """Test batch mode is properly cleaned up when exceptions occur."""
        state = get_application_state()
        spy = QSignalSpy(state.curves_changed)

        # Verify batch mode cleanup when exception occurs in context manager
        try:
            with state.batch_updates():
                state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])
                state.set_curve_data("curve2", [(1, 30.0, 40.0, "normal")])
                # Simulate an exception during batch operation
                raise ValueError("Test exception during batch operation")
        except ValueError:
            pass  # Expected exception

        # Verify signals were NOT emitted (exception clears pending signals)
        # This is the correct behavior - failed batch should not emit partial state
        assert spy.count() == 0, "Failed batch should not emit signals"

        # Verify batch mode was properly exited (not stuck in batch mode)
        # If batch mode cleanup failed, this would defer signals incorrectly
        state.set_curve_data("curve3", [(1, 50.0, 60.0, "normal")])
        assert spy.count() == 1, "Should emit signals immediately after batch mode exit"

    def test_batch_mode_nested_exception_safety(self) -> None:
        """Test that nested batch mode works correctly (inner batch is no-op)."""
        state = get_application_state()
        spy = QSignalSpy(state.curves_changed)

        # Outer batch
        with state.batch_updates():
            state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])

            # Inner batch (should be no-op, just pass through)
            with state.batch_updates():
                state.set_curve_data("curve2", [(1, 30.0, 40.0, "normal")])
                # Inner batch completes, but signals not emitted yet (outer batch active)

            # Still in outer batch
            state.set_curve_data("curve3", [(1, 50.0, 60.0, "normal")])

        # Signals emitted after outer batch completes
        # All 3 set_curve_data calls trigger same signal type (curves_changed),
        # so deduplication means only 1 emission with final state
        assert spy.count() == 1  # Deduplicated: last state wins

        # Verify all operations completed successfully
        assert "curve1" in state.get_all_curve_names()
        assert "curve2" in state.get_all_curve_names()
        assert "curve3" in state.get_all_curve_names()

    # ==================== Performance Tests ====================

    def test_large_dataset_performance(self) -> None:
        """Test performance with large datasets."""
        import time

        state = get_application_state()

        # 10,000 points
        large_data = [(i, float(i), float(i * 2), "normal") for i in range(10000)]

        start = time.perf_counter()
        state.set_curve_data("large", large_data)
        set_time = time.perf_counter() - start

        start = time.perf_counter()
        retrieved = state.get_curve_data("large")
        get_time = time.perf_counter() - start

        assert set_time < 0.1  # <100ms
        assert get_time < 0.05  # <50ms
        assert len(retrieved) == 10000

    def test_batch_speedup(self) -> None:
        """Test batch operations are faster."""
        import time

        # Individual updates
        reset_application_state()
        state = get_application_state()
        start = time.perf_counter()
        for i in range(100):
            state.set_curve_data(f"curve_{i}", [(i, float(i), float(i * 2), "normal")])
        individual_time = time.perf_counter() - start

        # Batch updates
        reset_application_state()
        state = get_application_state()
        start = time.perf_counter()
        with state.batch_updates():
            for i in range(100):
                state.set_curve_data(f"curve_{i}", [(i, float(i), float(i * 2), "normal")])
        batch_time = time.perf_counter() - start

        speedup = individual_time / batch_time
        assert speedup > 3.0  # At least 3x faster  # At least 3x faster


class TestWithActiveCurve:
    """Tests for with_active_curve helper."""

    @pytest.fixture(autouse=True)
    def reset_state(self) -> Generator[None, None, None]:
        """Reset state before each test."""
        reset_application_state()
        yield
        reset_application_state()

    def test_with_active_curve_success(self) -> None:
        """Should execute callback with active curve data."""
        state = get_application_state()
        # Setup active curve with data
        state.set_curve_data("TestCurve", [(1, 10.0, 20.0, "keyframe")])
        state.set_active_curve("TestCurve")

        results: list[tuple[str, CurveDataInput]] = []

        def collect_data(name: str, data: CurveDataInput) -> None:
            results.append((name, data))

        state.with_active_curve(collect_data)

        assert len(results) == 1
        assert results[0][0] == "TestCurve"
        assert len(results[0][1]) == 1

    def test_with_active_curve_no_active(self) -> None:
        """Should return None when no active curve."""
        state = get_application_state()
        state.set_active_curve(None)

        def return_value(name: str, data: CurveDataInput) -> str:
            return "value"

        result = state.with_active_curve(return_value)
        assert result is None

    def test_with_active_curve_no_data(self) -> None:
        """Should return None when active curve has no data."""
        state = get_application_state()
        state.set_active_curve("EmptyCurve")

        def return_value(name: str, data: CurveDataInput) -> str:
            return "value"

        result = state.with_active_curve(return_value)
        assert result is None

    def test_with_active_curve_return_value(self) -> None:
        """Should return callback result."""
        state = get_application_state()
        state.set_curve_data("TestCurve", [(1, 10.0, 20.0, "keyframe")])
        state.set_active_curve("TestCurve")

        def format_result(name: str, data: CurveDataInput) -> str:
            return f"Curve {name} has {len(data)} points"

        result = state.with_active_curve(format_result)
        assert result == "Curve TestCurve has 1 points"

    def test_with_active_curve_type_preservation(self) -> None:
        """Should preserve return type from callback."""
        state = get_application_state()
        state.set_curve_data("TestCurve", [(1, 10.0, 20.0, "keyframe"), (2, 15.0, 25.0, "normal")])
        state.set_active_curve("TestCurve")

        def count_points(name: str, data: CurveDataInput) -> int:
            return len(data)

        result = state.with_active_curve(count_points)
        assert isinstance(result, int)
        assert result == 2

    def test_with_active_curve_complex_operation(self) -> None:
        """Should handle complex operations in callback."""
        state = get_application_state()
        state.set_curve_data(
            "TestCurve", [(1, 10.0, 20.0, "keyframe"), (2, 15.0, 25.0, "normal"), (3, 20.0, 30.0, "keyframe")]
        )
        state.set_active_curve("TestCurve")

        def find_keyframes(name: str, data: CurveDataInput) -> list[int]:
            return [i for i, point in enumerate(data) if len(point) > 3 and point[3] == "keyframe"]

        result = state.with_active_curve(find_keyframes)
        assert result == [0, 2]

    def test_with_active_curve_side_effects(self) -> None:
        """Should allow callbacks with side effects."""
        state = get_application_state()
        state.set_curve_data("TestCurve", [(1, 10.0, 20.0, "keyframe")])
        state.set_active_curve("TestCurve")

        side_effect_tracker: list[str] = []

        def track_side_effect(name: str, data: CurveDataInput) -> None:
            side_effect_tracker.append(f"Processed {name} with {len(data)} points")

        result = state.with_active_curve(track_side_effect)
        assert result is None  # Void callback returns None
        assert len(side_effect_tracker) == 1
        assert "TestCurve" in side_effect_tracker[0]

    def test_with_active_curve_exception_propagation(self) -> None:
        """Should propagate exceptions from callback."""
        state = get_application_state()
        state.set_curve_data("TestCurve", [(1, 10.0, 20.0, "keyframe")])
        state.set_active_curve("TestCurve")

        def failing_callback(name: str, data: CurveDataInput) -> str:
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            state.with_active_curve(failing_callback)


class TestActiveCurveDataProperty:
    """Tests for active_curve_data property (Phase 4 Task 4.4)."""

    def test_active_curve_data_success_path(self) -> None:
        """Should return (curve_name, data) when active curve has data."""
        state = get_application_state()
        test_data = [(1, 10.0, 20.0), (2, 15.0, 25.0)]
        state.set_curve_data("TestCurve", test_data)
        state.set_active_curve("TestCurve")

        result = state.active_curve_data
        assert result is not None
        curve_name, data = result
        assert curve_name == "TestCurve"
        assert len(data) == 2
        assert data[0] == (1, 10.0, 20.0)
        assert data[1] == (2, 15.0, 25.0)

    def test_active_curve_data_no_active_curve(self) -> None:
        """Should return None when no active curve is set."""
        state = get_application_state()
        state.set_curve_data("TestCurve", [(1, 10.0, 20.0)])
        # Don't set active curve

        result = state.active_curve_data
        assert result is None

    def test_active_curve_data_active_curve_no_data(self) -> None:
        """Should return tuple with empty list when active curve has no data."""
        state = get_application_state()
        state.set_active_curve("NonExistentCurve")

        result = state.active_curve_data
        assert result is not None
        curve_name, data = result
        assert curve_name == "NonExistentCurve"
        assert data == []  # Non-existent curve returns empty list

    def test_active_curve_data_tuple_unpacking(self) -> None:
        """Should support tuple unpacking in walrus operator."""
        state = get_application_state()
        state.set_curve_data("Track1", [(1, 5.0, 10.0)])
        state.set_active_curve("Track1")

        # Pattern from documentation
        if (curve_data := state.active_curve_data) is None:
            pytest.fail("Expected active curve data to exist")
        curve_name, data = curve_data
        assert curve_name == "Track1"
        assert len(data) == 1

    def test_active_curve_data_multiple_curves(self) -> None:
        """Should return only active curve data when multiple curves exist."""
        state = get_application_state()
        state.set_curve_data("Track1", [(1, 10.0, 20.0)])
        state.set_curve_data("Track2", [(1, 30.0, 40.0)])
        state.set_curve_data("Track3", [(1, 50.0, 60.0)])
        state.set_active_curve("Track2")

        result = state.active_curve_data
        assert result is not None
        curve_name, data = result
        assert curve_name == "Track2"
        assert data[0] == (1, 30.0, 40.0)

    def test_active_curve_data_with_empty_curve_data(self) -> None:
        """Should return tuple with empty list (empty curves are valid for new curves)."""
        state = get_application_state()
        state.set_curve_data("EmptyCurve", [])
        state.set_active_curve("EmptyCurve")

        result = state.active_curve_data
        assert result is not None
        curve_name, data = result
        assert curve_name == "EmptyCurve"
        assert data == []  # Empty list is valid!

    def test_active_curve_data_after_active_curve_change(self) -> None:
        """Should reflect active curve changes."""
        state = get_application_state()
        state.set_curve_data("Track1", [(1, 10.0, 20.0)])
        state.set_curve_data("Track2", [(1, 30.0, 40.0)])
        state.set_active_curve("Track1")

        result1 = state.active_curve_data
        assert result1 is not None
        assert result1[0] == "Track1"

        state.set_active_curve("Track2")
        result2 = state.active_curve_data
        assert result2 is not None
        assert result2[0] == "Track2"
