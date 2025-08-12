#!/usr/bin/env python
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false

# Standard library imports

# Third-party imports
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar

from core.signal_manager import SignalManager

# Local imports - DI pattern
from services.service_registry_v2 import get_service
from services.service_protocols import (
    CurveServiceProtocol,
    DialogServiceProtocol,
    FileServiceProtocol,
    HistoryServiceProtocol,
    ImageServiceProtocol,
)

class MenuBar(QMenuBar):
    """Menu bar for the 3DE4 Curve Editor application."""

    def __init__(self, parent: "MainWindow"):  # MainWindow always provided
        super().__init__(parent)
        self.main_window = parent
        # Initialize signal manager for proper cleanup
        self.signal_manager = SignalManager(self)
        # Initialize actions that will be created in setup_menus
        self.auto_center_action: QAction | None = None

        # Initialize services through DI
        self._init_services()

        self.setup_menus()

    def _init_services(self):
        """Initialize services through dependency injection."""
        # Now using ServiceRegistryV2 consistently - should eliminate deadlock
        self.file_service = get_service(FileServiceProtocol)
        self.curve_service = get_service(CurveServiceProtocol)
        self.dialog_service = get_service(DialogServiceProtocol)
        self.history_service = get_service(HistoryServiceProtocol)
        self.image_service = get_service(ImageServiceProtocol)

    def setup_menus(self):
        """Create all menus and their actions."""
        self.create_file_menu()
        self.create_edit_menu()
        self.create_view_menu()
        self.create_tools_menu()
        self.create_help_menu()

    def create_file_menu(self):
        """Create the File menu."""
        file_menu = self.addMenu("&File")

        # Load track data
        load_action = QAction("&Open Track...", self)
        # Remove explicit shortcut assignment to avoid conflict
        # load_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('open_file')))
        self.signal_manager.connect(
            load_action.triggered,
            self._handle_load_track,
            "load_action.triggered"
        )
        file_menu.addAction(load_action)

        # Add track data
        add_action = QAction("&Add Track...", self)
        self.signal_manager.connect(
            add_action.triggered,
            self._handle_add_track,
            "add_action.triggered"
        )
        file_menu.addAction(add_action)

        # Save track data
        save_action = QAction("&Save Track...", self)
        # Remove explicit shortcut assignment to avoid conflict
        # save_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('save_file')))
        self.signal_manager.connect(
            save_action.triggered,
            self._handle_save_track,
            "save_action.triggered"
        )
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # Export to CSV
        export_action = QAction("&Export to CSV...", self)
        # Remove explicit shortcut assignment to avoid conflict and for consistency with other edits
        # export_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('export_csv')))
        # Use static method from FileOperations class
        self.signal_manager.connect(
            export_action.triggered,
            self._handle_export_csv,
            "export_action.triggered"
        )
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction("E&xit", self)
        # exit_action.setShortcut(QKeySequence('Alt+F4')) # Handled by OS/Window Manager
        self.signal_manager.connect(
            exit_action.triggered,
            self._handle_exit,
            "exit_action.triggered"
        )
        file_menu.addAction(exit_action)

    def create_edit_menu(self):
        """Create the Edit menu."""
        edit_menu = self.addMenu("&Edit")

        # Undo/Redo
        undo_action = QAction("&Undo", self)
        # Remove explicit shortcut assignment to avoid conflict
        # undo_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('undo')))
        # undo_action.triggered.connect(lambda: CurveOperations.undo(self.main_window)) # Original call removed
        self.signal_manager.connect(
            undo_action.triggered,
            self._handle_undo,
            "undo_action.triggered"
        )
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        # Remove explicit shortcut assignment to avoid conflict
        # redo_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('redo')))
        # redo_action.triggered.connect(lambda: CurveOperations.redo(self.main_window)) # Original call removed
        self.signal_manager.connect(
            redo_action.triggered,
            self._handle_redo,
            "redo_action.triggered"
        )
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        # Selection
        select_all_action = QAction("Select &All", self)
        # Remove explicit shortcut assignment to avoid conflict
        # select_all_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('select_all')))
        self.signal_manager.connect(
            select_all_action.triggered,
            self._handle_select_all,
            "select_all_action.triggered"
        )
        edit_menu.addAction(select_all_action)

        deselect_all_action = QAction("&Deselect All", self)
        # Remove explicit shortcut assignment to avoid conflict
        # deselect_all_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('deselect_all')))
        self.signal_manager.connect(
            deselect_all_action.triggered,
            self._handle_deselect_all,
            "deselect_all_action.triggered"
        )
        edit_menu.addAction(deselect_all_action)

        edit_menu.addSeparator()

        # Delete
        delete_action = QAction("&Delete Selected", self)
        # Explicitly set the shortcut to "Delete" to avoid ambiguity with "Del"
        # delete_action.setShortcut(QKeySequence("Delete")) # Removed shortcut to resolve ambiguity
        # delete_action.setShortcutContext(Qt.ApplicationShortcut) # Removed shortcut context
        self.signal_manager.connect(
            delete_action.triggered,
            self._handle_delete_selected,
            "delete_action.triggered"
        )
        edit_menu.addAction(delete_action)

    def create_view_menu(self):
        """Create the View menu."""
        view_menu = self.addMenu("&View")

        # Reset view
        reset_action = QAction("&Reset View", self)
        # reset_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('reset_view'))) # Handled by ShortcutManager
        self.signal_manager.connect(
            reset_action.triggered,
            self._handle_reset_view,
            "reset_action.triggered"
        )
        view_menu.addAction(reset_action)

        view_menu.addSeparator()

        # Toggle options
        grid_action = QAction("Show &Grid", self)
        # Remove the explicit shortcut assignment to avoid conflict with ShortcutManager
        # grid_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_grid')))
        grid_action.setCheckable(True)
        self.signal_manager.connect(
            grid_action.toggled,
            self._handle_grid_toggled,
            "grid_action.toggled"
        )
        view_menu.addAction(grid_action)

        velocity_action = QAction("Show &Velocity Vectors", self)
        # Remove explicit shortcut assignment to avoid conflict
        # velocity_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_velocity')))
        velocity_action.setCheckable(True)
        self.signal_manager.connect(
            velocity_action.toggled,
            self._handle_velocity_toggled,
            "velocity_action.toggled"
        )
        view_menu.addAction(velocity_action)

        frame_numbers_action = QAction("Show Frame &Numbers", self)
        # Remove explicit shortcut assignment to avoid conflict
        # frame_numbers_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_frame_numbers')))
        frame_numbers_action.setCheckable(True)
        self.signal_manager.connect(
            frame_numbers_action.toggled,
            self._handle_frame_numbers_toggled,
            "frame_numbers_action.toggled"
        )
        view_menu.addAction(frame_numbers_action)

        # Background
        background_action = QAction("Toggle &Background", self)
        # Remove explicit shortcut assignment to avoid conflict
        # background_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('toggle_background')))
        background_action.setCheckable(True)
        self.signal_manager.connect(
            background_action.toggled,
            self._handle_background_toggled,
            "background_action.toggled"
        )
        view_menu.addAction(background_action)

        # Auto-center on frame change
        self.auto_center_action = QAction("Auto-Center on Frame Change", self)
        self.auto_center_action.setCheckable(True)
        self.signal_manager.connect(
            self.auto_center_action.toggled,
            self._handle_auto_center_toggled,
            "auto_center_action.toggled"
        )
        view_menu.addAction(self.auto_center_action)

        view_menu.addSeparator()

        # Background image
        load_images_action = QAction("Load &Image Sequence...", self)
        # Remove explicit shortcut assignment to avoid conflict
        # load_images_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('load_images')))
        # Use static method from ImageOperations class
        self.signal_manager.connect(
            load_images_action.triggered,
            self._handle_load_images,
            "load_images_action.triggered"
        )
        view_menu.addAction(load_images_action)

    def create_tools_menu(self):
        """Create the Tools menu."""
        tools_menu = self.addMenu("&Tools")

        # Curve operations
        smooth_action = QAction("&Smooth Selected...", self)
        # Remove explicit shortcut assignment to avoid conflict
        # smooth_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('smooth_selected')))
        self.signal_manager.connect(
            smooth_action.triggered,
            self._handle_smooth_selected,
            "smooth_action.triggered"
        )
        tools_menu.addAction(smooth_action)

        filter_action = QAction("&Filter Selected...", self)
        # Remove explicit shortcut assignment to avoid conflict
        # filter_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('filter_selected')))
        self.signal_manager.connect(
            filter_action.triggered,
            self._handle_filter_selected,
            "filter_action.triggered"
        )
        tools_menu.addAction(filter_action)

        fill_gaps_action = QAction("Fill &Gaps...", self)
        # Remove explicit shortcut assignment to avoid conflict
        # fill_gaps_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('fill_gaps')))
        self.signal_manager.connect(
            fill_gaps_action.triggered,
            self._handle_fill_gaps,
            "fill_gaps_action.triggered"
        )
        tools_menu.addAction(fill_gaps_action)

        extrapolate_action = QAction("&Extrapolate...", self)
        # Remove explicit shortcut assignment to avoid conflict
        # extrapolate_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('extrapolate')))
        self.signal_manager.connect(
            extrapolate_action.triggered,
            self._handle_extrapolate,
            "extrapolate_action.triggered"
        )
        tools_menu.addAction(extrapolate_action)

        tools_menu.addSeparator()

        # Analysis
        detect_problems_action = QAction("&Detect Problems", self)
        # detect_problems_action.setShortcut(QKeySequence(ShortcutManager.get_shortcut_key('detect_problems'))) # Handled by ShortcutManager
        # detect_problems_action.triggered.connect(lambda: DialogService.show_problem_detection_dialog(cast(MainWindowProtocol, self.main_window)))
        # Temporarily disable until detect_problems is refactored
        detect_problems_action.setEnabled(False)
        detect_problems_action.setToolTip("Problem detection temporarily disabled during refactoring.")
        tools_menu.addAction(detect_problems_action)

    def create_help_menu(self):
        """Create the Help menu."""
        help_menu = self.addMenu("&Help")

        # Keyboard shortcuts
        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        self.signal_manager.connect(
            shortcuts_action.triggered,
            self._handle_show_shortcuts,
            "shortcuts_action.triggered"
        )
        help_menu.addAction(shortcuts_action)

    def _handle_auto_center_toggled(self, enabled: bool) -> None:
        """Handle auto-center toggled signal."""
        if self.main_window:
            self.main_window.set_centering_enabled(enabled)

    def _handle_grid_toggled(self, enabled: bool) -> None:
        """Handle grid toggled signal."""
        if self.main_window:
            pass  # TODO: implement grid toggle
            
    def _handle_velocity_toggled(self, enabled: bool) -> None:
        """Handle velocity toggled signal."""
        if self.main_window:
            pass  # TODO: implement velocity toggle

    def _handle_frame_numbers_toggled(self, enabled: bool) -> None:
        """Handle frame numbers toggled signal."""
        if self.main_window:
            pass  # TODO: implement frame numbers toggle

    def _handle_background_toggled(self, enabled: bool) -> None:
        """Handle background toggled signal."""
        if self.main_window:
            # Note: toggle_background method may need to be added to ImageServiceProtocol
            # For now, using legacy approach since it's a toggle operation
            ImageOperations.toggle_background(cast(MainWindowProtocol, cast(object, self.main_window)))

    # File menu handlers
    def _handle_load_track(self) -> None:
        """Handle load track action."""
        self.file_service.load_track_data(cast(MainWindowProtocol, cast(object, self.main_window)))

    def _handle_add_track(self) -> None:
        """Handle add track action."""
        self.file_service.add_track_data(cast(MainWindowProtocol, cast(object, self.main_window)))

    def _handle_save_track(self) -> None:
        """Handle save track action."""
        self.file_service.save_track_data(cast(MainWindowProtocol, cast(object, self.main_window)))

    def _handle_export_csv(self) -> None:
        """Handle export to CSV action."""
        self.file_service.export_to_csv(cast(MainWindowProtocol, cast(object, self.main_window)))

    def _handle_exit(self) -> None:
        """Handle exit action."""
        if self.main_window:
            self.main_window.close()

    # Edit menu handlers
    def _handle_undo(self) -> None:
        """Handle undo action."""
        self.history_service.undo(cast(HistoryContainerProtocol, cast(object, self.main_window)))

    def _handle_redo(self) -> None:
        """Handle redo action."""
        self.history_service.redo(cast(HistoryContainerProtocol, cast(object, self.main_window)))

    def _handle_select_all(self) -> None:
        """Handle select all action."""
        self.curve_service.select_all_points(self.main_window.curve_view, self.main_window)

    def _handle_deselect_all(self) -> None:
        """Handle deselect all action."""
        self.curve_service.clear_selection(self.main_window.curve_view, self.main_window)

    def _handle_delete_selected(self) -> None:
        """Handle delete selected action."""
        self.curve_service.delete_selected_points(self.main_window.curve_view, self.main_window)

    # View menu handlers
    def _handle_reset_view(self) -> None:
        """Handle reset view action."""
        self.curve_service.reset_view(cast(CurveViewProtocol, self.main_window.curve_view))

    def _handle_load_images(self) -> None:
        """Handle load image sequence action."""
        self.image_service.load_image_sequence(cast(MainWindowProtocol, cast(object, self.main_window)))

    # Tools menu handlers
    def _handle_smooth_selected(self) -> None:
        """Handle smooth selected action."""
        self.main_window.apply_smooth_operation()

    def _handle_filter_selected(self) -> None:
        """Handle filter selected action."""
        self.dialog_service.show_filter_dialog(self, [], [])

    def _handle_fill_gaps(self) -> None:
        """Handle fill gaps action."""
        self.dialog_service.show_fill_gaps_dialog(self, [], [])

    def _handle_extrapolate(self) -> None:
        """Handle extrapolate action."""
        self.dialog_service.show_extrapolate_dialog(self, [])

    # Help menu handlers
    def _handle_show_shortcuts(self) -> None:
        """Handle show keyboard shortcuts action."""
        self.dialog_service.show_shortcuts_dialog(cast(MainWindowProtocol, cast(object, self.main_window)))

    def __del__(self) -> None:
        """Destructor to ensure all signals are disconnected."""
        if hasattr(self, "signal_manager"):
            self.signal_manager.disconnect_all()
