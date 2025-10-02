"""
Image metadata extraction for various formats.

Provides utilities to extract technical metadata from images, with special
support for VFX formats like OpenEXR that contain critical production data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Configure logger
from core.logger_utils import get_logger

logger = get_logger("metadata_extractor")


@dataclass
class ImageMetadata:
    """
    Metadata extracted from an image file.

    Attributes:
        width: Image width in pixels
        height: Image height in pixels
        bit_depth: Bit depth (8, 16, 32, etc.)
        color_space: Color space identifier (sRGB, Linear, ACEScg, etc.)
        channels: Number of color channels
        file_size_bytes: File size in bytes
        format: File format (JPEG, PNG, EXR, etc.)
    """

    width: int = 0
    height: int = 0
    bit_depth: int = 0
    color_space: str = "Unknown"
    channels: int = 0
    file_size_bytes: int = 0
    format: str = "Unknown"

    @property
    def resolution_str(self) -> str:
        """Get resolution as string (e.g., '1920x1080')."""
        return f"{self.width}x{self.height}"

    @property
    def resolution_label(self) -> str:
        """Get resolution with common label (e.g., '3840x2160 (4K UHD)')."""
        # Common resolution labels
        labels = {
            (1920, 1080): "HD",
            (2048, 1556): "2K Academy",
            (2048, 1080): "2K DCI",
            (3840, 2160): "4K UHD",
            (4096, 2160): "4K DCI",
            (7680, 4320): "8K UHD",
        }

        label = labels.get((self.width, self.height))
        if label:
            return f"{self.width}x{self.height} ({label})"
        return f"{self.width}x{self.height}"

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size_bytes / (1024 * 1024)


class ImageMetadataExtractor:
    """
    Extract metadata from various image formats.

    Supports:
    - OpenEXR (via OpenEXR library)
    - Standard formats (via Pillow)
    """

    @staticmethod
    def extract(image_path: str) -> ImageMetadata | None:
        """
        Extract metadata from an image file.

        Args:
            image_path: Path to image file

        Returns:
            ImageMetadata object or None if extraction failed
        """
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_path}")
            return None

        path_obj = Path(image_path)
        extension = path_obj.suffix.lower()

        # Get file size
        file_size = os.path.getsize(image_path)

        # Try format-specific extractors
        if extension == ".exr":
            metadata = ImageMetadataExtractor._extract_exr_metadata(image_path)
        else:
            metadata = ImageMetadataExtractor._extract_standard_metadata(image_path)

        if metadata:
            metadata.file_size_bytes = file_size
            metadata.format = extension.upper().replace(".", "")

        return metadata

    @staticmethod
    def _extract_exr_metadata(image_path: str) -> ImageMetadata | None:
        """
        Extract metadata from OpenEXR file.

        Args:
            image_path: Path to EXR file

        Returns:
            ImageMetadata or None if extraction failed
        """
        try:
            import Imath
            import OpenEXR

            # Open EXR file
            exr_file = OpenEXR.InputFile(image_path)
            header = exr_file.header()

            # Get dimensions
            dw = header["dataWindow"]
            width = dw.max.x - dw.min.x + 1
            height = dw.max.y - dw.min.y + 1

            # Get channel info
            channels = header["channels"]
            channel_count = len(channels)

            # Determine bit depth from channel type
            # OpenEXR typically uses HALF (16-bit) or FLOAT (32-bit)
            bit_depth = 32  # Default to 32-bit
            if channels:
                first_channel = list(channels.values())[0]
                channel_type = first_channel.type
                if channel_type == Imath.PixelType(Imath.PixelType.HALF):
                    bit_depth = 16
                elif channel_type == Imath.PixelType(Imath.PixelType.FLOAT):
                    bit_depth = 32

            # Try to determine color space from metadata
            color_space = "Linear"  # Default for EXR
            if "chromaticities" in header:
                color_space = "Linear (with chromaticities)"

            # Some EXRs store color space in custom attributes
            if "colorSpace" in header:
                color_space = str(header["colorSpace"])

            metadata = ImageMetadata(
                width=width,
                height=height,
                bit_depth=bit_depth,
                color_space=color_space,
                channels=channel_count,
            )

            logger.debug(
                f"Extracted EXR metadata: {metadata.resolution_str}, {bit_depth}-bit, {channel_count} channels"
            )
            return metadata

        except ImportError:
            logger.debug("OpenEXR library not available")
            return None
        except Exception as e:
            logger.error(f"Failed to extract EXR metadata from {image_path}: {e}")
            return None

    @staticmethod
    def _extract_standard_metadata(image_path: str) -> ImageMetadata | None:
        """
        Extract metadata from standard image format using Pillow.

        Args:
            image_path: Path to image file

        Returns:
            ImageMetadata or None if extraction failed
        """
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode

                # Map PIL mode to bit depth and channels
                mode_info = {
                    "1": (1, 1),  # 1-bit black and white
                    "L": (8, 1),  # 8-bit grayscale
                    "P": (8, 1),  # 8-bit palette
                    "RGB": (8, 3),  # 8-bit RGB
                    "RGBA": (8, 4),  # 8-bit RGBA
                    "CMYK": (8, 4),  # 8-bit CMYK
                    "YCbCr": (8, 3),  # 8-bit YCbCr
                    "I": (32, 1),  # 32-bit integer grayscale
                    "F": (32, 1),  # 32-bit float grayscale
                }

                bit_depth, channels = mode_info.get(mode, (8, 3))

                # Try to get color space from ICC profile
                color_space = "sRGB"  # Default assumption
                if "icc_profile" in img.info:
                    color_space = "ICC Profile"

                metadata = ImageMetadata(
                    width=width,
                    height=height,
                    bit_depth=bit_depth,
                    color_space=color_space,
                    channels=channels,
                )

                logger.debug(f"Extracted metadata: {metadata.resolution_str}, {bit_depth}-bit, {channels} channels")
                return metadata

        except ImportError:
            logger.debug("Pillow library not available")
            return None
        except Exception as e:
            logger.error(f"Failed to extract metadata from {image_path}: {e}")
            return None
