"""Tests for FavoritesManager functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from core.favorites_manager import Favorite, FavoritesManager


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def favorites_manager(temp_config_dir):
    """Create FavoritesManager with temp directory."""
    return FavoritesManager(config_dir=temp_config_dir)


def test_favorites_manager_creates_config_dir(temp_config_dir):
    """Test FavoritesManager creates config directory if missing."""
    config_path = temp_config_dir / "subdir"
    assert not config_path.exists()

    FavoritesManager(config_dir=config_path)

    assert config_path.exists()
    assert config_path.is_dir()


def test_favorites_manager_empty_initially(favorites_manager):
    """Test favorites list is empty on first load."""
    assert favorites_manager.get_all() == []


def test_add_favorite(favorites_manager, temp_config_dir):
    """Test adding a favorite."""
    success = favorites_manager.add("Project A", "/path/to/project")

    assert success
    favorites = favorites_manager.get_all()
    assert len(favorites) == 1
    assert favorites[0].name == "Project A"
    assert favorites[0].path == "/path/to/project"

    # Verify JSON file created
    json_file = temp_config_dir / "favorites.json"
    assert json_file.exists()


def test_add_duplicate_favorite_fails(favorites_manager):
    """Test adding duplicate path is rejected."""
    favorites_manager.add("Project A", "/path/to/project")

    # Try to add same path again with different name
    success = favorites_manager.add("Project B", "/path/to/project")

    assert not success
    assert len(favorites_manager.get_all()) == 1


def test_remove_favorite(favorites_manager):
    """Test removing a favorite."""
    favorites_manager.add("Project A", "/path/to/project")
    favorites_manager.add("Project B", "/other/path")

    success = favorites_manager.remove("/path/to/project")

    assert success
    favorites = favorites_manager.get_all()
    assert len(favorites) == 1
    assert favorites[0].name == "Project B"


def test_remove_nonexistent_favorite_fails(favorites_manager):
    """Test removing non-existent favorite returns False."""
    success = favorites_manager.remove("/nonexistent/path")

    assert not success


def test_rename_favorite(favorites_manager):
    """Test renaming a favorite."""
    favorites_manager.add("Old Name", "/path/to/project")

    success = favorites_manager.rename("/path/to/project", "New Name")

    assert success
    favorites = favorites_manager.get_all()
    assert len(favorites) == 1
    assert favorites[0].name == "New Name"
    assert favorites[0].path == "/path/to/project"


def test_rename_nonexistent_favorite_fails(favorites_manager):
    """Test renaming non-existent favorite returns False."""
    success = favorites_manager.rename("/nonexistent/path", "New Name")

    assert not success


def test_move_up(favorites_manager):
    """Test moving favorite up in list."""
    favorites_manager.add("First", "/path/1")
    favorites_manager.add("Second", "/path/2")
    favorites_manager.add("Third", "/path/3")

    # Move "Third" up
    success = favorites_manager.move_up("/path/3")

    assert success
    favorites = favorites_manager.get_all()
    assert favorites[0].name == "First"
    assert favorites[1].name == "Third"  # Moved up
    assert favorites[2].name == "Second"


def test_move_up_first_item_fails(favorites_manager):
    """Test moving first item up returns False."""
    favorites_manager.add("First", "/path/1")
    favorites_manager.add("Second", "/path/2")

    success = favorites_manager.move_up("/path/1")

    assert not success


def test_move_down(favorites_manager):
    """Test moving favorite down in list."""
    favorites_manager.add("First", "/path/1")
    favorites_manager.add("Second", "/path/2")
    favorites_manager.add("Third", "/path/3")

    # Move "First" down
    success = favorites_manager.move_down("/path/1")

    assert success
    favorites = favorites_manager.get_all()
    assert favorites[0].name == "Second"
    assert favorites[1].name == "First"  # Moved down
    assert favorites[2].name == "Third"


def test_move_down_last_item_fails(favorites_manager):
    """Test moving last item down returns False."""
    favorites_manager.add("First", "/path/1")
    favorites_manager.add("Second", "/path/2")

    success = favorites_manager.move_down("/path/2")

    assert not success


def test_is_favorite(favorites_manager):
    """Test checking if path is favorited."""
    favorites_manager.add("Project", "/path/to/project")

    assert favorites_manager.is_favorite("/path/to/project")
    assert not favorites_manager.is_favorite("/other/path")


def test_get_all_returns_copy(favorites_manager):
    """Test get_all() returns a copy, not reference."""
    favorites_manager.add("Project", "/path/to/project")

    favorites = favorites_manager.get_all()
    favorites.append(Favorite("Fake", "/fake/path"))

    # Internal list should be unchanged
    assert len(favorites_manager.get_all()) == 1


def test_persistence_across_instances(temp_config_dir):
    """Test favorites persist across manager instances."""
    # Create first manager and add favorites
    manager1 = FavoritesManager(config_dir=temp_config_dir)
    manager1.add("Project A", "/path/a")
    manager1.add("Project B", "/path/b")

    # Create second manager - should load existing favorites
    manager2 = FavoritesManager(config_dir=temp_config_dir)
    favorites = manager2.get_all()

    assert len(favorites) == 2
    assert favorites[0].name == "Project A"
    assert favorites[1].name == "Project B"


def test_json_file_structure(favorites_manager, temp_config_dir):
    """Test JSON file has correct structure."""
    favorites_manager.add("Project A", "/path/a")
    favorites_manager.add("Project B", "/path/b")

    json_file = temp_config_dir / "favorites.json"
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    assert "favorites" in data
    assert isinstance(data["favorites"], list)
    assert len(data["favorites"]) == 2
    assert data["favorites"][0] == {"name": "Project A", "path": "/path/a"}
    assert data["favorites"][1] == {"name": "Project B", "path": "/path/b"}


def test_corrupted_json_file_recovery(temp_config_dir):
    """Test manager handles corrupted JSON gracefully."""
    # Create corrupted JSON file
    json_file = temp_config_dir / "favorites.json"
    json_file.write_text("{ invalid json", encoding="utf-8")

    # Should not crash, just start with empty list
    manager = FavoritesManager(config_dir=temp_config_dir)
    assert manager.get_all() == []


def test_add_multiple_favorites(favorites_manager):
    """Test adding multiple favorites maintains order."""
    names_paths = [
        ("Project A", "/path/a"),
        ("Project B", "/path/b"),
        ("Project C", "/path/c"),
        ("Project D", "/path/d"),
    ]

    for name, path in names_paths:
        favorites_manager.add(name, path)

    favorites = favorites_manager.get_all()
    assert len(favorites) == 4

    for i, (name, path) in enumerate(names_paths):
        assert favorites[i].name == name
        assert favorites[i].path == path


def test_favorite_dataclass():
    """Test Favorite dataclass."""
    fav = Favorite(name="Test", path="/test/path")

    assert fav.name == "Test"
    assert fav.path == "/test/path"

    # Test immutability via dataclass frozen=False (it's mutable in our impl)
    fav.name = "Updated"
    assert fav.name == "Updated"
