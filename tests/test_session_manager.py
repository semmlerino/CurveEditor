"""
Tests for SessionManager - following unified testing guide best practices.

Tests behavior rather than implementation, uses real components with test
dependencies, and mocks only at system boundaries (file I/O).
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
from pathlib import Path
from unittest.mock import patch

from ui.session_manager import SessionManager


class TestSessionManager:
    """Test SessionManager behavior using real components where possible."""

    def test_initialization_creates_session_directory(self, tmp_path):
        """Test that SessionManager creates session directory on initialization."""
        # Arrange - Use real temp directory instead of mocking
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        # Act - Real SessionManager with real filesystem
        session_manager = SessionManager(project_root)

        # Assert - Test actual behavior
        session_dir = project_root / "session"
        assert session_dir.exists()
        assert session_dir.is_dir()
        assert session_manager.session_file == session_dir / "last_session.json"

    def test_find_project_root_locates_main_py(self, tmp_path):
        """Test automatic project root discovery."""
        # Arrange - Create realistic project structure
        project_root = tmp_path / "curve_editor"
        project_root.mkdir()
        (project_root / "main.py").touch()  # Marker file
        (project_root / "ui").mkdir()

        # Act - SessionManager should find project root
        session_manager = SessionManager()

        # Assert - Should find actual project root containing main.py
        assert session_manager.project_root.name == "CurveEditor"  # Real project
        assert (session_manager.project_root / "main.py").exists()

    def test_save_and_load_session_data(self, tmp_path):
        """Test complete save/load cycle with real file operations."""
        # Arrange - Real SessionManager with temp directory
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        # Create actual files for testing
        tracking_file = project_root / "test_tracking.txt"
        tracking_file.touch()
        image_dir = project_root / "test_images"
        image_dir.mkdir()

        session_manager = SessionManager(project_root)

        session_data = session_manager.create_session_data(
            tracking_file=str(tracking_file),
            image_directory=str(image_dir),
            current_frame=42,
            zoom_level=1.5,
            pan_offset=(10.0, 20.0),
            active_points=["Point1", "Point2"],
        )

        # Act - Real save and load operations
        save_result = session_manager.save_session(session_data)
        loaded_data = session_manager.load_session()

        # Assert - Test actual behavior, not implementation details
        assert save_result is True
        assert loaded_data is not None
        assert loaded_data["tracking_file"] == str(tracking_file.resolve())  # Should resolve to absolute path
        assert loaded_data["image_directory"] == str(image_dir.resolve())  # Should resolve to absolute path
        assert loaded_data["current_frame"] == 42
        assert loaded_data["zoom_level"] == 1.5
        assert loaded_data["pan_offset"] == [10.0, 20.0]  # JSON converts tuple to list
        assert loaded_data["active_points"] == ["Point1", "Point2"]

    def test_relative_path_conversion_within_project(self, tmp_path):
        """Test path conversion for files within project tree."""
        # Arrange - Real directory structure
        project_root = tmp_path / "test_project"
        project_root.mkdir()
        data_file = project_root / "tracking_data.txt"
        data_file.touch()

        session_manager = SessionManager(project_root)

        # Act - Real path conversion
        relative_path = session_manager._make_relative_path(str(data_file))

        # Assert - Should convert to relative path
        assert relative_path == "tracking_data.txt"
        assert not Path(relative_path).is_absolute()

    def test_absolute_path_preserved_outside_project(self, tmp_path):
        """Test path handling for files outside project tree."""
        # Arrange - File outside project
        project_root = tmp_path / "project"
        project_root.mkdir()
        external_file = tmp_path / "external_data.txt"
        external_file.touch()

        session_manager = SessionManager(project_root)

        # Act - Real path processing
        processed_path = session_manager._make_relative_path(str(external_file))

        # Assert - Should keep absolute path
        assert Path(processed_path).is_absolute()
        assert processed_path == str(external_file.resolve())

    def test_path_resolution_existing_relative(self, tmp_path):
        """Test resolving relative paths that exist."""
        # Arrange - Real files
        project_root = tmp_path / "project"
        project_root.mkdir()
        data_file = project_root / "data.txt"
        data_file.touch()

        session_manager = SessionManager(project_root)

        # Act - Real path resolution
        resolved = session_manager._resolve_path("data.txt")

        # Assert - Should resolve to absolute path
        assert resolved is not None
        assert Path(resolved).is_absolute()
        assert Path(resolved) == data_file.resolve()

    def test_path_resolution_nonexistent_file(self, tmp_path):
        """Test handling of paths that no longer exist."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)

        # Act - Try to resolve non-existent file
        resolved = session_manager._resolve_path("missing_file.txt")

        # Assert - Should return None for missing files
        assert resolved is None

    def test_environment_variable_disables_persistence(self, tmp_path):
        """Test that environment variable disables session persistence."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)
        session_data = {"test": "data"}

        # Act - Mock environment variable at system boundary
        with patch.dict(os.environ, {"CURVE_EDITOR_NO_SESSION": "true"}):
            save_result = session_manager.save_session(session_data)
            load_result = session_manager.load_session()

        # Assert - Should disable persistence
        assert save_result is True  # Returns True but doesn't actually save
        assert load_result is None
        assert not session_manager.session_file.exists()

    def test_environment_variable_clears_existing_session(self, tmp_path):
        """Test session clearing via environment variable."""
        # Arrange - Create existing session
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)

        # Save initial session
        initial_data = {"initial": "data"}
        session_manager.save_session(initial_data)
        assert session_manager.session_file.exists()

        # Act - Clear session via environment
        with patch.dict(os.environ, {"CURVE_EDITOR_CLEAR_SESSION": "true"}):
            result = session_manager.load_session()

        # Assert - Session should be cleared
        assert result is None
        assert not session_manager.session_file.exists()

    def test_corrupted_session_file_handling(self, tmp_path):
        """Test graceful handling of corrupted session files."""
        # Arrange - Create corrupted session file
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)

        # Create invalid JSON file
        session_manager.session_file.parent.mkdir(exist_ok=True)
        with open(session_manager.session_file, "w") as f:
            f.write("invalid json content{")

        # Act - Try to load corrupted session
        result = session_manager.load_session()

        # Assert - Should handle corruption gracefully
        assert result is None

    def test_session_data_factory_method(self):
        """Test session data creation with default values."""
        # Arrange
        session_manager = SessionManager()

        # Act - Create session data with defaults
        session_data = session_manager.create_session_data()

        # Assert - Should have sensible defaults
        assert session_data["tracking_file"] is None
        assert session_data["image_directory"] is None
        assert session_data["current_frame"] == 1
        assert session_data["zoom_level"] == 1.0
        assert session_data["pan_offset"] == [0.0, 0.0]
        assert session_data["active_points"] == []
        assert session_data["window_geometry"] is None

    def test_has_session_detection(self, tmp_path):
        """Test session existence detection."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)

        # Act & Assert - No session initially
        assert not session_manager.has_session()

        # Save session and check again
        session_manager.save_session({"test": "data"})
        assert session_manager.has_session()

    def test_clear_session_removes_file(self, tmp_path):
        """Test session clearing removes the file."""
        # Arrange - Create session
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)
        session_manager.save_session({"test": "data"})
        assert session_manager.session_file.exists()

        # Act - Clear session
        result = session_manager.clear_session()

        # Assert - File should be removed
        assert result is True
        assert not session_manager.session_file.exists()

    def test_metadata_added_to_saved_session(self, tmp_path):
        """Test that metadata is automatically added to saved sessions."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)

        session_data = {"user_data": "test"}

        # Act - Save and reload
        session_manager.save_session(session_data)
        loaded_data = session_manager.load_session()

        # Assert - Metadata should be present
        assert loaded_data is not None
        assert "_metadata" in loaded_data
        assert "saved_at" in loaded_data["_metadata"]
        assert "version" in loaded_data["_metadata"]
        assert loaded_data["_metadata"]["version"] == "1.0"

    def test_windows_backslash_path_resolution(self, tmp_path):
        """Test that Windows-style paths with backslashes are resolved correctly."""
        # Arrange - Create project structure
        project_root = tmp_path / "project"
        project_root.mkdir()
        footage_dir = project_root / "footage" / "Burger"
        footage_dir.mkdir(parents=True)

        session_manager = SessionManager(project_root)

        # Act - Simulate Windows-style path from session file
        windows_path = "footage\\Burger"  # Windows-style relative path
        resolved_path = session_manager._resolve_path(windows_path)

        # Assert - Should resolve correctly despite backslashes
        assert resolved_path is not None
        assert Path(resolved_path) == footage_dir.resolve()

    def test_windows_absolute_path_with_backslashes(self, tmp_path):
        """Test handling of Windows absolute paths with backslashes."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        external_dir = tmp_path / "external" / "data"
        external_dir.mkdir(parents=True)

        session_manager = SessionManager(project_root)

        # Act - Simulate Windows absolute path
        # Use forward slashes for the drive but backslashes for subdirs
        windows_abs_path = str(external_dir).replace("/", "\\")
        resolved_path = session_manager._resolve_path(windows_abs_path)

        # Assert
        assert resolved_path is not None
        assert Path(resolved_path) == external_dir.resolve()

    def test_make_relative_path_returns_posix_format(self, tmp_path):
        """Test that _make_relative_path always returns POSIX-style paths."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        nested_file = project_root / "data" / "subfolder" / "file.txt"
        nested_file.parent.mkdir(parents=True)
        nested_file.touch()

        session_manager = SessionManager(project_root)

        # Act
        relative_path = session_manager._make_relative_path(str(nested_file))

        # Assert - Should use forward slashes even on Windows
        assert "/" in relative_path or len(relative_path.split("/")) == 1  # Single file or has forward slashes
        assert "\\" not in relative_path  # No backslashes
        assert relative_path == "data/subfolder/file.txt"

    def test_selection_state_persistence(self, tmp_path):
        """Test that selection state (selected_curves, show_all_curves) is saved and restored."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)

        # Create session data with selection state
        session_data = session_manager.create_session_data(
            tracking_file="/test/tracking.txt",
            current_frame=42,
            selected_curves=["Track1", "Track2", "Track3"],
            show_all_curves=True,
        )

        # Act - Save and reload
        session_manager.save_session(session_data)
        loaded_data = session_manager.load_session()

        # Assert - Selection state preserved
        assert loaded_data is not None
        assert "selected_curves" in loaded_data
        assert loaded_data["selected_curves"] == ["Track1", "Track2", "Track3"]
        assert "show_all_curves" in loaded_data
        assert loaded_data["show_all_curves"] is True

    def test_selection_state_defaults(self, tmp_path):
        """Test that selection state has sensible defaults when not provided."""
        # Arrange
        project_root = tmp_path / "project"
        project_root.mkdir()
        session_manager = SessionManager(project_root)

        # Create session without selection state
        session_data = session_manager.create_session_data(
            tracking_file="/test/tracking.txt",
            current_frame=10,
        )

        # Act - Save and reload
        session_manager.save_session(session_data)
        loaded_data = session_manager.load_session()

        # Assert - Default values
        assert loaded_data is not None
        assert loaded_data["selected_curves"] == []
        assert loaded_data["show_all_curves"] is False


class TestSessionManagerIntegration:
    """Integration tests for SessionManager with realistic scenarios."""

    def test_complete_session_workflow(self, tmp_path):
        """Test complete workflow: save session, restart app, load session."""
        # Arrange - Simulate application state
        project_root = tmp_path / "app"
        project_root.mkdir()
        tracking_file = project_root / "my_tracking.txt"
        tracking_file.touch()
        image_dir = project_root / "images"
        image_dir.mkdir()

        # First application instance
        session_manager1 = SessionManager(project_root)

        # Act - Save session and "restart" app
        session_data = session_manager1.create_session_data(
            tracking_file=str(tracking_file),
            image_directory=str(image_dir),
            current_frame=150,
            zoom_level=2.5,
            pan_offset=(100.0, 200.0),
            active_points=["Point1", "Point2", "Point3"],
        )
        save_success = session_manager1.save_session(session_data)

        # Simulate new application instance
        session_manager2 = SessionManager(project_root)
        restored_data = session_manager2.load_session()

        # Assert - Session should be fully restored
        assert save_success is True
        assert restored_data is not None
        assert restored_data["current_frame"] == 150
        assert restored_data["zoom_level"] == 2.5
        assert restored_data["active_points"] == ["Point1", "Point2", "Point3"]

        # Paths should be resolved to absolute paths when files exist
        assert Path(restored_data["tracking_file"]).is_absolute()
        assert Path(restored_data["image_directory"]).is_absolute()
        assert Path(restored_data["tracking_file"]) == tracking_file.resolve()
        assert Path(restored_data["image_directory"]) == image_dir.resolve()

    def test_cross_platform_path_handling(self, tmp_path):
        """Test path handling works across different path formats."""
        # Arrange - Mix of path formats
        project_root = tmp_path / "cross_platform"
        project_root.mkdir()

        session_manager = SessionManager(project_root)

        # Create files with different path representations
        local_file = project_root / "local.txt"
        local_file.touch()

        # Act - Test various path formats
        posix_path = session_manager._make_relative_path(str(local_file))
        resolved_back = session_manager._resolve_path(posix_path)

        # Assert - Should handle conversion correctly
        assert posix_path == "local.txt"
        assert resolved_back is not None
        assert Path(resolved_back) == local_file.resolve()
