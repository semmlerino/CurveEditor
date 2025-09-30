#!/usr/bin/env python
"""Favorites manager for directory bookmarks."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.logger_utils import get_logger

logger = get_logger("favorites_manager")


@dataclass
class Favorite:
    """A favorite directory bookmark."""

    name: str
    path: str


class FavoritesManager:
    """Manages user-curated favorite directories."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize favorites manager.

        Args:
            config_dir: Directory for favorites file (defaults to ~/.curveeditor)
        """
        if config_dir is None:
            config_dir = Path.home() / ".curveeditor"

        self.config_dir: Path = config_dir
        self.favorites_file: Path = config_dir / "favorites.json"
        self._favorites: list[Favorite] = []

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)

        # Load existing favorites
        self._load()

    def _load(self) -> None:
        """Load favorites from JSON file."""
        if not self.favorites_file.exists():
            logger.info("No favorites file found, starting with empty list")
            return

        try:
            with open(self.favorites_file, encoding="utf-8") as f:
                data: dict[str, list[dict[str, str]]] = json.load(f)

            self._favorites = [Favorite(**fav) for fav in data.get("favorites", [])]
            logger.info(f"Loaded {len(self._favorites)} favorites")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load favorites: {e}")
            self._favorites = []

    def _save(self) -> bool:
        """Save favorites to JSON file.

        Returns:
            True if save successful
        """
        try:
            data = {"favorites": [asdict(fav) for fav in self._favorites]}
            with open(self.favorites_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self._favorites)} favorites")
            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save favorites: {e}")
            return False

    def get_all(self) -> list[Favorite]:
        """Get all favorites.

        Returns:
            Copy of favorites list
        """
        return self._favorites.copy()

    def add(self, name: str, path: str) -> bool:
        """Add a favorite.

        Args:
            name: Display name for the favorite
            path: Directory path

        Returns:
            True if added successfully
        """
        # Check for duplicate path
        if any(fav.path == path for fav in self._favorites):
            logger.warning(f"Favorite already exists: {path}")
            return False

        self._favorites.append(Favorite(name=name, path=path))
        return self._save()

    def remove(self, path: str) -> bool:
        """Remove a favorite by path.

        Args:
            path: Path of favorite to remove

        Returns:
            True if removed successfully
        """
        original_len = len(self._favorites)
        self._favorites = [fav for fav in self._favorites if fav.path != path]

        if len(self._favorites) < original_len:
            return self._save()
        return False

    def rename(self, path: str, new_name: str) -> bool:
        """Rename a favorite.

        Args:
            path: Path of favorite to rename
            new_name: New display name

        Returns:
            True if renamed successfully
        """
        for fav in self._favorites:
            if fav.path == path:
                fav.name = new_name
                return self._save()
        return False

    def move_up(self, path: str) -> bool:
        """Move favorite up in the list.

        Args:
            path: Path of favorite to move

        Returns:
            True if moved successfully
        """
        for i, fav in enumerate(self._favorites):
            if fav.path == path and i > 0:
                self._favorites[i], self._favorites[i - 1] = self._favorites[i - 1], self._favorites[i]
                return self._save()
        return False

    def move_down(self, path: str) -> bool:
        """Move favorite down in the list.

        Args:
            path: Path of favorite to move

        Returns:
            True if moved successfully
        """
        for i, fav in enumerate(self._favorites):
            if fav.path == path and i < len(self._favorites) - 1:
                self._favorites[i], self._favorites[i + 1] = self._favorites[i + 1], self._favorites[i]
                return self._save()
        return False

    def is_favorite(self, path: str) -> bool:
        """Check if path is in favorites.

        Args:
            path: Path to check

        Returns:
            True if path is favorited
        """
        return any(fav.path == path for fav in self._favorites)
