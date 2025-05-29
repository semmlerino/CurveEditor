#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from services.logging_service import LoggingService
import logging_config

def main():
    """Main entry point for the application."""
    # Setup logging directory
    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "curve_editor.log")

    # Load and apply logging configuration
    config = logging_config.load_config()

    # Initialize logging with global level from config or environment
    global_level = os.environ.get('LOG_LEVEL', 'INFO')
    logger = LoggingService.setup_logging(
        level=global_level,
        log_file=log_file,
        console_output=True
    )

    # Set root logger level based on configuration
    logging.getLogger().setLevel(getattr(logging, global_level.upper()))

    # Apply module-specific log levels
    logging_config.apply_config(config)

    # Print confirmation of logging level
    logger.debug(f"Logging initialized at {global_level} level")
    logger.info(f"CurveEditor starting up - {global_level} logging enabled")

    # Start Qt application
    app = QApplication(sys.argv)
    window = MainWindow()
    app.installEventFilter(window)
    window.show()
    logger.info("Main window displayed")

    # Run the application
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
