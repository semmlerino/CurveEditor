#!/usr/bin/env python

import logging
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    """Main entry point for the application."""
    # Setup logging directory
    log_dir = Path.home() / ".curve_editor" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create the log file path
    log_file = log_dir / "curve_editor.log"

    # Load logging configuration - simplified for startup
    # config = logging_config.load_config()  # Disabled - config module not available
    config: dict[str, str | dict[str, str]] = {"global": "INFO", "services": {}}  # Simple fallback config

    # Get logging level from environment or config
    import os

    global_level_raw = os.environ.get("LOG_LEVEL", config.get("global", "INFO"))
    # Ensure global_level is a string
    global_level: str = global_level_raw if isinstance(global_level_raw, str) else "INFO"
    level_num = getattr(logging, global_level.upper(), logging.INFO)

    # Setup basic logging
    logging.basicConfig(
        level=level_num,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(str(log_file)), logging.StreamHandler()],
    )
    logger = logging.getLogger("main")
    logger.info("=" * 80)
    logger.info(f"CurveEditor starting up - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log level: {global_level}, Log file: {log_file}")
    logger.info("=" * 80)

    # Apply module-specific log levels from config
    services_config_raw = config.get("services")
    if isinstance(services_config_raw, dict):
        services_config: dict[str, str] = services_config_raw
        for service_name, service_level in services_config.items():
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

    # Qt object pooling is not currently implemented
    logger.info("Using standard Qt rendering")

    # Create main window with service registry
    logger.info("Creating main window...")

    # Use standard MainWindow (modern UI removed for simplicity and type safety)
    use_modern_ui = os.environ.get("USE_MODERN_UI", "false").lower() == "true"

    if use_modern_ui:
        logger.warning("Modern UI requested but no longer available - using standard MainWindow")

    logger.info("Using standard MainWindow")
    window = MainWindow()

    # Install event filter for debugging key events
    # Note: This was causing issues with key event propagation
    # Only enable if MainWindow.eventFilter is properly implemented
    app.installEventFilter(window)

    # Show window
    window.show()
    logger.info("Main window displayed successfully")

    # Verify logging is working
    if log_file.exists():
        logger.info(f"Log file verified: {log_file} (size: {log_file.stat().st_size} bytes)")
    else:
        logger.warning(f"Log file not found at: {log_file}")

    # Run the application
    logger.info("Starting Qt event loop...")
    exit_code = app.exec()

    logger.info(f"Application exiting with code {exit_code}")

    # No cleanup needed for standard Qt rendering

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
