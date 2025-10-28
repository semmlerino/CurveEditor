"""Test session persistence for image sequences.

Tests that background image sequences are properly saved and restored
across application sessions.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock

from stores.application_state import get_application_state
from ui.session_manager import SessionManager

logger = logging.getLogger(__name__)


class TestSessionImagePersistence:
    """Test suite for image sequence session persistence."""

    def test_save_session_includes_image_files(self, tmp_path: Path) -> None:
        """Test that save_session includes image files from ApplicationState."""
        # Setup
        session_manager = SessionManager(project_root=tmp_path)
        app_state = get_application_state()

        # Set up image sequence in ApplicationState
        test_images = ["frame_001.png", "frame_002.png", "frame_003.png"]
        test_directory = "/path/to/images"
        app_state.set_image_files(test_images, directory=test_directory)

        # Create session data
        session_data = session_manager.create_session_data(
            tracking_file=None, image_directory=test_directory
        )

        # Manually add image files (as done in MainWindow._save_current_session)
        session_data["image_files"] = test_images

        # Save session
        success = session_manager.save_session(session_data)
        assert success, "Session save should succeed"

        # Verify session file contains image files
        with open(session_manager.session_file) as f:
            saved_data = json.load(f)

        assert "image_files" in saved_data, "Session should contain image_files"
        assert saved_data["image_files"] == test_images, "Image files should match"
        assert saved_data["image_directory"] == test_directory, "Image directory should match"

    def test_load_session_restores_image_files(self, tmp_path: Path) -> None:
        """Test that load_session properly restores image files."""
        # Setup
        session_manager = SessionManager(project_root=tmp_path)
        app_state = get_application_state()

        # Clear any existing image data
        app_state.set_image_files([], directory=None)

        # Create session data with images
        test_images = ["frame_001.png", "frame_002.png", "frame_003.png"]
        test_directory = str(tmp_path / "images")

        session_data = {
            "tracking_file": None,
            "image_directory": test_directory,
            "image_files": test_images,
            "current_frame": 1,
            "zoom_level": 1.0,
            "pan_offset": [0.0, 0.0],
            "window_geometry": None,
            "active_points": [],
            "view_bounds": None,
            "recent_directories": [],
            "selected_curves": [],
            "show_all_curves": False,
        }

        # Save session
        session_manager.save_session(session_data)

        # Clear ApplicationState
        app_state.set_image_files([], directory=None)
        assert len(app_state.get_image_files()) == 0, "ApplicationState should be empty"

        # Load session
        loaded_data = session_manager.load_session()
        assert loaded_data is not None, "Session should load successfully"
        assert loaded_data["image_files"] == test_images, "Loaded image files should match"

    def test_restore_session_state_with_images(self, tmp_path: Path) -> None:
        """Test that restore_session_state properly restores images to ApplicationState."""
        # Setup
        session_manager = SessionManager(project_root=tmp_path)
        app_state = get_application_state()

        # Clear any existing image data
        app_state.set_image_files([], directory=None)

        # Create mock main window
        mock_main_window = MagicMock()
        mock_main_window.state_manager = Mock()
        mock_main_window.state_manager.image_directory = None
        mock_main_window.file_load_worker = Mock()
        mock_main_window.view_management_controller = Mock()

        # Create session data with images
        test_images = ["frame_001.png", "frame_002.png", "frame_003.png"]
        test_directory = str(tmp_path / "images")

        session_data = {
            "tracking_file": None,
            "image_directory": test_directory,
            "image_files": test_images,
            "current_frame": 1,
            "zoom_level": 1.0,
            "pan_offset": [0.0, 0.0],
            "active_points": [],
            "selected_curves": [],
            "show_all_curves": False,
            "recent_directories": [],
        }

        # Restore session state
        session_manager.restore_session_state(mock_main_window, session_data)

        # Verify ApplicationState was updated
        assert app_state.get_image_files() == test_images, "ApplicationState should have image files"
        assert app_state.get_image_directory() == test_directory, "ApplicationState should have directory"

        # Verify StateManager was updated
        assert mock_main_window.state_manager.image_directory == test_directory

        # Verify view_management_controller was called
        mock_main_window.view_management_controller.on_image_sequence_loaded.assert_called_once_with(
            test_directory, test_images
        )

        # Verify FileLoadWorker was NOT called with image directory (images already restored)
        mock_main_window.file_load_worker.start_work.assert_called_once_with(None, None)

    def test_restore_session_without_images_uses_worker(self, tmp_path: Path) -> None:
        """Test that restore falls back to FileLoadWorker when no image files in session."""
        # Setup
        session_manager = SessionManager(project_root=tmp_path)

        # Create mock main window
        mock_main_window = MagicMock()
        mock_main_window.state_manager = Mock()
        mock_main_window.file_load_worker = Mock()
        mock_main_window.view_management_controller = Mock()

        # Create session data WITHOUT image_files (legacy session format)
        test_directory = str(tmp_path / "images")

        session_data = {
            "tracking_file": None,
            "image_directory": test_directory,
            # No image_files key
            "current_frame": 1,
            "zoom_level": 1.0,
            "pan_offset": [0.0, 0.0],
            "active_points": [],
            "selected_curves": [],
            "show_all_curves": False,
            "recent_directories": [],
        }

        # Restore session state
        session_manager.restore_session_state(mock_main_window, session_data)

        # Verify FileLoadWorker WAS called with image directory (needs to scan)
        mock_main_window.file_load_worker.start_work.assert_called_once_with(None, test_directory)

        # Verify view_management_controller was NOT called (will be called by worker signal)
        mock_main_window.view_management_controller.on_image_sequence_loaded.assert_not_called()

    def test_session_roundtrip_preserves_images(self, tmp_path: Path) -> None:
        """Integration test: Save and load session preserves image sequence."""
        # Setup
        session_manager = SessionManager(project_root=tmp_path)
        app_state = get_application_state()

        # Create test directory (must exist for session manager validation)
        image_dir = tmp_path / "images"
        image_dir.mkdir()

        # Set up initial state
        test_images = ["frame_001.png", "frame_002.png", "frame_003.png"]
        test_directory = str(image_dir)
        app_state.set_image_files(test_images, directory=test_directory)

        # Save session (simulating MainWindow._save_current_session)
        session_data = session_manager.create_session_data(
            tracking_file=None, image_directory=test_directory
        )
        session_data["image_files"] = app_state.get_image_files()
        success = session_manager.save_session(session_data)
        assert success

        # Clear state
        app_state.set_image_files([], directory=None)

        # Load session
        loaded_data = session_manager.load_session()
        assert loaded_data is not None

        # Create mock main window for restoration
        mock_main_window = MagicMock()
        mock_main_window.state_manager = Mock()
        mock_main_window.file_load_worker = Mock()
        mock_main_window.view_management_controller = Mock()

        # Restore session
        session_manager.restore_session_state(mock_main_window, loaded_data)

        # Verify state was restored
        assert app_state.get_image_files() == test_images
        assert app_state.get_image_directory() == test_directory
