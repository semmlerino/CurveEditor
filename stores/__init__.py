"""
Reactive data stores for CurveEditor.

This module provides centralized state management with automatic UI updates
via Qt signals, solving the "orphaned component" problem.
"""

from .application_state import ApplicationState, get_application_state, reset_application_state
from .connection_verifier import ConnectionRegistry, ConnectionReport, ConnectionStatus, ConnectionVerifier
from .store_manager import StoreManager

__all__ = [
    "ApplicationState",
    "ConnectionRegistry",
    "ConnectionReport",
    "ConnectionStatus",
    "ConnectionVerifier",
    "StoreManager",
    "get_application_state",
    "get_store_manager",
    "reset_application_state",
]


# Singleton access
def get_store_manager() -> StoreManager:
    """Get the singleton StoreManager instance."""
    return StoreManager.get_instance()
