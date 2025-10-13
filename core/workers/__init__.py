"""
Worker threads and background processing for CurveEditor.

This package contains worker classes for asynchronous operations:
- DirectoryScanWorker: Background directory scanning and sequence detection
- ThumbnailCache: Thumbnail caching with disk and memory storage

Note: ThumbnailWorker was removed (never used, contained Qt threading violations).
Application uses synchronous thumbnail loading on main thread via ThumbnailCache.
"""

from core.workers.directory_scanner import DirectoryScanWorker
from core.workers.thumbnail_cache import ThumbnailCache

__all__ = [
    "DirectoryScanWorker",
    "ThumbnailCache",
]
