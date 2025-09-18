"""
Singleton manager for all application stores.

Provides centralized access to all reactive data stores, ensuring
single source of truth for application state.
"""

from typing import Optional

from PySide6.QtCore import QObject

from core.logger_utils import get_logger

from .curve_data_store import CurveDataStore

logger = get_logger("store_manager")


class StoreManager(QObject):
    """
    Singleton manager for all application stores.

    This ensures we have only one instance of each store throughout
    the application, preventing data synchronization issues.
    """

    _instance: Optional["StoreManager"] = None

    def __new__(cls) -> "StoreManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize stores (only called once due to singleton)."""
        # Prevent multiple initialization
        if hasattr(self, "_initialized"):
            return

        super().__init__()

        # Initialize all stores
        self.curve_store = CurveDataStore()

        # Future stores can be added here:
        # self.frame_store = FrameStore()
        # self.view_store = ViewStore()
        # self.selection_store = SelectionStore()

        self._initialized = True
        logger.info("StoreManager initialized with all stores")

    @classmethod
    def get_instance(cls) -> "StoreManager":
        """
        Get the singleton instance.

        Returns:
            The single StoreManager instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton (mainly for testing).

        Warning: This clears all application state!
        """
        if cls._instance:
            # Clear all store data
            cls._instance.curve_store.clear()
            logger.warning("StoreManager reset - all data cleared")

        cls._instance = None

    def get_curve_store(self) -> CurveDataStore:
        """
        Get the curve data store.

        Returns:
            The singleton CurveDataStore instance
        """
        return self.curve_store

    def connect_all_stores(self) -> None:
        """
        Set up inter-store connections if needed.

        This is where we'd connect signals between stores for
        coordinated updates.
        """
        # Example: When curve data changes, update frame store
        # self.curve_store.data_changed.connect(self.frame_store.update_from_curve_data)
        pass

    def save_state(self) -> dict:
        """
        Save all store states (for session persistence).

        Returns:
            Dictionary containing all store states
        """
        state = {
            "curve_data": self.curve_store.get_data(),
            "selection": list(self.curve_store.get_selection()),
            # Add other stores as they're implemented
        }
        logger.debug("Saved store state")
        return state

    def restore_state(self, state: dict) -> None:
        """
        Restore all store states.

        Args:
            state: Previously saved state dictionary
        """
        if "curve_data" in state:
            self.curve_store.set_data(state["curve_data"])

        if "selection" in state:
            for index in state["selection"]:
                self.curve_store.select(index, add_to_selection=True)

        logger.debug("Restored store state")
