#!/usr/bin/env python

"""
Service protocols for CurveEditor.

This module defines Protocol interfaces for dependency injection and type safety.
Minimal implementation for startup compatibility.
"""

import logging
from typing import Protocol, Any


class LoggingServiceProtocol(Protocol):
    """Protocol for logging service dependency injection."""
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name."""
        ...


class StatusServiceProtocol(Protocol):
    """Protocol for status service dependency injection."""
    
    def set_status(self, message: str) -> None:
        """Set status message."""
        ...
    
    def clear_status(self) -> None:
        """Clear status message."""
        ...


class ServiceProtocol(Protocol):
    """Base protocol for all services."""
    
    def initialize(self) -> None:
        """Initialize the service."""
        ...


# Simple implementations for backward compatibility
class SimpleLoggingService:
    """Simple logging service implementation."""
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name."""
        return logging.getLogger(name)


class SimpleStatusService:
    """Simple status service implementation."""
    
    def set_status(self, message: str) -> None:
        """Set status message."""
        # For startup, just log the status
        logging.getLogger("status").info(f"Status: {message}")
    
    def clear_status(self) -> None:
        """Clear status message."""
        # For startup, just log
        logging.getLogger("status").debug("Status cleared")


# Factory functions for creating simple implementations
def create_simple_logging_service() -> LoggingServiceProtocol:
    """Create a simple logging service."""
    return SimpleLoggingService()


def create_simple_status_service() -> StatusServiceProtocol:
    """Create a simple status service."""
    return SimpleStatusService()