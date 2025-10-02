"""
EXR Image Loader for CurveEditor.

Provides helper functions to load OpenEXR images using Pillow and convert
them to Qt image formats (QImage/QPixmap) with proper tone mapping.

QImage and QPixmap do not natively support OpenEXR format, so this module
bridges the gap using Pillow for reading and numpy for processing.

Note: Pillow must be compiled with OpenEXR support. If not available,
      consider installing imageio-ffmpeg as an alternative backend.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)


def load_exr_as_qimage(file_path: str) -> "QImage | None":
    """
    Load an OpenEXR image file and convert it to QImage.

    Tries multiple backends in order of preference:
    1. OpenEXR (official library - best quality)
    2. Pillow (if compiled with OpenEXR support)
    3. imageio (if compatible backend installed)

    Args:
        file_path: Path to the EXR file

    Returns:
        QImage object or None if loading failed
    """
    # Try OpenEXR first (best quality, most reliable)
    qimage = _load_exr_with_openexr(file_path)
    if qimage is not None:
        return qimage

    # Fallback to Pillow
    qimage = _load_exr_with_pillow(file_path)
    if qimage is not None:
        return qimage

    # Fallback to imageio
    qimage = _load_exr_with_imageio(file_path)
    if qimage is not None:
        return qimage

    # All backends failed
    logger.error(f"Failed to load EXR file {file_path}. " + "Consider installing: pip install OpenEXR")
    return None


def _load_exr_with_openexr(file_path: str) -> "QImage | None":
    """
    Load EXR using the official OpenEXR library.

    Args:
        file_path: Path to the EXR file

    Returns:
        QImage object or None if loading failed
    """
    try:
        import Imath
        import OpenEXR
        from PySide6.QtGui import QImage

        # Open the EXR file
        exr_file = OpenEXR.InputFile(file_path)

        # Get image header
        header = exr_file.header()
        dw = header["dataWindow"]
        width = dw.max.x - dw.min.x + 1
        height = dw.max.y - dw.min.y + 1

        # Get channel names (typically R, G, B, optionally A)
        channels = list(header["channels"].keys())

        # Read RGB channels (using FLOAT pixel type)
        float_type = Imath.PixelType(Imath.PixelType.FLOAT)

        # Determine available channels
        has_r = "R" in channels or "r" in channels
        has_g = "G" in channels or "g" in channels
        has_b = "B" in channels or "b" in channels

        if not (has_r and has_g and has_b):
            logger.debug(f"EXR file missing RGB channels: {channels}")
            return None

        # Read channel data
        r_channel = "R" if "R" in channels else "r"
        g_channel = "G" if "G" in channels else "g"
        b_channel = "B" if "B" in channels else "b"

        r_str = exr_file.channel(r_channel, float_type)
        g_str = exr_file.channel(g_channel, float_type)
        b_str = exr_file.channel(b_channel, float_type)

        # Convert to numpy arrays
        r_data = np.frombuffer(r_str, dtype=np.float32).reshape(height, width)
        g_data = np.frombuffer(g_str, dtype=np.float32).reshape(height, width)
        b_data = np.frombuffer(b_str, dtype=np.float32).reshape(height, width)

        # Stack into RGB image
        img_data = np.stack([r_data, g_data, b_data], axis=-1)

        # Apply tone mapping (HDR -> LDR conversion)
        img_data = _tone_map_hdr(img_data)

        # Convert to 8-bit
        img_8bit = (img_data * 255).astype(np.uint8)

        # Create QImage
        bytes_per_line = width * 3
        qimage = QImage(
            img_8bit.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        # Copy to ensure data persists
        qimage = qimage.copy()

        logger.debug(f"Loaded EXR with OpenEXR: {file_path} ({width}x{height})")
        return qimage

    except ImportError:
        logger.debug("OpenEXR library not available")
        return None
    except Exception as e:
        logger.debug(f"OpenEXR couldn't load {file_path}: {e}")
        return None


def _load_exr_with_pillow(file_path: str) -> "QImage | None":
    """
    Load EXR using Pillow (requires OpenEXR support).

    Args:
        file_path: Path to the EXR file

    Returns:
        QImage object or None if loading failed
    """
    try:
        from PIL import Image
        from PySide6.QtGui import QImage

        # Try to open with Pillow
        with Image.open(file_path) as img:
            # Convert to RGB mode (handles RGBA, grayscale, etc.)
            img = img.convert("RGB")

            # Convert to numpy array for tone mapping
            img_data = np.array(img, dtype=np.float32)

            # EXR data is typically 0-1 range but can exceed 1.0 (HDR)
            # Normalize if needed
            if img_data.max() > 1.0:
                # Apply tone mapping for HDR data
                img_data = _tone_map_hdr(img_data / 255.0)  # Pillow returns 0-255 for float
            else:
                # Already in 0-1 range
                img_data = _tone_map_hdr(img_data)

            # Convert to 8-bit
            img_8bit = (img_data * 255).astype(np.uint8)

            # Get dimensions
            height, width = img_8bit.shape[:2]
            bytes_per_line = width * 3

            # Create QImage
            qimage = QImage(
                img_8bit.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )

            # Copy to ensure data persists
            qimage = qimage.copy()

            logger.debug(f"Loaded EXR with Pillow: {file_path} ({width}x{height})")
            return qimage

    except ImportError:
        logger.debug("Pillow not available")
        return None
    except Exception as e:
        logger.debug(f"Pillow couldn't load EXR {file_path}: {e}")
        return None


def _load_exr_with_imageio(file_path: str) -> "QImage | None":
    """
    Load EXR using imageio (requires imageio-ffmpeg backend).

    Args:
        file_path: Path to the EXR file

    Returns:
        QImage object or None if loading failed
    """
    try:
        import imageio.v3 as iio
        from PySide6.QtGui import QImage

        # Read EXR file using imageio with explicit ffmpeg plugin
        # The 'ffmpeg' plugin is provided by imageio-ffmpeg package
        img_data = iio.imread(file_path, plugin="ffmpeg")

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

        logger.debug(f"Loaded EXR with imageio: {file_path} ({width}x{height})")
        return qimage

    except ImportError:
        logger.debug("imageio not available")
        return None
    except Exception as e:
        logger.debug(f"imageio couldn't load EXR {file_path}: {e}")
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


def _tone_map_hdr(img_data: NDArray[np.floating[Any]]) -> NDArray[np.floating[Any]]:
    """
    Apply tone mapping to convert HDR image data to LDR (0-1 range).

    Uses a hybrid approach:
    1. Simple exposure adjustment for linear EXR data
    2. Gamma correction for proper display
    3. Soft clipping for highlights

    This preserves color saturation better than Reinhard while maintaining detail.

    Args:
        img_data: Input image data (HDR, possibly with values > 1.0)

    Returns:
        Tone-mapped image data in 0-1 range
    """
    # Handle negative values (clamp to 0)
    img_data = np.maximum(img_data, 0)

    # Calculate luminance-based exposure
    # Use a percentile-based exposure to avoid being thrown off by outliers
    mid_gray = np.percentile(img_data, 50)  # Median brightness
    target_mid_gray = 0.18  # Standard 18% gray target

    if mid_gray > 0:
        exposure = target_mid_gray / mid_gray
        # Clamp exposure to reasonable range to avoid over-brightening dark images
        exposure = np.clip(exposure, 0.5, 4.0)
    else:
        exposure = 1.0

    # Apply exposure
    img_data = img_data * exposure

    # Soft clipping for highlights (preserves color better than hard clipping)
    # Values below 1.0 pass through linearly, values above compress smoothly
    img_data = np.where(
        img_data <= 1.0,
        img_data,
        1.0 - np.exp(-(img_data - 1.0)),  # Exponential rolloff for highlights
    )

    # Apply gamma correction (linear -> sRGB)
    # Standard gamma = 2.2 for proper display
    gamma = 2.2
    tone_mapped = np.power(img_data, 1.0 / gamma)

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

    # Final safety clamp
    tone_mapped = np.clip(tone_mapped, 0.0, 1.0)

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
