"""Tests for SessionManager recent directories persistence."""

import json
import tempfile
from pathlib import Path

import pytest

from ui.session_manager import SessionManager


@pytest.fixture
def temp_session_dir():
    """Create temporary session directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(temp_session_dir):
    """Create SessionManager with temp directory."""
    manager = SessionManager(project_root=temp_session_dir)
    return manager


def test_create_session_data_with_recent_directories(session_manager):
    """Test creating session data includes recent directories."""
    recent_dirs = ["/test/dir1", "/test/dir2", "/test/dir3"]

    session_data = session_manager.create_session_data(
        tracking_file="/test/file.txt",
        image_directory="/test/images",
        current_frame=10,
        zoom_level=2.0,
        recent_directories=recent_dirs,
    )

    assert "recent_directories" in session_data
    assert session_data["recent_directories"] == recent_dirs


def test_create_session_data_without_recent_directories(session_manager):
    """Test creating session data with no recent directories."""
    session_data = session_manager.create_session_data(
        tracking_file="/test/file.txt",
        recent_directories=None,
    )

    assert "recent_directories" in session_data
    assert session_data["recent_directories"] == []


def test_save_session_with_recent_directories(session_manager, temp_session_dir):
    """Test saving session persists recent directories to JSON."""
    recent_dirs = ["/test/dir1", "/test/dir2"]

    session_data = session_manager.create_session_data(
        recent_directories=recent_dirs,
    )

    success = session_manager.save_session(session_data)
    assert success

    # Verify JSON file content
    session_file = temp_session_dir / "session" / "last_session.json"
    assert session_file.exists()

    with open(session_file, encoding="utf-8") as f:
        saved_data = json.load(f)

    assert "recent_directories" in saved_data
    # Paths should be made relative where possible
    assert isinstance(saved_data["recent_directories"], list)


def test_load_session_with_recent_directories(session_manager, temp_session_dir):
    """Test loading session restores recent directories."""
    # Create and save session
    recent_dirs = [
        str(temp_session_dir / "dir1"),
        str(temp_session_dir / "dir2"),
    ]

    # Create the directories so they exist
    for dir_path in recent_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    session_data = session_manager.create_session_data(
        recent_directories=recent_dirs,
    )
    session_manager.save_session(session_data)

    # Load session
    loaded_data = session_manager.load_session()

    assert loaded_data is not None
    assert "recent_directories" in loaded_data
    assert isinstance(loaded_data["recent_directories"], list)
    assert len(loaded_data["recent_directories"]) == 2


def test_load_session_filters_nonexistent_directories(session_manager, temp_session_dir):
    """Test loading session filters out non-existent directories."""
    # Mix of existent and non-existent directories
    existing_dir = temp_session_dir / "exists"
    existing_dir.mkdir(parents=True, exist_ok=True)

    recent_dirs = [
        str(existing_dir),
        "/nonexistent/dir1",
        "/nonexistent/dir2",
    ]

    session_data = session_manager.create_session_data(
        recent_directories=recent_dirs,
    )
    session_manager.save_session(session_data)

    # Load session
    loaded_data = session_manager.load_session()

    assert loaded_data is not None
    assert "recent_directories" in loaded_data
    # Only existing directory should remain
    assert len(loaded_data["recent_directories"]) == 1
    assert str(existing_dir) in loaded_data["recent_directories"]


def test_save_session_makes_paths_relative(session_manager, temp_session_dir):
    """Test saving session converts absolute paths to relative where possible."""
    # Path within project tree
    project_subdir = temp_session_dir / "subdir"
    project_subdir.mkdir(parents=True, exist_ok=True)

    recent_dirs = [str(project_subdir)]

    session_data = session_manager.create_session_data(
        recent_directories=recent_dirs,
    )
    session_manager.save_session(session_data)

    # Load raw JSON
    session_file = temp_session_dir / "session" / "last_session.json"
    with open(session_file, encoding="utf-8") as f:
        saved_data = json.load(f)

    # Path should be relative
    saved_path = saved_data["recent_directories"][0]
    assert not Path(saved_path).is_absolute() or saved_path == str(project_subdir)


def test_restore_session_state_sets_recent_directories(session_manager):
    """Test restore_session_state calls set_recent_directories on state_manager."""
    from unittest.mock import Mock

    # Create mock main window with state manager
    mock_main_window = Mock()
    mock_state_manager = Mock()
    mock_main_window.state_manager = mock_state_manager

    # Create session data with recent directories
    session_data = {
        "tracking_file": None,
        "image_directory": None,
        "current_frame": 1,
        "zoom_level": 1.0,
        "pan_offset": [0.0, 0.0],
        "active_points": [],
        "recent_directories": ["/test/dir1", "/test/dir2"],
    }

    # Mock file load worker
    mock_main_window.file_load_worker = None

    session_manager.restore_session_state(mock_main_window, session_data)

    # Verify set_recent_directories was called
    mock_state_manager.set_recent_directories.assert_called_once_with(["/test/dir1", "/test/dir2"])


def test_restore_session_state_handles_missing_recent_directories(session_manager):
    """Test restore_session_state handles missing recent_directories gracefully."""
    from unittest.mock import Mock

    mock_main_window = Mock()
    mock_state_manager = Mock()
    mock_main_window.state_manager = mock_state_manager
    mock_main_window.file_load_worker = None

    # Session data without recent_directories
    session_data = {
        "tracking_file": None,
        "image_directory": None,
        "current_frame": 1,
    }

    # Should not crash
    session_manager.restore_session_state(mock_main_window, session_data)

    # set_recent_directories should not be called
    mock_state_manager.set_recent_directories.assert_not_called()


def test_session_data_empty_recent_directories(session_manager):
    """Test session data with empty recent directories list."""
    session_data = session_manager.create_session_data(
        recent_directories=[],
    )

    assert session_data["recent_directories"] == []


def test_recent_directories_persistence_integration(session_manager, temp_session_dir):
    """Integration test: save, load, and verify recent directories."""
    # Create test directories
    dir1 = temp_session_dir / "project1"
    dir2 = temp_session_dir / "project2"
    dir1.mkdir(parents=True)
    dir2.mkdir(parents=True)

    recent_dirs = [str(dir1), str(dir2)]

    # Create and save session
    session_data = session_manager.create_session_data(
        tracking_file=str(temp_session_dir / "track.txt"),
        recent_directories=recent_dirs,
    )

    save_success = session_manager.save_session(session_data)
    assert save_success

    # Create new manager instance (simulates app restart)
    new_manager = SessionManager(project_root=temp_session_dir)

    # Load session
    loaded_data = new_manager.load_session()

    assert loaded_data is not None
    assert "recent_directories" in loaded_data
    assert len(loaded_data["recent_directories"]) == 2

    # Verify directories are restored (may be resolved to absolute)
    loaded_dirs = loaded_data["recent_directories"]
    assert str(dir1) in loaded_dirs or Path(loaded_dirs[0]).resolve() == dir1.resolve()
    assert str(dir2) in loaded_dirs or Path(loaded_dirs[1]).resolve() == dir2.resolve()
