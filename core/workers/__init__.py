"""
Worker threads and background processing for CurveEditor.

This package contains worker classes for asynchronous operations:
- DirectoryScanWorker: Background directory scanning and sequence detection
- DirectoryScanCache: LRU cache for directory scan results
- ThumbnailCache: Thumbnail caching with disk and memory storage

Note: ThumbnailWorker was removed (never used, contained Qt threading violations).
Application uses synchronous thumbnail loading on main thread via ThumbnailCache.
"""

from core.workers.directory_scan_cache import DirectoryScanCache
from core.workers.directory_scanner import DirectoryScanWorker
from core.workers.thumbnail_cache import ThumbnailCache

__all__ = [
    "DirectoryScanCache",
    "DirectoryScanWorker",
    "ThumbnailCache",
]
