#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ImageService: facade for legacy ImageOperations (phase 1).
Dynamically attaches all static methods from the legacy ImageOperations class.
"""

from image_operations import ImageOperations as LegacyImageOps

class ImageService:
    """Facade for image operations (phase 1)."""
    pass

# Attach legacy static methods
for name, fn in LegacyImageOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(ImageService, name, staticmethod(fn))
