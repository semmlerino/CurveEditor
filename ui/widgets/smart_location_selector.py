#!/usr/bin/env python
"""
Smart Location Selector Widget for CurveEditor.

Provides an intelligent location selector that combines recent directories,
favorites, and quick access locations with path completion and project context.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QDir, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFileDialog,
    QFileSystemModel,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)

from core.logger_utils import get_logger
from core.user_preferences import UserPreferences

if TYPE_CHECKING:
    from ui.state_manager import StateManager

logger = get_logger("smart_location_selector")


class SmartLocationSelector(QWidget):
    """
    Smart location selector combining recent directories, favorites, and quick access.
    
    Features:
    - Dropdown with recent directories for current project context
    - Path completion for typed paths
    - Quick access to common locations (Desktop, Documents, etc.)
    - Browse button for fallback directory picker
    - Project context awareness
    """
    
    # Signals
    location_selected = Signal(str)  # Emitted when user selects a location
    location_changed = Signal(str)   # Emitted when location changes (including typing)
    
    def __init__(self, parent: QWidget | None = None, state_manager: "StateManager | None" = None):
        """
        Initialize the smart location selector.
        
        Args:
            parent: Parent widget
            state_manager: State manager for accessing preferences and recent directories
        """
        super().__init__(parent)
        self.state_manager = state_manager
        self._current_location: str = ""
        
        self._setup_ui()
        self._setup_completion()
        self._connect_signals()
        self._populate_locations()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Location combo box (editable)
        self.location_combo = QComboBox()
        self.location_combo.setEditable(True)
        self.location_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.location_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.location_combo.setMinimumWidth(300)
        
        # Set placeholder text
        if self.location_combo.lineEdit():
            self.location_combo.lineEdit().setPlaceholderText("Enter or select directory path...")
        
        # Tooltips
        self.location_combo.setToolTip(
            "Select from recent directories or type a path.\n"
            "Use Tab for path completion."
        )
        
        layout.addWidget(self.location_combo, stretch=1)
        
        # Quick access button
        self.quick_access_button = QToolButton()
        self.quick_access_button.setText("⚡")
        self.quick_access_button.setToolTip("Quick access to common locations")
        self.quick_access_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.quick_access_button.setFixedSize(32, 32)
        
        layout.addWidget(self.quick_access_button)
        
        # Browse button
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setToolTip("Browse for directory")
        self.browse_button.setMaximumWidth(80)
        
        layout.addWidget(self.browse_button)
        
        # Set up quick access menu
        self._setup_quick_access_menu()
    
    def _setup_completion(self) -> None:
        """Set up path completion for the combo box."""
        # Create directory model for completion
        self.dir_model = QFileSystemModel()
        self.dir_model.setRootPath("")
        self.dir_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        
        # Create completer
        self.completer = QCompleter()
        self.completer.setModel(self.dir_model)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        
        # Set completer on line edit
        if self.location_combo.lineEdit():
            self.location_combo.lineEdit().setCompleter(self.completer)
    
    def _setup_quick_access_menu(self) -> None:
        """Set up the quick access menu with common locations."""
        menu = QMenu(self)
        
        # Common locations
        locations = [
            ("🏠 Home", str(Path.home())),
            ("📄 Documents", str(Path.home() / "Documents")),
            ("🖥️ Desktop", str(Path.home() / "Desktop")),
            ("📥 Downloads", str(Path.home() / "Downloads")),
        ]
        
        # Add Pictures and Videos if they exist
        pictures_path = Path.home() / "Pictures"
        if pictures_path.exists():
            locations.append(("🖼️ Pictures", str(pictures_path)))
        
        videos_path = Path.home() / "Videos"
        if videos_path.exists():
            locations.append(("🎬 Videos", str(videos_path)))
        
        # Add system-specific locations
        if os.name == 'nt':  # Windows
            # Add common Windows locations
            if Path("C:/").exists():
                locations.append(("💾 C: Drive", "C:/"))
            if Path("D:/").exists():
                locations.append(("💾 D: Drive", "D:/"))
        else:  # Unix-like
            locations.extend([
                ("📁 /tmp", "/tmp"),
                ("📁 /usr/local", "/usr/local"),
            ])
        
        # Create menu actions
        for name, path in locations:
            if Path(path).exists():
                action = menu.addAction(name)
                action.triggered.connect(lambda checked, p=path: self._select_location(p))
        
        # Add separator and recent projects if available
        if self.state_manager:
            preferences = self.state_manager.get_user_preferences()
            if preferences.recent_directories:
                menu.addSeparator()
                
                # Add recent project contexts
                contexts = set()
                for context_dirs in preferences.recent_directories.values():
                    if context_dirs:
                        contexts.add(context_dirs[0])  # Most recent from each context
                
                if contexts:
                    recent_menu = menu.addMenu("📋 Recent Projects")
                    for context_path in sorted(contexts):
                        if Path(context_path).exists():
                            action = recent_menu.addAction(Path(context_path).name)
                            action.triggered.connect(lambda checked, p=context_path: self._select_location(p))
        
        self.quick_access_button.setMenu(menu)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Combo box signals
        self.location_combo.currentTextChanged.connect(self._on_location_changed)
        self.location_combo.activated.connect(self._on_location_activated)
        
        # Browse button
        self.browse_button.clicked.connect(self._browse_for_directory)
        
        # Line edit signals for immediate feedback
        if self.location_combo.lineEdit():
            self.location_combo.lineEdit().textChanged.connect(self._on_text_changed)
            self.location_combo.lineEdit().returnPressed.connect(self._on_return_pressed)
    
    def _populate_locations(self) -> None:
        """Populate the combo box with recent directories."""
        self.location_combo.clear()
        
        if not self.state_manager:
            return
        
        # Get recent directories for current project context
        recent_dirs = self.state_manager.get_recent_directories_for_project()
        
        # Add recent directories
        for directory in recent_dirs:
            if Path(directory).exists():
                self.location_combo.addItem(self._format_directory_display(directory), directory)
        
        # If no recent directories, add some sensible defaults
        if not recent_dirs:
            default_locations = [
                str(Path.home() / "Documents"),
                str(Path.home() / "Desktop"),
                str(Path.home()),
            ]
            
            for location in default_locations:
                if Path(location).exists():
                    self.location_combo.addItem(self._format_directory_display(location), location)
    
    def _format_directory_display(self, path: str) -> str:
        """
        Format directory path for display in combo box.
        
        Args:
            path: Full directory path
            
        Returns:
            Formatted display string
        """
        path_obj = Path(path)
        
        # Show relative to home if under home directory
        try:
            relative_to_home = path_obj.relative_to(Path.home())
            return f"~/{relative_to_home}"
        except ValueError:
            # Not under home directory, show full path but truncate if too long
            if len(path) > 60:
                return f"...{path[-57:]}"
            return path
    
    def _select_location(self, path: str) -> None:
        """
        Select a location programmatically.
        
        Args:
            path: Directory path to select
        """
        if Path(path).exists():
            self.set_location(path)
            self.location_selected.emit(path)
        else:
            logger.warning(f"Selected location does not exist: {path}")
    
    def _on_location_changed(self, text: str) -> None:
        """Handle combo box text change."""
        self._current_location = text
        self.location_changed.emit(text)
    
    def _on_location_activated(self, index: int) -> None:
        """Handle combo box item activation."""
        if index >= 0:
            # Get the actual path from item data
            path = self.location_combo.itemData(index)
            if path and Path(path).exists():
                self._current_location = path
                self.location_selected.emit(path)
    
    def _on_text_changed(self, text: str) -> None:
        """Handle line edit text change for real-time validation."""
        # Provide visual feedback for valid/invalid paths
        if self.location_combo.lineEdit():
            line_edit = self.location_combo.lineEdit()
            
            if text and Path(text).exists() and Path(text).is_dir():
                # Valid directory - normal styling
                line_edit.setStyleSheet("")
            elif text:
                # Invalid path - subtle red tint
                line_edit.setStyleSheet("QLineEdit { background-color: #ffe6e6; }")
            else:
                # Empty - normal styling
                line_edit.setStyleSheet("")
    
    def _on_return_pressed(self) -> None:
        """Handle return key press in line edit."""
        current_text = self.location_combo.currentText()
        if current_text and Path(current_text).exists() and Path(current_text).is_dir():
            self._current_location = current_text
            self.location_selected.emit(current_text)
    
    def _browse_for_directory(self) -> None:
        """Open directory browser dialog."""
        # Start from current location or home
        start_dir = self._current_location or str(Path.home())
        if not Path(start_dir).exists():
            start_dir = str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if directory:
            self.set_location(directory)
            self.location_selected.emit(directory)
    
    def set_location(self, path: str) -> None:
        """
        Set the current location.
        
        Args:
            path: Directory path to set
        """
        if Path(path).exists() and Path(path).is_dir():
            self._current_location = path
            
            # Update combo box
            display_text = self._format_directory_display(path)
            
            # Check if already in combo box
            index = self.location_combo.findData(path)
            if index >= 0:
                self.location_combo.setCurrentIndex(index)
            else:
                # Set text directly
                self.location_combo.setCurrentText(path)
            
            # Add to recent directories if we have state manager
            if self.state_manager:
                self.state_manager.add_recent_directory_for_project(path)
                # Refresh the combo box to show updated recent list
                self._populate_locations()
            
            logger.debug(f"Location set to: {path}")
        else:
            logger.warning(f"Invalid location: {path}")
    
    def get_location(self) -> str:
        """
        Get the current location.
        
        Returns:
            Current directory path
        """
        return self._current_location
    
    def refresh_locations(self) -> None:
        """Refresh the list of recent locations."""
        current_location = self._current_location
        self._populate_locations()
        
        # Restore current location if it was set
        if current_location:
            self.set_location(current_location)
    
    def set_project_context(self, project_name: str | None) -> None:
        """
        Set the project context and refresh locations.
        
        Args:
            project_name: Name of the current project
        """
        if self.state_manager:
            self.state_manager.set_project_context(project_name)
            self.refresh_locations()
            self._setup_quick_access_menu()  # Refresh quick access menu