"""Tracking points panel for displaying and managing multiple tracking points."""

from typing import TypedDict

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QColor, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.type_aliases import CurveDataList


class PointMetadata(TypedDict):
    """Type definition for point metadata."""

    visible: bool
    color: str


class TrackingPointsPanel(QWidget):
    """Panel displaying tracking point names with management capabilities."""

    # Signals
    points_selected: Signal = Signal(list)  # List of selected point names
    point_visibility_changed: Signal = Signal(str, bool)  # Point name, visible
    point_color_changed: Signal = Signal(str, str)  # Point name, color hex
    point_deleted: Signal = Signal(str)  # Point name
    point_renamed: Signal = Signal(str, str)  # Old name, new name

    def __init__(self, parent: QWidget | None = None):
        """Initialize the tracking points panel."""
        super().__init__(parent)
        self._tracked_data: dict[str, CurveDataList] = {}
        self._point_metadata: dict[str, PointMetadata] = {}  # Store visibility, color, etc.
        self._updating: bool = False  # Prevent recursive updates
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create table widget
        self.table: QTableWidget = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Visible", "Name", "Frames", "Color"])

        # Configure table appearance
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Visible checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Frame count
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Color

        self.table.setColumnWidth(0, 60)  # Visible
        self.table.setColumnWidth(2, 70)  # Frames
        self.table.setColumnWidth(3, 60)  # Color

        # Connect signals
        _ = self.table.itemSelectionChanged.connect(self._on_selection_changed)
        _ = self.table.itemChanged.connect(self._on_item_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        _ = self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

    def set_tracked_data(self, tracked_data: dict[str, CurveDataList]) -> None:
        """Update the displayed tracking data.

        Args:
            tracked_data: Dictionary of point names to trajectories
        """
        if self._updating:
            return

        self._updating = True
        self._tracked_data = tracked_data

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
                self._point_metadata[point_name] = {"visible": True, "color": colors[color_index % len(colors)]}
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
            self.table.setItem(i, 1, name_item)

            # Frame count
            count_item = QTableWidgetItem(str(len(trajectory)))
            count_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, count_item)

            # Color button
            color_button = QPushButton()
            color_button.setStyleSheet(f"background-color: {metadata['color']}; border: 1px solid black;")
            color_button.setMaximumHeight(20)
            _ = color_button.clicked.connect(lambda checked, name=point_name: self._on_color_button_clicked(name))
            self.table.setCellWidget(i, 3, color_button)

        self._updating = False

    def get_selected_points(self) -> list[str]:
        """Get list of selected tracking point names."""
        selected_points = []
        for item in self.table.selectedItems():
            if item.column() == 1:  # Name column
                selected_points.append(item.text())
        return selected_points

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

    def _on_selection_changed(self) -> None:
        """Handle table selection changes."""
        if self._updating:
            return

        selected_points = self.get_selected_points()
        self.points_selected.emit(selected_points)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle item editing (point renaming)."""
        if self._updating:
            return

        if item.column() == 1:  # Name column
            new_name = item.text()
            # Find the old name
            row = item.row()
            old_name = list(self._tracked_data.keys())[row] if row < len(self._tracked_data) else ""

            if old_name and new_name != old_name:
                self.point_renamed.emit(old_name, new_name)

    def _on_visibility_changed(self, point_name: str, visible: bool) -> None:
        """Handle visibility checkbox changes."""
        if point_name in self._point_metadata:
            self._point_metadata[point_name]["visible"] = visible
            self.point_visibility_changed.emit(point_name, visible)

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
                    button = self.table.cellWidget(row, 3)
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
        menu.addAction(hide_action)

        menu.addSeparator()

        # Delete action
        if len(selected_points) == 1:
            delete_action = QAction(f"Delete {selected_points[0]}", self)
        else:
            delete_action = QAction(f"Delete {len(selected_points)} points", self)
        _ = delete_action.triggered.connect(lambda: self._delete_points(selected_points))
        menu.addAction(delete_action)

        menu.exec(self.table.viewport().mapToGlobal(position))

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

    def _delete_points(self, points: list[str]) -> None:
        """Delete selected points."""
        for point_name in points:
            self.point_deleted.emit(point_name)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Delete:
            selected_points = self.get_selected_points()
            if selected_points:
                self._delete_points(selected_points)
        else:
            super().keyPressEvent(event)
