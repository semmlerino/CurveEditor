#!/usr/bin/env python

import logging
import os
import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication

# from config import logging_config  # Temporarily disabled - config module not available
from ui.main_window import MainWindow

def main():
    """Main entry point for the application."""
    # Setup logging directory
    log_dir = os.path.join(os.path.expanduser("~"), ".curve_editor", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Create the log file path
    log_file = os.path.join(log_dir, "curve_editor.log")

    # Load logging configuration - simplified for startup
    # config = logging_config.load_config()  # Disabled - config module not available
    config = {"global": "INFO", "services": {}}  # Simple fallback config

    # Get logging level from environment or config
    global_level = os.environ.get("LOG_LEVEL", config.get("global", "INFO"))
    level_num = getattr(logging, global_level.upper(), logging.INFO)

    # Setup basic logging
    logging.basicConfig(
        level=level_num,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("main")
    logger.info("=" * 80)
    logger.info(f"CurveEditor starting up - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log level: {global_level}, Log file: {log_file}")
    logger.info("=" * 80)

    # Apply module-specific log levels from config
    if isinstance(config.get("services"), dict):
        for service_name, service_level in config["services"].items():
            if isinstance(service_level, str):
                service_logger = logging.getLogger(f"services.{service_name}")
                service_logger.setLevel(getattr(logging, service_level.upper(), logging.INFO))
                logger.debug(f"Set {service_name} service log level to {service_level}")

    # Apply other module levels
    for module, level in config.items():
        if module in ["global", "services"] or not isinstance(level, str):
            continue
        module_logger = logging.getLogger(module)
        module_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.debug(f"Set {module} log level to {level}")

    # Initialize Qt application
    app = QApplication(sys.argv)

    # Initialize Qt object pooling for improved rendering performance - disabled for startup
    # try:
    #     from rendering.qt_object_pool import get_global_pool
    #     _pool = get_global_pool()  # Initialize global pool
    #     logger.info("Qt object pooling initialized - rendering performance optimized")
    # except ImportError:
    #     logger.warning("Qt object pooling not available - using standard rendering")
    logger.info("Qt object pooling disabled for startup - using standard rendering")

    # Create main window with service registry
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

    # Clean up Qt object pools - disabled for startup
    # try:
    #     from rendering.qt_object_pool import clear_global_pools
    #     clear_global_pools()
    #     logger.info("Qt object pools cleared")
    # except ImportError:
    #     pass
    logger.debug("Qt object pools cleanup skipped - pools not initialized")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()