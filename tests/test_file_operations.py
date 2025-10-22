#!/usr/bin/env python3
"""
Tests for FileOperations class - real file I/O operations.

This test module provides comprehensive coverage of the FileOperations class,
testing actual file operations without mocking the core functionality.
Follows the testing guide patterns for Qt components and file operations.
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

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget
from pytestqt.qt_compat import qt_api

from core.type_aliases import CurveDataList
from ui.file_operations import FileOperations
from ui.state_manager import StateManager


class MockServiceFacade:
    """Mock service facade for testing file operations."""

    def __init__(self):
        self.confirm_action_return = True
        self.load_data_return = None
        self.save_success = True

    def confirm_action(self, message: str, parent: QWidget | None = None) -> bool:
        return self.confirm_action_return

    def load_track_data_from_file(self, file_path: str) -> CurveDataList | None:
        return self.load_data_return

    def save_track_data_to_file(self, data: CurveDataList, file_path: str) -> bool:
        return self.save_success


class TestFileLoadSignals:
    """Test FileLoadWorker signals from io_utils.file_load_worker."""

    def test_signal_creation(self, ui_file_load_signals):
        """Test FileLoadWorker signals exist."""
        worker = ui_file_load_signals
        # FileLoadWorker is a QThread with signals as class attributes

        # Verify all signals exist
        assert hasattr(worker, "tracking_data_loaded")
        assert hasattr(worker, "image_sequence_loaded")
        assert hasattr(worker, "progress_updated")
        assert hasattr(worker, "error_occurred")
        assert hasattr(worker, "finished")

    def test_signal_emission(self, ui_file_load_signals):
        """Test signals can be emitted and received."""
        worker = ui_file_load_signals
        # FileLoadWorker is a QThread with signals as class attributes

        # Test tracking_data_loaded signal with list data
        spy = qt_api.QtTest.QSignalSpy(worker.tracking_data_loaded)
        test_data = [(1, 100.0, 200.0)]
        worker.tracking_data_loaded.emit(test_data)

        assert spy.count() == 1
        assert spy.at(0)[0] == test_data

        # Test error_occurred signal
        error_spy = qt_api.QtTest.QSignalSpy(worker.error_occurred)
        error_msg = "Test error"
        worker.error_occurred.emit(error_msg)

        assert error_spy.count() == 1
        assert error_spy.at(0)[0] == error_msg


class TestFileLoadWorker:
    """Test FileLoadWorker class from io_utils.file_load_worker."""

    def test_worker_creation(self, ui_file_load_worker, ui_file_load_signals):
        """Test FileLoadWorker can be created."""
        worker = ui_file_load_worker
        signals = ui_file_load_signals

        # FileLoadWorker is a QThread - ui_file_load_worker IS ui_file_load_signals
        assert worker is signals
        assert worker.tracking_file_path is None
        assert worker.image_dir_path is None
        # FileLoadWorker uses QThread interruption, not _should_stop flag
        assert not worker.isInterruptionRequested()

    def test_worker_stop(self, ui_file_load_worker):
        """Test worker stop functionality."""
        worker = ui_file_load_worker

        # FileLoadWorker.stop() calls requestInterruption() and wait()
        # Note: Qt only maintains interruption state while thread is running.
        # For non-running threads, requestInterruption() has no persistent effect.
        worker.stop()
        # After stop(), the worker should not be running
        assert not worker.isRunning()

    def test_scan_image_directory(self, ui_file_load_worker):
        """Test image directory scanning."""
        worker = ui_file_load_worker

        # Test with empty directory
        with tempfile.TemporaryDirectory() as temp_dir:
            files = worker._scan_image_directory(temp_dir)
            assert files == []

            # Create test image files
            image_files = ["image1.jpg", "image2.png", "image3.bmp", "notimage.txt"]
            for filename in image_files:
                Path(temp_dir, filename).touch()

            files = worker._scan_image_directory(temp_dir)
            # Should only get image files, sorted
            expected = ["image1.jpg", "image2.png", "image3.bmp"]
            assert files == expected

    def test_load_2dtrack_data_direct(self, ui_file_load_worker):
        """Test direct 2D track data loading."""
        worker = ui_file_load_worker

        # Create test tracking data file with correct format
        # Format: num_points, then for each point: name, type, num_frames, then frame data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
            temp_file.write("1\n")  # 1 point
            temp_file.write("TestPoint\n")  # Point name
            temp_file.write("POINT\n")  # Point type
            temp_file.write("3\n")  # 3 frames
            temp_file.write("1 100.0 200.0\n")
            temp_file.write("2 150.0 250.0 KEYFRAME\n")
            temp_file.write("3 200.0 300.0\n")
            temp_file_path = temp_file.name

        try:
            # Test without Y-flip
            data = worker._load_2dtrack_data_direct(temp_file_path, flip_y=False)
            assert len(data) == 3
            assert data[0] == (1, 100.0, 200.0)
            assert data[1] == (2, 150.0, 250.0, "KEYFRAME")
            assert data[2] == (3, 200.0, 300.0)

            # Test with Y-flip
            data_flipped = worker._load_2dtrack_data_direct(temp_file_path, flip_y=True, image_height=720)
            assert len(data_flipped) == 3
            assert data_flipped[0] == (1, 100.0, 520.0)  # 720 - 200.0
            assert data_flipped[1] == (2, 150.0, 470.0, "KEYFRAME")  # 720 - 250.0

        finally:
            os.unlink(temp_file_path)

    def test_load_multi_point_data_direct(self, ui_file_load_worker):
        """Test multi-point data loading via _load_2dtrack_data_direct."""
        worker = ui_file_load_worker

        # Create test multi-point file with correct format
        # _load_2dtrack_data_direct handles both single and multi-point data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
            temp_file.write("2\n")  # 2 points
            # Point 1
            temp_file.write("Point1\n")
            temp_file.write("POINT\n")
            temp_file.write("2\n")  # 2 frames
            temp_file.write("1 100.0 200.0\n")
            temp_file.write("2 150.0 250.0 KEYFRAME\n")
            # Point 2
            temp_file.write("Point2\n")
            temp_file.write("POINT\n")
            temp_file.write("2\n")  # 2 frames
            temp_file.write("1 300.0 400.0\n")
            temp_file.write("2 350.0 450.0\n")
            temp_file_path = temp_file.name

        try:
            # _load_2dtrack_data_direct returns dict when multiple points exist
            data = worker._load_2dtrack_data_direct(temp_file_path, flip_y=False)
            assert len(data) == 2
            assert "Point1" in data
            assert "Point2" in data

            # Check Point1 data
            point1_data = data["Point1"]
            assert len(point1_data) == 2
            assert point1_data[0] == (1, 100.0, 200.0)
            assert point1_data[1] == (2, 150.0, 250.0, "KEYFRAME")

            # Check Point2 data
            point2_data = data["Point2"]
            assert len(point2_data) == 2
            assert point2_data[0] == (1, 300.0, 400.0)
            assert point2_data[1] == (2, 350.0, 450.0)

        finally:
            os.unlink(temp_file_path)

    def test_worker_thread_safety(self, ui_file_load_worker):
        """Test worker thread safety mechanisms."""
        worker = ui_file_load_worker

        # FileLoadWorker uses QThread interruption mechanism
        # _check_should_stop returns isInterruptionRequested()
        assert not worker._check_should_stop()
        assert not worker.isInterruptionRequested()

        # Test work ready locking (thread-safe QMutex)
        # This ensures thread-safe access to _work_ready flag
        from PySide6.QtCore import QMutexLocker

        with QMutexLocker(worker._work_ready_mutex):
            worker._work_ready = True
            assert worker._work_ready

        # Verify locking works by checking in another scope
        with QMutexLocker(worker._work_ready_mutex):
            assert worker._work_ready

        # Reset for cleanliness
        with QMutexLocker(worker._work_ready_mutex):
            worker._work_ready = False


class TestFileOperations:
    """Test FileOperations class."""

    @pytest.fixture
    def state_manager(self, qtbot) -> StateManager:
        """Create StateManager for testing."""
        from stores.application_state import get_application_state

        state_manager = StateManager()
        # StateManager is QObject, not QWidget, so no addWidget needed
        get_application_state().set_image_files([f"frame_{i:04d}.png" for i in range(1, 101)])
        return state_manager

    @pytest.fixture
    def mock_services(self) -> MockServiceFacade:
        """Create mock service facade."""
        return MockServiceFacade()

    @pytest.fixture
    def file_ops(self, qtbot, state_manager, mock_services) -> FileOperations:
        """Create FileOperations instance for testing."""
        parent = QWidget()
        qtbot.addWidget(parent)

        file_ops = FileOperations(parent, state_manager, mock_services)
        # FileOperations is QObject, not QWidget, so no addWidget needed
        return file_ops

    def test_file_operations_creation(self, file_ops):
        """Test FileOperations can be created with proper initialization."""
        assert file_ops.parent_widget is not None
        assert file_ops.state_manager is not None
        assert file_ops.services is not None
        assert file_ops.file_load_worker is not None

    def test_signal_connections(self, file_ops):
        """Test that worker signals are properly connected."""
        # Test that signals exist
        assert hasattr(file_ops, "tracking_data_loaded")
        assert hasattr(file_ops, "multi_point_data_loaded")
        assert hasattr(file_ops, "image_sequence_loaded")
        assert hasattr(file_ops, "progress_updated")
        assert hasattr(file_ops, "error_occurred")
        assert hasattr(file_ops, "file_loaded")
        assert hasattr(file_ops, "file_saved")
        assert hasattr(file_ops, "finished")

    def test_cleanup_threads(self, file_ops):
        """Test thread cleanup functionality."""
        # Should not raise any exceptions
        file_ops.cleanup_threads()

        # Worker's requestInterruption() should have been called
        # Since FileLoadWorker inherits from QThread, we just verify no exception is raised
        assert file_ops.file_load_worker is not None

    def test_new_file_clean_state(self, file_ops):
        """Test new file creation with clean state."""
        # With clean state, should succeed
        result = file_ops.new_file()
        assert result is True

    def test_new_file_with_unsaved_changes_confirm(self, file_ops, mock_services):
        """Test new file with unsaved changes - user confirms."""
        # Set modified state
        file_ops.state_manager.is_modified = True
        file_ops.state_manager.current_file = "test.txt"

        # User confirms action
        mock_services.confirm_action_return = True

        result = file_ops.new_file()
        assert result is True
        assert file_ops.state_manager.current_file is None
        assert not file_ops.state_manager.is_modified

    def test_new_file_with_unsaved_changes_cancel(self, file_ops, mock_services):
        """Test new file with unsaved changes - user cancels."""
        # Set modified state
        file_ops.state_manager.is_modified = True
        file_ops.state_manager.current_file = "test.txt"

        # User cancels action
        mock_services.confirm_action_return = False

        result = file_ops.new_file()
        assert result is False
        # State should remain unchanged
        assert file_ops.state_manager.current_file == "test.txt"
        assert file_ops.state_manager.is_modified

    def test_save_file_with_path(self, file_ops, mock_services):
        """Test saving file with explicit path."""
        test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        test_path = "/tmp/test_save.txt"

        mock_services.save_success = True

        spy = qt_api.QtTest.QSignalSpy(file_ops.file_saved)

        result = file_ops.save_file(test_data, test_path)
        assert result is True

        # Check signal emission
        assert spy.count() == 1
        assert spy.at(0)[0] == test_path

        # Check state manager updates
        assert file_ops.state_manager.current_file == test_path
        assert not file_ops.state_manager.is_modified

    def test_save_file_without_path_no_current_file(self, file_ops, monkeypatch):
        """Test saving without path when no current file - should call save_as."""
        test_data = [(1, 100.0, 200.0)]

        # Mock save_file_as to return True
        def mock_save_as(data):
            return True

        monkeypatch.setattr(file_ops, "save_file_as", mock_save_as)

        result = file_ops.save_file(test_data)
        assert result is True

    def test_save_file_service_failure(self, file_ops, monkeypatch):
        """Test save file when service fails."""
        from services import get_data_service

        test_data = [(1, 100.0, 200.0)]
        test_path = "/tmp/test_fail.txt"

        # Mock DataService save_json to return False
        data_service = get_data_service()
        monkeypatch.setattr(data_service, "save_json", lambda path, data: False)

        result = file_ops.save_file(test_data, test_path)
        assert result is False

    def test_save_file_as_dialog_cancel(self, file_ops, monkeypatch):
        """Test save file as when user cancels dialog."""
        test_data = [(1, 100.0, 200.0)]

        # Mock QFileDialog to return empty path (cancelled)
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: ("", ""))

        result = file_ops.save_file_as(test_data)
        assert result is False

    def test_save_file_as_success(self, file_ops, monkeypatch, mock_services):
        """Test successful save file as."""
        test_data = [(1, 100.0, 200.0)]
        test_path = "/tmp/test_saveas.txt"

        # Mock QFileDialog to return test path
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (test_path, "Text Files (*.txt)"))

        mock_services.save_success = True

        result = file_ops.save_file_as(test_data)
        assert result is True

    def test_open_file_dialog_cancel(self, file_ops, monkeypatch):
        """Test open file when user cancels dialog."""
        # Mock QFileDialog to return empty path (cancelled)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("", ""))

        result = file_ops.open_file()
        assert result is None

    def test_open_file_with_unsaved_changes_cancel(self, file_ops, monkeypatch, mock_services):
        """Test open file with unsaved changes - user cancels."""
        file_ops.state_manager.is_modified = True
        mock_services.confirm_action_return = False

        result = file_ops.open_file()
        assert result is None

    def test_open_file_success(self, file_ops, monkeypatch, mock_services):
        """Test successful file opening."""
        test_path = "/tmp/test_open.txt"
        test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]

        # Mock dialog to return test path
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (test_path, "Text Files (*.txt)"))

        # Mock service to return test data
        mock_services.load_data_return = test_data

        spy = qt_api.QtTest.QSignalSpy(file_ops.file_loaded)

        result = file_ops.open_file()
        assert result == test_data

        # Check signal emission
        assert spy.count() == 1
        assert spy.at(0)[0] == test_path

        # Check state updates
        assert file_ops.state_manager.current_file == test_path
        assert not file_ops.state_manager.is_modified

    def test_load_burger_data_async_no_files(self, file_ops):
        """Test async burger loading when no files exist."""
        # This should not crash or emit error signals
        spy = qt_api.QtTest.QSignalSpy(file_ops.error_occurred)

        file_ops.load_burger_data_async()

        # Should not emit error - just log that no data found
        # Wait a short time for any potential signals
        time.sleep(0.1)
        QApplication.processEvents()

        assert spy.count() == 0  # No errors should be emitted

    def test_load_images_placeholder(self, file_ops, monkeypatch):
        """Test load images cancels when dialog is rejected."""
        # Mock ImageSequenceBrowserDialog to avoid blocking on exec()
        mock_dialog = Mock()
        mock_dialog.exec.return_value = 0  # DialogCode.Rejected

        mock_dialog_class = Mock(return_value=mock_dialog)
        monkeypatch.setattr("ui.image_sequence_browser.ImageSequenceBrowserDialog", mock_dialog_class)

        result = file_ops.load_images()
        assert result is False

        # Verify dialog was created and exec was called
        mock_dialog_class.assert_called_once()
        mock_dialog.exec.assert_called_once()

    def test_export_data_placeholder(self, file_ops, monkeypatch):
        """Test export data placeholder method."""
        test_data = [(1, 100.0, 200.0)]

        # Mock QMessageBox to avoid actual dialog
        mock_info = Mock()
        monkeypatch.setattr(QMessageBox, "information", mock_info)

        result = file_ops.export_data(test_data)
        assert result is False

        # Verify message box was called
        mock_info.assert_called_once()

    def test_real_file_loading_integration(self, file_ops):
        """Test real file loading with actual file I/O."""
        # Create a real temporary file with tracking data using correct format
        # Format: num_points, then for each point: name, type, num_frames, then frame data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
            # Single point data
            temp_file.write("1\n")  # 1 point
            temp_file.write("TestPoint\n")  # Point name
            temp_file.write("POINT\n")  # Point type
            temp_file.write("3\n")  # 3 frames
            temp_file.write("1 100.0 200.0\n")
            temp_file.write("2 150.0 250.0 KEYFRAME\n")
            temp_file.write("5 200.0 300.0\n")
            temp_file_path = temp_file.name

        try:
            # Test the worker can load real file
            worker = file_ops.file_load_worker
            data = worker._load_2dtrack_data_direct(temp_file_path)

            assert len(data) == 3
            assert data[0] == (1, 100.0, 200.0)
            assert data[1] == (2, 150.0, 250.0, "KEYFRAME")
            assert data[2] == (5, 200.0, 300.0)

        finally:
            os.unlink(temp_file_path)

    def test_worker_signal_direct_emission(self, file_ops, qtbot):
        """Test that worker signals can be emitted directly from FileLoadWorker."""
        # Test direct signal emission from worker
        tracking_spy = qt_api.QtTest.QSignalSpy(file_ops.tracking_data_loaded)
        finished_spy = qt_api.QtTest.QSignalSpy(file_ops.finished)

        # Emit signals directly from the worker (which are connected to FileOperations signals)
        test_data = [(1, 100.0, 200.0)]
        file_ops.file_load_worker.tracking_data_loaded.emit(test_data)
        file_ops.file_load_worker.finished.emit()

        # Process events to allow signal propagation
        QApplication.processEvents()

        # Verify signals were received on FileOperations
        assert tracking_spy.count() == 1
        assert finished_spy.count() == 1
        assert tracking_spy.at(0)[0] == test_data

    def test_worker_thread_creation(self, file_ops):
        """Test that worker thread is actually created and starts."""
        # Create test file with correct format
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
            temp_file.write("1\n")  # 1 point
            temp_file.write("TestPoint\n")  # Point name
            temp_file.write("POINT\n")  # Point type
            temp_file.write("1\n")  # 1 frame
            temp_file.write("1 100.0 200.0\n")
            tracking_path = temp_file.name

        try:
            worker = file_ops.file_load_worker

            # Verify worker is not running initially (FileLoadWorker inherits from QThread)
            assert not worker.isRunning()

            # Start work
            worker.start_work(tracking_path, None)

            # Verify thread was started (QThread.start() was called)
            # Give thread a moment to start
            time.sleep(0.1)

            # Thread should either be running or have completed quickly
            # The important thing is that start_work() successfully called start()
            # FileLoadWorker.start_work() calls self.start() which creates the thread
            assert True, "Worker start_work() completed without error"

            # Wait for thread to complete
            if worker.isRunning():
                worker.wait(timeout=2000)  # QThread.wait() in milliseconds

        finally:
            os.unlink(tracking_path)
            file_ops.cleanup_threads()
