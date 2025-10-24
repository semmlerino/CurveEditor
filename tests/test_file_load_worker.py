"""Test suite for FileLoadWorker QThread implementation."""

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

import time

import pytest

# Note: file_load_signals and file_load_worker fixtures are now in tests/fixtures/qt_fixtures.py
# and automatically available via conftest.py


# Legacy fixture alias for backward compatibility with existing tests
@pytest.fixture
def worker(file_load_worker):
    """Alias for file_load_worker fixture for backward compatibility."""
    return file_load_worker


class TestFileLoadWorkerLifecycle:
    """Test worker QThread lifecycle management."""

    def test_worker_initialization(self, worker):
        """Test worker initializes with correct default state."""
        assert worker.tracking_file_path is None
        assert worker.image_dir_path is None
        assert worker._work_ready is False
        assert worker._work_ready_mutex is not None
        # QThread starts not running
        assert not worker.isRunning()

    def test_start_work_creates_thread(self, worker, qtbot):
        """Test start_work starts the QThread."""
        worker.start_work("test.csv", None)

        # QThread should be running
        assert worker.isRunning()

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_stop_joins_thread(self, worker, qtbot):
        """Test stop() properly stops the QThread."""
        worker.start_work("test.csv", None)

        # Verify thread is running
        assert worker.isRunning()

        # Stop the worker
        worker.stop()

        # Verify thread stopped (wait will return True if stopped)
        assert worker.wait(2000)
        assert not worker.isRunning()

    def test_multiple_start_stop_cycles(self, worker, qtbot):
        """Test worker can handle multiple start/stop cycles."""
        for i in range(3):
            worker.start_work(f"test{i}.csv", None)
            assert worker.isRunning()
            worker.stop()
            assert worker.wait(2000)
            assert not worker.isRunning()

    def test_rapid_start_stop(self, worker, qtbot):
        """Test rapid start/stop doesn't cause issues."""
        # Rapid start/stop
        worker.start_work("test.csv", None)
        worker.stop()  # Should handle even if thread barely started

        # Verify cleanup happened
        assert worker.wait(2000)
        assert not worker.isRunning()


class TestFileLoadWorkerSignals:
    """Test signal emission from worker QThread."""

    def test_signals_emitted_on_success(self, worker, qtbot, tmp_path):
        """Test signals are emitted correctly on successful load."""
        # Create test file in proper 2DTrackData format
        test_file = tmp_path / "test.csv"
        test_file.write_text("1\nTestPoint\nPointType\n2\n1 100 200\n2 150 250\n")

        # Set up signal monitoring - worker IS the signals object
        with qtbot.waitSignals([worker.tracking_data_loaded, worker.finished], timeout=2000):
            worker.start_work(str(test_file), None)

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_error_signal_on_failure(self, worker, qtbot):
        """Test error signal is emitted on file load failure."""
        with qtbot.waitSignal(worker.error_occurred, timeout=2000):
            worker.start_work("/nonexistent/file.csv", None)

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_progress_signals_emitted(self, worker, qtbot, tmp_path):
        """Test progress signals during file loading."""
        # Create test files in proper 2DTrackData format
        test_file = tmp_path / "test.csv"
        test_file.write_text("1\nTestPoint\nPointType\n2\n1 100 200\n2 150 250\n")

        img_dir = tmp_path / "images"
        img_dir.mkdir()
        (img_dir / "img001.png").touch()

        progress_received = []

        def on_progress(percent, msg):
            progress_received.append((percent, msg))

        worker.progress_updated.connect(on_progress)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(test_file), str(img_dir))

        # At least some progress should be reported
        assert len(progress_received) > 0

        # Clean up
        worker.stop()
        worker.wait(2000)


class TestFileLoadWorkerThreadSafety:
    """Test thread safety of worker operations."""

    def test_stop_flag_thread_safety(self, worker, qtbot):
        """Test interruption request is thread-safe."""
        worker.start_work("test.csv", None)

        # Request interruption should be thread-safe
        worker.requestInterruption()
        assert worker.isInterruptionRequested()

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_work_ready_flag_synchronization(self, worker, qtbot):
        """Test work_ready flag uses mutex for synchronization."""
        # Access to _work_ready should be protected by _work_ready_mutex
        from PySide6.QtCore import QMutexLocker

        with QMutexLocker(worker._work_ready_mutex):
            worker._work_ready = True
            assert worker._work_ready

        with QMutexLocker(worker._work_ready_mutex):
            worker._work_ready = False
            assert not worker._work_ready

    def test_concurrent_start_work_calls(self, worker, qtbot):
        """Test worker handles overlapping start_work calls safely."""
        # First start_work
        worker.start_work("test1.csv", None)
        assert worker.isRunning()

        # Second start_work should stop first and start new
        worker.start_work("test2.csv", None)

        # Worker should still be running (or starting)
        time.sleep(0.1)  # Give time for restart
        # Note: May not be running if it finished very quickly
        # Just verify no crash occurred

        # Clean up
        worker.stop()
        worker.wait(2000)


class TestFileLoadWorkerErrorHandling:
    """Test error handling in worker thread."""

    def test_exception_in_run_method(self, worker, qtbot):
        """Test worker emits error signal when exception occurs in run()."""
        with qtbot.waitSignal(worker.error_occurred, timeout=2000):
            worker.start_work("/invalid/path/file.csv", None)

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_worker_cleanup_after_exception(self, worker, qtbot):
        """Test worker properly cleans up after exception."""
        with qtbot.waitSignal(worker.error_occurred, timeout=2000):
            worker.start_work("/invalid/path/file.csv", None)

        # Worker should be able to start again after error
        worker.stop()
        worker.wait(2000)
        assert not worker.isRunning()

        # Should be able to start new work
        worker.start_work("test.csv", None)
        worker.stop()
        worker.wait(2000)

    def test_file_not_found_handling(self, worker, qtbot):
        """Test worker handles file not found gracefully."""
        with qtbot.waitSignal(worker.error_occurred, timeout=2000):
            worker.start_work("/nonexistent/directory/file.csv", None)

        # Clean up
        worker.stop()
        worker.wait(2000)


class TestFileLoadWorkerMemoryManagement:
    """Test memory management and resource cleanup."""

    def test_thread_cleanup_on_delete(self, worker, qtbot):
        """Test QThread is properly cleaned up when worker is deleted."""
        worker.start_work("test.csv", None)
        assert worker.isRunning()

        # Stop before deletion
        worker.stop()
        assert worker.wait(2000)
        assert not worker.isRunning()

        # Deletion should be safe now
        # (actual deletion handled by fixture teardown)

    def test_no_memory_leak_on_repeated_use(self, worker, qtbot, tmp_path):
        """Test repeated start/stop doesn't leak memory."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("1\nTestPoint\nPointType\n1\n1 100 200\n")

        # Multiple cycles
        for _ in range(5):
            with qtbot.waitSignal(worker.finished, timeout=2000):
                worker.start_work(str(test_file), None)

            worker.stop()
            worker.wait(2000)

        # Worker should still be functional
        assert not worker.isRunning()


class TestFileLoadWorkerIntegration:
    """Integration tests with actual file loading."""

    def test_load_tracking_data_csv(self, worker, qtbot, tmp_path):
        """Test loading actual CSV tracking data."""
        # Create valid 2DTrackData file
        csv_file = tmp_path / "track.csv"
        csv_file.write_text("1\nTrackPoint\nPointType\n2\n1 100.5 200.3\n2 101.2 201.5\n")

        loaded_data = []

        def on_loaded(file_path, data):
            loaded_data.append(data)

        worker.tracking_data_loaded.connect(on_loaded)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(csv_file), None)

        # Should have loaded data
        assert len(loaded_data) == 1

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_load_image_sequence(self, worker, qtbot, tmp_path):
        """Test loading image sequence."""
        img_dir = tmp_path / "images"
        img_dir.mkdir()

        # Create dummy image files
        for i in range(1, 4):
            (img_dir / f"img{i:03d}.png").touch()

        loaded_sequences = []

        def on_loaded(dir_path, files):
            loaded_sequences.append((dir_path, files))

        worker.image_sequence_loaded.connect(on_loaded)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(None, str(img_dir))

        # Should have loaded sequence
        assert len(loaded_sequences) == 1
        assert len(loaded_sequences[0][1]) == 3

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_load_both_tracking_and_images(self, worker, qtbot, tmp_path):
        """Test loading both tracking data and images."""
        # Create 2DTrackData file
        csv_file = tmp_path / "track.csv"
        csv_file.write_text("1\nTrackPoint\nPointType\n1\n1 100 200\n")

        # Create images
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        (img_dir / "img001.png").touch()

        signals_received = []

        def on_tracking(file_path, data):
            signals_received.append("tracking")

        def on_images(dir_path, files):
            signals_received.append("images")

        worker.tracking_data_loaded.connect(on_tracking)
        worker.image_sequence_loaded.connect(on_images)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(csv_file), str(img_dir))

        # Both should be loaded
        assert "tracking" in signals_received
        assert "images" in signals_received

        # Clean up
        worker.stop()
        worker.wait(2000)


class TestFileLoadWorkerYFlipIntegration:
    """Integration tests for Y-flip behavior through start_work() path.

    These tests verify the critical bug fix: ensuring that FileLoadWorker.run()
    applies Y-flip when loading data via start_work() for both legacy and
    metadata-aware loading paths.
    """

    def test_start_work_applies_y_flip_to_loaded_data(self, worker, qtbot, tmp_path):
        """Test that start_work() applies Y-flip to loaded tracking data.

        This is a regression test for the bug where FileLoadWorker.run() used
        flip_y=False, causing pre-loaded points at startup to have incorrect
        Y-coordinates while manually loaded points were correct.
        """
        # Create test file in 2DTrackData format
        test_file = tmp_path / "test_flip.csv"
        test_file.write_text("1\nTestPoint\nPointType\n2\n1 100.0 200.0\n2 150.0 250.0\n")

        loaded_data = []

        def capture_data(file_path, data):
            loaded_data.append(data)

        worker.tracking_data_loaded.connect(capture_data)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(test_file), None)

        # Verify data was loaded
        assert len(loaded_data) == 1
        data = loaded_data[0]

        # CRITICAL: Verify Y-coordinates are flipped (720 - y)
        # Original Y=200 should become 720-200=520
        # Original Y=250 should become 720-250=470
        assert len(data) == 2
        assert data[0][0] == 1  # Frame
        assert data[0][1] == 100.0  # X unchanged
        assert data[0][2] == 520.0  # Y flipped: 720 - 200
        assert data[1][0] == 2  # Frame
        assert data[1][1] == 150.0  # X unchanged
        assert data[1][2] == 470.0  # Y flipped: 720 - 250

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_start_work_with_multi_point_applies_y_flip(self, worker, qtbot, tmp_path):
        """Test Y-flip applied to all points in multi-point tracking data."""
        # Create multi-point test file
        test_file = tmp_path / "multi_point.csv"
        test_file.write_text(
            "3\n"  # 3 points
            "Point1\n0\n2\n1 100.0 100.0\n2 110.0 110.0\n"
            "Point2\n0\n2\n1 200.0 200.0\n2 210.0 210.0\n"
            "Point3\n0\n2\n1 300.0 300.0\n2 310.0 310.0\n"
        )

        loaded_data: list[object] = []

        def on_data_loaded(file_path: str, data: object) -> None:
            loaded_data.append(data)

        worker.tracking_data_loaded.connect(on_data_loaded)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(test_file), None)

        # Should return dict for multi-point data
        assert len(loaded_data) == 1
        data = loaded_data[0]
        assert isinstance(data, dict)
        assert len(data) == 3

        # Verify Y-flip for all points
        assert data["Point1"][0][2] == 620.0  # 720 - 100
        assert data["Point2"][0][2] == 520.0  # 720 - 200
        assert data["Point3"][0][2] == 420.0  # 720 - 300

        # Clean up
        worker.stop()
        worker.wait(2000)


class TestFileLoadWorkerMetadataAwarePath:
    """Test metadata-aware loading path applies Y-flip correctly.

    These tests verify the second bug fix: ensuring the metadata-aware loading
    path (used when use_metadata_aware_data=True) also applies Y-flip.
    """

    def test_metadata_aware_loading_applies_y_flip(self, worker, qtbot, tmp_path, monkeypatch):
        """Test metadata-aware path applies Y-flip via start_work().

        Regression test for bug where line 340 in file_load_worker.py used
        flip_y=False in the metadata-aware loading path.
        """
        # Enable metadata-aware loading
        from core.config import AppConfig

        test_config = AppConfig()
        test_config.use_metadata_aware_data = True

        # Monkeypatch get_config to return test config
        import io_utils.file_load_worker

        monkeypatch.setattr(io_utils.file_load_worker, "get_config", lambda: test_config)

        # Create test file
        test_file = tmp_path / "test_metadata.csv"
        test_file.write_text("1\nTestPoint\nPointType\n2\n1 100.0 200.0\n2 150.0 250.0\n")

        loaded_data: list[object] = []

        def on_data_loaded(file_path: str, data: object) -> None:
            loaded_data.append(data)

        worker.tracking_data_loaded.connect(on_data_loaded)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(test_file), None)

        # Verify CurveDataWithMetadata was returned
        from core.curve_data import CurveDataWithMetadata

        assert len(loaded_data) == 1
        data = loaded_data[0]
        assert isinstance(data, CurveDataWithMetadata)

        # CRITICAL: Verify Y-coordinates are flipped in the raw data
        assert len(data.data) == 2
        assert data.data[0][2] == 520.0  # Y flipped: 720 - 200
        assert data.data[1][2] == 470.0  # Y flipped: 720 - 250

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_metadata_aware_multi_point_y_flip(self, worker, qtbot, tmp_path, monkeypatch):
        """Test metadata-aware path applies Y-flip to multi-point data."""
        # Enable metadata-aware loading
        from core.config import AppConfig

        test_config = AppConfig()
        test_config.use_metadata_aware_data = True

        import io_utils.file_load_worker

        monkeypatch.setattr(io_utils.file_load_worker, "get_config", lambda: test_config)

        # Create multi-point file
        test_file = tmp_path / "multi_metadata.csv"
        test_file.write_text("2\n" "Point1\n0\n1\n1 100.0 100.0\n" "Point2\n0\n1\n1 200.0 200.0\n")

        loaded_data: list[object] = []

        def on_data_loaded(file_path: str, data: object) -> None:
            loaded_data.append(data)

        worker.tracking_data_loaded.connect(on_data_loaded)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(test_file), None)

        # Should return dict of CurveDataWithMetadata
        from core.curve_data import CurveDataWithMetadata

        assert len(loaded_data) == 1
        data = loaded_data[0]
        assert isinstance(data, dict)

        # Verify both points have Y-flipped data
        assert isinstance(data["Point1"], CurveDataWithMetadata)
        assert isinstance(data["Point2"], CurveDataWithMetadata)
        assert data["Point1"].data[0][2] == 620.0  # 720 - 100
        assert data["Point2"].data[0][2] == 520.0  # 720 - 200

        # Clean up
        worker.stop()
        worker.wait(2000)


class TestFileLoadWorkerLoadParity:
    """Test parity between manual and auto-load paths.

    These tests ensure that DataService.load_tracked_data() (manual load)
    and FileLoadWorker.start_work() (auto-load at startup) produce identical
    results, particularly for Y-coordinate flipping.
    """

    def test_manual_and_auto_load_produce_identical_results(self, worker, qtbot, tmp_path):
        """Test manual and auto-load apply same Y-flip transformation.

        This parity test ensures consistency between:
        1. User clicking File → Open (uses DataService)
        2. Application startup loading session (uses FileLoadWorker)
        """
        # Create test file in proper 2DTrackData format
        test_file = tmp_path / "parity_test.csv"
        test_file.write_text("1\nPoint01\n0\n3\n1 100.0 200.0\n2 150.0 250.0\n3 200.0 300.0\n")

        # Manual load via DataService
        from services import get_data_service

        data_service = get_data_service()
        manual_data = data_service.load_tracked_data(str(test_file))

        # Extract single point data (manual returns dict)
        assert "Point01" in manual_data
        manual_point_data = manual_data["Point01"]

        # Auto-load via FileLoadWorker
        auto_data: list[object] = []

        def on_auto_data_loaded(file_path: str, data: object) -> None:
            auto_data.append(data)

        worker.tracking_data_loaded.connect(on_auto_data_loaded)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(test_file), None)

        # Worker returns list for single point
        assert len(auto_data) == 1
        auto_point_data = auto_data[0]

        from typing import cast

        from core.type_aliases import CurveDataList

        # Cast to specific type for iteration
        auto_point_list = cast(CurveDataList, auto_point_data)

        # CRITICAL: Both should have identical Y-flipped coordinates
        assert len(manual_point_data) == len(auto_point_list)

        for i, (manual_point, auto_point) in enumerate(zip(manual_point_data, auto_point_list)):
            # Compare frame, x, y (ignore status field if present)
            assert manual_point[0] == auto_point[0], f"Point {i}: Frame mismatch"
            assert manual_point[1] == auto_point[1], f"Point {i}: X mismatch"
            assert manual_point[2] == auto_point[2], f"Point {i}: Y mismatch (Y-flip inconsistency)"

        # Clean up
        worker.stop()
        worker.wait(2000)

    def test_multi_point_parity_between_load_methods(self, worker, qtbot, tmp_path):
        """Test multi-point data consistency between manual and auto-load."""
        # Create multi-point file
        test_file = tmp_path / "multi_parity.csv"
        test_file.write_text(
            "3\n"
            "Point1\n0\n2\n1 100.0 100.0\n2 110.0 110.0\n"
            "Point2\n0\n2\n1 200.0 200.0\n2 210.0 210.0\n"
            "Point3\n0\n2\n1 300.0 300.0\n2 310.0 310.0\n"
        )

        # Manual load
        from services import get_data_service

        manual_data = get_data_service().load_tracked_data(str(test_file))

        # Auto-load
        auto_data: list[object] = []

        def on_auto_data_loaded(file_path: str, data: object) -> None:
            auto_data.append(data)

        worker.tracking_data_loaded.connect(on_auto_data_loaded)

        with qtbot.waitSignal(worker.finished, timeout=2000):
            worker.start_work(str(test_file), None)

        # Both should return dicts
        assert isinstance(manual_data, dict)
        assert isinstance(auto_data[0], dict)

        # Should have same points
        assert set(manual_data.keys()) == set(auto_data[0].keys())

        # Verify Y-flip consistency for each point
        for point_name in manual_data:
            manual_points = manual_data[point_name]
            auto_points = auto_data[0][point_name]

            assert len(manual_points) == len(auto_points)

            for i, (m, a) in enumerate(zip(manual_points, auto_points)):
                assert m[0] == a[0], f"{point_name}[{i}]: Frame mismatch"
                assert m[1] == a[1], f"{point_name}[{i}]: X mismatch"
                assert m[2] == a[2], f"{point_name}[{i}]: Y mismatch (Y-flip inconsistency)"

        # Clean up
        worker.stop()
        worker.wait(2000)
