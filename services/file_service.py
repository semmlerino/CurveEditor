#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FileService: facade for legacy FileOperations (phase 1).
Dynamically attaches all static methods from the legacy FileOperations class.
"""

from file_operations import FileOperations as LegacyFileOps
from typing import Any

class FileService:
    """Facade for file operations (phase 1)."""
    @staticmethod
    def load_track_data(main_window: Any) -> None: ...
    @staticmethod
    def add_track_data(main_window: Any) -> None: ...
    @staticmethod
    def save_track_data(main_window: Any) -> None: ...
    @staticmethod
    def export_to_csv(main_window: Any) -> None: ...

# Attach legacy static methods (excluding private)
for name, fn in LegacyFileOps.__dict__.items():
    if callable(fn) and not name.startswith("_"):
        setattr(FileService, name, staticmethod(fn))
