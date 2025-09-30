#!/usr/bin/env python
"""
Integration tests for ImageService EXR loading functionality.

Tests that ImageService correctly delegates EXR loading to the exr_loader
module and handles caching appropriately.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from services.image_service import ImageService


class TestImageServiceExrLoading:
    """Test ImageService integration with EXR loader."""

    @patch("imageio.v3.imread")
    def test_exr_loading_failure_returns_none(self, mock_imread):
        """Test that failed EXR loading returns None."""
        mock_imread.side_effect = Exception("File not found")

        service = ImageService()
        result = service.load_image_from_path("/path/to/invalid.exr")

        assert result is None

    def test_validate_exr_path(self):
        """Test that EXR files pass validation when they exist."""
        service = ImageService()

        # Mock Path.exists() for a valid EXR file
        with patch.object(Path, "exists", return_value=True), patch.object(Path, "is_file", return_value=True):
            result = service.validate_image_path("/path/to/test.exr")
            assert result is True


class TestImageServiceExrInfo:
    """Test image info retrieval for EXR files."""

    def test_get_image_info_for_exr(self):
        """Test that get_image_info works for EXR files."""
        service = ImageService()

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value = Mock(st_size=1024000, st_mtime=1234567890.0)

            info = service.get_image_info("/path/to/test.exr")

            assert info["valid"] is True
            assert info["extension"] == ".exr"
            assert info["size_bytes"] == 1024000

    def test_exr_in_supported_formats(self):
        """Test that .exr is in the list of supported formats."""
        service = ImageService()
        formats = service.get_supported_formats()

        assert ".exr" in formats


class TestImageServiceExrPreloading:
    """Test preloading functionality with EXR files."""

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_preload_exr_images(self, mock_qimage_class, mock_imread):
        """Test preloading EXR images into cache."""
        # Mock imageio reading EXR data
        mock_imread.return_value = np.array([[[0.5, 0.6, 0.7]]], dtype=np.float32)

        # Mock QImage
        mock_qimage = Mock()
        mock_qimage.copy.return_value = mock_qimage
        mock_qimage_class.return_value = mock_qimage

        service = ImageService()

        exr_files = [
            "/path/render_0001.exr",
            "/path/render_0002.exr",
            "/path/render_0003.exr",
        ]

        with patch.object(service, "validate_image_path", return_value=True):
            count = service.preload_images(exr_files, max_preload=3)

        assert count == 3
        assert mock_imread.call_count == 3

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_preload_respects_max_limit(self, mock_qimage_class, mock_imread):
        """Test that preload respects max_preload limit."""
        # Mock imageio reading EXR data
        mock_imread.return_value = np.array([[[0.5, 0.6, 0.7]]], dtype=np.float32)

        # Mock QImage
        mock_qimage = Mock()
        mock_qimage.copy.return_value = mock_qimage
        mock_qimage_class.return_value = mock_qimage

        service = ImageService()

        exr_files = [f"/path/render_{i:04d}.exr" for i in range(1, 21)]

        with patch.object(service, "validate_image_path", return_value=True):
            count = service.preload_images(exr_files, max_preload=5)

        # Should only preload 5 images
        assert count == 5
        assert mock_imread.call_count == 5
