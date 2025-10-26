"""
StateSyncController - Manages signal connections and reactive state updates for CurveViewWidget.

This controller extracts signal handling responsibilities from CurveViewWidget:
- Connects to ApplicationState and StateManager signals
- Handles reactive updates when stores emit change notifications
- Synchronizes widget display state with underlying data stores

Architecture:
- Composed into CurveViewWidget (not inherited)
- Widget delegates all signal connection and handling to this controller
- Controller triggers widget updates (update(), invalidate_caches(), emit signals)
- Clean separation: signal handling logic isolated from widget's core responsibilities
"""

# Import cycle is expected: CurveViewWidget imports this controller
# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING

from core.logger_utils import get_logger
from core.type_aliases import CurveDataList
from services import get_data_service
from stores.application_state import ApplicationState
from ui.qt_utils import safe_slot

# Import cycle prevention: CurveViewWidget imports this controller
# So we can't import CurveViewWidget here - use TYPE_CHECKING
if TYPE_CHECKING:
    from ui.curve_view_widget import CurveViewWidget
    from ui.state_manager import StateManager

logger = get_logger("state_sync_controller")


class StateSyncController:
    """
    Manages signal connections and reactive state synchronization for CurveViewWidget.

    Responsibilities:
    - Connect to reactive store signals (CurveDataStore, ApplicationState, StateManager)
    - Handle signal callbacks and update widget state accordingly
    - Synchronize DataService with curve data changes
    - Maintain point collection consistency with store changes

    The controller reads from stores and triggers widget updates (update(), emit signals).
    """

    def __init__(self, widget: CurveViewWidget):
        """
        Initialize StateSyncController.

        Args:
            widget: The CurveViewWidget this controller manages
        """
        self.widget: CurveViewWidget = widget

        # Store references for signal connections
        self._app_state: ApplicationState = widget._app_state  # pyright: ignore[reportPrivateUsage]
        self._state_manager: StateManager | None = widget._state_manager  # pyright: ignore[reportPrivateUsage]

    def connect_all_signals(self) -> None:
        """Connect to all reactive store signals for automatic updates."""
        self._connect_app_state_signals()
        self._connect_state_manager_signals()
        logger.debug("Connected all signal handlers")

    # ==================== Signal Connection Methods ====================

    def _connect_app_state_signals(self) -> None:
        """Connect to ApplicationState signals for multi-curve reactive updates."""
        self._app_state.curves_changed.connect(self._on_app_state_curves_changed)
        self._app_state.selection_changed.connect(self._on_app_state_selection_changed)
        self._app_state.active_curve_changed.connect(self._on_app_state_active_curve_changed)
        self._app_state.curve_visibility_changed.connect(self._on_app_state_visibility_changed)

        logger.debug("Connected to ApplicationState signals")

    def _connect_state_manager_signals(self) -> None:
        """Connect to state manager signals for frame updates."""
        # Frame change handling now managed by FrameChangeCoordinator
        # No direct state manager connection needed
        logger.debug("Frame change handling delegated to FrameChangeCoordinator")

    # ==================== State Manager Signal Handlers ====================
    # Frame change handling now managed by FrameChangeCoordinator

    # ==================== ApplicationState Signal Handlers ====================

    @safe_slot
    def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
        """Handle ApplicationState curves_changed signal.

        Args:
            curves: Dictionary mapping curve names to curve data
        """
        # Update widget caches and display
        self.widget.invalidate_caches()
        self.widget.update()

        # Emit widget signal for backward compatibility
        self.widget.data_changed.emit()

        # Sync DataService with active curve
        active_curve = self._app_state.active_curve
        if active_curve and active_curve in curves:
            try:
                data_service = get_data_service()
                data_service.update_curve_data(curves[active_curve])
                logger.debug(f"Synced active curve '{active_curve}' to DataService")
            except Exception as e:
                logger.error(f"Failed to sync DataService: {e}")

        logger.debug(f"ApplicationState curves changed: {len(curves)} curves")

    @safe_slot
    def _on_app_state_selection_changed(self, indices: set[int], curve_name: str) -> None:
        """Handle ApplicationState selection_changed signal."""
        # Update display if this is the active curve
        if curve_name == self._app_state.active_curve:
            self.widget.update()
            # Emit widget signal for backward compatibility
            self.widget.selection_changed.emit(list(indices))
            logger.debug(f"ApplicationState selection changed for '{curve_name}': {len(indices)} selected")

    @safe_slot
    def _on_app_state_active_curve_changed(self, curve_name: str) -> None:
        """Handle ApplicationState active_curve_changed signal."""
        # Update display to show new active curve
        self.widget.invalidate_caches()
        self.widget.update()
        logger.debug(f"ApplicationState active curve changed to: '{curve_name}'")

    @safe_slot
    def _on_app_state_visibility_changed(self, curve_name: str, visible: bool) -> None:
        """Handle ApplicationState curve_visibility_changed signal."""
        # Update display
        self.widget.update()
        logger.debug(f"ApplicationState visibility changed for '{curve_name}': {visible}")
