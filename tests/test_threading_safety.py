#!/usr/bin/env python3
"""
Threading safety test suite for CurveEditor.

Tests all concurrent access patterns and verifies thread safety of:
- Service singleton initialization
- Cache operations
- History management
- Transform caching
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

import concurrent.futures
import threading
import time
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from services import (
    get_data_service,
    get_interaction_service,
    get_transform_service,
    get_ui_service,
)


class TestServiceThreadSafety:
    """Test thread safety of service layer."""

    def test_singleton_initialization_race(self):
        """Verify only one instance created under concurrent access."""
        results = set()
        barrier = threading.Barrier(20)  # Synchronize thread start

        def get_service():
            barrier.wait()  # All threads start together
            service = get_data_service()
            results.add(id(service))
            return service

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(get_service) for _ in range(100)]
            concurrent.futures.wait(futures)

        assert len(results) == 1, f"Multiple instances created: {len(results)}"

    def test_all_services_singleton_pattern(self):
        """Test that all services maintain singleton pattern under concurrent access."""
        services_to_test = [
            ("DataService", get_data_service),
            ("TransformService", get_transform_service),
            ("InteractionService", get_interaction_service),
            ("UIService", get_ui_service),
        ]

        for service_name, getter_func in services_to_test:
            results = set()
            barrier = threading.Barrier(10)

            def get_service(func=getter_func, barrier_obj=barrier, result_set=results):
                barrier_obj.wait()
                service = func()
                result_set.add(id(service))
                return service

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_service) for _ in range(50)]
                concurrent.futures.wait(futures)

            assert len(results) == 1, f"{service_name}: Multiple instances created ({len(results)})"

    def test_data_service_cache_concurrent_modifications(self):
        """Test DataService cache operations under heavy concurrent load."""
        service = get_data_service()
        errors = []

        def cache_stress_test(thread_id: int):
            try:
                for i in range(1000):
                    # Rapid cache operations
                    file_path = f"/tmp/test_{thread_id}_{i}.json"
                    service.add_recent_file(file_path)

                    # Verify recent files list integrity
                    recent = service._recent_files
                    if len(recent) > service._max_recent_files:
                        errors.append(f"Recent files exceeded limit: {len(recent)}")

            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = []
        for i in range(10):
            t = threading.Thread(target=cache_stress_test, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)
            if t.is_alive():
                import warnings

                warnings.warn(f"Thread {t.name} did not stop within timeout", stacklevel=2)

        assert not errors, f"Errors detected: {errors[:5]}"  # Show first 5 errors

    def test_transform_service_cache_concurrent_access(self):
        """Test TransformService cache under concurrent access."""
        from services.transform_service import ViewState

        service = get_transform_service()
        errors = []
        transforms_created = []

        def transform_operations(thread_id: int):
            try:
                for i in range(100):
                    # Create different view states
                    view_state = ViewState(
                        display_width=1920,
                        display_height=1080,
                        widget_width=800,
                        widget_height=600,
                        zoom_factor=1.0 + thread_id * 0.1,
                        offset_x=float(i),
                        offset_y=float(i),
                        scale_to_image=True,
                        flip_y_axis=False,
                        manual_x_offset=0.0,
                        manual_y_offset=0.0,
                    )

                    # Create transform (should use cache when appropriate)
                    transform = service.create_transform_from_view_state(view_state)
                    transforms_created.append(id(transform))

            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(transform_operations, i) for i in range(5)]
            concurrent.futures.wait(futures)

        assert not errors, f"Errors detected: {errors}"
        # Cache should be working (not all transforms unique)
        assert len(set(transforms_created)) < len(transforms_created), "Cache not being used"




    def test_service_initialization_with_exceptions(self):
        """Test that service initialization handles exceptions properly."""
        # This tests that even if initialization fails, the lock is properly released

        call_count = []

        def failing_init():
            call_count.append(1)
            if len(call_count) == 1:
                raise RuntimeError("Simulated initialization failure")
            return MagicMock()  # Second attempt succeeds

        with patch("services.data_service.DataService", side_effect=failing_init):
            results = []

            def try_get_service(thread_id: int):
                try:
                    get_data_service()
                    results.append(("success", thread_id))
                except RuntimeError:
                    results.append(("failure", thread_id))

            # Clear the singleton first
            import services

            services._data_service = None

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(try_get_service, i) for i in range(3)]
                concurrent.futures.wait(futures)

            # At least one should fail, others might succeed
            failures = [r for r in results if r[0] == "failure"]
            assert len(failures) >= 1, "Expected at least one initialization failure"


class TestConcurrentUserWorkflows:
    """Test realistic concurrent user workflows."""

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window for testing."""
        window = MagicMock()
        window.curve_widget = MagicMock()
        window.curve_widget.curve_data = []
        window.curve_widget.selected_indices = set()
        return window

    def test_concurrent_file_operations(self, mock_main_window):
        """Test concurrent file loading and saving."""
        service = get_data_service()
        operations_completed = []

        def file_operation(op_id: int):
            try:
                # Simulate file loading
                for i in range(10):
                    file_path = f"/tmp/data_{op_id}_{i}.json"
                    service.add_recent_file(file_path)

                    # Simulate some processing
                    time.sleep(0.001)

                operations_completed.append(op_id)
            except Exception as e:
                pytest.fail(f"Operation {op_id} failed: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(file_operation, i) for i in range(5)]
            concurrent.futures.wait(futures)

        assert len(operations_completed) == 5, "Not all operations completed"

        # Verify recent files list is consistent
        assert len(service._recent_files) <= 10  # Use hardcoded value


class TestStressTests:
    """Stress tests for thread safety."""

    def test_high_contention_service_access(self):
        """Test services under extremely high contention."""
        services = [
            get_data_service,
            get_transform_service,
            get_interaction_service,
            get_ui_service,
        ]

        barrier = threading.Barrier(50)
        errors = []

        def stress_test(thread_id: int):
            try:
                barrier.wait()  # All threads start simultaneously

                # Rapidly get all services
                for _ in range(100):
                    for getter in services:
                        service = getter()
                        assert service is not None

            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(stress_test, i) for i in range(50)]
            concurrent.futures.wait(futures)

        assert not errors, f"Errors under high contention: {errors[:5]}"

    def test_memory_consistency(self):
        """Test that shared state remains consistent under concurrent access."""
        service = get_data_service()

        # Track all values seen by threads
        seen_values = []
        lock = threading.Lock()

        def reader_thread():
            for _ in range(1000):
                files = service._recent_files.copy()
                with lock:
                    seen_values.append(len(files))

        def writer_thread(thread_id: int):
            for i in range(1000):
                service.add_recent_file(f"/tmp/file_{thread_id}_{i}.json")

        # Start readers and writers
        threads = []
        for _ in range(3):
            t = threading.Thread(target=reader_thread)
            threads.append(t)
            t.start()

        for i in range(3):
            t = threading.Thread(target=writer_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)
            if t.is_alive():
                import warnings

                warnings.warn(f"Thread {t.name} did not stop within timeout", stacklevel=2)

        # All seen values should be within valid range
        for value in seen_values:
            assert 0 <= value <= 10, f"Invalid list size seen: {value}"


class TestQtThreadingSafety:
    """Test Qt-specific threading safety patterns to prevent fatal crashes."""

    def test_thread_safe_image_creation(self):
        """Test QImage can be created safely in worker threads."""
        from PySide6.QtGui import QImage

        results = []
        errors = []

        def create_image_in_thread(thread_id: int):
            """Create and manipulate image in worker thread."""
            try:
                # ✅ SAFE - Use QImage instead of QPixmap (QPixmap requires main thread)
                image = QImage(100, 100, QImage.Format.Format_RGB32)

                # Thread-safe operations
                assert not image.isNull()
                assert image.width() == 100
                assert image.height() == 100
                assert image.sizeInBytes() > 0

                # Fill with color (thread-safe QImage operation)
                from PySide6.QtGui import QColor

                image.fill(QColor(255, 0, 0))

                results.append((thread_id, True))

            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple worker threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=create_image_in_thread, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)
            assert not t.is_alive(), "Thread should have completed"

        # Verify no threading violations occurred
        assert len(errors) == 0, f"Threading errors: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        # All operations should have succeeded
        for thread_id, success in results:
            assert success, f"Thread {thread_id} failed"


    def test_qt_pixmap_detection_in_worker_threads(self):
        """Test that QPixmap creation in worker threads is properly detected."""
        import threading
        from unittest.mock import patch

        thread_violations = []

        def check_thread_safety(*args, **kwargs):
            """Mock QPixmap constructor to detect thread violations."""
            current_thread = threading.current_thread()
            if current_thread.name != "MainThread":
                thread_violations.append(f"QPixmap created in {current_thread.name}")
                # Raise exception to prevent actual QPixmap creation which would crash
                raise RuntimeError(f"QPixmap cannot be created in worker thread: {current_thread.name}")

        def worker_thread_function():
            """Function that would violate Qt threading rules."""
            try:
                # This would normally crash Python with "Fatal Python error: Aborted"
                from PySide6.QtGui import QPixmap

                _pixmap = QPixmap(100, 100)  # Should be detected and prevented
            except RuntimeError:
                # Expected - our detection prevented the crash
                pass

        # Patch QPixmap to detect threading violations
        with patch("PySide6.QtGui.QPixmap", side_effect=check_thread_safety):
            worker_thread = threading.Thread(target=worker_thread_function)
            worker_thread.start()
            worker_thread.join(timeout=5.0)
            if worker_thread.is_alive():
                import warnings

                warnings.warn(f"Thread {worker_thread.name} did not stop within timeout", stacklevel=2)

        # Verify violation was detected
        assert len(thread_violations) == 1, f"Expected 1 violation, got: {thread_violations}"
        assert "QPixmap created in Thread-" in thread_violations[0]

    def test_image_size_consistency(self):
        """Test that QImage provides consistent interface."""
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QImage

        image = QImage(200, 150, QImage.Format.Format_RGB32)

        # Test size methods match
        assert image.width() == 200
        assert image.height() == 150

        size = image.size()
        assert isinstance(size, QSize)
        assert size.width() == 200
        assert size.height() == 150

        # Test image is properly initialized
        assert not image.isNull()
        assert image.sizeInBytes() > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
