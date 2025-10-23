"""
Singleton manager for all application stores.

Provides centralized access to all reactive data stores, ensuring
single source of truth for application state.
"""

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject

from core.logger_utils import get_logger
from core.type_aliases import CurveDataList

from .application_state import get_application_state
from .frame_store import FrameStore

if TYPE_CHECKING:
    from ui.state_manager import StateManager

logger = get_logger("store_manager")


class StoreManager(QObject):
    """
    Singleton manager for all application stores.

    This ensures we have only one instance of each store throughout
    the application, preventing data synchronization issues.
    """

    _instance: "StoreManager | None" = None

    frame_store: FrameStore
    _app_state: Any
    _initialized: bool

    def __new__(cls) -> "StoreManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize stores (only called once due to singleton)."""
        # Prevent multiple initialization
        # Using getattr with default to check if attribute exists (type-safe approach)
        if getattr(self, "_initialized", False):
            return

        super().__init__()

        # Initialize all stores
        self.frame_store = FrameStore()

        # Get ApplicationState reference
        self._app_state = get_application_state()

        # Future stores can be added here:
        # self.view_store = ViewStore()
        # self.selection_store = SelectionStore()

        # Connect stores to each other
        self._connect_stores()

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

        CRITICAL: Properly cleans up QObjects to prevent accumulation
        and segfaults in long test runs (see UNIFIED_TESTING_GUIDE).
        """
        if cls._instance:
            # Clear all store data
            cls._instance.frame_store.clear()
            logger.warning("StoreManager reset - all data cleared")

            # CRITICAL: Properly delete QObjects to prevent accumulation
            # Following pattern from UNIFIED_TESTING_GUIDE for QObject cleanup
            try:
                # Remove parents and schedule for deletion
                cls._instance.frame_store.setParent(None)
                cls._instance.frame_store.deleteLater()

                cls._instance.setParent(None)
                cls._instance.deleteLater()

                # Process events to ensure deleteLater() is handled
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                if app is not None:
                    app.processEvents()
            except RuntimeError:
                pass  # QObjects may already be deleted

        cls._instance = None

    def get_frame_store(self) -> FrameStore:
        """
        Get the frame store.

        Returns:
            The singleton FrameStore instance
        """
        return self.frame_store

    def set_state_manager(self, state_manager: "StateManager") -> None:
        """
        Set the StateManager reference for FrameStore delegation.

        Args:
            state_manager: The StateManager instance to delegate current_frame to
        """
        self.frame_store.set_state_manager(state_manager)
        logger.debug("StateManager reference set for FrameStore delegation")

    def _connect_stores(self) -> None:
        """Connect ApplicationState to FrameStore for coordinated updates."""
        # Connect to ApplicationState signals (replaces CurveDataStore signals)
        _ = self._app_state.curves_changed.connect(self._on_curves_changed)
        _ = self._app_state.active_curve_changed.connect(self._on_active_curve_changed)

        logger.debug("Connected ApplicationState signals for store coordination")

    def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
        """Sync FrameStore when curve data changes."""
        active = self._app_state.active_curve
        if active and active in curves:
            curve_data = curves[active]
            self.frame_store.sync_with_curve_data(curve_data)

    def _on_active_curve_changed(self, curve_name: str) -> None:
        """Sync FrameStore when active curve switches (without data change)."""
        if curve_name:
            curve_data = self._app_state.get_curve_data(curve_name)
            self.frame_store.sync_with_curve_data(curve_data)

    def connect_all_stores(self) -> None:
        """
        Set up inter-store connections if needed.

        This is where we'd connect signals between stores for
        coordinated updates.
        """
        # Example: When curve data changes, update frame store
        # self.curve_store.data_changed.connect(self.frame_store.update_from_curve_data)
        pass

    def save_state(self) -> dict[str, Any]:
        """
        Save all store states (for session persistence).

        Returns:
            Dictionary containing all store states
        """
        # Note: Curve data and selection now managed by ApplicationState
        state = {
            # Add other stores as they're implemented
        }
        logger.debug("Saved store state")
        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        """
        Restore all store states.

        Args:
            state: Previously saved state dictionary
        """
        # Note: Curve data and selection now managed by ApplicationState
        logger.debug("Restored store state")
