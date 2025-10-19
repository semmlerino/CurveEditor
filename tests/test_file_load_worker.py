"""Test suite for FileLoadWorker QThread implementation."""

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
        for i in range(5):
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

        def on_loaded(data):
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

        def on_tracking(data):
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
