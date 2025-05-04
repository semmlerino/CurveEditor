"""
Logging service for the CurveEditor application.

This module provides a central logging system to replace debug print statements
with configurable logging across the application.
"""

import logging
import os
from typing import Optional


class LoggingService:
    """Central logging service for the CurveEditor application."""

    # Class variable to track initialization
    _initialized: bool = False
    _root_logger: Optional[logging.Logger] = None

    @staticmethod
    def setup_logging(level=logging.INFO, log_file: Optional[str] = None,
                      console_output: bool = True) -> logging.Logger:
        """Set up the logging system.

        Args:
            level: The minimum logging level to capture
            log_file: Optional path to a log file
            console_output: Whether to output logs to console

        Returns:
            The configured root logger
        """
        if LoggingService._initialized:
            return LoggingService._root_logger or logging.getLogger('curve_editor')

        # Configure root logger
        logger = logging.getLogger('curve_editor')
        logger.setLevel(level)

        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Console handler (optional)
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            # Ensure directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        LoggingService._initialized = True
        LoggingService._root_logger = logger
        return logger

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger with the specified name.

        Args:
            name: The name for the logger, typically the module or class name

        Returns:
            A logger instance
        """
        # Ensure the root logger is initialized
        if not LoggingService._initialized:
            LoggingService.setup_logging()

        # Return a child logger
        return logging.getLogger(f'curve_editor.{name}')

    @staticmethod
    def set_level(level: int) -> None:
        """Set the logging level for all loggers.

        Args:
            level: The logging level to set (e.g., logging.DEBUG, logging.INFO)
        """
        if LoggingService._root_logger:
            LoggingService._root_logger.setLevel(level)
            for handler in LoggingService._root_logger.handlers:
                handler.setLevel(level)
