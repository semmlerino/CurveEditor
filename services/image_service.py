#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ImageService: facade for legacy ImageOperations (phase 1).
Dynamically attaches all static methods from the legacy ImageOperations class.
"""

from image_operations import ImageOperations as LegacyImageOps
from typing import Any

class ImageService:
    """Facade for image operations (phase 1)."""

    @staticmethod
    def load_image_sequence(main_window: Any) -> None:
        """Stub for load_image_sequence to satisfy UI typing."""
        pass

    @staticmethod
    def toggle_background(main_window: Any, enabled: bool) -> None:
        """Stub for toggle_background to satisfy UI typing."""
        pass

    @staticmethod
    def previous_image(main_window: Any) -> None:
        """Stub for previous_image to satisfy UI typing."""
        pass

    @staticmethod
    def next_image(main_window: Any) -> None:
        """Stub for next_image to satisfy UI typing."""
        pass

    @staticmethod
    def opacity_changed(main_window: Any, value: int) -> None:
        """Stub for opacity_changed to satisfy static analysis."""
        pass

# Attach legacy static methods
for name, fn in LegacyImageOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(ImageService, name, staticmethod(fn))
