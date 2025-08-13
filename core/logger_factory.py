#!/usr/bin/env python
"""
Logger factory for consistent logger creation across the application.

This module provides utilities for creating loggers with automatic
module name detection and consistent configuration.
"""

import inspect
import logging


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger with automatic module name detection.

    If no name is provided, automatically detects the calling module's name
    and uses that for the logger name. This ensures consistent logger naming
    across the application.

    Args:
        name: Optional logger name. If None, uses calling module's name.

    Returns:
        Configured logger instance.

    Example:
        ```python
        # In any module:
        from core.logger_factory import get_logger

        logger = get_logger()  # Automatically uses module name
        # or
        logger = get_logger("custom_name")  # Use custom name
        ```
    """
    if name is None:
        # Get the calling frame
        frame = inspect.currentframe()
        if frame and frame.f_back:
            # Get the module of the caller
            module = inspect.getmodule(frame.f_back)
            if module:
                name = module.__name__
            else:
                # Fallback to filename if module detection fails
                try:
                    filename = frame.f_back.f_code.co_filename
                    name = filename.split("/")[-1].split(".")[0]
                except (AttributeError, IndexError):
                    name = "unknown"
        else:
            name = "unknown"

    return logging.getLogger(name)


def get_child_logger(parent_logger: logging.Logger, child_name: str) -> logging.Logger:
    """
    Create a child logger from a parent logger.

    This is useful for creating sub-loggers within a module for different
    components or subsystems.

    Args:
        parent_logger: The parent logger instance.
        child_name: Name for the child logger.

    Returns:
        Child logger instance.

    Example:
        ```python
        logger = get_logger()
        db_logger = get_child_logger(logger, "database")
        # Creates logger with name "module_name.database"
        ```
    """
    return parent_logger.getChild(child_name)


def configure_logger(
    logger: logging.Logger,
    level: int = logging.INFO,
    format_string: str | None = None,
    add_console_handler: bool = True,
) -> logging.Logger:
    """
    Configure a logger with common settings.

    Args:
        logger: Logger to configure.
        level: Logging level (default: INFO).
        format_string: Custom format string for log messages.
        add_console_handler: Whether to add a console handler.

    Returns:
        Configured logger instance.
    """
    logger.setLevel(level)

    if add_console_handler and not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        if format_string is None:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        formatter = logging.Formatter(format_string)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# Convenience function for getting a debug logger
def get_debug_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger configured for debug output.

    Args:
        name: Optional logger name. If None, uses calling module's name.

    Returns:
        Logger configured with DEBUG level.
    """
    logger = get_logger(name)
    return configure_logger(logger, level=logging.DEBUG)
