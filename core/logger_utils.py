"""Centralized logger initialization and utilities.

This module provides common logging patterns to reduce duplication across the codebase.
Previously, `logger = logging.getLogger(__name__)` was repeated 35+ times.
"""

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__ from the calling module

    Returns:
        Configured logger instance

    Example:
        from core.logger_utils import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, message: str, exc: Exception, **kwargs: Any) -> None:
    """Log an exception with consistent formatting.

    Args:
        logger: Logger instance to use
        message: Context message for the exception
        exc: The exception to log
        **kwargs: Additional context to include in the log
    """
    logger.error(f"{message}: {exc.__class__.__name__}: {exc}", exc_info=True, extra=kwargs)


def log_debug_timing(logger: logging.Logger, operation: str, duration: float) -> None:
    """Log timing information for performance debugging.

    Args:
        logger: Logger instance to use
        operation: Name of the operation being timed
        duration: Duration in seconds
    """
    logger.debug(f"{operation} took {duration:.4f} seconds")
