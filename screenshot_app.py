#!/usr/bin/env python
"""
Script to run the CurveEditor app and capture a screenshot.
"""

import os
import sys
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def capture_screenshot():
    """Capture screenshot of the main window."""
    import glob

    app = QApplication.instance()
    if not app:
        return

    # Get the main window
    windows = app.topLevelWidgets()
    main_window = None
    for window in windows:
        if isinstance(window, MainWindow):
            main_window = window
            break

    if not main_window:
        print("Could not find MainWindow")
        app.quit()
        return

    # Make sure window is shown
    main_window.show()
    main_window.raise_()

    # Grab the window
    pixmap = main_window.grab()

    # Find the next available screenshot number
    existing_screenshots = glob.glob("timeline_screenshot_*.png")
    next_num = 1
    if existing_screenshots:
        numbers = []
        for filename in existing_screenshots:
            try:
                num = int(filename.replace("timeline_screenshot_", "").replace(".png", ""))
                numbers.append(num)
            except ValueError:
                continue
        if numbers:
            next_num = max(numbers) + 1

    # Save screenshot with incremented number
    filename = f"timeline_screenshot_{next_num}.png"
    if pixmap.save(filename):
        print(f"Screenshot saved to {filename}")
        print(f"Window size: {main_window.width()}x{main_window.height()}")
        print(f"Timeline tabs present: {main_window.timeline_tabs is not None}")
        if main_window.timeline_tabs:
            print(f"Timeline tabs visible: {main_window.timeline_tabs.isVisible()}")
    else:
        print(f"Failed to save screenshot to {filename}")

    # Quit the app
    app.quit()


def main():
    """Main entry point."""
    # Set offscreen platform for headless environment
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)

    # Create main window with mocked data loading
    with patch.object(MainWindow, "_load_burger_tracking_data"):
        window = MainWindow()

        # Add some test data to make the timeline more interesting
        test_data = [
            (1, 100.0, 200.0, "keyframe"),
            (5, 150.0, 250.0, "interpolated"),
            (10, 200.0, 300.0, "keyframe"),
            (15, 250.0, 350.0, "keyframe"),
            (20, 300.0, 400.0, "interpolated"),
            (25, 350.0, 450.0, "keyframe"),
        ]

        # Update timeline with test data
        window._update_timeline_tabs(test_data)

        # Set current frame to 10
        window.frame_spinbox.setValue(10)
        window._on_frame_changed(10)

        window.show()

        # Schedule screenshot capture after a short delay
        QTimer.singleShot(100, capture_screenshot)

        # Run the app briefly
        app.exec()


if __name__ == "__main__":
    main()
