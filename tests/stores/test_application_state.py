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

from collections.abc import Generator

import pytest
from PySide6.QtTest import QSignalSpy

from core.models import CurvePoint, PointStatus
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

        state.begin_batch()
        state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])
        state.set_curve_data("curve2", [(1, 30.0, 40.0, "normal")])
        state.set_curve_data("curve3", [(1, 50.0, 60.0, "normal")])

        # No signals yet
        assert spy.count() == 0

        state.end_batch()

        # Now signals emitted
        assert spy.count() > 0

    def test_batch_mode_eliminates_duplicates(self) -> None:
        """Test duplicate signals eliminated in batch mode."""
        state = get_application_state()
        spy = QSignalSpy(state.curves_changed)

        state.begin_batch()
        # Modify same curve 10 times
        for i in range(10):
            state.set_curve_data("test", [(i, float(i), float(i * 2), "normal")])
        state.end_batch()

        # Should emit only once
        assert spy.count() == 1

    def test_batch_mode_exception_handling(self) -> None:
        """Test batch mode is properly cleaned up when exceptions occur."""
        state = get_application_state()
        spy = QSignalSpy(state.curves_changed)

        # Verify batch mode cleanup with try/finally pattern
        try:
            state.begin_batch()
            try:
                state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])
                state.set_curve_data("curve2", [(1, 30.0, 40.0, "normal")])
                # Simulate an exception during batch operation
                raise ValueError("Test exception during batch operation")
            finally:
                # end_batch() MUST be called even when exception occurs
                state.end_batch()
        except ValueError:
            pass  # Expected exception

        # Verify signals were emitted despite the exception
        assert spy.count() > 0, "Signals should be emitted even when exception occurs"

        # Verify batch mode was properly exited (not stuck in batch mode)
        # If batch mode cleanup failed, this would defer signals incorrectly
        previous_count = spy.count()
        state.set_curve_data("curve3", [(1, 50.0, 60.0, "normal")])
        assert spy.count() > previous_count, "Should emit signals immediately after batch mode exit"

    def test_batch_mode_nested_exception_safety(self) -> None:
        """Test that batch mode state is correctly restored after exception."""
        state = get_application_state()

        # Start batch mode
        state.begin_batch()
        try:
            state.set_curve_data("curve1", [(1, 10.0, 20.0, "normal")])

            # Simulate exception mid-batch
            try:
                state.set_curve_data("invalid_curve", [])  # Edge case
                raise RuntimeError("Simulated error")
            except RuntimeError:
                pass  # Handle error but continue batch

            # Should still be in batch mode
            state.set_curve_data("curve2", [(1, 30.0, 40.0, "normal")])
        finally:
            state.end_batch()

        # Verify all operations completed successfully
        assert "curve1" in state.get_all_curve_names()
        assert "curve2" in state.get_all_curve_names()

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
        state.begin_batch()
        for i in range(100):
            state.set_curve_data(f"curve_{i}", [(i, float(i), float(i * 2), "normal")])
        state.end_batch()
        batch_time = time.perf_counter() - start

        speedup = individual_time / batch_time
        assert speedup > 3.0  # At least 3x faster
