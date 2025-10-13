"""
Directory scanning worker for asynchronous image sequence detection.

This module provides a QThread-based worker for scanning directories and
detecting image sequences without blocking the UI thread.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, override

from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    pass

# Configure logger
from core.logger_utils import get_logger

logger = get_logger("directory_scanner")


class DirectoryScanWorker(QThread):
    """
    Background worker for scanning directories and detecting image sequences.

    Signals:
        progress: Emitted during scanning with (current_count, total_estimate, message)
        sequences_found: Emitted when scanning completes with list of sequences
        error_occurred: Emitted if an error occurs during scanning
    """

    # Signals
    progress = Signal(int, int, str)  # current, total, message
    sequences_found = Signal(list)  # list[ImageSequence]
    error_occurred = Signal(str)  # error_message

    # Supported image extensions
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".exr", ".hdr", ".dpx"}

    def __init__(self, directory: str):
        """
        Initialize directory scan worker.

        Args:
            directory: Directory path to scan
        """
        super().__init__()
        self.directory = directory

    def stop(self) -> None:
        """Request the worker to stop processing."""
        self.requestInterruption()
        if self.isRunning():
            self.wait(2000)  # Wait up to 2 seconds
        logger.debug("Scan stop requested")

    @override
    def run(self) -> None:
        """Execute the directory scan in background thread."""
        try:
            logger.debug(f"Starting directory scan: {self.directory}")

            # Step 1: Scan for image files
            self.progress.emit(0, 100, "Scanning directory...")
            image_files = self._scan_for_images()

            if self.isInterruptionRequested():
                logger.debug("Scan cancelled after file scanning")
                return

            # Step 2: Detect sequences
            self.progress.emit(50, 100, "Detecting sequences...")
            sequences = self._detect_sequences(image_files)

            if self.isInterruptionRequested():
                logger.debug("Scan cancelled after sequence detection")
                return

            # Step 3: Emit results
            self.progress.emit(100, 100, f"Found {len(sequences)} sequences")
            self.sequences_found.emit(sequences)

            logger.debug(f"Scan complete: {len(sequences)} sequences found")

        except Exception as e:
            logger.error(f"Error during directory scan: {e}")
            self.error_occurred.emit(str(e))

    def _scan_for_images(self) -> list[str]:
        """
        Scan directory for image files.

        Returns:
            Sorted list of image filenames
        """
        image_files = []

        try:
            if not os.path.isdir(self.directory):
                logger.warning(f"Directory does not exist: {self.directory}")
                return []

            all_files = os.listdir(self.directory)
            total_files = len(all_files)

            for idx, filename in enumerate(all_files):
                if self.isInterruptionRequested():
                    return []

                file_path = os.path.join(self.directory, filename)

                if os.path.isfile(file_path):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in self.IMAGE_EXTENSIONS:
                        image_files.append(filename)

                # Update progress every 100 files
                if idx % 100 == 0 and total_files > 0:
                    progress_pct = int((idx / total_files) * 50)  # 0-50% for scanning
                    self.progress.emit(progress_pct, 100, f"Scanning... ({len(image_files)} images found)")

            image_files.sort()
            logger.debug(f"Found {len(image_files)} image files")
            return image_files

        except Exception as e:
            logger.error(f"Error scanning directory: {e}")
            raise

    def _detect_sequences(self, image_files: list[str]) -> list[dict[str, str | int | list[int] | list[str]]]:
        """
        Detect image sequences from a list of filenames.

        Args:
            image_files: List of image filenames to analyze

        Returns:
            List of sequence dictionaries (to be converted to ImageSequence objects by caller)
        """
        # Pattern to match: prefix + frame_number (3+ digits) + extension
        pattern = re.compile(r"^(.*)(\d{3,})(\.\w+)$")

        # Dictionary to group files
        sequence_groups: dict[tuple[str, int, str], list[tuple[int, str]]] = {}
        non_sequence_files: list[str] = []

        total_files = len(image_files)

        for idx, filename in enumerate(image_files):
            if self.isInterruptionRequested():
                return []

            match = pattern.match(filename)
            if match:
                base_name = match.group(1)
                frame_str = match.group(2)
                extension = match.group(3)
                padding = len(frame_str)
                frame_num = int(frame_str)

                key = (base_name, padding, extension)
                if key not in sequence_groups:
                    sequence_groups[key] = []
                sequence_groups[key].append((frame_num, filename))
            else:
                non_sequence_files.append(filename)

            # Update progress
            if idx % 50 == 0 and total_files > 0:
                progress_pct = 50 + int((idx / total_files) * 50)  # 50-100% for detection
                self.progress.emit(progress_pct, 100, f"Detecting sequences... ({len(sequence_groups)} found)")

        # Create sequence dictionaries
        sequences = []

        for (base_name, padding, extension), files in sequence_groups.items():
            if self.isInterruptionRequested():
                return []

            # Sort by frame number
            files.sort(key=lambda x: x[0])

            frames = [frame for frame, _ in files]
            file_list = [filename for _, filename in files]

            # Create sequence dict (will be converted to ImageSequence by caller)
            sequence = {
                "base_name": base_name,
                "padding": padding,
                "extension": extension,
                "frames": frames,
                "file_list": file_list,
                "directory": self.directory,
            }
            sequences.append(sequence)

        # Add non-sequence files as single-frame sequences
        for filename in non_sequence_files:
            if self.isInterruptionRequested():
                return []

            base_name, extension = os.path.splitext(filename)
            sequence = {
                "base_name": base_name,
                "padding": 0,
                "extension": extension,
                "frames": [0],
                "file_list": [filename],
                "directory": self.directory,
            }
            sequences.append(sequence)

        # Sort by base name
        sequences.sort(key=lambda x: x["base_name"])

        logger.debug(f"Detected {len(sequences)} sequences")
        return sequences
