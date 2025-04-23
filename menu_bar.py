# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import typing
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QMenuBar
from PySide6.QtGui import QAction
# from keyboard_shortcuts import ShortcutManager
from services.file_service import FileService as FileOperations
from services.image_service import ImageService as ImageOperations
from services.curve_service import CurveService as CurveViewOperations
from services.visualization_service import VisualizationService as VisualizationOperations
from services.dialog_service import DialogService as DialogOperations
from services.history_service import HistoryService as HistoryOperations # Assuming undo/redo will use this
# from curve_operations import CurveOperations # Removed, logic moved
# Removed: from main_window import MainWindow (causes circular import)

if typing.TYPE_CHECKING:
    from main_window import MainWindow
    # Service facades imported above; no redeclaration needed here

class MenuBar(QMenuBar):
    """Menu bar for the 3DE4 Curve Editor application."""
    
    def __init__(self, parent: 'MainWindow'): # MainWindow always provided
        super().__init__(parent)
        self.main_window = parent
        self.setup_menus()
    
    def setup_menus(self):
        """Create all menus and their actions."""
        self.create_file_menu()
        self.create_edit_menu()
        self.create_view_menu()
        self.create_tools_menu()
        self.create_help_menu()
    
    def create_file_menu(self):
        """Create the File menu."""
        file_menu = self.addMenu('&File')
        
        # Load track data
        load_action = QAction('&Open Track...', self)
        # Remove explicit shortcut assignment to avoid conflict
        # load_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('open_file')))
        load_action.triggered.connect(lambda: FileOperations.load_track_data(self.main_window))
        file_menu.addAction(load_action)
        
        # Add track data
        add_action = QAction('&Add Track...', self)
        add_action.triggered.connect(lambda: FileOperations.add_track_data(self.main_window))
        file_menu.addAction(add_action)
        
        # Save track data
        save_action = QAction('&Save Track...', self)
        # Remove explicit shortcut assignment to avoid conflict
        # save_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('save_file')))
        save_action.triggered.connect(lambda: FileOperations.save_track_data(self.main_window))
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # Export to CSV
        export_action = QAction('&Export to CSV...', self)
        # Remove explicit shortcut assignment to avoid conflict and for consistency with other edits
        # export_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('export_csv')))
        # Use static method from FileOperations class
        export_action.triggered.connect(lambda: FileOperations.export_to_csv(self.main_window))
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction('E&xit', self)
        # exit_action.setShortcut(QKeySequence('Alt+F4')) # Handled by OS/Window Manager
        exit_action.triggered.connect(lambda: self.main_window.close() if self.main_window else None)
        file_menu.addAction(exit_action)
    
    def create_edit_menu(self):
        """Create the Edit menu."""
        edit_menu = self.addMenu('&Edit')
        
        # Undo/Redo
        undo_action = QAction('&Undo', self)
        # Remove explicit shortcut assignment to avoid conflict
        # undo_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('undo')))
        # undo_action.triggered.connect(lambda: CurveOperations.undo(self.main_window)) # Original call removed
        undo_action.triggered.connect(lambda: HistoryOperations.undo_action(self.main_window)) # Corrected method name
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('&Redo', self)
        # Remove explicit shortcut assignment to avoid conflict
        # redo_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('redo')))
        # redo_action.triggered.connect(lambda: CurveOperations.redo(self.main_window)) # Original call removed
        redo_action.triggered.connect(lambda: HistoryOperations.redo_action(self.main_window)) # Corrected method name
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        # Selection
        select_all_action = QAction('Select &All', self)
        # Remove explicit shortcut assignment to avoid conflict
        # select_all_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('select_all')))
        select_all_action.triggered.connect(lambda: CurveViewOperations.select_all_points(self.main_window.curve_view, self.main_window))
        edit_menu.addAction(select_all_action)
        
        deselect_all_action = QAction('&Deselect All', self)
        # Remove explicit shortcut assignment to avoid conflict
        # deselect_all_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('deselect_all')))
        deselect_all_action.triggered.connect(lambda: CurveViewOperations.clear_selection(self.main_window.curve_view, self.main_window)) # Use correct method name
        edit_menu.addAction(deselect_all_action)
        
        edit_menu.addSeparator()
        
        # Delete
        delete_action = QAction('&Delete Selected', self)
        # Explicitly set the shortcut to "Delete" to avoid ambiguity with "Del"
        # delete_action.setShortcut(QKeySequence("Delete")) # Removed shortcut to resolve ambiguity
        # delete_action.setShortcutContext(Qt.ApplicationShortcut) # Removed shortcut context
        delete_action.triggered.connect(lambda: CurveViewOperations.delete_selected_points(self.main_window.curve_view, self.main_window))
        edit_menu.addAction(delete_action)
    
    def create_view_menu(self):
        """Create the View menu."""
        view_menu = self.addMenu('&View')
        
        # Reset view
        reset_action = QAction('&Reset View', self)
        # reset_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('reset_view'))) # Handled by ShortcutManager
        reset_action.triggered.connect(lambda: CurveViewOperations.reset_view(self.main_window))
        view_menu.addAction(reset_action)
        
        view_menu.addSeparator()
        
        # Toggle options
        grid_action = QAction('Show &Grid', self)
        # Remove the explicit shortcut assignment to avoid conflict with ShortcutManager
        # grid_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_grid')))
        grid_action.setCheckable(True)
        grid_action.toggled.connect(self._handle_grid_toggled)
        view_menu.addAction(grid_action)
        
        velocity_action = QAction('Show &Velocity Vectors', self)
        # Remove explicit shortcut assignment to avoid conflict
        # velocity_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_velocity')))
        velocity_action.setCheckable(True)
        velocity_action.toggled.connect(self._handle_velocity_toggled)
        view_menu.addAction(velocity_action)
        
        frame_numbers_action = QAction('Show Frame &Numbers', self)
        # Remove explicit shortcut assignment to avoid conflict
        # frame_numbers_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_frame_numbers')))
        frame_numbers_action.setCheckable(True)
        frame_numbers_action.toggled.connect(self._handle_frame_numbers_toggled)
        view_menu.addAction(frame_numbers_action)
        
        # Background
        background_action = QAction('Toggle &Background', self)
        # Remove explicit shortcut assignment to avoid conflict
        # background_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_background')))
        background_action.setCheckable(True)
        background_action.toggled.connect(self._handle_background_toggled)
        view_menu.addAction(background_action)
        
        # Auto-center on frame change
        self.auto_center_action = QAction('Auto-Center on Frame Change', self)
        self.auto_center_action.setCheckable(True)
        self.auto_center_action.toggled.connect(self._handle_auto_center_toggled)
        view_menu.addAction(self.auto_center_action)

        
        view_menu.addSeparator()
        
        # Background image
        load_images_action = QAction('Load &Image Sequence...', self)
        # Remove explicit shortcut assignment to avoid conflict
        # load_images_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('load_images')))
        # Use static method from ImageOperations class
        load_images_action.triggered.connect(lambda: ImageOperations.load_image_sequence(self.main_window))
        view_menu.addAction(load_images_action)
    
    def create_tools_menu(self):
        """Create the Tools menu."""
        tools_menu = self.addMenu('&Tools')
        
        # Curve operations
        smooth_action = QAction('&Smooth Selected...', self)
        # Remove explicit shortcut assignment to avoid conflict
        # smooth_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('smooth_selected')))
        smooth_action.triggered.connect(self.main_window.show_smooth_dialog) # Connect to MainWindow method
        tools_menu.addAction(smooth_action)
        
        filter_action = QAction('&Filter Selected...', self)
        # Remove explicit shortcut assignment to avoid conflict
        # filter_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('filter_selected')))
        filter_action.triggered.connect(lambda: DialogOperations.show_filter_dialog(self.main_window))
        tools_menu.addAction(filter_action)
        
        fill_gaps_action = QAction('Fill &Gaps...', self)
        # Remove explicit shortcut assignment to avoid conflict
        # fill_gaps_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('fill_gaps')))
        fill_gaps_action.triggered.connect(lambda: DialogOperations.show_fill_gaps_dialog(self.main_window))
        tools_menu.addAction(fill_gaps_action)
        
        extrapolate_action = QAction('&Extrapolate...', self)
        # Remove explicit shortcut assignment to avoid conflict
        # extrapolate_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('extrapolate')))
        extrapolate_action.triggered.connect(lambda: DialogOperations.show_extrapolate_dialog(self.main_window))
        tools_menu.addAction(extrapolate_action)
        
        tools_menu.addSeparator()
        
        # Analysis
        detect_problems_action = QAction('&Detect Problems', self)
        # detect_problems_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('detect_problems'))) # Handled by ShortcutManager
        # detect_problems_action.triggered.connect(lambda: DialogOperations.show_problem_detection_dialog(self.main_window, CurveOperations.detect_problems(self.main_window))) # TODO: Move detect_problems logic
        # Temporarily disable until detect_problems is refactored
        detect_problems_action.setEnabled(False)
        detect_problems_action.setToolTip("Problem detection temporarily disabled during refactoring.")
        tools_menu.addAction(detect_problems_action)
    
    def create_help_menu(self):
        """Create the Help menu."""
        help_menu = self.addMenu('&Help')
        
        # Keyboard shortcuts
        shortcuts_action = QAction('&Keyboard Shortcuts', self)
        shortcuts_action.triggered.connect(lambda: DialogOperations.show_shortcuts_dialog(self.main_window))
        help_menu.addAction(shortcuts_action)

    def _handle_auto_center_toggled(self, enabled: bool) -> None:
        """Handle auto-center toggled signal."""
        if self.main_window:
            self.main_window.set_centering_enabled(enabled)

    def _handle_grid_toggled(self, enabled: bool) -> None:
        """Handle grid toggled signal."""
        if self.main_window:
            VisualizationOperations.toggle_grid(self.main_window, enabled)

    def _handle_velocity_toggled(self, enabled: bool) -> None:
        """Handle velocity toggled signal."""
        if self.main_window:
            VisualizationOperations.toggle_velocity_vectors(self.main_window, enabled)

    def _handle_frame_numbers_toggled(self, enabled: bool) -> None:
        """Handle frame numbers toggled signal."""
        if self.main_window:
            VisualizationOperations.toggle_all_frame_numbers(self.main_window, enabled)

    def _handle_background_toggled(self, enabled: bool) -> None:
        """Handle background toggled signal."""
        if self.main_window:
            ImageOperations.toggle_background(self.main_window, enabled)