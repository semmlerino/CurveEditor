"""Point list widget for displaying and editing curve points in a table."""

from typing_extensions import override

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.models import PointStatus


class PointListWidget(QWidget):
    """Widget displaying curve points in a table format with editing capabilities."""

    # Signals
    point_selected: Signal = Signal(list)  # List of selected indices
    point_edited: Signal = Signal(int, float, float)  # Index, new_x, new_y
    point_deleted: Signal = Signal(list)  # List of indices to delete
    point_status_changed: Signal = Signal(int, PointStatus)  # Index, new_status

    def __init__(self, parent: QWidget | None = None):
        """Initialize the point list widget."""
        super().__init__(parent)
        self._curve_data: list[tuple[int, float, float] | tuple[int, float, float, PointStatus]] = []
        self._updating: bool = False  # Prevent recursive updates
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create table widget
        self.table: QTableWidget = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["", "Frame", "X", "Y", "Status"])

        # Configure table appearance
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Selection indicator
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Frame
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # X
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Y
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Status

        self.table.setColumnWidth(0, 30)  # Selection indicator
        self.table.setColumnWidth(1, 60)  # Frame
        self.table.setColumnWidth(4, 80)  # Status

        # Connect signals
        _ = self.table.itemSelectionChanged.connect(self._on_selection_changed)
        _ = self.table.itemChanged.connect(self._on_item_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        _ = self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

    def set_curve_data(
        self, curve_data: list[tuple[int, float, float] | tuple[int, float, float, PointStatus]]
    ) -> None:
        """Update the displayed curve data.

        Args:
            curve_data: List of tuples (frame, x, y, [status])
        """
        if self._updating:
            return

        self._updating = True
        self._curve_data = curve_data

        # Clear and repopulate table
        self.table.setRowCount(len(curve_data))

        for i, point_data in enumerate(curve_data):
            frame = point_data[0]
            x = point_data[1]
            y = point_data[2]
            status = point_data[3] if len(point_data) > 3 else PointStatus.NORMAL

            # Selection indicator (empty initially)
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(i, 0, item)

            # Frame
            item = QTableWidgetItem(str(frame))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, item)

            # X coordinate
            item = QTableWidgetItem(f"{x:.2f}")
            item.setData(Qt.ItemDataRole.UserRole, x)  # Store exact value
            self.table.setItem(i, 2, item)

            # Y coordinate
            item = QTableWidgetItem(f"{y:.2f}")
            item.setData(Qt.ItemDataRole.UserRole, y)  # Store exact value
            self.table.setItem(i, 3, item)

            # Status
            status_text = self._status_to_text(status)
            item = QTableWidgetItem(status_text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, item)

        self._updating = False

    def set_selected_indices(self, indices: list[int]) -> None:
        """Update the selection to match the given indices.

        Args:
            indices: List of row indices to select
        """
        if self._updating:
            return

        self._updating = True

        # Clear current selection
        self.table.clearSelection()

        # Clear all selection indicators
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setText("")

        # Select specified rows and update indicators
        for index in indices:
            if 0 <= index < self.table.rowCount():
                self.table.selectRow(index)
                item = self.table.item(index, 0)
                if item:
                    item.setText("●")

        self._updating = False

    def _on_selection_changed(self) -> None:
        """Handle table selection changes."""
        if self._updating:
            return

        selected_indices: list[int] = []
        for item in self.table.selectedItems():
            row = item.row()
            if row not in selected_indices:
                selected_indices.append(row)

        # Update selection indicators
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setText("●" if row in selected_indices else "")

        self.point_selected.emit(sorted(selected_indices))

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle item editing."""
        if self._updating:
            return

        row = item.row()
        col = item.column()

        # Only X and Y columns are editable
        if col == 2:  # X coordinate
            try:
                new_x = float(item.text())
                y = self._curve_data[row][2] if row < len(self._curve_data) else 0.0
                self.point_edited.emit(row, new_x, y)
            except ValueError:
                # Restore original value on invalid input
                original_x = item.data(Qt.ItemDataRole.UserRole)
                item.setText(f"{original_x:.2f}")

        elif col == 3:  # Y coordinate
            try:
                new_y = float(item.text())
                x = self._curve_data[row][1] if row < len(self._curve_data) else 0.0
                self.point_edited.emit(row, x, new_y)
            except ValueError:
                # Restore original value on invalid input
                original_y = item.data(Qt.ItemDataRole.UserRole)
                item.setText(f"{original_y:.2f}")

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu for selected points."""
        selected_rows = []
        for item in self.table.selectedItems():
            row = item.row()
            if row not in selected_rows:
                selected_rows.append(row)

        if not selected_rows:
            return

        menu = QMenu(self)

        # Delete action
        delete_action = QAction("Delete", self)
        _ = delete_action.triggered.connect(lambda: self.point_deleted.emit(selected_rows))
        _ = menu.addAction(delete_action)

        # Status actions
        _ = menu.addSeparator()
        normal_action = QAction("Set Normal", self)
        _ = normal_action.triggered.connect(lambda: self._set_status_for_rows(selected_rows, PointStatus.NORMAL))
        _ = menu.addAction(normal_action)

        interpolated_action = QAction("Set Interpolated", self)
        _ = interpolated_action.triggered.connect(
            lambda: self._set_status_for_rows(selected_rows, PointStatus.INTERPOLATED)
        )
        _ = menu.addAction(interpolated_action)

        keyframe_action = QAction("Set Keyframe", self)
        _ = keyframe_action.triggered.connect(lambda: self._set_status_for_rows(selected_rows, PointStatus.KEYFRAME))
        _ = menu.addAction(keyframe_action)

        _ = menu.exec(self.table.viewport().mapToGlobal(position))

    def _set_status_for_rows(self, rows: list[int], status: PointStatus) -> None:
        """Set status for multiple rows."""
        for row in rows:
            self.point_status_changed.emit(row, status)

    def _status_to_text(self, status: PointStatus) -> str:
        """Convert PointStatus to display text."""
        if status == PointStatus.NORMAL:
            return "Normal"
        elif status == PointStatus.INTERPOLATED:
            return "Interp"
        elif status == PointStatus.KEYFRAME:
            return "Key"
        return "Normal"

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Delete:
            selected_rows = []
            for item in self.table.selectedItems():
                row = item.row()
                if row not in selected_rows:
                    selected_rows.append(row)
            if selected_rows:
                self.point_deleted.emit(selected_rows)
        else:
            super().keyPressEvent(event)
