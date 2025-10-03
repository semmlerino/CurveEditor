"""
Reactive data stores for CurveEditor.

This module provides centralized state management with automatic UI updates
via Qt signals, solving the "orphaned component" problem.
"""

from .application_state import ApplicationState, ViewState, get_application_state, reset_application_state
from .connection_verifier import ConnectionRegistry, ConnectionReport, ConnectionStatus, ConnectionVerifier
from .curve_data_store import CurveDataStore
from .store_manager import StoreManager

__all__ = [
    # New ApplicationState architecture
    "ApplicationState",
    "ViewState",
    "get_application_state",
    "reset_application_state",
    # Legacy stores (for backward compatibility during migration)
    "CurveDataStore",
    "StoreManager",
    "get_store_manager",
    # Connection verification
    "ConnectionVerifier",
    "ConnectionRegistry",
    "ConnectionStatus",
    "ConnectionReport",
]


# Singleton access
def get_store_manager() -> StoreManager:
    """Get the singleton StoreManager instance."""
    return StoreManager.get_instance()
