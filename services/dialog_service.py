#!/usr/bin/env python
"""Simplified dialog service using Qt's built-in dialogs."""

from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

class DialogService:
    """Simple dialog service using Qt's built-in dialogs."""
    
    @staticmethod
    def get_smooth_window_size(parent: QWidget) -> int | None:
        """Get smoothing window size from user."""
        value, ok = QInputDialog.getInt(
            parent, "Smooth Curve", "Window size:", 5, 3, 20
        )
        return value if ok else None
    
    @staticmethod
    def get_filter_params(parent: QWidget) -> tuple[str, int] | None:
        """Get filter type and parameters."""
        filter_types = ["Median", "Butterworth"]
        filter_type, ok = QInputDialog.getItem(
            parent, "Filter Curve", "Filter type:", filter_types, 0, False
        )
        if not ok:
            return None
            
        if filter_type == "Median":
            window, ok = QInputDialog.getInt(
                parent, "Median Filter", "Window size:", 5, 3, 20
            )
            return (filter_type, window) if ok else None
        else:  # Butterworth
            cutoff, ok = QInputDialog.getDouble(
                parent, "Butterworth Filter", "Cutoff frequency:", 0.1, 0.01, 1.0, 2
            )
            return (filter_type, int(cutoff * 100)) if ok else None
    
    @staticmethod
    def get_offset_values(parent: QWidget) -> tuple[float, float] | None:
        """Get X and Y offset values."""
        x_offset, ok = QInputDialog.getDouble(
            parent, "Offset Curve", "X offset:", 0.0, -1000.0, 1000.0, 2
        )
        if not ok:
            return None
            
        y_offset, ok = QInputDialog.getDouble(
            parent, "Offset Curve", "Y offset:", 0.0, -1000.0, 1000.0, 2
        )
        return (x_offset, y_offset) if ok else None
    
    @staticmethod
    def get_fill_gaps_size(parent: QWidget) -> int | None:
        """Get maximum gap size to fill."""
        value, ok = QInputDialog.getInt(
            parent, "Fill Gaps", "Maximum gap size:", 10, 1, 100
        )
        return value if ok else None
    
    @staticmethod
    def show_error(parent: QWidget, message: str) -> None:
        """Show error message."""
        QMessageBox.critical(parent, "Error", message)
    
    @staticmethod
    def show_warning(parent: QWidget, message: str) -> None:
        """Show warning message."""
        QMessageBox.warning(parent, "Warning", message)
    
    @staticmethod
    def show_info(parent: QWidget, message: str) -> None:
        """Show info message."""
        QMessageBox.information(parent, "Information", message)
    
    @staticmethod
    def confirm_action(parent: QWidget, message: str) -> bool:
        """Ask for confirmation."""
        result = QMessageBox.question(parent, "Confirm", message)
        return result == QMessageBox.StandardButton.Yes

# Module-level singleton
_instance = DialogService()

def get_dialog_service() -> DialogService:
    """Get the singleton instance of DialogService."""
    return _instance