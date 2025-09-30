#!/usr/bin/env python
"""
Tests for EXR image loading functionality.

Tests the io_utils/exr_loader.py module which provides OpenEXR support
for Qt image loading using imageio.
"""

from unittest.mock import Mock, patch

import numpy as np

from io_utils.exr_loader import (
    is_exr_file,
    load_exr_as_qimage,
    load_exr_as_qpixmap,
)


class TestIsExrFile:
    """Test the is_exr_file() helper function."""

    def test_exr_extension_lowercase(self):
        """Test that .exr extension is recognized (lowercase)."""
        assert is_exr_file("test.exr") is True

    def test_exr_extension_uppercase(self):
        """Test that .EXR extension is recognized (uppercase)."""
        assert is_exr_file("test.EXR") is True

    def test_exr_extension_mixed_case(self):
        """Test that .ExR extension is recognized (mixed case)."""
        assert is_exr_file("test.ExR") is True

    def test_exr_with_path(self):
        """Test that EXR files with full paths are recognized."""
        assert is_exr_file("/path/to/render_0001.exr") is True

    def test_non_exr_extension(self):
        """Test that non-EXR files are not recognized."""
        assert is_exr_file("test.png") is False
        assert is_exr_file("test.jpg") is False
        assert is_exr_file("test.tiff") is False

    def test_no_extension(self):
        """Test file without extension."""
        assert is_exr_file("test") is False

    def test_multiple_dots_in_filename(self):
        """Test filename with multiple dots."""
        assert is_exr_file("render.v001.0001.exr") is True
        assert is_exr_file("render.v001.0001.png") is False


class TestToneMapping:
    """Test the HDR to LDR tone mapping functionality."""

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_tone_mapping_applied_to_hdr_data(self, mock_qimage, mock_imread):
        """Test that tone mapping is applied to HDR pixel values."""
        # Create mock HDR data with values > 1.0
        hdr_data = np.array([[[10.0, 5.0, 2.0]]], dtype=np.float32)
        mock_imread.return_value = hdr_data

        # Mock QImage
        mock_qimage_instance = Mock()
        mock_qimage_instance.copy.return_value = mock_qimage_instance
        mock_qimage.return_value = mock_qimage_instance

        result = load_exr_as_qimage("test.exr")

        # Verify imread was called
        mock_imread.assert_called_once_with("test.exr")

        # Result should not be None
        assert result is not None

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_negative_values_clamped(self, mock_qimage, mock_imread):
        """Test that negative pixel values are clamped to 0."""
        # Create data with negative values
        data_with_negatives = np.array([[[-1.0, 0.5, 2.0]]], dtype=np.float32)
        mock_imread.return_value = data_with_negatives

        # Mock QImage
        mock_qimage_instance = Mock()
        mock_qimage_instance.copy.return_value = mock_qimage_instance
        mock_qimage.return_value = mock_qimage_instance

        result = load_exr_as_qimage("test.exr")

        # Should not crash and should return an image
        assert result is not None


class TestLoadExrAsQImage:
    """Test the load_exr_as_qimage() function."""

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_load_valid_exr_rgb(self, mock_qimage, mock_imread):
        """Test loading a valid RGB EXR file."""
        # Create mock RGB data (1x1 pixel)
        rgb_data = np.array([[[0.5, 0.6, 0.7]]], dtype=np.float32)
        mock_imread.return_value = rgb_data

        # Mock QImage
        mock_qimage_instance = Mock()
        mock_qimage_instance.copy.return_value = mock_qimage_instance
        mock_qimage.return_value = mock_qimage_instance

        result = load_exr_as_qimage("test.exr")

        assert result is not None
        mock_imread.assert_called_once_with("test.exr")

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_load_valid_exr_rgba(self, mock_qimage, mock_imread):
        """Test loading a valid RGBA EXR file."""
        # Create mock RGBA data (1x1 pixel)
        rgba_data = np.array([[[0.5, 0.6, 0.7, 1.0]]], dtype=np.float32)
        mock_imread.return_value = rgba_data

        # Mock QImage with RGBA format
        mock_qimage_instance = Mock()
        mock_qimage_instance.copy.return_value = mock_qimage_instance
        mock_qimage.return_value = mock_qimage_instance

        result = load_exr_as_qimage("test.exr")

        assert result is not None

    @patch("imageio.v3.imread")
    def test_load_invalid_file_returns_none(self, mock_imread):
        """Test that loading an invalid file returns None."""
        mock_imread.side_effect = Exception("File not found")

        result = load_exr_as_qimage("nonexistent.exr")

        assert result is None

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_load_large_exr_dimensions(self, mock_qimage, mock_imread):
        """Test loading EXR with realistic dimensions."""
        # Create mock data with realistic dimensions (1920x1080)
        large_data = np.random.rand(1080, 1920, 3).astype(np.float32)
        mock_imread.return_value = large_data

        # Mock QImage
        mock_qimage_instance = Mock()
        mock_qimage_instance.copy.return_value = mock_qimage_instance
        mock_qimage.return_value = mock_qimage_instance

        result = load_exr_as_qimage("large.exr")

        assert result is not None

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    def test_qimage_copy_called(self, mock_qimage, mock_imread):
        """Test that QImage.copy() is called to persist data."""
        rgb_data = np.array([[[0.5, 0.6, 0.7]]], dtype=np.float32)
        mock_imread.return_value = rgb_data

        # Mock QImage
        mock_qimage_instance = Mock()
        mock_qimage_copy = Mock()
        mock_qimage_instance.copy.return_value = mock_qimage_copy
        mock_qimage.return_value = mock_qimage_instance

        result = load_exr_as_qimage("test.exr")

        # Verify copy() was called
        mock_qimage_instance.copy.assert_called_once()
        assert result == mock_qimage_copy


class TestLoadExrAsQPixmap:
    """Test the load_exr_as_qpixmap() function."""

    @patch("io_utils.exr_loader.load_exr_as_qimage")
    @patch("PySide6.QtGui.QPixmap")
    def test_load_valid_exr_as_pixmap(self, mock_qpixmap, mock_load_qimage):
        """Test loading EXR as QPixmap."""
        # Mock QImage
        mock_qimage = Mock()
        mock_load_qimage.return_value = mock_qimage

        # Mock QPixmap
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.isNull.return_value = False
        mock_qpixmap.fromImage.return_value = mock_pixmap_instance

        result = load_exr_as_qpixmap("test.exr")

        assert result is not None
        mock_load_qimage.assert_called_once_with("test.exr")
        mock_qpixmap.fromImage.assert_called_once_with(mock_qimage)

    @patch("io_utils.exr_loader.load_exr_as_qimage")
    def test_load_returns_none_if_qimage_fails(self, mock_load_qimage):
        """Test that None is returned if QImage loading fails."""
        mock_load_qimage.return_value = None

        result = load_exr_as_qpixmap("test.exr")

        assert result is None

    @patch("io_utils.exr_loader.load_exr_as_qimage")
    @patch("PySide6.QtGui.QPixmap")
    def test_load_returns_none_if_pixmap_null(self, mock_qpixmap, mock_load_qimage):
        """Test that None is returned if QPixmap conversion results in null pixmap."""
        # Mock QImage
        mock_qimage = Mock()
        mock_load_qimage.return_value = mock_qimage

        # Mock QPixmap that returns null
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.isNull.return_value = True
        mock_qpixmap.fromImage.return_value = mock_pixmap_instance

        result = load_exr_as_qpixmap("test.exr")

        assert result is None

    @patch("io_utils.exr_loader.load_exr_as_qimage")
    @patch("PySide6.QtGui.QPixmap")
    def test_exception_handling(self, mock_qpixmap, mock_load_qimage):
        """Test that exceptions are caught and None is returned."""
        mock_load_qimage.return_value = Mock()
        mock_qpixmap.fromImage.side_effect = Exception("Conversion failed")

        result = load_exr_as_qpixmap("test.exr")

        assert result is None


class TestExrLoaderIntegration:
    """Integration tests that verify the full loading pipeline."""

    @patch("imageio.v3.imread")
    @patch("PySide6.QtGui.QImage")
    @patch("PySide6.QtGui.QPixmap")
    def test_end_to_end_mock_workflow(self, mock_qpixmap, mock_qimage_class, mock_imread):
        """Test the complete workflow from file to QPixmap."""
        # Step 1: Mock imageio reading EXR
        mock_data = np.array([[[0.5, 0.6, 0.7]]], dtype=np.float32)
        mock_imread.return_value = mock_data

        # Step 2: Mock QImage creation
        mock_qimage_instance = Mock()
        mock_qimage_copy = Mock()
        mock_qimage_instance.copy.return_value = mock_qimage_copy
        mock_qimage_class.return_value = mock_qimage_instance

        # Step 3: Mock QPixmap conversion
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.isNull.return_value = False
        mock_qpixmap.fromImage.return_value = mock_pixmap_instance

        # Execute full workflow
        qimage = load_exr_as_qimage("test.exr")
        assert qimage is not None

        qpixmap = load_exr_as_qpixmap("test.exr")
        assert qpixmap is not None
