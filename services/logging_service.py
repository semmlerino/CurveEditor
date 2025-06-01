#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix the LoggingService to ensure log files are properly created.
"""

import logging
import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime


class LoggingService:
    """Central logging service for the CurveEditor application."""

    # Class variables to track initialization and state
    _initialized: bool = False
    _root_logger: Optional[logging.Logger] = None
    _log_file: Optional[str] = None
    _file_handler: Optional[logging.FileHandler] = None
    _console_handler: Optional[logging.StreamHandler] = None

    @classmethod
    def setup_logging(cls, level=logging.INFO, log_file: Optional[str] = None,
                     console_output: bool = True) -> logging.Logger:
        """Set up and configure logging for the application.

        Args:
            level: Logging level (default: INFO)
            log_file: Path to log file (default: None)
            console_output: Whether to output logs to console (default: True)

        Returns:
            Configured root logger
        """
        # Don't reinitialize if already done unless explicitly requested
        if cls._initialized and cls._root_logger is not None:
            return cls._root_logger

        # Get the curve_editor logger (not root to avoid conflicts)
        logger = logging.getLogger('curve_editor')
        logger.setLevel(level)
        logger.handlers.clear()  # Clear any existing handlers
        logger.propagate = False  # Don't propagate to root logger

        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')

        # Set up console logging
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            cls._console_handler = console_handler

        # Set up file logging
        if log_file:
            try:
                # Ensure log directory exists
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)

                # Create file handler with explicit error handling
                file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                file_handler.setLevel(level)
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)

                cls._log_file = log_file
                cls._file_handler = file_handler

                # Write initial message and flush immediately
                logger.info(f"Logging initialized - Level: {logging.getLevelName(level)}, File: {log_file}")
                file_handler.flush()  # Force flush to ensure file is written

            except Exception as e:
                # Print error to stderr for visibility
                import traceback
                print(f"ERROR: Failed to set up file logging: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                if console_output:
                    logger.error(f"Failed to set up file logging: {e}")

        cls._initialized = True
        cls._root_logger = logger

        return logger

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger with the specified name.

        Args:
            name: The name for the logger, typically the module or class name

        Returns:
            A logger instance
        """
        if not cls._initialized:
            cls.setup_logging()

        # Create child logger under curve_editor namespace
        child_logger = logging.getLogger(f'curve_editor.{name}')

        # IMPORTANT: Ensure child loggers propagate to parent
        # This is critical for log messages to reach the file handler
        child_logger.propagate = True

        return child_logger

    @classmethod
    def set_level(cls, level: int) -> None:
        """Set the logging level for all loggers.

        Args:
            level: The logging level to set (e.g., logging.DEBUG, logging.INFO)
        """
        if cls._root_logger:
            cls._root_logger.setLevel(level)
            # Update handler levels
            if cls._file_handler:
                cls._file_handler.setLevel(level)
            if cls._console_handler:
                cls._console_handler.setLevel(level)

    @classmethod
    def get_log_file(cls) -> Optional[str]:
        """Get the current log file path.

        Returns:
            Path to the current log file or None if not configured
        """
        return cls._log_file

    @classmethod
    def set_module_level(cls, module_name: str, level: int) -> None:
        """Set logging level for a specific module.

        Args:
            module_name: Name of the module (e.g., 'file_service', 'curve_service')
            level: Logging level to set
        """
        logger = cls.get_logger(module_name)
        logger.setLevel(level)

    @classmethod
    def configure_logging(cls, level: int = logging.INFO,
                          log_file: Optional[str] = None,
                          console_output: bool = True) -> logging.Logger:
        """Compatibility wrapper for legacy calls expecting `configure_logging`.

        Delegates to :py:meth:`setup_logging` so that existing code and unit tests
        can keep using ``LoggingService.configure_logging`` without changes.

        Args:
            level: Minimum logging level to capture (default: ``logging.INFO``).
            log_file: Optional path to a log file that should receive log output.
            console_output: Whether to output logs to the console as well.

        Returns:
            The configured root logger instance.
        """
        return cls.setup_logging(level=level, log_file=log_file, console_output=console_output)

    @classmethod
    def close(cls) -> None:
        """Close all handlers and clean up."""
        if cls._file_handler:
            cls._file_handler.flush()  # Flush before closing
            cls._file_handler.close()
            cls._file_handler = None
        if cls._console_handler:
            cls._console_handler.flush()  # Flush before closing
            cls._console_handler.close()
            cls._console_handler = None
        cls._initialized = False
        cls._root_logger = None
        cls._log_file = None
