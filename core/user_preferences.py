#!/usr/bin/env python
"""
User Preferences for CurveEditor.

This module defines user preferences data structures and serialization
for the image sequence browser and other UI components.
"""

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Literal

from core.logger_utils import get_logger

logger = get_logger("user_preferences")


@dataclass
class UserPreferences:
    """
    User preferences for the CurveEditor application.

    These preferences control interface behavior, default settings,
    and user workflow optimizations.
    """

    # Interface preferences
    interface_mode: Literal["simple", "advanced"] = "simple"
    default_sort_order: str = "name"
    sort_ascending: bool = True

    # Display preferences
    show_thumbnails: bool = True
    thumbnail_size: int = 150
    thumbnails_per_row: int = 4
    max_thumbnails: int = 12

    # Behavior preferences
    auto_detect_project_context: bool = True
    remember_window_size: bool = True
    auto_refresh_directories: bool = True
    show_sequence_metadata: bool = True

    # Performance preferences
    enable_thumbnail_cache: bool = True
    max_cache_size_mb: int = 500
    background_scanning: bool = True

    # Recent directories (per project context)
    recent_directories: dict[str, list[str]] = field(default_factory=dict)
    max_recent_directories: int = 10

    # Window state
    window_size: tuple[int, int] = (1200, 600)
    splitter_sizes: list[int] = field(default_factory=lambda: [250, 350, 600])

    def to_dict(self) -> dict[str, Any]:
        """Convert preferences to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreferences":
        """Create preferences from dictionary."""
        # Handle missing fields gracefully
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered_data)

    def save_to_file(self, file_path: Path) -> bool:
        """
        Save preferences to JSON file.

        Args:
            file_path: Path to save preferences file

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved user preferences to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save preferences to {file_path}: {e}")
            return False

    @classmethod
    def load_from_file(cls, file_path: Path) -> "UserPreferences":
        """
        Load preferences from JSON file.

        Args:
            file_path: Path to preferences file

        Returns:
            UserPreferences instance (defaults if file doesn't exist or is invalid)
        """
        if not file_path.exists():
            logger.debug(f"Preferences file {file_path} doesn't exist, using defaults")
            return cls()

        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            preferences = cls.from_dict(data)
            logger.debug(f"Loaded user preferences from {file_path}")
            return preferences

        except Exception as e:
            logger.error(f"Failed to load preferences from {file_path}: {e}")
            return cls()

    def get_recent_directories(self, project_context: str | None = None) -> list[str]:
        """
        Get recent directories for a specific project context.

        Args:
            project_context: Project identifier (None for global)

        Returns:
            List of recent directory paths
        """
        context_key = project_context or "global"
        return self.recent_directories.get(context_key, [])

    def add_recent_directory(self, path: str, project_context: str | None = None) -> None:
        """
        Add a directory to recent directories list.

        Args:
            path: Directory path to add
            project_context: Project identifier (None for global)
        """
        context_key = project_context or "global"

        if context_key not in self.recent_directories:
            self.recent_directories[context_key] = []

        recent_list = self.recent_directories[context_key]

        # Remove if already exists
        if path in recent_list:
            recent_list.remove(path)

        # Add to front
        recent_list.insert(0, path)

        # Limit size
        if len(recent_list) > self.max_recent_directories:
            recent_list[:] = recent_list[:self.max_recent_directories]

        logger.debug(f"Added {path} to recent directories for context '{context_key}'")

    def remove_recent_directory(self, path: str, project_context: str | None = None) -> None:
        """
        Remove a directory from recent directories list.

        Args:
            path: Directory path to remove
            project_context: Project identifier (None for global)
        """
        context_key = project_context or "global"

        if context_key in self.recent_directories:
            recent_list = self.recent_directories[context_key]
            if path in recent_list:
                recent_list.remove(path)
                logger.debug(f"Removed {path} from recent directories for context '{context_key}'")
