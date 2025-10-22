"""Automatic coordinate system detection from file content and metadata.

This module provides intelligent detection of coordinate systems from various
file formats, extracting dimensions and coordinate conventions to enable
proper transformation without manual configuration.
"""

import os
import re
from pathlib import Path

from core.coordinate_system import CoordinateMetadata, CoordinateOrigin, CoordinateSystem


class CoordinateDetector:
    """Automatic detection of coordinate systems from files."""

    # File extension to coordinate system mapping
    EXTENSION_MAP: dict[str, CoordinateSystem | None] = {
        ".2dt": CoordinateSystem.THREE_DE_EQUALIZER,
        ".3de": CoordinateSystem.THREE_DE_EQUALIZER,
        ".txt": None,  # Need to check content
        ".nk": CoordinateSystem.NUKE,
        ".ma": CoordinateSystem.MAYA,
        ".mb": CoordinateSystem.MAYA,
        ".json": None,  # Need to check content
        ".csv": None,  # Need to check content
    }

    # Pattern to detect 3DEqualizer format in text files
    PATTERN_3DE: re.Pattern[str] = re.compile(r"(?:3DEqualizer|3DE|2DTrack|SDPX|IMAGE)", re.IGNORECASE)

    # Pattern to extract image dimensions from headers
    PATTERN_DIMENSIONS: re.Pattern[str] = re.compile(
        r"(?:IMAGE|RESOLUTION|SIZE|DIM).*?(\d{3,4})\s*[xX,]\s*(\d{3,4})", re.IGNORECASE
    )

    # Pattern for specific dimension formats
    PATTERN_WIDTH_HEIGHT: re.Pattern[str] = re.compile(
        r"(?:WIDTH|W)\s*[:=]\s*(\d+).*?(?:HEIGHT|H)\s*[:=]\s*(\d+)", re.IGNORECASE | re.DOTALL
    )

    @classmethod
    def detect_from_file(cls, file_path: str, content: str | None = None) -> CoordinateMetadata:
        """Detect coordinate system from file path and optional content.

        Args:
            file_path: Path to the file
            content: Optional file content (first few lines)

        Returns:
            Detected CoordinateMetadata
        """
        # Try to read content if not provided
        if content is None and os.path.exists(file_path):
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    # Read first 1KB for detection
                    content = f.read(1024)
            except Exception:
                content = ""

        # Try content detection first (more reliable)
        system = None
        if content:
            system = cls._detect_system_from_content(content, file_path)

        # Fall back to extension/filename detection
        if system is None:
            system = cls._detect_system_from_extension(file_path)

        # Extract dimensions from content
        width, height = cls._extract_dimensions(content) if content else (None, None)

        # Check if coordinates are normalized for 3DE
        uses_normalized = False
        if system == CoordinateSystem.THREE_DE_EQUALIZER and content:
            uses_normalized = cls._has_normalized_coordinates(content)

        # Apply defaults based on system
        if system == CoordinateSystem.THREE_DE_EQUALIZER:
            return CoordinateMetadata(
                system=system,
                origin=CoordinateOrigin.BOTTOM_LEFT,
                width=width or 1280,
                height=height or 720,
                uses_normalized_coordinates=uses_normalized,
            )
        elif system == CoordinateSystem.NUKE:
            return CoordinateMetadata(
                system=system, origin=CoordinateOrigin.BOTTOM_LEFT, width=width or 1920, height=height or 1080
            )
        elif system == CoordinateSystem.MAYA:
            return CoordinateMetadata(
                system=system, origin=CoordinateOrigin.CENTER, width=width or 1920, height=height or 1080
            )
        else:
            # Default to Qt screen coordinates
            return CoordinateMetadata(
                system=CoordinateSystem.QT_SCREEN,
                origin=CoordinateOrigin.TOP_LEFT,
                width=width or 1920,
                height=height or 1080,
            )

    @classmethod
    def _detect_system_from_extension(cls, file_path: str) -> CoordinateSystem | None:
        """Detect coordinate system from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Detected coordinate system or None
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        # Check filename patterns first (more specific)
        name_lower = path.name.lower()
        if "2dtrack" in name_lower or "3de" in name_lower or "3dequalizer" in name_lower:
            return CoordinateSystem.THREE_DE_EQUALIZER
        elif "nuke" in name_lower:
            return CoordinateSystem.NUKE
        elif "maya" in name_lower:
            return CoordinateSystem.MAYA

        # Then check direct extension mapping
        if ext in cls.EXTENSION_MAP and cls.EXTENSION_MAP[ext] is not None:
            return cls.EXTENSION_MAP[ext]

        return None

    @classmethod
    def _detect_system_from_content(cls, content: str, file_path: str) -> CoordinateSystem | None:
        """Detect coordinate system from file content.

        Args:
            content: File content to analyze
            file_path: Path for context (reserved for future use)

        Returns:
            Detected coordinate system or None
        """
        # file_path parameter reserved for future pattern matching based on path
        # Check for 3DEqualizer markers
        if cls.PATTERN_3DE.search(content):
            return CoordinateSystem.THREE_DE_EQUALIZER

        # Check for format-specific headers
        lines = content.split("\n")[:10]  # Check first 10 lines

        for line in lines:
            line_lower = line.lower()

            # 3DEqualizer format indicators
            if any(marker in line_lower for marker in ["3dequalizer", "2dtrack", "sdpx"]):
                return CoordinateSystem.THREE_DE_EQUALIZER

            # Nuke format indicators
            if "nuke" in line_lower or "foundry" in line_lower:
                return CoordinateSystem.NUKE

            # Maya format indicators
            if "maya" in line_lower or "autodesk" in line_lower:
                return CoordinateSystem.MAYA

        # Check for 3DEqualizer structure pattern (e.g., Point01_only.txt format)
        if cls._has_3de_structure(content):
            return CoordinateSystem.THREE_DE_EQUALIZER

        # Check data format patterns
        if cls._looks_like_3de_data(content):
            return CoordinateSystem.THREE_DE_EQUALIZER

        return None

    @classmethod
    def _has_3de_structure(cls, content: str) -> bool:
        """Check if content has 3DEqualizer file structure.

        3DE files often have this structure:
        - Line 1: Version number (often "1")
        - Line 2: Point name (e.g., "Point1", "Point01")
        - Line 3: Number (often "0")
        - Line 4: Frame count
        - Lines 5+: frame x y [status]

        Args:
            content: File content to check

        Returns:
            True if matches 3DE structure
        """
        lines = content.strip().split("\n")

        if len(lines) < 5:
            return False

        try:
            # Check line 1: should be a small integer (version)
            version = int(lines[0].strip())
            if version < 0 or version > 100:  # Reasonable version range
                return False

            # Check line 2: should contain "Point" or be a name
            point_line = lines[1].strip()
            if not point_line:
                return False

            # Check line 3: should be a small integer (often 0)
            identifier = int(lines[2].strip())
            if identifier < 0 or identifier > 1000:  # Reasonable range
                return False

            # Check line 4: should be frame count
            frame_count = int(lines[3].strip())
            if frame_count <= 0 or frame_count > 10000:  # Reasonable frame range
                return False

            # Check first data line (line 5)
            if len(lines) > 4:
                parts = lines[4].strip().split()
                if len(parts) >= 3:
                    frame = int(parts[0])
                    x = float(parts[1])
                    y = float(parts[2])
                    # Basic sanity check on coordinates
                    if frame > 0 and 0 <= x <= 10000 and 0 <= y <= 10000:
                        return True

        except (ValueError, IndexError):
            pass

        return False

    @classmethod
    def _looks_like_3de_data(cls, content: str) -> bool:
        """Check if content looks like 3DEqualizer tracking data.

        3DE data typically has:
        - Frame numbers starting from 1
        - X coordinates in pixel range (0-2000) OR normalized range (0-1)
        - Y coordinates in pixel range (0-2000) OR normalized range (0-1)
        - Optional status field

        Args:
            content: File content to check

        Returns:
            True if likely 3DE data
        """
        lines = content.strip().split("\n")

        # Skip header lines
        data_lines: list[tuple[int, float, float]] = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                # Try to parse as data
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        frame = int(parts[0])
                        x = float(parts[1])
                        y = float(parts[2])
                        data_lines.append((frame, x, y))
                    except ValueError:
                        continue

        if len(data_lines) < 2:
            return False

        # Check if frames are sequential starting from 1
        frames = [d[0] for d in data_lines]
        if min(frames) == 1 and max(frames) - min(frames) == len(frames) - 1:
            # Check if coordinates are in typical 3DE range
            xs = [d[1] for d in data_lines]
            ys = [d[2] for d in data_lines]

            # Check for pixel coordinates (0-2000 range)
            if 0 <= min(xs) <= max(xs) <= 2000 and 0 <= min(ys) <= max(ys) <= 2000:
                return True

            # Check for normalized coordinates (0-1 range)
            if 0 <= min(xs) <= max(xs) <= 1 and 0 <= min(ys) <= max(ys) <= 1:
                return True

        return False

    @classmethod
    def _has_normalized_coordinates(cls, content: str) -> bool:
        """Check if 3DEqualizer data uses normalized coordinates [0-1].

        Args:
            content: File content to analyze

        Returns:
            True if coordinates appear to be normalized
        """
        lines = content.strip().split("\n")

        # Collect coordinate data
        xs: list[float] = []
        ys: list[float] = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        xs.append(x)
                        ys.append(y)
                    except ValueError:
                        continue
        if len(xs) < 1:
            return False

        # Check if all coordinates are in [0,1] range
        max_x = max(xs)
        max_y = max(ys)
        min_x = min(xs)
        min_y = min(ys)

        # Normalized coordinates should all be between 0 and 1
        # Allow small tolerance for floating point precision
        if 0 <= min_x and max_x <= 1.001 and 0 <= min_y and max_y <= 1.001:
            # Handle single point case first
            if len(xs) == 1:  # Single point case
                return True

            # Additional check: ensure we don't have degenerate cases
            # (all points at exactly the same coordinate)
            x_range = max_x - min_x
            y_range = max_y - min_y

            # Reduce threshold - tracking data can have very small movement
            # Also allow case where one axis has no movement but other does
            if x_range > 0.0001 or y_range > 0.0001:  # Very small threshold
                return True
        return False

    @classmethod
    def _extract_dimensions(cls, content: str) -> tuple[int | None, int | None]:
        """Extract image dimensions from file content.

        Args:
            content: File content to parse

        Returns:
            Tuple of (width, height) or (None, None)
        """
        if not content:
            return None, None

        # Try dimension pattern first
        match = cls.PATTERN_DIMENSIONS.search(content)
        if match:
            try:
                width = int(match.group(1))
                height = int(match.group(2))
                # Sanity check dimensions
                if 100 <= width <= 8000 and 100 <= height <= 8000:
                    return width, height
            except (ValueError, IndexError):
                pass

        # Try width/height pattern
        match = cls.PATTERN_WIDTH_HEIGHT.search(content)
        if match:
            try:
                width = int(match.group(1))
                height = int(match.group(2))
                if 100 <= width <= 8000 and 100 <= height <= 8000:
                    return width, height
            except (ValueError, IndexError):
                pass

        # Try to infer from data range
        dimensions = cls._infer_dimensions_from_data(content)
        if dimensions:
            return dimensions

        return None, None

    @classmethod
    def _infer_dimensions_from_data(cls, content: str) -> tuple[int, int] | None:
        """Infer dimensions from coordinate data range.

        Args:
            content: File content with coordinate data

        Returns:
            Inferred (width, height) or None
        """
        lines = content.strip().split("\n")
        xs: list[float] = []
        ys: list[float] = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        xs.append(x)
                        ys.append(y)
                    except ValueError:
                        continue

        if not xs or not ys:
            return None

        # Check if coordinates look like pixel values
        max_x = max(xs)
        max_y = max(ys)

        # Common resolutions
        common_resolutions = [
            (1280, 720),  # 720p
            (1920, 1080),  # 1080p
            (2560, 1440),  # 1440p
            (3840, 2160),  # 4K
            (640, 480),  # VGA
            (1024, 768),  # XGA
        ]

        # Find closest matching resolution
        for width, height in common_resolutions:
            if max_x <= width * 1.1 and max_y <= height * 1.1:
                return width, height

        # Round to nearest 10
        width = int((max_x + 9) // 10) * 10
        height = int((max_y + 9) // 10) * 10

        if 100 <= width <= 8000 and 100 <= height <= 8000:
            return width, height

        return None


def detect_coordinate_system(
    file_path: str, content: str | None = None, width: int | None = None, height: int | None = None
) -> CoordinateMetadata:
    """Convenience function to detect coordinate system.

    Args:
        file_path: Path to the file
        content: Optional file content
        width: Optional width override
        height: Optional height override

    Returns:
        Detected or default CoordinateMetadata
    """
    metadata = CoordinateDetector.detect_from_file(file_path, content)

    # Apply overrides if provided (create new metadata instance to avoid mutation)
    if width is not None or height is not None:
        from dataclasses import replace

        updates = {}
        if width is not None:
            updates["width"] = width
        if height is not None:
            updates["height"] = height
        metadata = replace(metadata, **updates)

    return metadata


def get_system_info(system: CoordinateSystem) -> dict[str, str | CoordinateOrigin | list[str] | tuple[int, int]]:
    """Get information about a coordinate system.

    Args:
        system: The coordinate system

    Returns:
        Dictionary with system information
    """
    if system == CoordinateSystem.THREE_DE_EQUALIZER:
        return {
            "name": system.value,
            "origin": CoordinateOrigin.BOTTOM_LEFT,
            "description": "3DEqualizer tracking data with bottom-left origin",
            "file_extensions": [".2dt", ".3de", ".txt"],
            "default_dimensions": (1280, 720),
        }
    elif system == CoordinateSystem.NUKE:
        return {
            "name": system.value,
            "origin": CoordinateOrigin.BOTTOM_LEFT,
            "description": "Nuke compositor with bottom-left origin",
            "file_extensions": [".nk"],
            "default_dimensions": (1920, 1080),
        }
    elif system == CoordinateSystem.MAYA:
        return {
            "name": system.value,
            "origin": CoordinateOrigin.CENTER,
            "description": "Maya 3D with configurable origin (usually center)",
            "file_extensions": [".ma", ".mb"],
            "default_dimensions": (1920, 1080),
        }
    elif system == CoordinateSystem.QT_SCREEN:
        return {
            "name": system.value,
            "origin": CoordinateOrigin.TOP_LEFT,
            "description": "Qt/PySide screen coordinates with top-left origin",
            "file_extensions": [],
            "default_dimensions": (1920, 1080),
        }
    elif system == CoordinateSystem.OPENGL:
        return {
            "name": system.value,
            "origin": CoordinateOrigin.BOTTOM_LEFT,
            "description": "OpenGL rendering with bottom-left origin",
            "file_extensions": [],
            "default_dimensions": (1920, 1080),
        }
    elif system == CoordinateSystem.CURVE_EDITOR_INTERNAL:
        return {
            "name": system.value,
            "origin": CoordinateOrigin.TOP_LEFT,
            "description": "CurveEditor internal normalized format",
            "file_extensions": [],
            "default_dimensions": (1920, 1080),
        }
    # All enum cases exhaustively handled above
