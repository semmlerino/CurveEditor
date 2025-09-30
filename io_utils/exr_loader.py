"""
EXR Image Loader for CurveEditor.

Provides helper functions to load OpenEXR images using imageio and convert
them to Qt image formats (QImage/QPixmap) with proper tone mapping.

QImage and QPixmap do not natively support OpenEXR format, so this module
bridges the gap using imageio for reading and numpy for processing.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)


def load_exr_as_qimage(file_path: str) -> "QImage | None":
    """
    Load an OpenEXR image file and convert it to QImage.

    Args:
        file_path: Path to the EXR file

    Returns:
        QImage object or None if loading failed
    """
    try:
        import imageio.v3 as iio
        from PySide6.QtGui import QImage

        # Read EXR file using imageio
        img_data = iio.imread(file_path)

        # Apply tone mapping (HDR -> LDR conversion)
        img_data = _tone_map_hdr(img_data)

        # Convert to 8-bit RGB
        img_8bit = (img_data * 255).astype(np.uint8)

        # Get dimensions
        height, width = img_8bit.shape[:2]
        bytes_per_line = width * 3

        # Handle RGB vs RGBA
        if img_8bit.shape[2] == 4:
            # RGBA format
            qimage = QImage(
                img_8bit.data,
                width,
                height,
                img_8bit.strides[0],
                QImage.Format.Format_RGBA8888,
            )
        else:
            # RGB format
            qimage = QImage(
                img_8bit.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )

        # Copy the image data to ensure it persists
        qimage = qimage.copy()

        logger.debug(f"Loaded EXR image: {file_path} ({width}x{height})")
        return qimage

    except Exception as e:
        logger.error(f"Failed to load EXR image {file_path}: {e}")
        return None


def load_exr_as_qpixmap(file_path: str) -> "QPixmap | None":
    """
    Load an OpenEXR image file and convert it to QPixmap.

    Args:
        file_path: Path to the EXR file

    Returns:
        QPixmap object or None if loading failed
    """
    try:
        from PySide6.QtGui import QPixmap

        # Load as QImage first
        qimage = load_exr_as_qimage(file_path)

        if qimage is None:
            return None

        # Convert to QPixmap
        pixmap = QPixmap.fromImage(qimage)

        if pixmap.isNull():
            logger.error(f"Failed to convert QImage to QPixmap for {file_path}")
            return None

        logger.debug(f"Converted EXR to QPixmap: {file_path}")
        return pixmap

    except Exception as e:
        logger.error(f"Failed to load EXR as QPixmap {file_path}: {e}")
        return None


def _tone_map_hdr(img_data: np.ndarray) -> np.ndarray:
    """
    Apply simple tone mapping to convert HDR image data to LDR (0-1 range).

    Uses Reinhard tone mapping: out = in / (1 + in)
    This compresses the high dynamic range while preserving detail.

    Args:
        img_data: Input image data (HDR, possibly with values > 1.0)

    Returns:
        Tone-mapped image data in 0-1 range
    """
    # Handle negative values (clamp to 0)
    img_data = np.maximum(img_data, 0)

    # Reinhard tone mapping: simple and effective
    # Formula: L_out = L_in / (1 + L_in)
    tone_mapped = img_data / (1.0 + img_data)

    # Ensure RGB channels (handle grayscale or RGBA)
    if len(tone_mapped.shape) == 2:
        # Grayscale - convert to RGB
        tone_mapped = np.stack([tone_mapped] * 3, axis=-1)
    elif tone_mapped.shape[2] == 1:
        # Single channel - convert to RGB
        tone_mapped = np.repeat(tone_mapped, 3, axis=-1)
    elif tone_mapped.shape[2] > 3:
        # RGBA - keep only RGB for now (could preserve alpha if needed)
        tone_mapped = tone_mapped[:, :, :3]

    return tone_mapped


def is_exr_file(file_path: str) -> bool:
    """
    Check if a file is an EXR file based on extension.

    Args:
        file_path: Path to check

    Returns:
        True if file has .exr extension (case-insensitive)
    """
    return Path(file_path).suffix.lower() == ".exr"
