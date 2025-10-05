"""
StateSyncController - Manages signal connections and reactive state updates for CurveViewWidget.

This controller extracts signal handling responsibilities from CurveViewWidget:
- Connects to CurveDataStore, ApplicationState, and StateManager signals
- Handles reactive updates when stores emit change notifications
- Synchronizes widget display state with underlying data stores

Architecture:
- Composed into CurveViewWidget (not inherited)
- Widget delegates all signal connection and handling to this controller
- Controller triggers widget updates (update(), invalidate_caches(), emit signals)
- Clean separation: signal handling logic isolated from widget's core responsibilities
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from core.logger_utils import get_logger
from core.models import CurvePoint, PointCollection, PointStatus
from core.type_aliases import CurveDataList
from services import get_data_service

# Import cycle prevention: CurveViewWidget imports this controller
# So we can't import CurveViewWidget here - use Any for the type
if TYPE_CHECKING:
    pass  # Intentionally empty - no imports to avoid cycle

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

    def __init__(self, widget: Any):  # CurveViewWidget - type hint removed to break cycle
        """
        Initialize StateSyncController.

        Args:
            widget: The CurveViewWidget this controller manages
        """
        self.widget = widget

        # Store references for signal connections
        self._curve_store = widget._curve_store
        self._app_state = widget._app_state
        self._state_manager = widget._state_manager

    def connect_all_signals(self) -> None:
        """Connect to all reactive store signals for automatic updates."""
        self._connect_store_signals()
        self._connect_app_state_signals()
        self._connect_state_manager_signals()
        logger.debug("Connected all signal handlers")

    # ==================== Signal Connection Methods ====================

    def _connect_store_signals(self) -> None:
        """Connect to reactive store signals for automatic updates."""
        # Connect store signals to widget updates
        self._curve_store.data_changed.connect(self._on_store_data_changed)
        self._curve_store.point_added.connect(self._on_store_point_added)
        self._curve_store.point_updated.connect(self._on_store_point_updated)
        self._curve_store.point_removed.connect(self._on_store_point_removed)
        self._curve_store.point_status_changed.connect(self._on_store_status_changed)
        self._curve_store.selection_changed.connect(self._on_store_selection_changed)

        # Ensure DataService stays synchronized with curve data changes
        _ = self._curve_store.data_changed.connect(self._sync_data_service)

        logger.debug("Connected to reactive store signals")

    def _connect_app_state_signals(self) -> None:
        """Connect to ApplicationState signals for multi-curve reactive updates."""
        self._app_state.curves_changed.connect(self._on_app_state_curves_changed)
        self._app_state.selection_changed.connect(self._on_app_state_selection_changed)
        self._app_state.active_curve_changed.connect(self._on_app_state_active_curve_changed)
        self._app_state.curve_visibility_changed.connect(self._on_app_state_visibility_changed)

        logger.debug("Connected to ApplicationState signals")

    def _connect_state_manager_signals(self) -> None:
        """Connect to state manager signals for frame updates."""
        # Use injected state manager or fallback to main window
        if self._state_manager is not None:
            state_manager = self._state_manager
            state_manager.frame_changed.connect(self._on_state_frame_changed)
            logger.debug("Connected to state manager frame_changed signal")
        else:
            # No state manager available - will connect later if main window provides one
            logger.debug("No state manager available - state manager connection will be made when available")

    # ==================== CurveDataStore Signal Handlers ====================

    def _on_state_frame_changed(self, frame: int) -> None:
        """Handle frame changes from state manager."""
        logger.debug(f"[FRAME] State manager frame changed to {frame}, updating view")

        # Force a full update to ensure current frame highlighting updates
        self.widget.invalidate_caches()
        self.widget.update()

        # Handle centering mode
        if self.widget.centering_mode:
            logger.debug(f"[CENTERING] Auto-centering on frame {frame} (centering mode enabled)")
            self.widget.center_on_frame(frame)

    def _on_store_data_changed(self) -> None:
        """Handle store data changed signal."""
        # Update internal point collection
        data = self.widget.curve_data
        if data:
            formatted_data = []
            for point in data:
                if len(point) >= 3:
                    formatted_data.append((int(point[0]), float(point[1]), float(point[2])))
            self.widget.point_collection = PointCollection.from_tuples(formatted_data)
        else:
            self.widget.point_collection = None

        # Clear caches and update display
        self.widget.invalidate_caches()
        self.widget.update()

        # Propagate signal to widget listeners
        self.widget.data_changed.emit()

    def _on_store_point_added(self, index: int, point: object) -> None:
        """Handle store point added signal."""

        # Cast to expected tuple type for type safety
        point_tuple = cast(tuple[int, float, float] | tuple[int, float, float, str | bool], point)

        # Update collection if needed
        if self.widget.point_collection:
            self.widget.point_collection.points.append(CurvePoint.from_tuple(point_tuple))
        else:
            self.widget.point_collection = PointCollection([CurvePoint.from_tuple(point_tuple)])

        self.widget._invalidate_point_region(index)
        self.widget.update()
        self.widget.data_changed.emit()

    def _on_store_point_updated(self, index: int, x: float, y: float) -> None:
        """Handle store point updated signal."""
        # Update collection
        if self.widget.point_collection and index < len(self.widget.point_collection.points):
            old_cp = self.widget.point_collection.points[index]
            self.widget.point_collection.points[index] = old_cp.with_coordinates(x, y)

        self.widget._invalidate_point_region(index)
        self.widget.point_moved.emit(index, x, y)
        self.widget.update()
        self.widget.data_changed.emit()

    def _on_store_point_removed(self, index: int) -> None:
        """Handle store point removed signal."""
        # Update collection
        if self.widget.point_collection and index < len(self.widget.point_collection.points):
            del self.widget.point_collection.points[index]

        self.widget.invalidate_caches()
        self.widget.update()
        self.widget.data_changed.emit()

    def _on_store_status_changed(self, index: int, status: str) -> None:
        """Handle store point status changed signal."""
        # Update collection if needed
        if self.widget.point_collection and index < len(self.widget.point_collection.points):
            old_cp = self.widget.point_collection.points[index]
            # Map string status to PointStatus enum using from_legacy
            status_enum = PointStatus.from_legacy(status)
            self.widget.point_collection.points[index] = old_cp.with_status(status_enum)

        # Handle restoration logic via data service
        data_service = get_data_service()
        data_service.handle_point_status_change(index, status)

        self.widget.update()
        self.widget.data_changed.emit()
        # Emit point_moved for compatibility with old code that listens for status changes
        point = self._curve_store.get_point(index)
        if point and len(point) >= 3:
            self.widget.point_moved.emit(index, point[1], point[2])

    def _on_store_selection_changed(self, selection: set[int], curve_name: str | None = None) -> None:
        """Handle store selection changed signal.

        Phase 4: Removed __default__ - curve_name is now optional.
        """
        # Update widget selection display
        self.widget.update()

        # Emit widget's selection_changed signal (list format for compatibility)
        self.widget.selection_changed.emit(list(selection))
        logger.debug(f"Store selection changed for '{curve_name}': {len(selection)} selected")

    def _sync_data_service(self) -> None:
        """Synchronize DataService with current curve data."""
        try:
            data_service = get_data_service()
            current_data = self._curve_store.get_data()
            data_service.update_curve_data(current_data)
            logger.debug(f"Synchronized DataService with {len(current_data)} points")
        except Exception as e:
            logger.error(f"Failed to synchronize DataService: {e}")

    # ==================== ApplicationState Signal Handlers ====================

    def _on_app_state_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
        """Handle ApplicationState curves_changed signal.

        Phase 4: Removed __default__ sync - StateSyncController only handles
        active_curve_changed for CurveDataStore sync now.

        Args:
            curves: Dictionary mapping curve names to curve data
        """
        # Multi-curve state has changed - repaint to show all visible curves
        self.widget.invalidate_caches()
        self.widget.update()
        logger.debug(f"ApplicationState curves changed: {len(curves)} curves")

    def _on_app_state_selection_changed(self, indices: set[int], curve_name: str) -> None:
        """Handle ApplicationState selection_changed signal."""
        # Update display if this is the active curve
        if curve_name == self._app_state.active_curve:
            self.widget.update()
            logger.debug(f"ApplicationState selection changed for '{curve_name}': {len(indices)} selected")

    def _on_app_state_active_curve_changed(self, curve_name: str) -> None:
        """Handle ApplicationState active_curve_changed signal.

        Syncs the new active curve to CurveDataStore for backward compatibility.
        Phase 3.2: Added automatic sync to remove manual syncing from facade.
        """
        # Sync active curve to CurveDataStore for backward compatibility
        if curve_name:
            curve_data = self._app_state.get_curve_data(curve_name)
            if curve_data is not None:
                self._curve_store.set_data(curve_data, preserve_selection_on_sync=True)
                logger.debug(f"Synced active curve '{curve_name}' to CurveDataStore")

        # Update display to show new active curve
        self.widget.invalidate_caches()
        self.widget.update()
        logger.debug(f"ApplicationState active curve changed to: '{curve_name}'")

    def _on_app_state_visibility_changed(self, curve_name: str, visible: bool) -> None:
        """Handle ApplicationState curve_visibility_changed signal."""
        # Update display
        self.widget.update()
        logger.debug(f"ApplicationState visibility changed for '{curve_name}': {visible}")
