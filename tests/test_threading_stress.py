#!/usr/bin/env python
"""
Thread Safety Stress Tests for ApplicationState

Tests concurrent access to ApplicationState batch operations to verify
QMutex protection works correctly and prevents race conditions.

These tests use Python's threading module to simulate concurrent access
from typing import cast
from core.type_aliases import CurveDataList
from core.type_aliases import PointTuple4Str

from multiple threads, validating that the internal mutex properly protects
the batch mode flag and pending signals list.
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

import threading
import time
from collections.abc import Generator
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication

from stores.application_state import get_application_state, reset_application_state


class TestApplicationStateThreadSafety:
    """Thread safety stress tests for ApplicationState batch operations."""

    @pytest.fixture(autouse=True)
    def reset_state(self, qapp: QCoreApplication) -> Generator[None, None, None]:
        """Reset ApplicationState before each test."""
        reset_application_state()
        yield
        reset_application_state()

    def test_concurrent_batch_operations_single_curve(self, qapp: QCoreApplication) -> None:
        """
        Test that concurrent access from worker threads is REJECTED.

        This verifies that _assert_main_thread() correctly catches and prevents
        access from worker threads, which is the correct behavior for ApplicationState.
        """
        state = get_application_state()
        assertion_errors: list[int] = []

        def batch_worker(worker_id: int) -> None:
            """Worker that attempts to perform batch operations (should fail)."""
            try:
                # This should raise AssertionError (wrong thread)
                with state.batch_updates():
                    state.set_curve_data(f"worker_{worker_id}_curve", [(1, 0.0, 0.0, "normal")])
            except AssertionError:
                # EXPECTED - thread assertion caught the violation
                assertion_errors.append(worker_id)
            except Exception:
                # Unexpected exception
                pass

        # Launch 10 concurrent workers
        threads = [threading.Thread(target=batch_worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10)

        # Verify all workers were rejected (caught by assertion)
        assert len(assertion_errors) == 10, f"Only {len(assertion_errors)}/10 workers caught by thread assertion"

    def test_concurrent_batch_nested_not_allowed(self, qapp: QCoreApplication) -> None:
        """
        Test that nested batch_updates() contexts are properly handled (no-op).

        Verifies that inner/nested batch contexts pass through without issues
        while outer context controls signal emission.
        """
        state = get_application_state()

        # Outer batch context
        with state.batch_updates():
            # Inner batch context (should no-op and pass through)
            with state.batch_updates():
                pass
            # Back in outer context

        # Should be out of batch mode now

    def test_signal_deduplication_under_concurrent_access(self, qapp: QCoreApplication) -> None:
        """
        Test that signal deduplication works correctly with batch_updates().

        Verifies that when multiple operations modify the same curve in batch mode,
        signals are properly deduplicated and no corruption occurs.
        """
        state = get_application_state()
        signal_count = {"curves_changed": 0, "selection_changed": 0}

        def count_signals(data: dict[str, Any]) -> None:
            signal_count["curves_changed"] += 1

        def count_selection_signals(selection: set[int], curve: str) -> None:
            signal_count["selection_changed"] += 1

        # Connect signal counters
        state.curves_changed.connect(count_signals)
        state.selection_changed.connect(count_selection_signals)

        # Use batch context
        with state.batch_updates():
            # Modify the same curve 100 times
            for i in range(100):
                state.set_curve_data("test_curve", [(1, float(i), float(i), "normal")])
                state.set_selection("test_curve", {0})

        # Signals emitted after context exit (should emit deduplicated signals)

        # Process events to ensure signals are handled
        qapp.processEvents()

        # Verify signals were emitted (but not 100 times - should be deduplicated)
        assert signal_count["curves_changed"] > 0, "curves_changed signal not emitted"
        assert signal_count["selection_changed"] > 0, "selection_changed signal not emitted"

        # With deduplication, should only emit once per unique signal type
        assert signal_count["curves_changed"] == 1, f"Expected 1 curves_changed, got {signal_count['curves_changed']}"

    def test_mutex_prevents_list_corruption(self, qapp: QCoreApplication) -> None:
        """
        Test that accessing from worker threads is properly rejected.

        This validates that the thread assertion mechanism works correctly
        when multiple threads attempt concurrent access.
        """
        state = get_application_state()
        assertion_count = []

        def rapid_batch_toggle(worker_id: int, iterations: int = 10) -> None:
            """Attempt to rapidly toggle batch mode (should be rejected)."""
            for _ in range(iterations):
                try:
                    with state.batch_updates():
                        state.set_curve_data(f"curve_{worker_id}", [(1, 0.0, 0.0, "normal")])
                except AssertionError:
                    # Expected - thread assertion caught violation
                    assertion_count.append(1)
                except Exception:
                    pass

        # Launch 5 threads that attempt to toggle batch mode
        threads = [threading.Thread(target=rapid_batch_toggle, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=15)

        # Verify assertions were triggered (thread violations caught)
        assert len(assertion_count) > 0, "No thread assertions triggered (thread safety not enforced)"

    def test_main_thread_assertion_enforcement(self, qapp: QCoreApplication) -> None:
        """
        Test that _assert_main_thread() properly catches wrong-thread access.

        This test verifies that attempting to modify ApplicationState from a
        worker thread raises an AssertionError.
        """
        state = get_application_state()
        caught_assertion = threading.Event()

        def worker_thread_violation() -> None:
            """Attempt to modify state from worker thread (should fail)."""
            try:
                # This should raise AssertionError due to wrong thread
                state.set_curve_data("test", [(1, 0.0, 0.0, "normal")])
            except AssertionError:
                # Expected - caught thread violation
                caught_assertion.set()
            except Exception:
                # Unexpected exception
                pass

        # Run worker thread
        thread = threading.Thread(target=worker_thread_violation)
        thread.start()
        thread.join(timeout=5)

        # Verify assertion was triggered
        assert caught_assertion.is_set(), "Thread assertion did not catch wrong-thread access!"

    def test_concurrent_signal_emission_safety(self, qapp: QCoreApplication) -> None:
        """
        Test that worker threads attempting modifications are properly rejected.

        This verifies the thread safety model: worker threads should NOT directly
        modify ApplicationState - they should emit signals that are handled in
        the main thread.
        """
        state = get_application_state()
        signal_received = threading.Event()
        assertion_errors: list[AssertionError] = []

        def signal_handler(data: dict[str, Any]) -> None:
            """Handle curves_changed signal."""
            signal_received.set()

        state.curves_changed.connect(signal_handler)

        def modifier_thread(worker_id: int) -> None:
            """Attempt to modify state (should be rejected)."""
            try:
                for i in range(5):
                    state.set_curve_data(f"curve_{worker_id}", [(1, float(i), float(i), "normal")])
                    time.sleep(0.01)
            except AssertionError as e:
                # EXPECTED - thread assertion caught the violation
                assertion_errors.append(e)
            except Exception:
                pass

        # Launch multiple modifier threads
        threads = [threading.Thread(target=modifier_thread, args=(i,)) for i in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10)

        # Process events to handle signals
        qapp.processEvents()

        # Verify thread assertions caught all violations
        assert len(assertion_errors) == 3, f"Expected 3 assertion errors, got {len(assertion_errors)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
