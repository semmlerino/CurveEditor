"""
DEPRECATED: This module contained unused parallel thumbnail generation code.

The application uses synchronous thumbnail loading via ThumbnailCache,
which loads images on the main thread (thread-safe). The ThumbnailWorker
and ThumbnailBatchLoader classes were never integrated into the application
and contained Qt threading violations (QPixmap/QWidget creation in worker threads).

This file is kept as a placeholder to prevent import errors, but the classes
have been removed. Use ThumbnailCache for thumbnail operations.

For history, see commit that removed the classes.
"""

# This module no longer exports any classes
__all__: list[str] = []
