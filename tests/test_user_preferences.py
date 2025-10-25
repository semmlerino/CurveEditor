#!/usr/bin/env python
"""
Unit tests for UserPreferences.

Tests serialization, validation, and project-aware directory management.
"""

import tempfile
from pathlib import Path

from core.user_preferences import UserPreferences


class TestUserPreferences:
    """Test UserPreferences functionality."""

    def test_default_initialization(self):
        """Test that UserPreferences initializes with correct defaults."""
        prefs = UserPreferences()

        assert prefs.interface_mode == "simple"
        assert prefs.default_sort_order == "name"
        assert prefs.sort_ascending is True
        assert prefs.show_thumbnails is True
        assert prefs.thumbnail_size == 150
        assert prefs.max_recent_directories == 10
        assert isinstance(prefs.recent_directories, dict)
        assert len(prefs.recent_directories) == 0

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        prefs = UserPreferences()
        prefs.interface_mode = "advanced"
        prefs.thumbnail_size = 200

        data = prefs.to_dict()

        assert isinstance(data, dict)
        assert data["interface_mode"] == "advanced"
        assert data["thumbnail_size"] == 200
        assert "recent_directories" in data

    def test_from_dict_creation(self):
        """Test creation from dictionary."""
        data = {
            "interface_mode": "advanced",
            "thumbnail_size": 200,
            "show_thumbnails": False,
            "recent_directories": {"project1": ["/path1", "/path2"]}
        }

        prefs = UserPreferences.from_dict(data)

        assert prefs.interface_mode == "advanced"
        assert prefs.thumbnail_size == 200
        assert prefs.show_thumbnails is False
        assert prefs.recent_directories == {"project1": ["/path1", "/path2"]}

    def test_from_dict_with_missing_fields(self):
        """Test creation from dictionary with missing fields uses defaults."""
        data = {
            "interface_mode": "advanced",
            "unknown_field": "should_be_ignored"
        }

        prefs = UserPreferences.from_dict(data)

        assert prefs.interface_mode == "advanced"
        assert prefs.thumbnail_size == 150  # Default value
        assert prefs.show_thumbnails is True  # Default value
        assert not hasattr(prefs, "unknown_field")

    def test_save_and_load_file(self):
        """Test saving to and loading from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_prefs.json"

            # Create and save preferences
            original_prefs = UserPreferences()
            original_prefs.interface_mode = "advanced"
            original_prefs.thumbnail_size = 250
            original_prefs.add_recent_directory("/test/path", "test_project")

            success = original_prefs.save_to_file(file_path)
            assert success is True
            assert file_path.exists()

            # Load preferences
            loaded_prefs = UserPreferences.load_from_file(file_path)

            assert loaded_prefs.interface_mode == "advanced"
            assert loaded_prefs.thumbnail_size == 250
            assert loaded_prefs.get_recent_directories("test_project") == ["/test/path"]

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file returns defaults."""
        nonexistent_path = Path("/nonexistent/path/prefs.json")

        prefs = UserPreferences.load_from_file(nonexistent_path)

        # Should return default preferences
        assert prefs.interface_mode == "simple"
        assert prefs.thumbnail_size == 150

    def test_save_file_creates_directory(self):
        """Test that saving creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "dir" / "prefs.json"

            prefs = UserPreferences()
            success = prefs.save_to_file(nested_path)

            assert success is True
            assert nested_path.exists()
            assert nested_path.parent.exists()

    def test_get_recent_directories_global(self):
        """Test getting recent directories for global context."""
        prefs = UserPreferences()
        prefs.add_recent_directory("/path1")
        prefs.add_recent_directory("/path2")

        recent = prefs.get_recent_directories()

        assert recent == ["/path2", "/path1"]  # Most recent first

    def test_get_recent_directories_project_context(self):
        """Test getting recent directories for specific project."""
        prefs = UserPreferences()
        prefs.add_recent_directory("/global/path")
        prefs.add_recent_directory("/project/path", "test_project")

        global_recent = prefs.get_recent_directories()
        project_recent = prefs.get_recent_directories("test_project")

        assert global_recent == ["/global/path"]
        assert project_recent == ["/project/path"]

    def test_add_recent_directory_limits_size(self):
        """Test that recent directories list is limited to max size."""
        prefs = UserPreferences()
        prefs.max_recent_directories = 3

        # Add more directories than the limit
        for i in range(5):
            prefs.add_recent_directory(f"/path{i}")

        recent = prefs.get_recent_directories()

        assert len(recent) == 3
        assert recent == ["/path4", "/path3", "/path2"]  # Most recent first, limited to 3

    def test_add_recent_directory_removes_duplicates(self):
        """Test that adding existing directory moves it to front."""
        prefs = UserPreferences()
        prefs.add_recent_directory("/path1")
        prefs.add_recent_directory("/path2")
        prefs.add_recent_directory("/path3")
        prefs.add_recent_directory("/path1")  # Re-add first path

        recent = prefs.get_recent_directories()

        assert recent == ["/path1", "/path3", "/path2"]  # path1 moved to front
        assert len(recent) == 3  # No duplicates

    def test_remove_recent_directory(self):
        """Test removing directory from recent list."""
        prefs = UserPreferences()
        prefs.add_recent_directory("/path1")
        prefs.add_recent_directory("/path2")
        prefs.add_recent_directory("/path3")

        prefs.remove_recent_directory("/path2")

        recent = prefs.get_recent_directories()
        assert recent == ["/path3", "/path1"]
        assert "/path2" not in recent

    def test_remove_recent_directory_project_context(self):
        """Test removing directory from specific project context."""
        prefs = UserPreferences()
        prefs.add_recent_directory("/global/path")
        prefs.add_recent_directory("/project/path1", "test_project")
        prefs.add_recent_directory("/project/path2", "test_project")

        prefs.remove_recent_directory("/project/path1", "test_project")

        global_recent = prefs.get_recent_directories()
        project_recent = prefs.get_recent_directories("test_project")

        assert global_recent == ["/global/path"]  # Unchanged
        assert project_recent == ["/project/path2"]  # path1 removed

    def test_invalid_json_file_returns_defaults(self):
        """Test that invalid JSON file returns default preferences."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "invalid.json"

            # Write invalid JSON
            with open(file_path, 'w') as f:
                f.write("{ invalid json }")

            prefs = UserPreferences.load_from_file(file_path)

            # Should return defaults despite invalid file
            assert prefs.interface_mode == "simple"
            assert prefs.thumbnail_size == 150
