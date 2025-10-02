#!/usr/bin/env python
"""
Tests for Phase 1 image browser improvements.

Tests async loading, metadata extraction, gap detection, and caching.
"""

import tempfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from core.metadata_extractor import ImageMetadata
from core.workers import DirectoryScanWorker, ThumbnailCache
from ui.image_sequence_browser import ImageSequence, ImageSequenceBrowserDialog


class TestImageSequenceMetadata:
    """Test ImageSequence metadata fields and gap detection."""

    def test_sequence_with_gaps(self):
        """Test gap detection in sequences."""
        sequence = ImageSequence(
            base_name="render_",
            padding=4,
            extension=".jpg",
            frames=[1, 2, 3, 5, 7, 8, 9, 10],  # Missing 4 and 6
            file_list=["render_0001.jpg", "render_0002.jpg"],
            directory="/test",
        )

        assert sequence.has_gaps is True
        assert sequence.missing_frames == [4, 6]

    def test_sequence_without_gaps(self):
        """Test sequence with no gaps."""
        sequence = ImageSequence(
            base_name="render_",
            padding=4,
            extension=".jpg",
            frames=[1, 2, 3, 4, 5],
            file_list=["render_0001.jpg"],
            directory="/test",
        )

        assert sequence.has_gaps is False
        assert sequence.missing_frames == []

    def test_display_name_with_metadata(self):
        """Test display name includes metadata."""
        sequence = ImageSequence(
            base_name="render_",
            padding=4,
            extension=".exr",
            frames=[1, 2, 3],
            file_list=["render_0001.exr"],
            directory="/test",
            resolution=(3840, 2160),
            bit_depth=32,
        )

        display_name = sequence.display_name
        assert "4K" in display_name or "3840x2160" in display_name
        assert "32bit" in display_name


class TestImageMetadataExtractor:
    """Test metadata extraction."""

    def test_metadata_resolution_labels(self):
        """Test common resolution labels."""
        metadata = ImageMetadata(width=3840, height=2160, bit_depth=32)

        assert "4K UHD" in metadata.resolution_label

    def test_file_size_calculation(self):
        """Test file size conversion."""
        metadata = ImageMetadata(file_size_bytes=1024 * 1024 * 5)  # 5 MB

        assert metadata.file_size_mb == pytest.approx(5.0)


class TestThumbnailCache:
    """Test thumbnail caching system."""

    def test_cache_initialization(self):
        """Test cache initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = ThumbnailCache(cache_dir=Path(temp_dir))

            assert cache.cache_dir.exists()

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        cache = ThumbnailCache()

        key1 = cache.get_cache_key("/path/to/image.exr", 150)
        key2 = cache.get_cache_key("/path/to/image.exr", 150)

        assert key1 == key2

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = ThumbnailCache()

        stats = cache.get_cache_stats()

        assert "memory_entries" in stats
        assert "disk_entries" in stats
        assert stats["memory_entries"] == 0


class TestDirectoryScanWorker:
    """Test directory scanning worker."""

    def test_worker_initialization(self):
        """Test worker can be created."""
        worker = DirectoryScanWorker("/test/path")

        assert worker.directory == "/test/path"
        assert worker._cancelled is False

    def test_cancel_mechanism(self):
        """Test cancellation mechanism."""
        worker = DirectoryScanWorker("/test/path")

        worker.cancel()

        assert worker._cancelled is True


class TestImageBrowserDialog:
    """Test image browser dialog integration."""

    @pytest.fixture
    def qapp(self) -> QApplication:
        """Ensure QApplication exists."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_dialog_initializes(self, qapp: QApplication):
        """Test dialog initializes with new features."""
        dialog = ImageSequenceBrowserDialog()

        # Check new attributes exist
        assert hasattr(dialog, "thumbnail_cache")
        assert hasattr(dialog, "scan_worker")
        assert hasattr(dialog, "metadata_extractor")
        assert hasattr(dialog, "progress_bar")
        assert hasattr(dialog, "cancel_scan_button")

        # Check UI elements created
        assert dialog.progress_bar is not None
        assert dialog.cancel_scan_button is not None

        # Check initially hidden
        assert dialog.progress_bar.isVisible() is False
        assert dialog.cancel_scan_button.isVisible() is False

        dialog.close()

    def test_cache_initialized(self, qapp: QApplication):
        """Test thumbnail cache is initialized."""
        dialog = ImageSequenceBrowserDialog()

        assert dialog.thumbnail_cache is not None
        assert hasattr(dialog.thumbnail_cache, "get")
        assert hasattr(dialog.thumbnail_cache, "store")

        dialog.close()
