#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from services.logging_service import LoggingService
import logging_config


def main():
    """Main entry point for the application."""
    # Setup logging directory
    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Create the log file path
    log_file = os.path.join(log_dir, "curve_editor.log")

    # Load logging configuration
    config = logging_config.load_config()

    # Get logging level from environment or config
    global_level = os.environ.get('LOG_LEVEL', config.get('global', 'INFO'))
    level_num = getattr(logging, global_level.upper(), logging.INFO)

    # Initialize logging through LoggingService
    logger = LoggingService.setup_logging(level=level_num, log_file=log_file, console_output=True)
    logger.info("=" * 80)
    logger.info(f"CurveEditor starting up - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log level: {global_level}, Log file: {log_file}")
    logger.info("=" * 80)

    # Apply module-specific log levels from config
    if isinstance(config.get('services'), dict):
        for service_name, service_level in config['services'].items():
            if isinstance(service_level, str):
                LoggingService.set_module_level(
                    f"services.{service_name}",
                    getattr(logging, service_level.upper(), logging.INFO)
                )
                logger.debug(f"Set {service_name} service log level to {service_level}")

    # Apply other module levels
    for module, level in config.items():
        if module in ['global', 'services'] or not isinstance(level, str):
            continue
        LoggingService.set_module_level(module, getattr(logging, level.upper(), logging.INFO))
        logger.debug(f"Set {module} log level to {level}")

    # Initialize Qt application
    app = QApplication(sys.argv)

    # Create main window
    logger.info("Creating main window...")
    window = MainWindow()
    app.installEventFilter(window)

    # Show window
    window.show()
    logger.info("Main window displayed successfully")

    # Verify logging is working
    if os.path.exists(log_file):
        logger.info(f"Log file verified: {log_file} (size: {os.path.getsize(log_file)} bytes)")
    else:
        logger.warning(f"Log file not found at: {log_file}")

    # Run the application
    logger.info("Starting Qt event loop...")
    exit_code = app.exec()

    logger.info(f"Application exiting with code {exit_code}")
    LoggingService.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
