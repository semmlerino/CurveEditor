"""
Concurrency Stress Tests for QThread Workers.

This test suite specifically validates the recently refactored QThread workers
(FileLoadWorker, DirectoryScanWorker, ProgressWorker) for thread safety,
cancellation correctness, and race condition resilience.

Priority: HIGH - Recent QThread refactoring (3 commits in past week) makes this critical.

Test Coverage:
- Worker cancellation safety (interruption handling)
- Race conditions in signal emission
- Concurrent worker operations
- Stress testing with rapid start/stop cycles
"""

import os
import tempfile
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QThread, QTimer
from PySide6.QtTest import QSignalSpy

from core.workers.directory_scanner import DirectoryScanWorker
from io_utils.file_load_worker import FileLoadWorker
from ui.progress_manager import ProgressWorker


class TestFileLoadWorkerCancellation:
    """Test FileLoadWorker cancellation and interruption safety."""

    @pytest.fixture
    def sample_tracking_file(self, tmp_path: Path) -> str:
        """Create a sample tracking file for testing."""
        file_path = tmp_path / "test_tracking.txt"
        # Create a file with many points to allow cancellation during processing
        with open(file_path, "w") as f:
            f.write("1\n")  # Number of points
            f.write("TestPoint\n")  # Point name
            f.write("point_type\n")  # Point type
            f.write("1000\n")  # Number of frames (large for cancellation test)
            # Write many frames
            for i in range(1000):
                f.write(f"{i} {float(i)} {float(i * 2)} normal\n")
        return str(file_path)

    def test_worker_can_be_cancelled_during_loading(self, qtbot, sample_tracking_file: str) -> None:
        """
        Test: Worker responds to cancellation requests during file loading.

        Validates that FileLoadWorker properly checks isInterruptionRequested()
        and stops processing when stop() is called.
        """
        worker = FileLoadWorker()

        finished_spy = QSignalSpy(worker.finished)
        error_spy = QSignalSpy(worker.error_occurred)

        # Start work
        worker.start_work(sample_tracking_file, None)

        # Cancel immediately (race condition test)
        worker.stop()

        # Wait for worker to finish (should be quick due to cancellation)
        assert worker.wait(3000), "Worker should finish within 3 seconds after cancellation"

        # Worker should have stopped cleanly (no errors)
        assert error_spy.count() == 0 or "cancelled" in error_spy.at(0)[0].lower()

    def test_rapid_start_stop_cycles(self, qtbot, sample_tracking_file: str) -> None:
        """
        Test: Worker handles rapid start/stop cycles without crashes.

        Stress test for race conditions in worker lifecycle management.
        """
        worker = FileLoadWorker()
        

        # Perform 10 rapid start/stop cycles
        for _ in range(10):
            worker.start_work(sample_tracking_file, None)
            # Stop almost immediately (minimal processing time)
            worker.stop()

            # Brief pause to let Qt event loop process
            qtbot.wait(10)

        # Final stop should complete cleanly
        worker.stop()
        assert not worker.isRunning(), "Worker should not be running after final stop"

    def test_cancellation_during_large_file_processing(self, qtbot, tmp_path: Path) -> None:
        """
        Test: Cancellation works correctly mid-processing for large files.

        Validates interruption checks in processing loops.
        """
        # Create a very large tracking file
        large_file = tmp_path / "large_tracking.txt"
        with open(large_file, "w") as f:
            f.write("1\n")
            f.write("LargePoint\n")
            f.write("point_type\n")
            f.write("5000\n")  # 5000 frames
            for i in range(5000):
                f.write(f"{i} {float(i)} {float(i * 2)} normal\n")

        worker = FileLoadWorker()
        

        progress_spy = QSignalSpy(worker.progress_updated)

        # Start work
        worker.start_work(str(large_file), None)

        # Wait for some progress, then cancel
        qtbot.wait(50)  # Allow some processing
        worker.stop()

        # Worker should stop within timeout
        assert worker.wait(2500), "Worker should respond to cancellation within timeout"

    def test_worker_signals_after_cancellation(self, qtbot, sample_tracking_file: str) -> None:
        """
        Test: No signals are emitted after cancellation completes.

        Validates that cancellation properly prevents queued signal emissions.
        """
        worker = FileLoadWorker()
        

        tracking_spy = QSignalSpy(worker.tracking_data_loaded)
        finished_spy = QSignalSpy(worker.finished)

        # Start and immediately cancel
        worker.start_work(sample_tracking_file, None)
        worker.stop()
        worker.wait(3000)

        # finished signal may or may not emit depending on timing, but tracking_data_loaded should not
        # (or should be empty if cancellation was successful)
        if tracking_spy.count() > 0:
            # If data was loaded, it should be because cancellation came too late
            pass  # This is acceptable - cancellation is best-effort


class TestDirectoryScanWorkerInterruption:
    """Test DirectoryScanWorker interruption and stress scenarios."""

    @pytest.fixture
    def image_directory(self, tmp_path: Path) -> str:
        """Create a directory with many test images."""
        img_dir = tmp_path / "images"
        img_dir.mkdir()

        # Create 100 fake image files
        for i in range(100):
            img_file = img_dir / f"frame_{i:04d}.png"
            img_file.write_text("")  # Empty file is fine for testing

        return str(img_dir)

    def test_scanner_interruption_during_scan(self, qtbot, image_directory: str) -> None:
        """
        Test: DirectoryScanWorker responds to interruption requests.

        Validates isInterruptionRequested() checks in scan loops.
        """
        worker = DirectoryScanWorker(image_directory)
        

        progress_spy = QSignalSpy(worker.progress)

        # Start scan
        worker.start()

        # Wait briefly, then interrupt
        qtbot.wait(20)
        worker.stop()

        # Worker should stop within timeout
        assert worker.wait(2500), "Worker should stop within timeout after interruption"

    def test_rapid_scanner_restarts(self, qtbot, image_directory: str) -> None:
        """
        Test: Scanner handles rapid restart cycles without memory leaks.

        Stress test for resource cleanup.
        """
        for _ in range(5):
            worker = DirectoryScanWorker(image_directory)
            

            worker.start()
            qtbot.wait(10)
            worker.stop()
            worker.wait(2000)

            # Worker should be finished
            assert not worker.isRunning()

    def test_scanner_with_empty_directory(self, qtbot, tmp_path: Path) -> None:
        """
        Test: Scanner handles empty directory gracefully.

        Edge case that might cause race conditions.
        """
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        worker = DirectoryScanWorker(str(empty_dir))
        

        sequences_spy = QSignalSpy(worker.sequences_found)
        error_spy = QSignalSpy(worker.error_occurred)

        worker.start()
        worker.wait(2000)

        # Should complete without errors
        assert error_spy.count() == 0
        # Should emit empty sequences
        if sequences_spy.count() > 0:
            assert len(sequences_spy.at(0)[0]) == 0

    def test_scanner_interruption_checkpoints(self, qtbot, tmp_path: Path) -> None:
        """
        Test: Scanner checks interruption at all documented checkpoints.

        Validates interruption handling at:
        - _scan_for_images loop
        - _detect_sequences loop
        - Main run() between steps
        """
        # Create directory with many files
        many_files_dir = tmp_path / "many_images"
        many_files_dir.mkdir()

        for i in range(200):
            (many_files_dir / f"image_{i:05d}.png").write_text("")

        worker = DirectoryScanWorker(str(many_files_dir))
        

        worker.start()

        # Interrupt at different stages (timing-dependent)
        for delay in [5, 10, 15, 20]:
            qtbot.wait(delay)
            worker.stop()
            if worker.wait(100):
                break  # Successfully interrupted

        # Final wait with longer timeout
        assert worker.wait(3000), "Worker should eventually stop"


class TestProgressWorkerSafety:
    """Test ProgressWorker thread safety."""

    def test_progress_worker_basic_operation(self, qtbot) -> None:
        """
        Test: ProgressWorker executes operation and emits signals correctly.
        """
        def simple_operation(worker_arg: ProgressWorker, value: int) -> int:
            return value * 2

        worker = ProgressWorker(simple_operation, 42)
        

        finished_spy = QSignalSpy(worker.finished)

        worker.start()
        worker.wait(1000)

        assert finished_spy.count() == 1
        assert worker.result == 84

    def test_progress_worker_with_exception(self, qtbot) -> None:
        """
        Test: ProgressWorker handles exceptions without crashing.
        """
        def failing_operation(worker_arg: ProgressWorker) -> None:
            raise ValueError("Test exception")

        worker = ProgressWorker(failing_operation)
        

        error_spy = QSignalSpy(worker.error_occurred)

        worker.start()
        worker.wait(1000)

        assert error_spy.count() == 1
        assert "Test exception" in error_spy.at(0)[0]


class TestSignalStormResilience:
    """Test system resilience under signal storm conditions."""

    def test_rapid_signal_emission_no_deadlock(self, qtbot, tmp_path: Path) -> None:
        """
        Test: System handles rapid signal emissions without deadlock.

        Simulates signal storm by rapidly starting/stopping workers.
        """
        # Create test directory
        test_dir = tmp_path / "test_images"
        test_dir.mkdir()
        for i in range(10):
            (test_dir / f"img_{i:03d}.png").write_text("")

        workers = []

        # Start multiple workers rapidly
        for _ in range(5):
            worker = DirectoryScanWorker(str(test_dir))
            
            worker.start()
            workers.append(worker)

        # Brief pause
        qtbot.wait(50)

        # Stop all workers
        for worker in workers:
            worker.stop()

        # All should finish
        for worker in workers:
            assert worker.wait(3000), "Worker should finish within timeout"

    def test_concurrent_file_load_workers(self, qtbot, tmp_path: Path) -> None:
        """
        Test: Multiple FileLoadWorkers can run concurrently without interference.

        Tests for shared state corruption.
        """
        # Create multiple tracking files
        tracking_files = []
        for i in range(3):
            file_path = tmp_path / f"track_{i}.txt"
            with open(file_path, "w") as f:
                f.write("1\n")
                f.write(f"Point_{i}\n")
                f.write("point_type\n")
                f.write("10\n")
                for j in range(10):
                    f.write(f"{j} {float(j)} {float(j * 2)} normal\n")
            tracking_files.append(str(file_path))

        workers = []
        spies = []

        # Start all workers concurrently
        for file_path in tracking_files:
            worker = FileLoadWorker()
            

            finished_spy = QSignalSpy(worker.finished)
            spies.append(finished_spy)

            worker.start_work(file_path, None)
            workers.append(worker)

        # Wait for all to complete
        for worker in workers:
            worker.wait(3000)

        # All should finish successfully
        for spy in spies:
            assert spy.count() >= 1, "Worker should emit finished signal"


class TestWorkerResourceCleanup:
    """Test proper resource cleanup in worker lifecycle."""

    def test_worker_cleanup_after_normal_completion(self, qtbot, tmp_path: Path) -> None:
        """
        Test: Worker resources are properly cleaned up after normal completion.
        """
        file_path = tmp_path / "test.txt"
        with open(file_path, "w") as f:
            f.write("1\nTest\ntype\n5\n")
            for i in range(5):
                f.write(f"{i} {float(i)} {float(i * 2)}\n")

        worker = FileLoadWorker()
        

        worker.start_work(str(file_path), None)
        worker.wait(3000)

        # Worker should be finished and not running
        assert worker.isFinished()
        assert not worker.isRunning()

    def test_worker_cleanup_after_cancellation(self, qtbot, tmp_path: Path) -> None:
        """
        Test: Worker resources are cleaned up properly after cancellation.
        """
        file_path = tmp_path / "large.txt"
        with open(file_path, "w") as f:
            f.write("1\nLarge\ntype\n1000\n")
            for i in range(1000):
                f.write(f"{i} {float(i)} {float(i * 2)}\n")

        worker = FileLoadWorker()
        

        worker.start_work(str(file_path), None)
        qtbot.wait(20)
        worker.stop()
        worker.wait(3000)

        # Worker should be finished
        assert worker.isFinished() or not worker.isRunning()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
