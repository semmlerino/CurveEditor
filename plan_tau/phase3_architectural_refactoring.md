## 🏗️ **PHASE 3: ARCHITECTURAL REFACTORING (WEEKS 3-4)**

**Objective:** Split god objects, remove technical debt
**Total Effort:** 10-12 days
**Priority:** HIGH - Architecture quality

---

### **Task 3.1: Split MultiPointTrackingController**
**Time:** 2-3 days
**Impact:** 1,165 lines → 3 controllers (~400 lines each)

#### **Current Issues:**
- Handles 7 different concerns in one 1,165-line class
- 30 methods with unclear responsibilities
- Difficult to test (mock 20+ dependencies)

#### **New Architecture:**

```
MultiPointTrackingController (1,165 lines)
    ↓ SPLIT INTO ↓
├── TrackingDataController (~400 lines)
│   ├── load_single_point_data()
│   ├── load_multi_point_data()
│   ├── _parse_tracking_file()
│   └── _validate_tracking_data()
│
├── TrackingDisplayController (~400 lines)
│   ├── update_display_preserve_selection()
│   ├── update_display_with_selection()
│   ├── update_display_reset_selection()
│   ├── _prepare_display_data()
│   └── _update_timeline_for_tracking()
│
└── TrackingSelectionController (~350 lines)
    ├── sync_panel_to_view()
    ├── sync_view_to_panel()
    ├── handle_panel_selection_changed()
    └── handle_view_selection_changed()
```

#### **Implementation Plan:**

**Step 1: Create new controller files**

**IMPORTANT: Qt @Slot Decorators**

All signal handler methods in new controllers/services should use `@Slot` decorators for:
- 5-10% performance improvement
- Type safety at connection time
- Better Qt tooling support

**Pattern:**
```python
from PySide6.QtCore import QObject, Signal, Slot

class MyController(QObject):
    data_loaded = Signal(str, list)

    @Slot(Path, result=bool)  # ← Add @Slot decorator
    def load_data(self, file_path: Path) -> bool:
        """Load data from file."""
        ...
```

**When to use @Slot:**
- Methods connected to signals
- Methods called across thread boundaries
- Public methods that might be connected later

**Parameters:**
- Specify argument types: `@Slot(str, int)`
- Specify return type: `@Slot(result=bool)`
- No types if method takes no args: `@Slot()`

**Stacking with @safe_slot (Phase 4):**
```python
from PySide6.QtCore import Slot
from ui.qt_utils import safe_slot  # Added in Phase 4

class MyWidget(QWidget):
    @Slot(dict)          # ← Qt performance decorator (outer)
    @safe_slot           # ← Destruction guard (inner)
    def _on_curves_changed(self, curves: dict) -> None:
        """Handle curves changed signal."""
        self.update_display(curves)
```

**Note:** Apply @Slot decorators to ALL public methods in Phase 3 controllers/services (estimated 20+ methods).

---

**IMPORTANT: Protocol Definitions for Type Safety**

CLAUDE.md mandates "Protocol Interfaces: Type-safe duck-typing via protocols". New controllers/services should define and use Protocol interfaces for dependencies.

**Why Protocols:**
- Type-safe duck typing
- Better testability (easy mocking)
- Clear interface contracts
- Loose coupling

**Create: `ui/protocols/controller_protocols.py` (EXPAND EXISTING)**

```python
"""Protocol definitions for controller interfaces."""

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from core.type_aliases import CurveDataList

class MainWindowProtocol(Protocol):
    """Protocol for MainWindow interface used by controllers.

    Defines minimum interface needed by controllers, not full MainWindow API.
    """
    @property
    def curve_widget(self) -> "CurveViewProtocol": ...

    @property
    def state_manager(self) -> "StateManagerProtocol": ...

    @property
    def tracking_panel(self) -> QWidget | None: ...

    def update_status(self, message: str) -> None: ...

class CurveViewProtocol(Protocol):
    """Protocol for CurveViewWidget interface."""
    def update(self) -> None: ...

    def set_curves_data(
        self,
        curves: dict[str, "CurveDataList"],
        metadata: dict,
        active: str | None,
        selected_curves: list[str] | None = None
    ) -> None: ...

    @property
    def pan_offset_y(self) -> float: ...

    @property
    def zoom_level(self) -> float: ...

class StateManagerProtocol(Protocol):
    """Protocol for StateManager interface (UI state only)."""
    @property
    def zoom_level(self) -> float: ...

    @property
    def pan_offset(self) -> tuple[float, float]: ...

    @property
    def current_tool(self) -> str: ...
```

**Usage in Controllers:**

```python
# Instead of:
def __init__(self, main_window: "MainWindow") -> None:
    self.main_window = main_window

# Use Protocol:
from ui.protocols.controller_protocols import MainWindowProtocol

def __init__(self, main_window: MainWindowProtocol) -> None:
    self.main_window = main_window
```

**Benefits:**
- Type checker validates protocol compliance
- Tests can use simple mock objects instead of full MainWindow
- Clear documentation of what each controller needs
- Prevents accidentally using non-public APIs

**File: `ui/controllers/tracking_data_controller.py`**

```python
"""Controller for loading and validating tracking data."""

from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from stores.application_state import get_application_state
from core.type_aliases import CurveDataList

class TrackingDataController(QObject):
    """Handles loading tracking data from files.

    Responsibilities:
        - Load single-point tracking data
        - Load multi-point tracking data
        - Parse and validate tracking files
        - Emit signals when data loaded

    Signals:
        data_loaded: Emitted when tracking data successfully loaded
                     Args: (curve_name, curve_data)
        load_error: Emitted when loading fails
                    Args: (error_message)
    """

    data_loaded = Signal(str, list)  # curve_name, curve_data
    load_error = Signal(str)

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize tracking data controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window
        self._app_state = get_application_state()

    @Slot(Path, result=bool)
    def load_single_point_data(self, file_path: Path) -> bool:
        """Load single tracking point from file.

        Args:
            file_path: Path to tracking data file

        Returns:
            True if loaded successfully
        """
        try:
            # Extract logic from MultiPointTrackingController.load_single_point_tracking_data
            data = self._parse_tracking_file(file_path)
            if not data:
                self.load_error.emit(f"No valid data in {file_path.name}")
                return False

            # Validate data
            if not self._validate_tracking_data(data):
                self.load_error.emit(f"Invalid data format in {file_path.name}")
                return False

            # Store in ApplicationState
            curve_name = file_path.stem
            self._app_state.set_curve_data(curve_name, data)

            # Emit success signal
            self.data_loaded.emit(curve_name, data)
            return True

        except Exception as e:
            self.load_error.emit(f"Error loading {file_path.name}: {e}")
            return False

    def load_multi_point_data(self, tracking_data: dict[str, CurveDataList]) -> bool:
        """Load multiple tracking points.

        Args:
            tracking_data: Dictionary mapping curve names to curve data

        Returns:
            True if loaded successfully
        """
        # Extract logic from MultiPointTrackingController.load_multi_point_tracking_data
        pass

    def _parse_tracking_file(self, file_path: Path) -> CurveDataList:
        """Parse tracking data from file.

        Args:
            file_path: Path to file

        Returns:
            List of curve points
        """
        # Extract parsing logic
        pass

    def _validate_tracking_data(self, data: CurveDataList) -> bool:
        """Validate tracking data format.

        Args:
            data: Curve data to validate

        Returns:
            True if valid
        """
        # Extract validation logic
        pass
```

**File: `ui/controllers/tracking_display_controller.py`**

```python
"""Controller for updating tracking point display."""

from PySide6.QtCore import QObject, Signal
from stores.application_state import get_application_state

class TrackingDisplayController(QObject):
    """Handles visual display of tracking data.

    Responsibilities:
        - Update curve view with tracking data
        - Manage curve visibility
        - Sync timeline with tracking data

    Signals:
        display_updated: Emitted when display refreshed
    """

    display_updated = Signal()

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize tracking display controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window
        self._app_state = get_application_state()

    def update_display_preserve_selection(self) -> None:
        """Update display, preserving current selection."""
        curves, metadata, active = self._prepare_display_data()
        self.main_window.curve_widget.set_curves_data(curves, metadata, active)
        self.display_updated.emit()

    def update_display_with_selection(self, selected: list[str]) -> None:
        """Update display with specific curve selection."""
        curves, metadata, active = self._prepare_display_data()
        self.main_window.curve_widget.set_curves_data(
            curves, metadata, active, selected_curves=selected
        )
        self.display_updated.emit()

    def update_display_reset_selection(self) -> None:
        """Update display, resetting selection to active curve only."""
        curves, metadata, active = self._prepare_display_data()
        selected = [active] if active else []
        self.main_window.curve_widget.set_curves_data(
            curves, metadata, active, selected_curves=selected
        )
        self.display_updated.emit()

    def _prepare_display_data(self) -> tuple[dict, dict, str | None]:
        """Prepare curve data for display (common logic)."""
        # Extract from MultiPointTrackingController.update_curve_display
        pass
```

**File: `ui/controllers/tracking_selection_controller.py`**

```python
"""Controller for synchronizing tracking point selection."""

from PySide6.QtCore import QObject, Signal, Qt
from stores.application_state import get_application_state

class TrackingSelectionController(QObject):
    """Handles selection synchronization between panel and view.

    Responsibilities:
        - Sync panel selection → curve view
        - Sync curve view selection → panel
        - Handle selection change events
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize tracking selection controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window
        self._app_state = get_application_state()
        self._syncing = False  # Prevent circular updates

    def connect_signals(self) -> None:
        """Connect selection synchronization signals."""
        # Panel → View
        if self.main_window.tracking_panel is not None:
            _ = self.main_window.tracking_panel.selection_changed.connect(
                self.handle_panel_selection_changed,
                Qt.QueuedConnection
            )

        # ApplicationState → Both
        _ = self._app_state.selection_state_changed.connect(
            self._on_selection_state_changed,
            Qt.QueuedConnection
        )

    def sync_panel_to_view(self, selected_curve: str) -> None:
        """Update curve view based on panel selection.

        Args:
            selected_curve: Name of curve selected in panel
        """
        if self._syncing:
            return

        self._syncing = True
        try:
            # Update ApplicationState
            self._app_state.set_active_curve(selected_curve)

            # Update curve view will happen via signal
        finally:
            self._syncing = False

    def handle_panel_selection_changed(self, curve_name: str) -> None:
        """Handle selection change in tracking panel.

        Args:
            curve_name: Newly selected curve name
        """
        self.sync_panel_to_view(curve_name)

    def _on_selection_state_changed(self) -> None:
        """Handle selection state change from ApplicationState."""
        if self._syncing:
            return

        # Update panel and view to reflect new selection
        pass
```

**Step 2: Create facade controller**

**File: `ui/controllers/multi_point_tracking_controller.py` (NEW - Facade)**

```python
"""Facade controller for multi-point tracking (delegates to sub-controllers)."""

from PySide6.QtCore import QObject, Signal
from ui.controllers.tracking_data_controller import TrackingDataController
from ui.controllers.tracking_display_controller import TrackingDisplayController
from ui.controllers.tracking_selection_controller import TrackingSelectionController

class MultiPointTrackingController(QObject):
    """Facade for multi-point tracking functionality.

    This is a thin facade that delegates to specialized controllers:
        - TrackingDataController: Loading and parsing
        - TrackingDisplayController: Visual updates
        - TrackingSelectionController: Selection synchronization

    Maintains backward compatibility with existing MainWindow references.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize multi-point tracking controller.

        Args:
            main_window: Reference to main application window
        """
        super().__init__()
        self.main_window = main_window

        # Create sub-controllers
        self.data_controller = TrackingDataController(main_window)
        self.display_controller = TrackingDisplayController(main_window)
        self.selection_controller = TrackingSelectionController(main_window)

        # Connect sub-controller signals
        self._connect_sub_controllers()

    def _connect_sub_controllers(self) -> None:
        """Wire up sub-controllers."""
        # Data loaded → Update display
        _ = self.data_controller.data_loaded.connect(
            lambda: self.display_controller.update_display_reset_selection()
        )

        # Connect selection controller signals
        self.selection_controller.connect_signals()

    # Backward compatibility methods (delegate to sub-controllers)

    def load_single_point_tracking_data(self, file_path) -> bool:
        """Load single point (delegates to data controller)."""
        return self.data_controller.load_single_point_data(file_path)

    def load_multi_point_tracking_data(self, data: dict) -> bool:
        """Load multi-point (delegates to data controller)."""
        return self.data_controller.load_multi_point_data(data)

    def update_curve_display(self, selected: list[str] | None = None) -> None:
        """Update display (delegates to display controller)."""
        if selected is not None:
            self.display_controller.update_display_with_selection(selected)
        else:
            self.display_controller.update_display_preserve_selection()
```

**Step 3: Migration strategy**

1. **Phase 3.1a:** Create new controller files with extracted logic
2. **Phase 3.1b:** Create facade controller for backward compatibility
3. **Phase 3.1c:** Update MainWindow to use facade (no other code changes needed)
4. **Phase 3.1d:** Run tests to verify functionality preserved
5. **Phase 3.1e:** (Optional) Gradually update callers to use sub-controllers directly

#### **Verification Steps:**

```bash
# 1. Verify file structure
ls -la ui/controllers/tracking_*.py
# Should show:
# - tracking_data_controller.py
# - tracking_display_controller.py
# - tracking_selection_controller.py
# - multi_point_tracking_controller.py (facade)

# 2. Count lines per file
wc -l ui/controllers/tracking_*.py
# Each should be ~300-400 lines

# 3. Run comprehensive tracking tests
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v
~/.local/bin/uv run pytest tests/test_insert_track_integration.py -v

# 4. Manual test: Load multi-point tracking file, verify all features work
```

#### **Success Metrics:**
- ✅ 1,165 lines split into 3 controllers (~400 lines each)
- ✅ All tracking tests pass
- ✅ Backward compatibility maintained (facade pattern)
- ✅ Each controller has single responsibility

---

### **Task 3.2: Refactor InteractionService Internals**
**Time:** 3-4 days
**Impact:** 1,480 lines → organized into internal helpers (~300-400 lines each)

**IMPORTANT:** This task maintains the documented 4-service architecture (Data, Interaction, Transform, UI). We refactor InteractionService INTERNALLY using helper classes, NOT by creating new top-level services.

#### **Current Issues:**
- Handles 8 different concerns in one 1,480-line class
- 48 methods mixing mouse events, commands, selection, point manipulation
- 114-line `add_to_history()` method with deep nesting

#### **New Architecture:**

```
InteractionService (1,480 lines, single file)
    ↓ REFACTOR INTERNALLY ↓
InteractionService (~200 lines - coordination)
    └── Uses internal helpers:
        ├── _MouseHandler (~300 lines)
        │   ├── handle_mouse_press()
        │   ├── handle_mouse_move()
        │   ├── handle_mouse_release()
        │   ├── handle_wheel()
        │   └── handle_key_press()
        │
        ├── _SelectionManager (~400 lines)
        │   ├── find_point_at()
        │   ├── select_point()
        │   ├── select_all()
        │   ├── clear_selection()
        │   ├── rubber_band_selection()
        │   └── get_selection_info()
        │
        ├── _CommandHistory (~350 lines)
        │   ├── execute_command()
        │   ├── undo()
        │   ├── redo()
        │   ├── can_undo/can_redo()
        │   └── clear_history()
        │
        └── _PointManipulator (~400 lines)
            ├── move_point()
            ├── delete_points()
            ├── nudge_points()
            ├── toggle_point_status()
            └── validate_point_move()
```

**Why Internal Helpers, Not Separate Services:**
- ✅ Maintains documented 4-service architecture (CLAUDE.md)
- ✅ Single file keeps related functionality together
- ✅ Internal classes (prefixed with `_`) clearly mark implementation details
- ✅ No service getter pollution (still just `get_interaction_service()`)
- ✅ Simpler testing (one service, not five)
- ✅ Follows existing codebase patterns (services are top-level concepts)

#### **Implementation Plan:**

**IMPORTANT:** New code in Tasks 3.1 and 3.2 must use `get_application_state()` directly.
**DO NOT** use StateManager data methods - they are being removed in Task 3.3.

**Step 1: Refactor InteractionService with internal helpers**

**File: `services/interaction_service.py` (REFACTORED - all in one file)**

```python
"""Service for user interactions - refactored with internal helper classes.

This file contains InteractionService with internal helper classes for organization.
All helpers are prefixed with _ to indicate they are internal implementation details.
"""

from PySide6.QtCore import QObject, Signal, QPoint, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from stores.application_state import get_application_state
from core.commands.base_command import BaseCommand
from core.models import CurvePoint, PointStatus

# ============================================================================
# INTERNAL HELPER CLASSES (implementation details, not exported)
# ============================================================================

class _MouseHandler:
    """Internal helper for mouse/keyboard event handling.

    NOT a QObject - lightweight helper class owned by InteractionService.
    """

    def __init__(self, owner: "InteractionService") -> None:
        """Initialize with reference to owner service for signal emission."""
        self._owner = owner
        self._app_state = get_application_state()
        self._drag_start: QPoint | None = None
        self._dragging_curve: str | None = None
        self._dragging_index: int | None = None

    def handle_mouse_press(
        self,
        event: QMouseEvent,
        view: "CurveViewWidget",
        main_window: "MainWindow"
    ) -> bool:
        """Handle mouse press - delegates to selection manager."""
        # Use owner's selection manager (internal coordination)
        result = self._owner._selection.find_point_at(
            view, event.pos().x(), event.pos().y(), mode="active"
        )

        if result:
            curve_name, point_index = result
            # Emit signal via owner (only service has signals)
            self._owner.point_clicked.emit(curve_name, point_index, view, main_window)

            # Track drag
            self._drag_start = event.pos()
            self._dragging_curve = curve_name
            self._dragging_index = point_index
            return True
        return False

    def handle_mouse_move(self, event: QMouseEvent, view: "CurveViewWidget") -> bool:
        """Handle mouse move during drag."""
        if self._drag_start is not None:
            delta = event.pos() - self._drag_start
            self._owner.drag_moved.emit(event.pos(), delta)
            return True
        return False

    def handle_mouse_release(
        self, event: QMouseEvent, view: "CurveViewWidget", main_window: "MainWindow"
    ) -> bool:
        """Handle mouse release - end drag."""
        if self._drag_start is not None:
            total_delta = event.pos() - self._drag_start
            self._owner.drag_finished.emit(event.pos(), total_delta)

            # Reset drag state
            self._drag_start = None
            self._dragging_curve = None
            self._dragging_index = None
            return True
        return False

    # Additional methods: handle_wheel(), handle_key_press(), etc.
    # ... (extract from current InteractionService)


class _SelectionManager:
    """Internal helper for point selection operations.

    NOT a QObject - lightweight helper class.
    """

    def __init__(self, owner: "InteractionService") -> None:
        """Initialize with reference to owner service."""
        self._owner = owner
        self._app_state = get_application_state()

    def find_point_at(
        self,
        view: "CurveViewWidget",
        screen_x: float,
        screen_y: float,
        mode: str = "active"
    ) -> tuple[str, int] | None:
        """Find point at screen coordinates."""
        # Extract from InteractionService.find_point_at
        pass

    def select_point(
        self,
        view: "CurveViewWidget",
        main_window: "MainWindow",
        curve_name: str,
        point_index: int
    ) -> None:
        """Select a single point."""
        self._app_state.set_selection(curve_name, {point_index})
        self._owner.selection_updated.emit(curve_name, [point_index])

    def select_all_points(
        self,
        view: "CurveViewWidget",
        main_window: "MainWindow",
        curve_name: str | None = None
    ) -> None:
        """Select all points in curve."""
        if curve_name is None:
            curve_name = self._app_state.active_curve
        if curve_name is None:
            return

        curve_data = self._app_state.get_curve_data(curve_name)
        if curve_data:
            all_indices = set(range(len(curve_data)))
            self._app_state.set_selection(curve_name, all_indices)
            self._owner.selection_updated.emit(curve_name, list(all_indices))

    # Additional methods: clear_selection(), rubber_band_selection(), etc.
    # ... (extract from current InteractionService)


class _CommandHistory:
    """Internal helper for command history (undo/redo).

    NOT a QObject - lightweight helper class.
    """

    def __init__(self, owner: "InteractionService") -> None:
        """Initialize with reference to owner service."""
        self._owner = owner
        self._history: list[BaseCommand] = []
        self._history_index: int = -1
        self._max_history: int = 100

    def execute_command(self, command: BaseCommand) -> bool:
        """Execute command and add to history."""
        if command.execute():
            # Clear redo history
            self._history = self._history[:self._history_index + 1]

            # Add to history
            self._history.append(command)
            self._history_index += 1

            # Compress if needed
            if len(self._history) > self._max_history:
                self._compress_history()

            # Emit via owner
            self._owner.command_executed.emit(command.name)
            self._owner.history_changed.emit(self.can_undo(), self.can_redo())
            return True
        return False

    def undo(self) -> bool:
        """Undo last command."""
        if not self.can_undo():
            return False

        command = self._history[self._history_index]
        if command.undo():
            self._history_index -= 1
            self._owner.history_changed.emit(self.can_undo(), self.can_redo())
            return True
        return False

    def redo(self) -> bool:
        """Redo next command."""
        if not self.can_redo():
            return False

        command = self._history[self._history_index + 1]
        if command.redo():
            self._history_index += 1
            self._owner.history_changed.emit(self.can_undo(), self.can_redo())
            return True
        return False

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._history_index >= 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._history_index < len(self._history) - 1

    def clear_history(self) -> None:
        """Clear all history."""
        self._history.clear()
        self._history_index = -1
        self._owner.history_changed.emit(False, False)

    def _compress_history(self) -> None:
        """Remove old history entries."""
        if len(self._history) > self._max_history:
            remove_count = len(self._history) - self._max_history
            self._history = self._history[remove_count:]
            self._history_index -= remove_count


class _PointManipulator:
    """Internal helper for point manipulation operations.

    NOT a QObject - lightweight helper class.
    """

    def __init__(self, owner: "InteractionService") -> None:
        """Initialize with reference to owner service."""
        self._owner = owner
        self._app_state = get_application_state()

    def move_point(
        self,
        curve_name: str,
        point_index: int,
        new_x: float,
        new_y: float,
        validate: bool = True
    ) -> bool:
        """Move a single point."""
        if validate and not self.validate_point_move(curve_name, point_index, new_x, new_y):
            return False

        curve_data = self._app_state.get_curve_data(curve_name)
        if not curve_data or point_index >= len(curve_data):
            return False

        # Create new point
        old_point = curve_data[point_index]
        new_point = CurvePoint(
            frame=old_point.frame,
            x=new_x,
            y=new_y,
            status=old_point.status
        )

        # Update
        new_curve_data = list(curve_data)
        new_curve_data[point_index] = new_point
        self._app_state.set_curve_data(curve_name, new_curve_data)

        self._owner.points_modified.emit(curve_name, [point_index])
        return True

    def delete_points(self, curve_name: str, point_indices: set[int]) -> bool:
        """Delete multiple points."""
        curve_data = self._app_state.get_curve_data(curve_name)
        if not curve_data:
            return False

        # Create new data without deleted points
        new_curve_data = [
            point for i, point in enumerate(curve_data)
            if i not in point_indices
        ]

        self._app_state.set_curve_data(curve_name, new_curve_data)
        self._owner.points_modified.emit(curve_name, sorted(list(point_indices)))
        return True

    def validate_point_move(
        self, curve_name: str, point_index: int, new_x: float, new_y: float
    ) -> bool:
        """Validate if point move is allowed."""
        # Extract validation logic
        return True

    # Additional methods: nudge_points(), toggle_point_status(), etc.
    # ... (extract from current InteractionService)


# ============================================================================
# PUBLIC INTERACTION SERVICE (the only exported class)
# ============================================================================

class InteractionService(QObject):
    """Service for user interactions - coordinates internal helpers.

    This is the public service interface. Internal organization uses
    helper classes (_MouseHandler, _SelectionManager, etc.) for code organization
    while maintaining the 4-service architecture.
    """

    # Signals (only the service has signals, helpers emit via owner)
    point_clicked = Signal(str, int, object, object)
    drag_started = Signal(QPoint, str, int)
    drag_moved = Signal(QPoint, QPoint)
    drag_finished = Signal(QPoint, QPoint)
    selection_updated = Signal(str, list)
    history_changed = Signal(bool, bool)
    command_executed = Signal(str)
    points_modified = Signal(str, list)

    def __init__(self) -> None:
        """Initialize interaction service with internal helpers."""
        super().__init__()  # No parent - singleton pattern

        # Create internal helpers (lightweight, not QObjects)
        self._selection = _SelectionManager(self)
        self._mouse = _MouseHandler(self)
        self._commands = _CommandHistory(self)
        self._points = _PointManipulator(self)

        # Connect internal signals
        self._connect_internal_handlers()

    def _connect_internal_handlers(self) -> None:
        """Wire up internal signal handling."""
        # Mouse click → Select point (internal coordination)
        _ = self.point_clicked.connect(
            lambda curve, idx, view, window:
            self._selection.select_point(view, window, curve, idx),
            Qt.QueuedConnection
        )

        # Drag finished → Create command (internal coordination)
        _ = self.drag_finished.connect(
            self._on_drag_finished,
            Qt.QueuedConnection
        )

    def _on_drag_finished(self, end_pos: QPoint, delta: QPoint) -> None:
        """Handle drag finished - create move command."""
        # Create MovePointCommand and execute via command helper
        pass

    # ========================================================================
    # PUBLIC API (delegates to internal helpers)
    # ========================================================================

    def handle_mouse_press(self, event, view, main_window) -> bool:
        """Delegate to mouse handler."""
        return self._mouse.handle_mouse_press(event, view, main_window)

    def handle_mouse_move(self, event, view) -> bool:
        """Delegate to mouse handler."""
        return self._mouse.handle_mouse_move(event, view)

    def handle_mouse_release(self, event, view, main_window) -> bool:
        """Delegate to mouse handler."""
        return self._mouse.handle_mouse_release(event, view, main_window)

    def find_point_at(self, view, x, y, mode="active"):
        """Delegate to selection manager."""
        return self._selection.find_point_at(view, x, y, mode)

    def select_all_points(self, view, main_window, curve_name=None) -> None:
        """Delegate to selection manager."""
        self._selection.select_all_points(view, main_window, curve_name)

    def execute_command(self, command) -> bool:
        """Delegate to command history."""
        return self._commands.execute_command(command)

    def undo(self) -> bool:
        """Delegate to command history."""
        return self._commands.undo()

    def redo(self) -> bool:
        """Delegate to command history."""
        return self._commands.redo()

    def can_undo(self) -> bool:
        """Delegate to command history."""
        return self._commands.can_undo()

    def can_redo(self) -> bool:
        """Delegate to command history."""
        return self._commands.can_redo()

    def move_point(self, curve_name, index, x, y, validate=True) -> bool:
        """Delegate to point manipulator."""
        return self._points.move_point(curve_name, index, x, y, validate)

    def delete_points(self, curve_name, indices) -> bool:
        """Delegate to point manipulator."""
        return self._points.delete_points(curve_name, indices)

    # ... All other public methods delegate to appropriate helper ...
```

**Key Design Points:**

1. **Single File:** All code in `services/interaction_service.py`
2. **Internal Helpers:** Classes prefixed with `_` are implementation details
3. **Not QObjects:** Helpers are lightweight classes, not QObject subclasses
4. **Owner Pattern:** Helpers hold reference to owner service for signal emission
5. **Public API Unchanged:** Same `get_interaction_service()` interface
6. **Maintains 4-Service Architecture:** Still just Data, Interaction, Transform, UI

**Step 2: Migration Strategy**

1. **Phase 3.2a:** Extract logic from InteractionService into internal helpers (2 days)
   - Create `_MouseHandler` class with mouse/keyboard methods
   - Create `_SelectionManager` class with selection methods
   - Create `_CommandHistory` class with undo/redo methods
   - Create `_PointManipulator` class with point manipulation methods
   - All in same file: `services/interaction_service.py`

2. **Phase 3.2b:** Update InteractionService to coordinate helpers (1 day)
   - Create helper instances in `__init__`
   - Update public methods to delegate to helpers
   - Wire up internal signal connections

3. **Phase 3.2c:** Run tests to verify functionality preserved (1 day)
   - No changes to service getter needed (still `get_interaction_service()`)
   - No changes to calling code needed (same public API)
   - Tests pass unchanged (internal refactoring only)

#### **Verification Steps:**

```bash
# 1. Verify single file (NOT multiple service files)
ls -la services/*interaction*.py
# Should show ONLY:
# - interaction_service.py (refactored)
# NOT: mouse_interaction_service.py, selection_service.py, etc.

# 2. Verify internal helpers exist
grep "^class _MouseHandler:" services/interaction_service.py
grep "^class _SelectionManager:" services/interaction_service.py
grep "^class _CommandHistory:" services/interaction_service.py
grep "^class _PointManipulator:" services/interaction_service.py
# Should find all 4 internal helper classes

# 3. Verify 4-service architecture maintained
ls services/*.py | grep -E "(data|interaction|transform|ui)_service.py" | wc -l
# Should show: 4 services (NOT 8)

# 4. Count lines (should be similar to current, just reorganized)
wc -l services/interaction_service.py
# Should be ~1,400-1,500 lines (slightly reduced from 1,480 due to better organization)

# 5. Run interaction service tests
~/.local/bin/uv run pytest tests/test_interaction_service.py -v
~/.local/bin/uv run pytest tests/test_interaction_mouse_events.py -v
~/.local/bin/uv run pytest tests/test_interaction_history.py -v
```

#### **Success Metrics:**
- ✅ 1,480 lines refactored with internal helpers
- ✅ All interaction tests pass
- ✅ Command history functionality preserved
- ✅ Mouse/keyboard events work correctly
- ✅ **4-service architecture maintained** (NOT 8 services)
- ✅ Single file, better organized
- ✅ Backward compatible (same public API)
### **Task 3.3: Remove StateManager Data Delegation**
**Time:** 3-4 days (+ 4-8 hours REQUIRED preparation)
**Impact:** Removes ~210 lines of deprecated delegation (six-agent review corrected from 350)

#### **🔴 CRITICAL: REQUIRED PREPARATION (4-8 hours)**

**Six-agent review identified BLOCKING issue:** Task 3.3 lacks callsite inventory. Time estimate is unreliable without knowing how many files need changes.

**BEFORE starting Task 3.3, complete this preparation:**

```bash
# Step 1: Create comprehensive callsite inventory (2-4 hours)
echo "=== StateManager Data Delegation Callsite Inventory ===" > phase3_task33_inventory.txt
echo "" >> phase3_task33_inventory.txt

# Find all data delegation usage
echo "## track_data access:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.track_data" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

echo "" >> phase3_task33_inventory.txt
echo "## has_data access:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.has_data" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

echo "" >> phase3_task33_inventory.txt
echo "## data_bounds access:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.data_bounds" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

echo "" >> phase3_task33_inventory.txt
echo "## selected_points access:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.selected_points" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

echo "" >> phase3_task33_inventory.txt
echo "## image_files access:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.image_files\|state_manager\.set_image_files" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

echo "" >> phase3_task33_inventory.txt
echo "## current_frame delegation (if removing):" >> phase3_task33_inventory.txt
grep -rn "state_manager\.current_frame" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

# Step 2: Analyze impact (1-2 hours)
echo "" >> phase3_task33_inventory.txt
echo "## IMPACT SUMMARY:" >> phase3_task33_inventory.txt
echo "Total callsites: $(cat phase3_task33_inventory.txt | grep -E '\.py:[0-9]+:' | wc -l)" >> phase3_task33_inventory.txt
echo "Files impacted: $(cat phase3_task33_inventory.txt | grep -E '\.py:[0-9]+:' | cut -d: -f1 | sort -u | wc -l)" >> phase3_task33_inventory.txt

# Step 3: Create migration checklist (1-2 hours)
cat phase3_task33_inventory.txt | grep -E '\.py:[0-9]+:' | cut -d: -f1 | sort -u > phase3_task33_files.txt
echo "Files requiring migration:"
cat phase3_task33_files.txt

# Step 4: Adjust time estimate based on findings
# Rule of thumb: 30-60 min per file for manual migration
# If >50 files impacted, may need 1-2 weeks instead of 3-4 days
```

**DO NOT START TASK 3.3 WITHOUT THIS INVENTORY**

The six-agent review found that this task could impact 100+ files across the codebase. Without the inventory:
- ❌ Time estimate is unreliable
- ❌ Risk of missing conversions (silent failures)
- ❌ No rollback strategy if partial migration fails

#### **Current Issues:**
- StateManager has ~210 lines of core delegation + ~140 lines infrastructure = ~350 lines total
- Comments say "DEPRECATED: delegated to ApplicationState"
- Creates confusion: "Which API should I use?"
- Two sources of truth (StateManager vs ApplicationState)

#### **Implementation Strategy:**

**Step 1: Identify all delegation properties**

```bash
# Find all @property decorators that delegate
grep -A 5 "@property" ui/state_manager.py | grep -B 3 "_app_state"
```

**Step 2: Manual migration (context-aware refactoring)**

⚠️ **IMPORTANT:** This migration must be done MANUALLY, not with automated regex replacement.

**Why Manual Migration?**
Automated regex produces inefficient code with repeated singleton calls:
```python
# ❌ BAD: Automated regex result
data = get_application_state().get_curve_data(get_application_state().active_curve)
# Calls get_application_state() TWICE!
```

**Correct Manual Pattern:**
```python
# ✅ GOOD: Manual context-aware refactoring
state = get_application_state()
active = state.active_curve
if active is not None:
    data = state.get_curve_data(active)
    # Reuse state and active throughout method
```

**Migration Process:**

1. **Find all StateManager data access:**
```bash
# Identify all callsites
grep -rn "state_manager\.track_data\|state_manager\.current_frame" ui/ services/ core/ --include="*.py"
```

2. **For each file, refactor using this pattern:**
```python
# At the start of each method that uses state_manager data:
from stores.application_state import get_application_state

def some_method(self):
    # Step 1: Get state once at method start
    state = get_application_state()

    # Step 2: For track_data access, get active curve
    active = state.active_curve
    if active is None:
        return  # Handle no active curve

    # Step 3: Get curve data
    curve_data = state.get_curve_data(active)
    if curve_data is None:
        return  # Handle no data

    # Step 4: Use curve_data throughout the rest of the method
    # ... rest of method uses curve_data ...
```

**Common Patterns:**

**Pattern 1: Direct property access**
```python
# BEFORE:
frame = state_manager.current_frame

# AFTER:
frame = get_application_state().current_frame
```

**Pattern 2: track_data access**
```python
# BEFORE:
data = state_manager.track_data
if data:
    process(data)

# AFTER:
state = get_application_state()
active = state.active_curve
if active is not None:
    data = state.get_curve_data(active)
    if data is not None:
        process(data)
```

**Pattern 3: has_data check**
```python
# BEFORE:
if state_manager.has_data:
    do_something()

# AFTER:
state = get_application_state()
active = state.active_curve
if active is not None and state.get_curve_data(active) is not None:
    do_something()
```

**Pattern 4: selected_points access**
```python
# BEFORE:
selection = state_manager.selected_points

# AFTER:
state = get_application_state()
active = state.active_curve
selection = state.get_selection(active) if active else set()
```

3. **Verify each file after migration:**
```bash
# Run tests for the modified file
~/.local/bin/uv run pytest tests/test_<modified_file>.py -v

# Check type safety
./bpr path/to/modified_file.py
```

**Step 3: Remove delegation properties from StateManager**

Keep only UI-specific properties:
- `zoom_level`
- `pan_offset`
- `window_size`
- `window_position`
- `is_fullscreen`
- `current_tool`

Remove all data-related properties:
- `track_data` (use `app_state.get_curve_data()`)
- `current_frame` (use `app_state.current_frame`)
- `has_data` (use `app_state.get_curve_data() is not None`)
- `data_bounds` (calculate from `app_state.get_curve_data()`)
- `selected_points` (use `app_state.get_selection()`)
- All other data delegations

#### **Verification Steps:**

```bash
# 1. Count properties before
grep -c "@property" ui/state_manager.py
# Before: ~50

# 2. Run migration
python3 tools/migrate_state_manager.py

# 3. Count properties after
grep -c "@property" ui/state_manager.py
# After: ~15 (only UI properties)

# 4. Run full test suite
~/.local/bin/uv run pytest tests/ -x
```

#### **Success Metrics:**
- ✅ ~350 lines removed from StateManager
- ✅ Only UI-specific properties remain
- ✅ All tests pass
- ✅ Single source of truth (ApplicationState)

---

### **Phase 3 Completion Checklist:**

```bash
cat > verify_phase3.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Phase 3 Verification ==="

echo "1. MultiPointTrackingController split..."
if [ -f "ui/controllers/tracking_data_controller.py" ] && \
   [ -f "ui/controllers/tracking_display_controller.py" ] && \
   [ -f "ui/controllers/tracking_selection_controller.py" ]; then
    echo "✅ PASS: Sub-controllers created"
else
    echo "❌ FAIL: Missing sub-controllers"
    exit 1
fi

echo "2. InteractionService refactored with internal helpers..."
# Verify single file (NOT multiple service files)
if [ -f "services/interaction_service.py" ] && \
   ! [ -f "services/mouse_interaction_service.py" ] && \
   ! [ -f "services/selection_service.py" ]; then
    # Verify internal helpers exist
    if grep -q "^class _MouseHandler:" services/interaction_service.py && \
       grep -q "^class _SelectionManager:" services/interaction_service.py; then
        echo "✅ PASS: InteractionService refactored with internal helpers"
    else
        echo "❌ FAIL: Internal helpers not found"
        exit 1
    fi
else
    echo "❌ FAIL: Should be single file, not multiple services"
    exit 1
fi

# Verify 4-service architecture maintained
SERVICE_COUNT=$(ls services/*.py | grep -E "(data|interaction|transform|ui)_service.py" | wc -l)
if [ "$SERVICE_COUNT" -eq 4 ]; then
    echo "✅ PASS: 4-service architecture maintained"
else
    echo "❌ FAIL: Found $SERVICE_COUNT services (should be 4)"
    exit 1
fi

echo "3. StateManager delegation removed..."
PROP_COUNT=$(grep -c "@property" ui/state_manager.py)
if [ "$PROP_COUNT" -lt 20 ]; then
    echo "✅ PASS: StateManager simplified ($PROP_COUNT properties)"
else
    echo "❌ FAIL: Too many properties remaining ($PROP_COUNT)"
    exit 1
fi

echo "4. Running architectural tests..."
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v
~/.local/bin/uv run pytest tests/test_interaction_service.py -v
~/.local/bin/uv run pytest tests/test_state_manager.py -v

echo "=== Phase 3 COMPLETE ==="
EOF

chmod +x verify_phase3.sh
./verify_phase3.sh
```

**Phase 3 Success Criteria:**
- ✅ 2,645 lines of god objects → 7 focused components (3 controllers + 4 internal helpers)
- ✅ ~350 lines of delegation removed
- ✅ All architectural tests pass
- ✅ Single Responsibility Principle enforced
- ✅ Backward compatibility maintained
- ✅ **4-service architecture maintained** (Data, Interaction, Transform, UI)

---


---

**Navigation:**
- [← Previous: Phase 2 Quick Wins](phase2_quick_wins.md)
- [→ Next: Phase 4 Polish & Optimization](phase4_polish_optimization.md)
- [← Back to Overview](README.md)
