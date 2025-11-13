#!/usr/bin/env python
"""
Directory Scan Cache for CurveEditor.

Caches directory scan results to eliminate redundant file system scans
when navigating between directories.
"""

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.logger_utils import get_logger

logger = get_logger("directory_scan_cache")


@dataclass(frozen=True)
class CacheKey:
    """
    Cache key for directory scan results.

    Combines directory path with modification time to automatically
    invalidate cache when directory contents change.
    """

    directory: str
    mtime: float

    @classmethod
    def from_directory(cls, directory: str) -> "CacheKey | None":
        """
        Create cache key from directory path.

        Args:
            directory: Directory path

        Returns:
            CacheKey if directory exists and is accessible, None otherwise
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists() or not dir_path.is_dir():
                return None

            mtime = dir_path.stat().st_mtime
            return cls(directory=directory, mtime=mtime)
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot create cache key for {directory}: {e}")
            return None


class DirectoryScanCache:
    """
    LRU cache for directory scan results.

    Features:
    - Automatic invalidation based on directory modification time
    - LRU eviction policy
    - Thread-safe for read/write operations
    - Configurable maximum size

    Cache stores raw sequence dictionaries as returned by DirectoryScanWorker,
    not ImageSequence objects (those are created on-demand in the UI layer).
    """

    def __init__(self, max_size: int = 50):
        """
        Initialize directory scan cache.

        Args:
            max_size: Maximum number of directories to cache (default: 50)
        """
        self._cache: OrderedDict[CacheKey, list[dict[str, Any]]] = OrderedDict()
        self._max_size: int = max_size
        logger.info(f"Initialized DirectoryScanCache with max_size={max_size}")

    def get(self, directory: str) -> list[dict[str, Any]] | None:
        """
        Retrieve cached scan results for a directory.

        Automatically checks if directory has been modified since caching
        and invalidates stale entries.

        Args:
            directory: Directory path to retrieve results for

        Returns:
            List of sequence dictionaries if cached and still valid, None otherwise
        """
        # Create current cache key (includes mtime check)
        current_key = CacheKey.from_directory(directory)
        if current_key is None:
            return None

        # Check if we have a cached entry
        if current_key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(current_key)
            logger.debug(f"Cache hit for {directory}")
            return self._cache[current_key]

        # Check for stale entries (same directory, different mtime)
        stale_keys = [
            key for key in self._cache
            if key.directory == directory and key.mtime != current_key.mtime
        ]

        # Remove stale entries
        for stale_key in stale_keys:
            del self._cache[stale_key]
            logger.debug(f"Removed stale cache entry for {directory} (mtime changed)")

        logger.debug(f"Cache miss for {directory}")
        return None

    def put(self, directory: str, sequences: list[dict[str, Any]]) -> None:
        """
        Store scan results in cache.

        Args:
            directory: Directory path
            sequences: List of sequence dictionaries from DirectoryScanWorker
        """
        cache_key = CacheKey.from_directory(directory)
        if cache_key is None:
            logger.warning(f"Cannot cache results for {directory} (key creation failed)")
            return

        # Store in cache
        self._cache[cache_key] = sequences
        self._cache.move_to_end(cache_key)

        # Evict oldest entries if cache is full
        while len(self._cache) > self._max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"Evicted cache entry for {evicted_key.directory} (LRU)")

        logger.debug(f"Cached {len(sequences)} sequences for {directory}")

    def invalidate(self, directory: str) -> None:
        """
        Invalidate all cache entries for a directory.

        Args:
            directory: Directory path to invalidate
        """
        keys_to_remove = [key for key in self._cache if key.directory == directory]

        for key in keys_to_remove:
            del self._cache[key]
            logger.debug(f"Invalidated cache entry for {directory}")

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cache entries")

    def get_size(self) -> int:
        """
        Get current cache size.

        Returns:
            Number of cached directories
        """
        return len(self._cache)

    def get_cached_directories(self) -> list[str]:
        """
        Get list of cached directory paths.

        Returns:
            List of directory paths currently in cache (most recent last)
        """
        return [key.directory for key in self._cache.keys()]
