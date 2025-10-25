# CurveEditor Refactoring Implementation Plan

## Overview

This plan implements the verified findings from the codebase consolidation analysis, addressing SOLID, DRY, KISS, and YAGNI violations across 4 progressive phases.

**Total Effort:** 44.5-62.5 hours
**Expected Quality Improvement:** 62 → 100 points (+61%)
**Recommended Scope:** Phases 1-2 (80% benefit for 38% time)

---

## Phase Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                  Phase 1: Quick Wins                        │
│                  ✓ Can start immediately                    │
│                  ✓ 2.5 hours, +15 points                    │
│                  ✓ LOW risk                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 2: Protocol Adoption                     │
│              • Requires Phase 1 (cleaner code)              │
│              • 10-14 hours, +10 points                      │
│              • MEDIUM risk                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Phase 3: Dependency Injection                    │
│            • Requires Phase 2 (protocols ready)             │
│            • 12-16 hours, +5 points                         │
│            • HIGH risk                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Phase 4: God Class Refactoring                    │
│           • Requires Phase 3 (DI for split stores)          │
│           • 20-30 hours, +8 points                          │
│           • VERY HIGH risk                                  │
│           ⚠️  OPTIONAL for personal tool                     │
└─────────────────────────────────────────────────────────────┘
```

**Checkpoint Validation:** After each phase, all tests must pass, type checking must be clean, and manual smoke test must succeed before proceeding.

---

## Phase 1: Quick Wins

**Goal:** Low-effort, high-impact improvements to reduce complexity and improve maintainability

**Duration:** 2.5 hours
**Impact:** +15 points (62→77)
**ROI:** 6.0 points/hour
**Risk:** LOW

### Tasks

#### 1.1 Extract Internal Classes from InteractionService (1 hour)

**Current State:** `services/interaction_service.py` has 1,761 lines with 4 internal classes starting around line 1462

**Changes:**

1. **Create `services/interaction/mouse_handler.py`:**
```python
from typing import TYPE_CHECKING
from PySide6.QtCore import QPointF
from protocols.state import CurveDataProvider, SelectionProvider

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from ui.curve_view_widget import CurveViewWidget

class MouseHandler:
    """Handles mouse interaction logic for curve editing."""

    def __init__(self, state: CurveDataProvider & SelectionProvider):
        self._state = state

    def handle_click(self, view: "CurveViewWidget", pos: QPointF,
                     main_window: "MainWindow") -> bool:
        """Handle mouse click at position."""
        # Move logic from _MouseHandler internal class
        pass
```

2. **Create `services/interaction/selection_manager.py`:**
```python
from protocols.state import SelectionProvider, SelectionModifier

class SelectionManager:
    """Manages point selection state and operations."""

    def __init__(self, state: SelectionProvider & SelectionModifier):
        self._state = state

    def select_points(self, curve_name: str, indices: set[int]) -> None:
        """Select points by indices."""
        pass
```

3. **Create `services/interaction/command_history.py`:**
```python
from collections import deque
from typing import Protocol

class CommandHistory:
    """Manages undo/redo command history."""

    def __init__(self, max_history: int = 100):
        self._undo_stack: deque = deque(maxlen=max_history)
        self._redo_stack: deque = deque(maxlen=max_history)

    def execute(self, command) -> bool:
        """Execute command and add to history."""
        pass
```

4. **Create `services/interaction/point_manipulator.py`:**
```python
from protocols.state import CurveDataProvider, CurveDataModifier

class PointManipulator:
    """Handles point manipulation operations."""

    def __init__(self, state: CurveDataProvider & CurveDataModifier):
        self._state = state

    def move_point(self, curve_name: str, index: int, dx: float, dy: float) -> bool:
        """Move point by delta."""
        pass
```

5. **Update `services/interaction_service.py`:**
```python
from services.interaction.mouse_handler import MouseHandler
from services.interaction.selection_manager import SelectionManager
from services.interaction.command_history import CommandHistory
from services.interaction.point_manipulator import PointManipulator

class InteractionService:
    def __init__(self):
        self._state = get_application_state()  # Will be DI in Phase 3

        # Composed from extracted classes
        self._mouse = MouseHandler(state=self._state)
        self._selection = SelectionManager(state=self._state)
        self._commands = CommandHistory()
        self._points = PointManipulator(state=self._state)
```

**Files Modified:**
- `services/interaction_service.py` (reduce from 1,761 to ~1,450 lines)
- `services/interaction/mouse_handler.py` (new)
- `services/interaction/selection_manager.py` (new)
- `services/interaction/command_history.py` (new)
- `services/interaction/point_manipulator.py` (new)

#### 1.2 Add Missing Docstrings (0.83 hours / 50 minutes)

**Find methods without docstrings:**
```bash
~/.local/bin/uv run ruff check . --select D102,D103
```

**Add numpy-style docstrings to 10 public methods:**
```python
def get_position_at_frame(self, curve_name: str, frame: int) -> tuple[float, float]:
    """Get curve position at specific frame.

    Parameters
    ----------
    curve_name : str
        Name of the curve to query
    frame : int
        Frame number to get position at

    Returns
    -------
    tuple[float, float]
        (x, y) position at the frame

    Notes
    -----
    Returns held position for inactive segments (gaps).
    """
    pass
```

**Priority targets:**
- `stores/application_state.py`: Public methods missing docstrings
- `services/data_service.py`: Core data operations
- `services/interaction_service.py`: Public API methods

#### 1.3 Remove Dead Code (0.33 hours / 20 minutes)

**Find candidates:**
```bash
# Find commented code blocks
mcp__serena__search_for_pattern --substring_pattern "^\s*#.*def |^\s*#.*class " --paths_include_glob "*.py"

# Find unreachable code after returns
~/.local/bin/uv run ruff check . --select F841,F401
```

**Remove identified dead code blocks (estimated 2 blocks):**
- Commented-out legacy code
- Unreachable code after returns
- Unused imports

#### 1.4 Reduce Nesting Depth (0.33 hours / 20 minutes)

**Find overly nested functions (depth > 4):**
```bash
~/.local/bin/uv run ruff check . --select C901
```

**Refactor using early returns:**

**Before:**
```python
def process_point(self, point):
    if point is not None:
        if point.status == PointStatus.NORMAL:
            if self.is_selected(point):
                if self.validate(point):
                    # Deep nesting - hard to read
                    self.update(point)
```

**After:**
```python
def process_point(self, point):
    # Early returns reduce nesting
    if point is None:
        return

    if point.status != PointStatus.NORMAL:
        return

    if not self.is_selected(point):
        return

    if not self.validate(point):
        return

    # Main logic at top level - easy to read
    self.update(point)
```

**Target 2 functions with excessive nesting**

### Success Metrics

- [ ] InteractionService: 1,761 → ~1,450 lines (17% reduction)
- [ ] 4 new service files created in `services/interaction/`
- [ ] Public method docstring coverage: 90%+ (verify with `ruff check . --select D102,D103`)
- [ ] Dead code blocks: 0
- [ ] Max nesting depth: ≤3 (verify with `ruff check . --select C901`)
- [ ] All 100+ tests pass
- [ ] Type checking: 0 errors

### Verification Steps

```bash
# 1. Run all tests
~/.local/bin/uv run pytest tests/ -v

# 2. Type checking
./bpr --errors-only

# 3. Linting (should have fewer violations than before)
~/.local/bin/uv run ruff check .

# 4. Check metrics
# Line count reduction
wc -l services/interaction_service.py  # Should be ~1,450
ls services/interaction/               # Should have 4 new files

# Docstring coverage
~/.local/bin/uv run ruff check . --select D102,D103 | wc -l  # Should be low

# Nesting depth
~/.local/bin/uv run ruff check . --select C901  # Should show max depth ≤3

# 5. Manual smoke test
python main.py
# - Load curve file
# - Select points
# - Move points
# - Undo/redo
# - Verify no regressions
```

### Rollback Strategy

**Git workflow:**
```bash
git checkout -b phase-1-quick-wins
# Make changes with frequent commits
git commit -m "Extract MouseHandler from InteractionService"
git commit -m "Extract SelectionManager from InteractionService"
# etc.

# If validation fails:
git checkout main
git branch -D phase-1-quick-wins
```

**Risk:** LOW - Internal refactoring only, no API changes

---

## Phase 2: Protocol Adoption

**Goal:** Replace concrete type dependencies with protocol interfaces for better testability and decoupling

**Duration:** 10-14 hours
**Impact:** +10 points (77→87)
**ROI:** 0.83 points/hour
**Risk:** MEDIUM

### Tasks

#### 2.1 Audit Current Type Dependencies (2 hours)

**Find all concrete type uses:**
```bash
# StateManager dependencies
mcp__serena__search_for_pattern --substring_pattern ": StateManager" --paths_include_glob "**/*.py"

# MainWindow dependencies
mcp__serena__search_for_pattern --substring_pattern ": MainWindow" --paths_include_glob "**/*.py"

# ApplicationState dependencies
mcp__serena__search_for_pattern --substring_pattern "get_application_state\(\)" --paths_include_glob "**/*.py"
```

**Create replacement mapping:**
- Map each concrete type usage to required protocols
- Identify protocol intersections needed (e.g., `FrameProvider & CurveDataProvider`)
- Document in `PROTOCOL_MIGRATION_MAP.md`

#### 2.2 Update Controllers (4-6 hours)

**Target files (8 controllers):**
- `ui/controllers/action_handler_controller.py`
- `ui/controllers/multi_point_tracking_controller.py`
- `ui/controllers/point_editor_controller.py`
- `ui/controllers/signal_connection_manager.py`
- `ui/controllers/timeline_controller.py`
- `ui/controllers/ui_initialization_controller.py`
- `ui/controllers/view_camera_controller.py`
- `ui/controllers/view_management_controller.py`

**Example: ActionHandlerController**

**Before (`ui/controllers/action_handler_controller.py:35`):**
```python
from ui.state_manager import StateManager
from ui.main_window import MainWindow

class ActionHandlerController:
    def __init__(self, state_manager: StateManager, main_window: MainWindow):
        self.state_manager: StateManager = state_manager
        self.main_window: MainWindow = main_window

    def handle_smooth(self):
        # Tightly coupled to concrete types
        curve_data = self.main_window.curve_data
        frame = self.state_manager.current_frame
```

**After:**
```python
from protocols.state import FrameProvider, CurveDataProvider
from protocols.ui import MainWindowProtocol

class ActionHandlerController:
    def __init__(self,
                 state: FrameProvider & CurveDataProvider,
                 main_window: MainWindowProtocol):
        self._state = state
        self._main_window = main_window

    def handle_smooth(self):
        # Decoupled, testable with simple mocks
        if (cd := self._state.active_curve_data) is None:
            return
        curve_name, curve_data = cd
        frame = self._state.current_frame
```

**Test benefits:**
```python
# Before: Mock entire MainWindow (50+ methods)
mock_window = Mock(spec=MainWindow)
mock_window.curve_data = ...
mock_window.current_frame = ...
# ... 48 more methods

# After: Mock protocol (2-3 properties)
class MockState:
    active_curve_data = ("Track1", [CurvePoint(...)])
    current_frame = 42

controller = ActionHandlerController(MockState(), mock_window)
# 98% simpler mocking!
```

**Repeat for all 8 controllers** (~30-45 minutes each)

#### 2.3 Update Services (3-4 hours)

**Target files:**
- `services/data_service.py`
- `services/interaction_service.py`
- `services/transform_service.py`
- `services/ui_service.py`

**Example: DataService method**

**Before:**
```python
def get_position_at_frame(self, curve_name: str, frame: int) -> tuple[float, float]:
    state = get_application_state()  # Concrete dependency
    data = state.get_curve_data(curve_name)
```

**After:**
```python
from protocols.state import CurveDataProvider

class DataService:
    def __init__(self, state: CurveDataProvider):
        self._state = state

    def get_position_at_frame(self, curve_name: str, frame: int) -> tuple[float, float]:
        data = self._state.get_curve_data(curve_name)  # Protocol dependency
```

**Note:** Full DI happens in Phase 3, but we prepare signatures here

#### 2.4 Update Commands (1-2 hours)

**Update `core/commands/curve_commands.py:62`:**

**Before:**
```python
class CurveDataCommand(Command):
    def _get_active_curve_data(self) -> tuple[str, CurveDataList] | None:
        app_state = get_application_state()  # Service locator anti-pattern
        if (cd := app_state.active_curve_data) is None:
            return None
        return cd
```

**After:**
```python
from protocols.state import CurveDataProvider

class CurveDataCommand(Command):
    def __init__(self, description: str, state: CurveDataProvider):
        super().__init__(description)
        self._state = state

    def _get_active_curve_data(self) -> tuple[str, CurveDataList] | None:
        if (cd := self._state.active_curve_data) is None:
            return None
        return cd
```

**Update all command subclasses** to accept `state` parameter

#### 2.5 Verify Protocol Conformance (1 hour)

**Ensure all protocols are `@runtime_checkable`:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class FrameProvider(Protocol):
    @property
    def current_frame(self) -> int: ...
```

**Test protocol conformance:**
```python
# Add to tests/protocols/test_state_protocols.py
def test_application_state_conforms_to_frame_provider():
    state = ApplicationState()
    assert isinstance(state, FrameProvider)

def test_application_state_conforms_to_curve_provider():
    state = ApplicationState()
    assert isinstance(state, CurveDataProvider)
```

### Success Metrics

- [ ] Protocol imports: 80+ occurrences (up from 37, 60%+ adoption)
- [ ] Concrete `StateManager` type annotations: <10 (down from 30+)
- [ ] Concrete `MainWindow` type annotations: <15 (down from 40+)
- [ ] TYPE_CHECKING guards: <150 (down from 181, protocols reduce circular deps)
- [ ] All protocols have `@runtime_checkable` decorator
- [ ] Protocol conformance tests pass
- [ ] All 100+ tests pass (update mocks to use protocols)
- [ ] Type checking: 0 errors

### Verification Steps

```bash
# 1. Count protocol usage
grep -r "from protocols" --include="*.py" | wc -l  # Should be 80+

# 2. Verify reduced concrete types
grep -r ": StateManager" --include="*.py" | wc -l  # Should be <10
grep -r ": MainWindow" --include="*.py" | wc -l   # Should be <15

# 3. TYPE_CHECKING reduction
grep -r "TYPE_CHECKING" --include="*.py" | wc -l  # Should be <150

# 4. Run protocol conformance tests
~/.local/bin/uv run pytest tests/protocols/ -v

# 5. Run all tests
~/.local/bin/uv run pytest tests/ -v

# 6. Type checking
./bpr --errors-only

# 7. Manual smoke test
python main.py
# - All functionality from Phase 1
# - Verify no regressions
```

### Rollback Strategy

**Git workflow:**
```bash
git checkout -b phase-2-protocol-adoption
# Commit after each controller/service update
git commit -m "Update ActionHandlerController to use protocols"
git commit -m "Update DataService to use protocols"
# etc.

# If validation fails:
git checkout main
git branch -D phase-2-protocol-adoption
```

**Risk:** MEDIUM - Type changes may break tests, requires mock updates

---

## Phase 3: Dependency Injection

**Goal:** Eliminate service locator anti-pattern, enable true testability with injected dependencies

**Duration:** 12-16 hours
**Impact:** +5 points (87→92)
**ROI:** 0.40 points/hour
**Risk:** HIGH

### Prerequisites

- Phase 2 complete (protocols in place)
- All tests passing with protocol-based mocks

### Tasks

#### 3.1 Map Dependency Graph (2 hours)

**Analyze service dependencies:**
```bash
# Find all service getter calls
mcp__serena__search_for_pattern --substring_pattern "get_.*_service\(\)" --paths_include_glob "**/*.py"

# Create dependency graph
# Example output:
# TransformService → (no service dependencies)
# DataService → ApplicationState
# InteractionService → ApplicationState, DataService
# UIService → ApplicationState
```

**Document in `SERVICE_DEPENDENCY_GRAPH.md`:**
```
TransformService (leaf - no service deps)
├── ApplicationState ✓

DataService
├── ApplicationState ✓

InteractionService
├── ApplicationState ✓
└── DataService ✓

UIService
├── ApplicationState ✓

MainWindow (root)
├── All 4 services
└── ApplicationState
```

**Migration order:** TransformService → DataService → UIService → InteractionService → MainWindow

#### 3.2 Create Dependency Container (2 hours)

**Create `core/dependency_container.py`:**
```python
from typing import TYPE_CHECKING

from stores.application_state import ApplicationState
from services.data_service import DataService
from services.interaction_service import InteractionService
from services.transform_service import TransformService
from services.ui_service import UIService

if TYPE_CHECKING:
    from protocols.state import CurveState, FrameProvider, SelectionState

class ServiceContainer:
    """Centralized dependency injection container.

    Manages lifecycle of all services and state, ensuring
    dependencies are properly injected and initialized.
    """

    _instance: "ServiceContainer | None" = None

    def __init__(self):
        """Initialize all services with dependencies."""
        # State first (no dependencies)
        self._state = ApplicationState()

        # Services with dependencies (order matters!)
        self._transform = TransformService()  # No service deps
        self._data = DataService(state=self._state)
        self._ui = UIService(state=self._state)
        self._interaction = InteractionService(
            state=self._state,
            data_service=self._data
        )

    @classmethod
    def instance(cls) -> "ServiceContainer":
        """Get singleton container instance."""
        if cls._instance is None:
            cls._instance = ServiceContainer()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    @property
    def state(self) -> "CurveState & FrameProvider & SelectionState":
        """Get application state."""
        return self._state

    @property
    def data_service(self) -> DataService:
        """Get data service."""
        return self._data

    @property
    def interaction_service(self) -> InteractionService:
        """Get interaction service."""
        return self._interaction

    @property
    def transform_service(self) -> TransformService:
        """Get transform service."""
        return self._transform

    @property
    def ui_service(self) -> UIService:
        """Get UI service."""
        return self._ui
```

#### 3.3 Update Services to Accept Dependencies (6-10 hours)

**Update each service in dependency order:**

**3.3.1 TransformService (no changes needed - no service deps)**

**3.3.2 DataService**

**Before:**
```python
class DataService:
    def __init__(self):
        self._state = get_application_state()  # Service locator
```

**After:**
```python
from protocols.state import CurveDataProvider, ImageSequenceProvider

class DataService:
    def __init__(self, state: CurveDataProvider & ImageSequenceProvider):
        self._state = state  # Injected dependency
```

**3.3.3 UIService**

**Before:**
```python
class UIService:
    def __init__(self):
        self._state = get_application_state()  # Service locator
```

**After:**
```python
from protocols.state import FrameProvider, CurveDataProvider

class UIService:
    def __init__(self, state: FrameProvider & CurveDataProvider):
        self._state = state  # Injected dependency
```

**3.3.4 InteractionService**

**Before:**
```python
class InteractionService:
    def __init__(self):
        self._state = get_application_state()  # Service locator
        self._data_service = get_data_service()  # Service locator
```

**After:**
```python
from protocols.state import CurveState, SelectionState
from services.data_service import DataService

class InteractionService:
    def __init__(self,
                 state: CurveState & SelectionState,
                 data_service: DataService):
        self._state = state  # Injected
        self._data_service = data_service  # Injected
```

**Update internal service methods** to use `self._state` instead of calling `get_application_state()`

#### 3.4 Update MainWindow and Main Entry Point (2 hours)

**Update `main.py`:**
```python
import sys
from PySide6.QtWidgets import QApplication
from core.dependency_container import ServiceContainer
from ui.main_window import MainWindow

def main():
    """Application entry point with dependency injection."""
    app = QApplication(sys.argv)

    # Create container (initializes all services with dependencies)
    container = ServiceContainer.instance()

    # Pass container to MainWindow
    window = MainWindow(container=container)
    window.show()

    return sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

**Update `ui/main_window.py`:**
```python
from core.dependency_container import ServiceContainer

class MainWindow(QMainWindow):
    def __init__(self, container: ServiceContainer):
        super().__init__()

        # Get services from container (not service locators!)
        self._container = container
        self._state = container.state
        self._data_service = container.data_service
        self._interaction_service = container.interaction_service
        self._transform_service = container.transform_service
        self._ui_service = container.ui_service

        # Initialize UI with injected dependencies
        self._setup_ui()
```

**Update controllers** to receive dependencies via MainWindow:
```python
# In MainWindow._setup_controllers():
self._action_handler = ActionHandlerController(
    state=self._state,
    main_window=self
)
```

#### 3.5 Update Commands to Use Injected State (2 hours)

**Update `core/commands/curve_commands.py`:**
```python
from protocols.state import CurveDataProvider, CurveDataModifier

class CurveDataCommand(Command):
    def __init__(self, description: str, state: CurveDataProvider & CurveDataModifier):
        super().__init__(description)
        self._state = state  # Injected, not service locator
        self._target_curve: str | None = None

    def _get_active_curve_data(self) -> tuple[str, CurveDataList] | None:
        # Use injected state
        if (cd := self._state.active_curve_data) is None:
            return None
        curve_name, data = cd
        self._target_curve = curve_name  # Store for undo/redo
        return cd
```

**Update command creation sites** to inject state:
```python
# Before:
command = SmoothCommand(description="Smooth points")

# After:
command = SmoothCommand(
    description="Smooth points",
    state=self._state  # Inject from MainWindow/controller
)
```

#### 3.6 Update Tests to Use DI (2 hours)

**Create test fixtures with DI:**
```python
# tests/conftest.py
import pytest
from core.dependency_container import ServiceContainer

@pytest.fixture
def container():
    """Provide clean service container for tests."""
    ServiceContainer.reset()
    container = ServiceContainer.instance()
    yield container
    ServiceContainer.reset()

@pytest.fixture
def state(container):
    """Provide application state from container."""
    return container.state

@pytest.fixture
def data_service(container):
    """Provide data service from container."""
    return container.data_service
```

**Update tests to use fixtures:**
```python
# Before (service locator in tests - hard to control):
def test_smooth_command():
    state = get_application_state()  # Gets global state
    state.set_curve_data("Track1", test_data)
    command = SmoothCommand(...)

# After (DI in tests - full control):
def test_smooth_command(state):
    state.set_curve_data("Track1", test_data)  # Fixture-provided state
    command = SmoothCommand(..., state=state)  # Inject
```

### Success Metrics

- [ ] `get_application_state()` calls: <150 (down from 730, 80% reduction)
- [ ] `get_X_service()` calls: <50 (down from 200+)
- [ ] `ServiceContainer` created in `core/dependency_container.py`
- [ ] All services accept dependencies in `__init__`
- [ ] `main.py` creates container and passes to MainWindow
- [ ] All tests use DI (no service locator calls in test code)
- [ ] All 100+ tests pass
- [ ] Type checking: 0 errors

### Verification Steps

```bash
# 1. Count service locator usage (should be drastically reduced)
grep -r "get_application_state()" --include="*.py" | wc -l  # <150
grep -r "get_.*_service()" --include="*.py" | wc -l        # <50

# 2. Verify container exists
ls core/dependency_container.py  # Should exist

# 3. Verify main.py uses container
grep "ServiceContainer" main.py  # Should be present

# 4. Run all tests (with DI)
~/.local/bin/uv run pytest tests/ -v --tb=short

# 5. Type checking
./bpr --errors-only

# 6. Manual smoke test
python main.py
# - All functionality from Phases 1-2
# - Verify dependency injection working
# - Check for any initialization order issues

# 7. Test cleanup (verify container resets work)
~/.local/bin/uv run pytest tests/ -v --count=3  # Run 3 times
```

### Rollback Strategy

**Git workflow:**
```bash
git checkout -b phase-3-dependency-injection

# Feature flag during migration (add to core/feature_flags.py):
USE_DEPENDENCY_INJECTION = False  # Toggle to rollback

# Migrate incrementally with commits:
git commit -m "Create ServiceContainer"
git commit -m "Update DataService to use DI"
git commit -m "Update InteractionService to use DI"
git commit -m "Update main.py to use container"
git commit -m "Update tests to use DI fixtures"

# If validation fails at any point:
# 1. Revert last commit
git revert HEAD

# 2. Or revert entire phase
git checkout main
git branch -D phase-3-dependency-injection

# 3. Or use feature flag
# Set USE_DEPENDENCY_INJECTION = False to use old service locators
```

**Risk Mitigation:**
- Maintain dual code paths during migration (feature flag)
- Update services one at a time (not all at once)
- Commit after each service update
- Run tests after each commit

**Risk:** HIGH - Touches 730 call sites, potential initialization order bugs

---

## Phase 4: God Class Refactoring

**Goal:** Split ApplicationState and InteractionService into focused domain classes

**Duration:** 20-30 hours
**Impact:** +8 points (92→100)
**ROI:** 0.36 points/hour
**Risk:** VERY HIGH

### Prerequisites

- Phase 3 complete (DI infrastructure in place)
- All tests passing with injected dependencies

### ⚠️ Recommendation

**Consider Phase 4 OPTIONAL for personal tool:**
- Phases 1-3 deliver 80%+ of benefit (62→92 points)
- Phase 4 has highest risk, lowest ROI
- May not be worth 20-30 hours for single-user tool

**If proceeding, use facade pattern for indefinite backward compatibility**

### Tasks

#### 4.1 Split ApplicationState into Domain Stores (15-20 hours)

**Create domain stores:**

**4.1.1 Create `stores/curve_store.py` (3 hours):**
```python
from PySide6.QtCore import QObject, Signal
from core.type_aliases import CurveDataList

class CurveStore(QObject):
    """Manages curve data and metadata."""

    # Signals
    curves_changed = Signal(dict)  # Emits all curves
    active_curve_changed = Signal(str)  # Emits active curve name

    def __init__(self):
        super().__init__()
        self._curves: dict[str, CurveDataList] = {}
        self._metadata: dict[str, dict] = {}
        self._active_curve: str | None = None

    def get_curve_data(self, name: str) -> CurveDataList | None:
        """Get curve data by name."""
        return self._curves.get(name)

    def set_curve_data(self, name: str, data: CurveDataList) -> None:
        """Set curve data."""
        self._curves[name] = data
        self.curves_changed.emit(self._curves.copy())

    @property
    def active_curve(self) -> str | None:
        """Get active curve name."""
        return self._active_curve

    @active_curve.setter
    def active_curve(self, name: str | None) -> None:
        """Set active curve."""
        if self._active_curve != name:
            self._active_curve = name
            self.active_curve_changed.emit(name or "")
```

**4.1.2 Create `stores/selection_store.py` (2 hours):**
```python
from PySide6.QtCore import QObject, Signal

class SelectionStore(QObject):
    """Manages point selection state."""

    # Signals
    selection_changed = Signal(set, str)  # (selected_curves, active_curve)

    def __init__(self):
        super().__init__()
        self._selected_curves: set[str] = set()
        self._point_selections: dict[str, set[int]] = {}

    def get_selection(self, curve_name: str) -> set[int]:
        """Get selected point indices for curve."""
        return self._point_selections.get(curve_name, set()).copy()

    def set_selection(self, curve_name: str, indices: set[int]) -> None:
        """Set selected point indices."""
        self._point_selections[curve_name] = indices
        self.selection_changed.emit(self._selected_curves, curve_name)
```

**4.1.3 Create `stores/frame_store.py` (2 hours):**
```python
from PySide6.QtCore import QObject, Signal

class FrameStore(QObject):
    """Manages frame navigation state."""

    # Signals
    frame_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self._current_frame: int = 0
        self._total_frames: int = 0

    @property
    def current_frame(self) -> int:
        """Get current frame."""
        return self._current_frame

    def set_frame(self, frame: int) -> None:
        """Set current frame."""
        if self._current_frame != frame:
            self._current_frame = frame
            self.frame_changed.emit(frame)
```

**4.1.4 Create `stores/image_store.py` (2 hours):**
```python
from PySide6.QtCore import QObject, Signal

class ImageStore(QObject):
    """Manages image sequence."""

    # Signals
    image_sequence_changed = Signal(list, str)  # (files, directory)

    def __init__(self):
        super().__init__()
        self._image_files: list[str] = []
        self._image_directory: str = ""

    def set_image_files(self, files: list[str], directory: str = "") -> None:
        """Set image sequence."""
        self._image_files = files
        self._image_directory = directory
        self.image_sequence_changed.emit(files, directory)

    def get_image_files(self) -> list[str]:
        """Get image files."""
        return self._image_files.copy()
```

**4.1.5 Create `stores/batch_coordinator.py` (2 hours):**
```python
from contextlib import contextmanager
from PySide6.QtCore import QObject, Signal

class BatchCoordinator(QObject):
    """Coordinates batch updates across stores."""

    # Signals
    batch_started = Signal()
    batch_ended = Signal()

    def __init__(self):
        super().__init__()
        self._batch_depth: int = 0

    @contextmanager
    def batch_updates(self):
        """Context manager for batch updates."""
        self._batch_depth += 1
        if self._batch_depth == 1:
            self.batch_started.emit()

        try:
            yield
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0:
                self.batch_ended.emit()

    @property
    def is_batching(self) -> bool:
        """Check if currently in batch mode."""
        return self._batch_depth > 0
```

**4.1.6 Create ApplicationState Facade (3 hours):**
```python
from PySide6.QtCore import QObject, Signal
from stores.curve_store import CurveStore
from stores.selection_store import SelectionStore
from stores.frame_store import FrameStore
from stores.image_store import ImageStore
from stores.batch_coordinator import BatchCoordinator

class ApplicationState(QObject):
    """Facade for backward compatibility.

    Delegates to domain stores while maintaining existing API.
    Eventually, callers should migrate to using stores directly.
    """

    # Forward signals from stores
    curves_changed = Signal(dict)
    selection_changed = Signal(set, str)
    frame_changed = Signal(int)
    image_sequence_changed = Signal(list, str)

    def __init__(self):
        super().__init__()

        # Create domain stores
        self._curves = CurveStore()
        self._selection = SelectionStore()
        self._frames = FrameStore()
        self._images = ImageStore()
        self._batch = BatchCoordinator()

        # Forward signals
        self._curves.curves_changed.connect(self.curves_changed)
        self._selection.selection_changed.connect(self.selection_changed)
        self._frames.frame_changed.connect(self.frame_changed)
        self._images.image_sequence_changed.connect(self.image_sequence_changed)

    # Delegation methods (maintain backward compatibility)

    def get_curve_data(self, name: str):
        """Delegate to curve store."""
        return self._curves.get_curve_data(name)

    def set_curve_data(self, name: str, data):
        """Delegate to curve store."""
        self._curves.set_curve_data(name, data)

    @property
    def active_curve(self):
        """Delegate to curve store."""
        return self._curves.active_curve

    @active_curve.setter
    def active_curve(self, name):
        """Delegate to curve store."""
        self._curves.active_curve = name

    # ... etc for all methods (delegate to appropriate store)
```

**4.1.7 Gradually Migrate Callers (3-8 hours):**

**Phase 4a: Services use stores directly**
```python
# Before:
state = get_application_state()
data = state.get_curve_data(name)

# After:
curves = container.curves  # Direct store access
data = curves.get_curve_data(name)
```

**Phase 4b: Controllers use stores directly**
**Phase 4c: Remove facade (OPTIONAL - breaking change)**

#### 4.2 Split InteractionService (5-10 hours)

**Already started in Phase 1** with 4 internal class extractions.

**Phase 4 completes it:**

1. **Promote internal classes to full services** (2 hours):
   - Move from `services/interaction/` to `services/`
   - Add full service interfaces
   - Register in ServiceContainer

2. **Update dependency injection** (2 hours):
   - ServiceContainer creates all 4 services
   - InteractionService becomes thin coordinator
   - Or eliminate InteractionService entirely (delegate to specific services)

3. **Update callers** (1-6 hours):
   - MainWindow uses specific services directly
   - Controllers use specific services directly

### Success Metrics

- [ ] ApplicationState: <300 lines (down from 1,160, 74% reduction)
- [ ] 5 domain stores created: CurveStore, SelectionStore, FrameStore, ImageStore, BatchCoordinator
- [ ] ApplicationState is thin facade (<300 lines of delegation)
- [ ] InteractionService: <500 lines (down from 1,761, 72% reduction)
- [ ] 4 interaction services extracted: MouseHandler, SelectionManager, CommandHistory, PointManipulator
- [ ] Average class size: <250 lines (was 400+)
- [ ] All 100+ tests pass
- [ ] Type checking: 0 errors
- [ ] No performance regression (benchmark critical paths)

### Verification Steps

```bash
# 1. Line count verification
wc -l stores/application_state.py  # Should be <300
wc -l stores/curve_store.py stores/selection_store.py stores/frame_store.py stores/image_store.py
wc -l services/interaction_service.py  # Should be <500

# 2. Verify stores created
ls stores/curve_store.py stores/selection_store.py stores/frame_store.py \
   stores/image_store.py stores/batch_coordinator.py

# 3. Run all tests
~/.local/bin/uv run pytest tests/ -v --tb=short

# 4. Type checking
./bpr --errors-only

# 5. Performance benchmark
~/.local/bin/uv run pytest tests/performance/ -v
# Compare with baseline from before Phase 4

# 6. Signal forwarding test
~/.local/bin/uv run pytest tests/stores/test_signal_forwarding.py -v

# 7. Comprehensive smoke test
python main.py
# - Load large curve file (1000+ points)
# - Test all features from Phases 1-3
# - Monitor for memory leaks (check task manager)
# - Verify signal propagation works correctly
```

### Rollback Strategy

**Git workflow:**
```bash
git checkout -b phase-4-god-class-refactoring

# Commit after each store creation:
git commit -m "Create CurveStore"
git commit -m "Create SelectionStore"
git commit -m "Create ApplicationState facade with delegation"
git commit -m "Migrate services to use CurveStore directly"

# If validation fails:
# OPTION 1: Revert specific store
git revert <commit-hash>

# OPTION 2: Revert entire phase
git checkout main
git branch -D phase-4-god-class-refactoring

# OPTION 3: Keep facade indefinitely (don't migrate callers)
# ApplicationState facade maintains full backward compatibility
```

**Risk Mitigation:**
- **Keep facade indefinitely** - Don't remove, deprecate only
- Create stores one at a time (not all at once)
- Test signal forwarding thoroughly
- Benchmark performance before/after
- Use event bus for store-to-store communication if needed
- Consider stopping before Phase 4c (facade removal)

**Risk:** VERY HIGH - 2,921 lines of code affected, complex signal forwarding, potential state synchronization bugs

---

## Cross-Phase Checkpoint Validation

**After completing each phase, validate ALL of the following before proceeding:**

### Automated Validation

```bash
#!/bin/bash
# checkpoint_validation.sh

echo "=== Checkpoint Validation ==="

# 1. Tests
echo -e "\n[1/5] Running tests..."
~/.local/bin/uv run pytest tests/ -v --tb=short || exit 1

# 2. Type checking
echo -e "\n[2/5] Type checking..."
./bpr --errors-only || exit 1

# 3. Linting
echo -e "\n[3/5] Linting..."
~/.local/bin/uv run ruff check . || exit 1

# 4. Code metrics
echo -e "\n[4/5] Code metrics..."
echo "ApplicationState lines: $(wc -l stores/application_state.py | awk '{print $1}')"
echo "InteractionService lines: $(wc -l services/interaction_service.py | awk '{print $1}')"
echo "get_application_state() calls: $(grep -r "get_application_state()" --include="*.py" | wc -l)"
echo "Protocol imports: $(grep -r "from protocols" --include="*.py" | wc -l)"

# 5. Build test
echo -e "\n[5/5] Build test..."
python -m py_compile main.py || exit 1

echo -e "\n✅ All validation passed!"
```

### Manual Smoke Test Checklist

Run application and test:

- [ ] **Launch:** Application starts without errors
- [ ] **Load curve:** Load existing curve file (e.g., `.txt` format)
- [ ] **View:** Zoom, pan, fit to view all work
- [ ] **Select:** Click to select points, drag to box-select
- [ ] **Edit:** Move points with mouse, nudge with numpad
- [ ] **Timeline:** Navigate frames, points move correctly
- [ ] **Undo/Redo:** Ctrl+Z and Ctrl+Y work for all operations
- [ ] **Multi-curve:** Switch between curves, operations target correct curve
- [ ] **Image sequence:** Load images, verify display synchronized with frame
- [ ] **Save:** Save curve, reload, verify data integrity
- [ ] **Performance:** No lag during zoom/pan, smooth frame navigation

**If any smoke test fails, STOP and debug before proceeding to next phase.**

---

## Risk Matrix

| Phase | Risk Level | Key Risks | Mitigation |
|-------|-----------|-----------|------------|
| **1** | 🟢 LOW | Breaking internal classes | Check external imports, frequent commits |
| **2** | 🟡 MEDIUM | Protocol conformance failures | @runtime_checkable, incremental migration |
| **3** | 🟠 HIGH | Circular dependencies, init order | Map dependencies first, feature flag |
| **4** | 🔴 VERY HIGH | Signal forwarding, state sync | Keep facade indefinitely, benchmark |

---

## Success Tracking

### Overall Metrics

| Metric | Baseline | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Target |
|--------|----------|---------|---------|---------|---------|--------|
| **Quality Score** | 62 | 77 | 87 | 92 | 100 | 100 |
| **ApplicationState (lines)** | 1,160 | 1,160 | 1,160 | 1,160 | <300 | <300 |
| **InteractionService (lines)** | 1,761 | ~1,450 | ~1,450 | ~1,450 | <500 | <500 |
| **Protocol Imports** | 37 | 37 | 80+ | 80+ | 80+ | 80+ |
| **get_*_state/service()** | 730 | 730 | <700 | <150 | <150 | <150 |
| **TYPE_CHECKING guards** | 181 | 181 | <150 | <100 | <100 | <100 |
| **Avg Class Size** | 400+ | ~350 | ~350 | ~350 | <250 | <250 |
| **Tests Passing** | 100% | 100% | 100% | 100% | 100% | 100% |

---

## Recommended Implementation Path

### For Personal Tool (RECOMMENDED)

**Stop after Phase 2 or 3:**

**Phase 1 + 2 (12.5-16.5 hours):**
- **Benefit:** 62 → 87 points (+40% improvement)
- **Effort:** 38% of total time
- **Outcome:** 80% of total benefit
- **Risk:** LOW → MEDIUM
- **Delivers:** Clean code, testable architecture, reduced complexity

**Phase 1 + 2 + 3 (24.5-32.5 hours):**
- **Benefit:** 62 → 92 points (+48% improvement)
- **Effort:** 73% of total time
- **Outcome:** 92% of total benefit
- **Risk:** LOW → MEDIUM → HIGH
- **Delivers:** Above + true DI, no service locators, excellent testability

**Phase 4 (optional, add 20-30 hours):**
- **Benefit:** 92 → 100 points (+9% additional improvement)
- **Effort:** +45% more time
- **Outcome:** Last 8% of benefit
- **Risk:** VERY HIGH
- **ROI:** Questionable for single-user tool

### For Team/Production Tool

**Complete all 4 phases:**
- Full enterprise-grade architecture
- Optimal maintainability
- Clear separation of concerns
- Worth the 20-30 hour investment for Phase 4

---

## Conclusion

This plan provides a comprehensive, phased approach to refactoring the CurveEditor codebase. **For a personal tool, stopping after Phase 2 or 3 is recommended**, achieving 80-92% of the benefit with manageable risk.

**Next steps:**
1. Review this plan
2. Decide on phase scope (1-2, 1-3, or all 4)
3. Create feature branch for chosen phase
4. Begin implementation with frequent commits
5. Validate at each checkpoint
6. Celebrate wins!

---

*Generated from verified codebase consolidation analysis*
*Based on SOLID_ANALYSIS_REPORT.md and CODEBASE_CONSOLIDATION_SYNTHESIS.md*
