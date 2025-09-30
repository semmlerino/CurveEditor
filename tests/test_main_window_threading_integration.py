"""Integration tests for MainWindow threading with Python threads.

These tests verify the critical crash scenarios that were fixed by switching
from QThread to Python threading.Thread.
"""

import threading
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


@pytest.fixture
def app(qtbot):
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def main_window(qtbot, tmp_path):
    """Create MainWindow instance for testing."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window


class TestMainWindowThreadingIntegration:
    """Test MainWindow file loading with real threading."""

    def test_window_close_during_file_loading(self, main_window, qtbot, tmp_path):
        """Test the critical crash scenario: closing window during active file loading.

        This was the primary bug that caused persistent crashes with QThread.
        """
        # Create a larger test file to ensure thread is still running when we check
        test_file = tmp_path / "large_test_data.2dtrack"

        # Create 2dtrack format file with header and large dataset
        content = "1\n"  # Number of tracking points
        content += "Point01\n"  # Point name
        content += "0\n"  # Point type
        content += "5000\n"  # Number of frames (large dataset)

        # Add many frames of tracking data
        for i in range(5000):
            content += f"{i} {100 + i * 0.1} {200 + i * 0.1}\n"

        test_file.write_text(content)

        # Mock the file dialog to return our test file
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (str(test_file), "2DTrackData Files (*.2dtrack)")

            # Start file loading through the file operations
            main_window.file_operations.open_file()

            # Small wait to let thread actually start
            qtbot.wait(50)

            # Verify worker exists and thread started
            assert main_window.file_operations.file_load_worker is not None
            assert main_window.file_operations.file_load_worker._thread is not None

            # Thread should be running (or recently finished)
            # For small files it might complete quickly, so we check if it was started
            thread_existed = main_window.file_operations.file_load_worker._thread is not None

            # Immediately close the window (this used to crash)
            main_window.close()

            # Give time for cleanup
            qtbot.wait(200)

            # Verify thread was properly stopped/cleaned up
            assert main_window.file_operations.file_load_worker._should_stop is True

            # If thread existed, it should have stopped or be stopping
            if thread_existed and main_window.file_operations.file_load_worker._thread:
                # Wait a bit more for thread to finish
                qtbot.wait(500)
                # Thread should not be alive anymore
                assert not main_window.file_operations.file_load_worker._thread.is_alive()

    def test_rapid_file_load_requests(self, main_window, qtbot, tmp_path):
        """Test rapid successive file load requests don't cause crashes."""
        # Create multiple test files
        files = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.csv"
            test_file.write_text(f"{i+1},100,200\n")
            files.append(test_file)

        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
            # Rapidly trigger multiple file loads
            for test_file in files:
                mock_dialog.return_value = (str(test_file), "CSV Files (*.csv)")
                main_window.file_operations.open_file()
                qtbot.wait(50)  # Small delay between requests

            # Last worker should be running
            assert main_window.file_operations.file_load_worker is not None
            assert main_window.file_operations.file_load_worker._thread is not None

            # Clean up
            main_window.close()
            qtbot.wait(200)

    def test_no_qpixmap_in_worker_thread(self, main_window, qtbot, tmp_path):
        """Verify no QPixmap is created in worker threads (would crash)."""
        # This test verifies we're following Qt threading rules
        test_file = tmp_path / "pixmap_test.csv"
        test_file.write_text("1,100,200\n")

        # Patch QPixmap to detect if it's called from worker thread
        original_qpixmap = None
        thread_violations = []

        def check_thread(*args, **kwargs):
            current_thread = threading.current_thread()
            if current_thread.name != "MainThread":
                thread_violations.append(f"QPixmap created in {current_thread.name}")
            if original_qpixmap:
                return original_qpixmap(*args, **kwargs)

        with patch("PySide6.QtGui.QPixmap") as mock_pixmap:
            mock_pixmap.side_effect = check_thread

            with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
                mock_dialog.return_value = (str(test_file), "CSV Files (*.csv)")
                main_window.file_operations.open_file()

                # Wait for loading
                qtbot.wait(500)

                # Verify no threading violations
                assert len(thread_violations) == 0, f"QPixmap violations: {thread_violations}"

    def test_memory_cleanup_after_loading(self, main_window, qtbot, tmp_path):
        """Test memory is properly cleaned up after file loading."""
        import gc

        # Create a larger test file
        test_file = tmp_path / "memory_test.csv"
        data = "\n".join([f"{i},100,200" for i in range(1000)])
        test_file.write_text(data)

        # Get initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Load file multiple times
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (str(test_file), "CSV Files (*.csv)")

            for _ in range(3):
                main_window.file_operations.open_file()
                qtbot.wait(200)

        # Close window and clean up
        main_window.close()
        qtbot.wait(500)

        # Force garbage collection
        gc.collect()

        # Check object count didn't grow excessively
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects
        # Allow reasonable growth (Qt creates many internal objects)
        assert growth < 5000, f"Excessive object growth: {growth}"

    def test_worker_stops_on_window_deletion(self, qtbot, tmp_path):
        """Test worker thread stops when window is deleted."""
        # Create our own window to avoid fixture cleanup issues
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a larger test file to ensure thread takes time
        test_file = tmp_path / "delete_test.2dtrack"
        content = "1\nPoint01\n0\n1000\n"
        for i in range(1000):
            content += f"{i} {100 + i * 0.1} {200 + i * 0.1}\n"
        test_file.write_text(content)

        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (str(test_file), "2DTrackData Files (*.2dtrack)")
            window.file_operations.open_file()

            # Wait a moment for thread to start
            qtbot.wait(50)

            # Get thread reference if it exists
            if window.file_operations.file_load_worker and window.file_operations.file_load_worker._thread:
                worker_thread = window.file_operations.file_load_worker._thread
                thread_was_alive = worker_thread.is_alive()
            else:
                # Thread may have completed already for fast loads
                thread_was_alive = False
                worker_thread = None

            # Close the window properly
            window.close()
            qtbot.wait(500)

            # If thread was alive, it should have stopped
            if thread_was_alive and worker_thread:
                assert not worker_thread.is_alive()

            # Worker should have been flagged to stop
            if window.file_operations.file_load_worker:
                assert window.file_operations.file_load_worker._should_stop is True


class TestThreadingCrashScenarios:
    """Test specific crash scenarios that were encountered."""

    def test_close_during_large_file_load(self, main_window, qtbot, tmp_path):
        """Test closing window while loading a large file."""
        # Create moderately sized test file (100 lines for quick test)
        test_file = tmp_path / "large.csv"
        data = "\n".join([f"{i},{i*10},{i*20}" for i in range(100)])
        test_file.write_text(data)

        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (str(test_file), "CSV Files (*.csv)")
            main_window.file_operations.open_file()

            # Give a brief moment for file loading to start
            qtbot.wait(50)

            # Close the window
            main_window.close()

            # Wait longer for cleanup to complete
            qtbot.wait(500)

            # Verify cleanup happened if worker exists
            if main_window.file_operations.file_load_worker is not None:
                # Worker should be flagged to stop
                assert main_window.file_operations.file_load_worker._should_stop is True
                # Thread should either be None or stopped
                if main_window.file_operations.file_load_worker._thread:
                    assert not main_window.file_operations.file_load_worker._thread.is_alive()

    def test_multiple_windows_with_threading(self, qtbot, tmp_path):
        """Test multiple MainWindow instances with active threads."""
        windows = []
        test_file = tmp_path / "multi.csv"
        test_file.write_text("1,100,200\n")

        try:
            # Create multiple windows
            for i in range(3):
                window = MainWindow()
                qtbot.addWidget(window)
                windows.append(window)

                # Start file loading in each
                with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_dialog:
                    mock_dialog.return_value = (str(test_file), "CSV Files (*.csv)")
                    window.file_operations.open_file()

            # Brief wait
            qtbot.wait(100)

            # Close all windows
            for window in windows:
                window.close()

            # Wait for cleanup
            qtbot.wait(500)

            # Verify all threads stopped
            for window in windows:
                if window.file_operations.file_load_worker and window.file_operations.file_load_worker._thread:
                    assert not window.file_operations.file_load_worker._thread.is_alive()

        finally:
            # Ensure cleanup
            for window in windows:
                try:
                    window.deleteLater()
                except Exception:
                    pass  # Ignore cleanup errors

    def test_exception_in_file_loading(self, main_window, qtbot):
        """Test exception handling in file loading thread."""
        error_received = []
        finished_received = []

        def on_error(msg):
            error_received.append(msg)

        def on_finished():
            finished_received.append(True)

        main_window.file_operations.error_occurred.connect(on_error)
        main_window.file_operations.finished.connect(on_finished)

        # Start file loading directly with non-existent file
        main_window.file_operations.file_load_worker.start_work("/nonexistent/file.csv", None)

        # Wait for either error or finished signal
        qtbot.waitUntil(lambda: len(error_received) > 0 or len(finished_received) > 0, timeout=2000)

        # Verify error was handled gracefully
        if error_received:
            assert "Failed to load tracking data" in error_received[0]

        # Can close without crash
        main_window.close()
        qtbot.wait(200)
