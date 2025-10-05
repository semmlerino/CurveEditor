#!/usr/bin/env python
"""
Integration tests for ImageSequenceBrowserDialog initialization.

These tests verify that the dialog can be constructed without AttributeErrors,
catching initialization order issues that static analysis might miss.
"""

from typing import cast

import pytest
from PySide6.QtWidgets import QApplication

from ui.image_sequence_browser import ImageSequenceBrowserDialog


class TestImageSequenceBrowserInitialization:
    """Test that dialog initializes correctly without errors."""

    @pytest.fixture
    def qapp(self) -> QApplication:
        """Ensure QApplication exists."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return cast(QApplication, app)

    def test_dialog_initializes_without_errors(self, qapp: QApplication):
        """Test that dialog can be created without AttributeError.

        This catches initialization order issues like calling methods
        that access attributes before they're created.
        """
        # This should not raise AttributeError
        dialog = ImageSequenceBrowserDialog()

        # Verify key attributes exist
        assert hasattr(dialog, "tree_view")
        assert hasattr(dialog, "file_model")
        assert hasattr(dialog, "sequence_list")
        assert hasattr(dialog, "address_bar")

        dialog.close()

    def test_dialog_initializes_with_start_directory(self, qapp: QApplication, tmp_path):
        """Test dialog initialization with a starting directory."""
        # Create a temporary directory
        test_dir = tmp_path / "test_images"
        test_dir.mkdir()

        # Should not raise AttributeError
        dialog = ImageSequenceBrowserDialog(start_directory=str(test_dir))

        assert hasattr(dialog, "tree_view")
        assert dialog.tree_view is not None

        dialog.close()

    def test_dialog_windows_drive_selector(self, qapp: QApplication):
        """Test that drive selector doesn't cause AttributeError on Windows."""
        # This test catches the specific bug where _populate_drives()
        # was called before tree_view was created
        dialog = ImageSequenceBrowserDialog()

        # On Windows, drive_selector should exist
        # On other platforms, it should be None
        import sys

        if sys.platform == "win32":
            assert hasattr(dialog, "drive_selector")

        dialog.close()
