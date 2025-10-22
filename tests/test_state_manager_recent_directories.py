"""Tests for StateManager recent directories functionality."""

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

import pytest

from ui.state_manager import StateManager


@pytest.fixture
def state_manager():
    """Create StateManager instance for testing."""
    return StateManager()


def test_recent_directories_empty_initially(state_manager):
    """Test recent directories list is empty on initialization."""
    assert state_manager.recent_directories == []


def test_add_recent_directory(state_manager):
    """Test adding a directory to recent list."""
    state_manager.add_recent_directory("/test/dir1")

    assert len(state_manager.recent_directories) == 1
    assert state_manager.recent_directories[0] == "/test/dir1"


def test_add_recent_directory_normalizes_path(state_manager):
    """Test paths are normalized when added."""
    import os
    from pathlib import Path

    # Add relative path
    test_path = "relative/path"
    state_manager.add_recent_directory(test_path)

    # Should be normalized to absolute
    result = state_manager.recent_directories[0]
    assert os.path.isabs(result) or Path(result).is_absolute()


def test_add_recent_directory_most_recent_first(state_manager):
    """Test most recent directory appears first."""
    state_manager.add_recent_directory("/test/dir1")
    state_manager.add_recent_directory("/test/dir2")
    state_manager.add_recent_directory("/test/dir3")

    assert state_manager.recent_directories[0] == "/test/dir3"
    assert state_manager.recent_directories[1] == "/test/dir2"
    assert state_manager.recent_directories[2] == "/test/dir1"


def test_add_duplicate_moves_to_top(state_manager):
    """Test adding duplicate directory moves it to top instead of duplicating."""
    state_manager.add_recent_directory("/test/dir1")
    state_manager.add_recent_directory("/test/dir2")
    state_manager.add_recent_directory("/test/dir3")

    # Add dir1 again - should move to top
    state_manager.add_recent_directory("/test/dir1")

    recents = state_manager.recent_directories
    assert len(recents) == 3  # Still 3, not 4
    assert recents[0] == "/test/dir1"  # Moved to top
    assert recents[1] == "/test/dir3"
    assert recents[2] == "/test/dir2"


def test_recent_directories_max_limit(state_manager):
    """Test recent directories list caps at max size (10)."""
    # Add 15 directories
    for i in range(15):
        state_manager.add_recent_directory(f"/test/dir{i}")

    recents = state_manager.recent_directories
    assert len(recents) == 10  # Capped at max

    # Most recent should be dir14
    assert recents[0] == "/test/dir14"
    # Oldest retained should be dir5
    assert recents[-1] == "/test/dir5"
    # dir0-dir4 should have been dropped
    assert "/test/dir0" not in recents


def test_set_recent_directories(state_manager):
    """Test setting recent directories list directly."""
    directories = ["/test/dir1", "/test/dir2", "/test/dir3"]
    state_manager.set_recent_directories(directories)

    assert state_manager.recent_directories == directories


def test_set_recent_directories_respects_max_limit(state_manager):
    """Test set_recent_directories caps at max size."""
    # Try to set 15 directories
    directories = [f"/test/dir{i}" for i in range(15)]
    state_manager.set_recent_directories(directories)

    assert len(state_manager.recent_directories) == 10  # Capped


def test_recent_directories_returns_copy(state_manager):
    """Test recent_directories property returns a copy, not reference."""
    state_manager.add_recent_directory("/test/dir1")

    recents = state_manager.recent_directories
    recents.append("/should/not/affect/internal/list")

    # Internal list should be unchanged
    assert len(state_manager.recent_directories) == 1
    assert "/should/not/affect/internal/list" not in state_manager.recent_directories


def test_reset_to_defaults_clears_recent_directories(state_manager):
    """Test reset_to_defaults() clears recent directories."""
    state_manager.add_recent_directory("/test/dir1")
    state_manager.add_recent_directory("/test/dir2")

    assert len(state_manager.recent_directories) == 2

    state_manager.reset_to_defaults()

    assert state_manager.recent_directories == []


def test_recent_directories_with_special_characters(state_manager):
    """Test handling paths with special characters."""
    paths = [
        "/test/dir with spaces",
        "/test/dir-with-dashes",
        "/test/dir_with_underscores",
        "/test/dir.with.dots",
    ]

    for path in paths:
        state_manager.add_recent_directory(path)

    recents = state_manager.recent_directories
    assert len(recents) == 4
    # All paths should be present (order reversed due to FIFO)
    for path in paths:
        assert any(path in r for r in recents)
