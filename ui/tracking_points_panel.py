"""Tracking points panel for displaying and managing multiple tracking points."""

from typing import TypedDict, override

from PySide6.QtCore import QEvent, QItemSelectionModel, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.display_mode import DisplayMode
from core.logger_utils import get_logger
from core.models import TrackingDirection
from core.signal_manager import SignalManager
from core.type_aliases import CurveDataInput

logger = get_logger(__name__)


class TrackingTableEventFilter(QObject):
    """Event filter for tracking table to handle tracking direction shortcuts."""

    def __init__(self, panel: "TrackingPointsPanel") -> None:
        """Initialize the event filter.

        Args:
            panel: The tracking points panel that owns the table
        """
        super().__init__()
        self.panel = panel

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Filter events for the tracking table.

        Args:
            watched: The object that would receive the event (should be the table)
            event: The event to filter

        Returns:
            True if event was handled and should be consumed, False otherwise
        """
        # Only handle key press events
        if event.type() != QEvent.Type.KeyPress:
            return False

        if not isinstance(event, QKeyEvent):
            return False

        # Only handle shortcuts when the table has focus
        # This allows global shortcuts to work when other widgets have focus
        if not self.panel.table.hasFocus():
            return False

        key = event.key()
        modifiers = event.modifiers()

        # Handle tracking direction shortcuts
        tracking_direction = None

        # Check for Shift+1, Shift+2, Shift+F3
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            if key == Qt.Key.Key_1:
                tracking_direction = TrackingDirection.TRACKING_BW
            elif key == Qt.Key.Key_2:
                tracking_direction = TrackingDirection.TRACKING_FW
            elif key == Qt.Key.Key_F3:
                tracking_direction = TrackingDirection.TRACKING_FW_BW

        # Check for symbol keys !, ", and @ (international keyboard layouts - separate check)
        if key == Qt.Key.Key_Exclam:  # ! (Shift+1 on most layouts)
            tracking_direction = TrackingDirection.TRACKING_BW
        elif key == Qt.Key.Key_QuoteDbl:  # " (Shift+2 on German layout)
            tracking_direction = TrackingDirection.TRACKING_FW
        elif key == Qt.Key.Key_At:  # @ (Shift+2 on US layout)
            tracking_direction = TrackingDirection.TRACKING_FW

        # If we found a tracking direction shortcut, handle it
        if tracking_direction is not None:
            return self._handle_tracking_direction_shortcut(tracking_direction)

        # Not a tracking direction shortcut, continue normal processing
        return False

    def _handle_tracking_direction_shortcut(self, direction: TrackingDirection) -> bool:
        """Handle a tracking direction shortcut.

        Args:
            direction: The tracking direction to set

        Returns:
            True if the shortcut was handled, False otherwise
        """
        # Get selected points from the panel
        selected_points = self.panel.get_selected_points()

        if not selected_points:
            # No points selected, don't consume the event
            return False

        # Set tracking direction for all selected points
        for point_name in selected_points:
            if point_name in self.panel._point_metadata:
                self.panel._point_metadata[point_name]["tracking_direction"] = direction
                self.panel.tracking_direction_changed.emit(point_name, direction)

        # Update the direction dropdowns in the table
        self.panel._update_direction_dropdowns_for_points(selected_points, direction)

        # Event was handled, consume it
        return True


class PointMetadata(TypedDict):
    """Type definition for point metadata."""

    visible: bool
    color: str
    tracking_direction: TrackingDirection


class TrackingPointsPanel(QWidget):
    """Panel displaying tracking point names with management capabilities."""

    # Signals
    point_visibility_changed: Signal = Signal(str, bool)  # Point name, visible
    point_color_changed: Signal = Signal(str, str)  # Point name, color hex
    tracking_direction_changed: Signal = Signal(str, object)  # Point name, TrackingDirection
    point_deleted: Signal = Signal(str)  # Point name
    point_renamed: Signal = Signal(str, str)  # Old name, new name

    def __init__(self, parent: QWidget | None = None):
        """Initialize the tracking points panel."""
        super().__init__(parent)

        # Signal management for proper cleanup
        self.signal_manager: SignalManager = SignalManager(self)

        self._point_metadata: dict[str, PointMetadata] = {}  # Store visibility, color, etc.
        self._updating: bool = False  # Prevent recursive updates
        self._update_depth: int = 0  # Track recursion depth for app state sync (more robust than boolean)
        self._updating_display_mode: bool = False  # Prevent display mode signal loops
        self._active_point: str | None = None  # Active timeline point (whose timeline is displayed)

        # NEW: ApplicationState reference
        from stores.application_state import get_application_state

        self._app_state = get_application_state()

        self._init_ui()

        # Install event filter for tracking direction shortcuts
        # Set self as parent for proper Qt ownership and automatic cleanup
        self._table_event_filter = TrackingTableEventFilter(self)
        self._table_event_filter.setParent(self)
        self.table.installEventFilter(self._table_event_filter)

        # NEW: Subscribe to ApplicationState changes (for reverse sync)
        # Use SignalManager to ensure automatic cleanup on widget destruction
        _ = self.signal_manager.connect(
            self._app_state.selection_state_changed,
            self._on_app_state_changed,
            "selection_state_changed",
        )

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add checkbox for toggling multi-curve display
        self.display_mode_checkbox: QCheckBox = QCheckBox("Show all curves")
        self.display_mode_checkbox.setToolTip(
            "When checked, displays all visible curves simultaneously.\n"
            "When unchecked, shows only the selected/active curve."
        )
        self.display_mode_checkbox.setChecked(False)
        _ = self.display_mode_checkbox.toggled.connect(self._on_display_mode_checkbox_toggled)
        layout.addWidget(self.display_mode_checkbox)

        # Create table widget
        self.table: QTableWidget = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Visible", "Name", "Frames", "Direction", "Color"])

        # Configure table appearance
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        # Disable mouse tracking to prevent hover selection
        self.table.setMouseTracking(False)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Visible checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Frame count
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Direction
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Color

        self.table.setColumnWidth(0, 60)  # Visible
        self.table.setColumnWidth(2, 70)  # Frames
        self.table.setColumnWidth(3, 80)  # Direction
        self.table.setColumnWidth(4, 60)  # Color

        # Connect signals
        _ = self.table.itemSelectionChanged.connect(self._on_selection_changed)
        _ = self.table.itemChanged.connect(self._on_item_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        _ = self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

    def set_tracked_data(self, tracked_data: dict[str, CurveDataInput]) -> None:
        """Update the displayed tracking data.

        Args:
            tracked_data: Dictionary of point names to trajectories
        """
        if self._updating:
            return

        self._updating = True

        # Initialize metadata for new points
        colors = [
            "#FF0000",
            "#00FF00",
            "#0000FF",
            "#FFFF00",
            "#FF00FF",
            "#00FFFF",
            "#FF8000",
            "#80FF00",
            "#0080FF",
            "#FF0080",
            "#80FF80",
            "#8080FF",
        ]

        color_index = 0
        for point_name in tracked_data:
            if point_name not in self._point_metadata:
                self._point_metadata[point_name] = {
                    "visible": True,
                    "color": colors[color_index % len(colors)],
                    "tracking_direction": TrackingDirection.TRACKING_FW_BW,  # Default
                }
                color_index += 1

        # Clear and repopulate table
        self.table.setRowCount(len(tracked_data))

        for i, (point_name, trajectory) in enumerate(tracked_data.items()):
            metadata = self._point_metadata[point_name]

            # Visible checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(metadata["visible"])
            _ = checkbox.stateChanged.connect(
                lambda state, name=point_name: self._on_visibility_changed(name, state == Qt.CheckState.Checked.value)
            )
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, checkbox_widget)

            # Point name
            name_item = QTableWidgetItem(point_name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
            # Store original point name in UserRole for rename detection
            name_item.setData(Qt.ItemDataRole.UserRole, point_name)
            self.table.setItem(i, 1, name_item)

            # Frame count
            count_item = QTableWidgetItem(str(len(trajectory)))
            count_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, count_item)

            # Tracking direction dropdown
            direction_combo = QComboBox()
            direction_combo.addItems(["FW", "BW", "FW+BW"])
            current_direction = metadata["tracking_direction"]
            direction_combo.setCurrentText(current_direction.abbreviation)
            _ = direction_combo.currentTextChanged.connect(
                lambda text, name=point_name: self._on_direction_changed(name, text)
            )
            self.table.setCellWidget(i, 3, direction_combo)

            # Color button
            color_button = QPushButton()
            color_button.setStyleSheet(f"background-color: {metadata['color']}; border: 1px solid black;")
            color_button.setMaximumHeight(20)
            _ = color_button.clicked.connect(lambda checked, name=point_name: self._on_color_button_clicked(name))
            self.table.setCellWidget(i, 4, color_button)

        # Reapply active point styling if an active point is set
        if self._active_point is not None:
            self._update_point_styling(self._active_point, is_active=True)

        self._updating = False

    def get_selected_points(self) -> list[str]:
        """Get list of selected tracking point names."""
        selected_points = []
        selected_rows = set()

        # Get all selected rows using selection model
        for index in self.table.selectionModel().selectedIndexes():
            selected_rows.add(index.row())

        # Get point names for selected rows
        for row in selected_rows:
            item = self.table.item(row, 1)  # Name column
            if item:
                selected_points.append(item.text())

        # DEBUG: Log selected points
        logger.info(f"[MULTI-CURVE-DEBUG] get_selected_points() returning: {selected_points}")

        return selected_points

    def set_selected_points(self, point_names: list[str]) -> None:
        """
        Programmatically select points in the table to sync with external state.

        This method updates the visual selection in the table without emitting
        the points_selected signal, preventing infinite loops when synchronizing
        selection state between the curve view and side pane.

        Args:
            point_names: List of point names to select in the table
        """
        if self._updating:
            return

        self._updating = True
        try:
            # Clear current selection
            self.table.clearSelection()

            # Find and select rows that match the point names
            selection_model = self.table.selectionModel()  # Returns non-None QItemSelectionModel

            for row in range(self.table.rowCount()):
                name_item = self.table.item(row, 1)  # Name column
                if name_item and name_item.text() in point_names:
                    # Select the entire row
                    selection_model.select(
                        self.table.model().index(row, 0),
                        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                    )
        finally:
            self._updating = False

    def set_active_point(self, point_name: str | None) -> None:
        """Set the active timeline point with visual differentiation.

        The active point is visually distinct from selected points:
        - Active point: Bold text, highlighted background (timeline being displayed)
        - Selected points: Normal table selection highlighting

        Args:
            point_name: Name of the active point, or None to clear active state
        """
        # Clear old active point styling
        if self._active_point is not None:
            self._update_point_styling(self._active_point, is_active=False)

        # Update active point
        self._active_point = point_name

        # Apply new active point styling
        if self._active_point is not None:
            self._update_point_styling(self._active_point, is_active=True)

    def _update_point_styling(self, point_name: str, is_active: bool) -> None:
        """Update the visual styling of a point row.

        Args:
            point_name: Name of the point to update
            is_active: Whether the point is the active timeline point
        """
        # Find the row for this point
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)  # Name column
            if name_item and name_item.text() == point_name:
                if is_active:
                    # Active point: bold font and distinct background
                    font = QFont()
                    font.setBold(True)
                    name_item.setFont(font)
                    # Light blue background to indicate active timeline
                    name_item.setBackground(QBrush(QColor("#2b5278")))
                else:
                    # Normal point: regular font and no special background
                    font = QFont()
                    font.setBold(False)
                    name_item.setFont(font)
                    # Clear background (use default)
                    name_item.setBackground(QBrush())
                break

    def get_visible_points(self) -> list[str]:
        """Get list of visible tracking point names."""
        visible_points = []
        for point_name, metadata in self._point_metadata.items():
            if metadata["visible"]:
                visible_points.append(point_name)
        return visible_points

    def get_point_color(self, point_name: str) -> str:
        """Get color for a tracking point."""
        if point_name in self._point_metadata:
            return self._point_metadata[point_name]["color"]
        return "#FFFFFF"

    def get_tracking_direction(self, point_name: str) -> TrackingDirection:
        """Get tracking direction for a tracking point."""
        if point_name in self._point_metadata:
            return self._point_metadata[point_name]["tracking_direction"]
        return TrackingDirection.TRACKING_FW_BW  # Default

    def get_point_visibility(self, point_name: str) -> bool:
        """Get visibility status for a tracking point."""
        if point_name in self._point_metadata:
            return self._point_metadata[point_name]["visible"]
        return True  # Default to visible

    def _on_display_mode_checkbox_toggled(self, checked: bool) -> None:
        """Handle toggle of display mode checkbox - update ApplicationState.

        Updates ApplicationState which automatically computes correct display_mode.
        Re-entrancy guard prevents infinite loops.

        Args:
            checked: Whether to show all curves
        """
        # Re-entrancy guard: prevent signal loops
        if self._updating_display_mode:
            return

        self._updating_display_mode = True
        try:
            # Update ApplicationState (single source of truth)
            self._app_state.set_show_all_curves(checked)
        finally:
            self._updating_display_mode = False

    def _on_app_state_changed(self, selected_curves: set[str], show_all: bool) -> None:
        """
        Sync UI when ApplicationState changes (reverse flow).

        Handles external changes to selection state (e.g., from other UI or API).
        Uses recursion counter to prevent circular updates (more robust than boolean flag).

        Args:
            selected_curves: Set of selected curve names from ApplicationState
            show_all: Show-all-curves mode from ApplicationState
        """
        # Use recursion counter to prevent re-entrant calls
        if self._update_depth > 0:
            return

        self._update_depth += 1
        try:
            # Update table selection to match ApplicationState
            self.set_selected_points(list(selected_curves))

            # Update checkbox to match ApplicationState
            if self.display_mode_checkbox.isChecked() != show_all:
                self.display_mode_checkbox.setChecked(show_all)
        finally:
            self._update_depth -= 1

    def _determine_mode_from_checkbox(self, checked: bool) -> DisplayMode:
        """Determine DisplayMode from checkbox state and selection context.

        Mapping Logic:
            - checked=True → DisplayMode.ALL_VISIBLE (always)
            - checked=False + has selection → DisplayMode.SELECTED
            - checked=False + no selection → DisplayMode.ACTIVE_ONLY

        Args:
            checked: Checkbox state (True = show all curves)

        Returns:
            DisplayMode enum value based on checkbox and selection state
        """
        if checked:
            return DisplayMode.ALL_VISIBLE

        # Checkbox unchecked: determine SELECTED vs ACTIVE_ONLY
        if self._has_selection():
            return DisplayMode.SELECTED
        else:
            return DisplayMode.ACTIVE_ONLY

    def _has_selection(self) -> bool:
        """Check if any curves are selected in the table.

        Returns:
            True if one or more curves are selected, False otherwise
        """
        selected_items = self.table.selectedItems()
        return len(selected_items) > 0

    def _mode_to_checkbox_state(self, mode: DisplayMode) -> bool:
        """Convert DisplayMode to checkbox state (for reverse mapping).

        Args:
            mode: DisplayMode enum value

        Returns:
            True if mode is ALL_VISIBLE, False for SELECTED or ACTIVE_ONLY
        """
        return mode == DisplayMode.ALL_VISIBLE

    def _on_selection_changed(self) -> None:
        """Handle table selection changes - update ApplicationState."""
        if self._updating:
            return

        selected_points = self.get_selected_points()

        # Update ApplicationState (single source of truth)
        # This triggers selection_state_changed signal → MultiPointTrackingController
        self._app_state.set_selected_curves(set(selected_points))

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle item editing (point renaming)."""
        if self._updating:
            return

        if item.column() == 1:  # Name column
            new_name = item.text()
            # Get the old name from UserRole data (stored when item was created)
            old_name = item.data(Qt.ItemDataRole.UserRole)

            if old_name and new_name != old_name:
                # Update UserRole data with new name for future edits
                item.setData(Qt.ItemDataRole.UserRole, new_name)
                self.point_renamed.emit(old_name, new_name)

    def _on_visibility_changed(self, point_name: str, visible: bool) -> None:
        """Handle visibility checkbox changes."""
        if point_name in self._point_metadata:
            self._point_metadata[point_name]["visible"] = visible
            self.point_visibility_changed.emit(point_name, visible)

    def _on_direction_changed(self, point_name: str, direction_text: str) -> None:
        """Handle tracking direction dropdown changes."""
        if self._updating:
            return

        if point_name in self._point_metadata:
            new_direction = TrackingDirection.from_abbreviation(direction_text)
            self._point_metadata[point_name]["tracking_direction"] = new_direction
            self.tracking_direction_changed.emit(point_name, new_direction)

    def _on_color_button_clicked(self, point_name: str) -> None:
        """Handle color button click."""
        current_color = QColor(self._point_metadata[point_name]["color"])
        color = QColorDialog.getColor(current_color, self, f"Choose color for {point_name}")

        if color.isValid():
            color_hex = color.name()
            self._point_metadata[point_name]["color"] = color_hex

            # Update button color
            for row in range(self.table.rowCount()):
                if self.table.item(row, 1).text() == point_name:
                    button = self.table.cellWidget(row, 4)  # Color button is now in column 4
                    if button:
                        button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid black;")
                    break

            self.point_color_changed.emit(point_name, color_hex)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu for selected points."""
        selected_points = self.get_selected_points()

        if not selected_points:
            return

        menu = QMenu(self)

        # Visibility actions
        show_action = QAction("Show", self)
        _ = show_action.triggered.connect(lambda: self._set_visibility_for_points(selected_points, True))
        menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        _ = hide_action.triggered.connect(lambda: self._set_visibility_for_points(selected_points, False))
        _ = menu.addAction(hide_action)

        _ = menu.addSeparator()

        # Tracking direction submenu
        direction_menu = QMenu("Set Direction", self)

        fw_action = QAction("Forward (FW)", self)
        _ = fw_action.triggered.connect(
            lambda: self._set_direction_for_points(selected_points, TrackingDirection.TRACKING_FW)
        )
        _ = direction_menu.addAction(fw_action)

        bw_action = QAction("Backward (BW)", self)
        _ = bw_action.triggered.connect(
            lambda: self._set_direction_for_points(selected_points, TrackingDirection.TRACKING_BW)
        )
        _ = direction_menu.addAction(bw_action)

        fwbw_action = QAction("Bidirectional (FW+BW)", self)
        _ = fwbw_action.triggered.connect(
            lambda: self._set_direction_for_points(selected_points, TrackingDirection.TRACKING_FW_BW)
        )
        _ = direction_menu.addAction(fwbw_action)

        _ = menu.addMenu(direction_menu)

        _ = menu.addSeparator()

        # Delete action
        if len(selected_points) == 1:
            delete_action = QAction(f"Delete {selected_points[0]}", self)
        else:
            delete_action = QAction(f"Delete {len(selected_points)} points", self)
        _ = delete_action.triggered.connect(lambda: self._delete_points(selected_points))
        _ = menu.addAction(delete_action)

        _ = menu.exec(self.table.viewport().mapToGlobal(position))

    def _set_visibility_for_points(self, points: list[str], visible: bool) -> None:
        """Set visibility for multiple points."""
        for point_name in points:
            if point_name in self._point_metadata:
                self._point_metadata[point_name]["visible"] = visible
                self.point_visibility_changed.emit(point_name, visible)

        # Update checkboxes
        for row in range(self.table.rowCount()):
            point_name = self.table.item(row, 1).text()
            if point_name in points:
                checkbox_widget = self.table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(visible)

    def _set_direction_for_points(self, points: list[str], direction: TrackingDirection) -> None:
        """Set tracking direction for multiple points."""
        for point_name in points:
            if point_name in self._point_metadata:
                self._point_metadata[point_name]["tracking_direction"] = direction
                self.tracking_direction_changed.emit(point_name, direction)

        # Update dropdowns
        for row in range(self.table.rowCount()):
            point_name = self.table.item(row, 1).text()
            if point_name in points:
                direction_combo = self.table.cellWidget(row, 3)  # Direction is in column 3
                if direction_combo and isinstance(direction_combo, QComboBox):
                    direction_combo.setCurrentText(direction.abbreviation)

    def _update_direction_dropdowns_for_points(self, points: list[str], direction: TrackingDirection) -> None:
        """Update direction dropdowns for specified points without changing metadata."""
        for row in range(self.table.rowCount()):
            point_name_item = self.table.item(row, 1)
            if point_name_item:
                point_name = point_name_item.text()
                if point_name in points:
                    direction_combo = self.table.cellWidget(row, 3)  # Direction is in column 3
                    if direction_combo and isinstance(direction_combo, QComboBox):
                        direction_combo.setCurrentText(direction.abbreviation)

    def _delete_points(self, points: list[str]) -> None:
        """Delete selected points."""
        for point_name in points:
            self.point_deleted.emit(point_name)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events.

        All keyboard shortcuts are now handled by the global shortcut system.
        This method just ensures proper event propagation.
        """
        # Let the event propagate to the global event filter
        super().keyPressEvent(event)

    @override
    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Clean up event filters to prevent accumulation across tests.

        CRITICAL: Properly removes event filter to prevent resource exhaustion
        after 1580+ tests (see UNIFIED_TESTING_GUIDE). Without this cleanup,
        event filters accumulate in QApplication causing timeouts when
        setStyleSheet() triggers events through all accumulated filters.
        """
        # Remove event filter from table
        if hasattr(self, "_table_event_filter") and hasattr(self, "table"):
            try:
                self.table.removeEventFilter(self._table_event_filter)
                self._table_event_filter.deleteLater()
            except RuntimeError:
                pass  # QObject may already be deleted

        # Call parent cleanup
        super().closeEvent(event)
