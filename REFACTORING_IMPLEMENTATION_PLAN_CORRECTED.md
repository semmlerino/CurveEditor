# CurveEditor Refactoring Implementation Plan (CORRECTED)

**Version:** 2.0 (Corrected based on agent verification)
**Date:** 2025-10-25
**Changes:** Fixed based on PLAN_VERIFICATION_REPORT.md and AGENT_VERIFICATION_SYNTHESIS.md

---

## ⚠️ IMPORTANT: Verification Results

This plan has been **corrected** based on comprehensive verification by 5 specialized agents who analyzed the actual codebase:

**Original plan issues found:**
- ❌ Phase 1: Internal class extraction not viable (85% incomplete, would worsen design)
- ❌ Phase 2: Wrong protocols proposed (missing 4 UI state properties)
- ❌ Phase 3: Critical stale state bug not addressed, wrong dependencies, effort underestimated 4×
- ❌ Baseline metrics: TYPE_CHECKING = 603 (not 181 claimed) - 233% error
- ❌ Phase dependencies: Claimed linear, actually independent

**Corrected plan:**
- ✅ Phase 1: Removed internal class extraction, kept valuable tasks
- ✅ Phase 1.5: Added controller tests (enables Phase 2 verification)
- ✅ Phase 2: Fixed protocols, type annotations only
- ✅ Phase 3: Fixed dependencies, hybrid approach, realistic effort
- ✅ Metrics: Corrected baselines

**Verification confidence:** VERY HIGH (95%+) - all claims verified against actual code

---

## Overview

**RECOMMENDED SCOPE:** Execute Phases 1 + 1.5 + 2 ONLY, skip Phases 3-4

**Revised Total Effort:** 13.5-17.5 hours (was 44.5-62.5)
**Revised Quality Improvement:** 62 → 80 points (+29%, was +61%)
**ROI:** 1.03-1.33 points/hour (EXCELLENT)

**Why stop after Phase 2:**
- ✅ Achieves 60% of total possible benefit efficiently
- ✅ Low-medium risk (with controller tests)
- ✅ High ROI (1.0-1.3 pts/hr vs 0.08-0.32 for Phases 3-4)
- 🔴 Phase 3 has critical stale state bug, 4× underestimated effort
- 🔴 Phase 4 ROI too low for personal tool (0.2-0.3 pts/hr)

---

## Phase Dependencies (CORRECTED)

**IMPORTANT:** Original plan claimed strict linear dependencies. **Verification shows phases are mostly independent.**

```
┌─────────────────────────────────────────────────────────────┐
│                  Phase 1: Quick Wins (REVISED)              │
│                  ✓ Can start immediately                    │
│                  ✓ 1.5 hours, +8 points                     │
│                  ✓ LOW risk                                 │
│                  ✓ SKIP internal class extraction          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 1.5: Controller Tests (NEW)              │
│              • Independent, enables Phase 2 verification   │
│              • 4-6 hours, risk reduction                    │
│              • LOW risk                                     │
│              • REQUIRED before Phase 2                      │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│         Phase 2: Protocol Adoption (CORRECTED)              │
│         • Requires Phase 1.5 (controller tests)             │
│         • 8-10 hours, +10 points                            │
│         • LOW-MEDIUM risk (with tests)                      │
│         • TYPE ANNOTATIONS ONLY                             │
└─────────────────────────────────────────────────────────────┘

   ⚠️  STOP HERE - Recommended stopping point (60% benefit achieved)

                         ↓ (NOT RECOMMENDED)
┌─────────────────────────────────────────────────────────────┐
│     Phase 3: Dependency Injection (CORRECTED)               │
│     • 48-66 hours (NOT 12-16), +5 points                    │
│     • VERY HIGH risk                                        │
│     • ROI: 0.08-0.10 pts/hr (POOR)                          │
│     • ⚠️  SKIP - Stale state bug, low ROI                    │
└─────────────────────────────────────────────────────────────┘
                         ↓ (NOT RECOMMENDED)
┌─────────────────────────────────────────────────────────────┐
│           Phase 4: God Class Split                          │
│           • 25-40 hours, +8 points                          │
│           • VERY HIGH risk                                  │
│           • ROI: 0.20-0.32 pts/hr (POOR)                    │
│           • ⚠️  SKIP - Too low ROI for personal tool         │
└─────────────────────────────────────────────────────────────┘
```

**Checkpoint Validation:** After each phase, run tests, type checking, and manual smoke test.

---

## Phase 1: Quick Wins (REVISED)

**Goal:** Low-effort, high-impact improvements (documentation, cleanup)

**Duration:** 1.5 hours (was 2.5)
**Impact:** +8 points (62→70) (was +15)
**ROI:** 5.3 points/hour
**Risk:** LOW

### Changes from Original Plan

**REMOVED:** Task 1.1 (Extract Internal Classes from InteractionService)
- **Why:** Agent verification found plan is 85% incomplete, would increase complexity
- **Evidence:** Plan shows 1-2 methods per class, actual has 6-12 methods per class
- **Conclusion:** Internal classes are GOOD architecture (facade pattern), extraction not viable

**KEPT:** Tasks 1.2-1.4 (still valuable)

---

### Tasks

#### ~~1.1 Extract Internal Classes~~ **REMOVED - NOT VIABLE**

**Verification Finding:**
- ❌ Plan shows `MouseHandler.handle_click()` (1 method)
- ✅ Actual `_MouseHandler` has 6 methods: `__init__`, `handle_mouse_press`, `handle_mouse_move`, `handle_mouse_release`, `handle_wheel_event`, `handle_key_event`
- ❌ Plan missing: `_SelectionManager` spatial index (PointIndex - 64.7× performance optimization)
- ❌ Plan missing: `_CommandHistory` CommandManager integration (dual-mode legacy support)
- ❌ Plan missing: Complex circular dependencies between internal classes

**Conclusion:** Internal classes are tightly coupled by design (facade pattern). Extraction would:
1. Increase complexity (need to inject 2-3 dependencies into each class)
2. Create circular imports (classes depend on each other)
3. Break encapsulation (internal implementation → public interfaces)
4. Provide zero benefit (current design is already well-organized)

**Recommendation:** **Keep internal classes as-is** - they're good architecture.

---

#### 1.2 Add Missing Docstrings (0.83 hours / 50 minutes)

**Unchanged from original plan.**

Find methods without docstrings:
```bash
~/.local/bin/uv run ruff check . --select D102,D103
```

Add numpy-style docstrings to 10 public methods in:
- `stores/application_state.py`: Public methods missing docstrings
- `services/data_service.py`: Core data operations
- `services/interaction_service.py`: Public API methods

**Example:**
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
```

**Files Modified:**
- `stores/application_state.py`
- `services/data_service.py`
- `services/interaction_service.py`

**Verification:** Run `~/.local/bin/uv run ruff check . --select D102,D103` (should show fewer violations)

---

#### 1.3 Remove Dead Code (0.33 hours / 20 minutes)

**Unchanged from original plan.**

Search for unused code patterns:
```bash
grep -r "TODO.*remove\|DEPRECATED\|UNUSED" --include="*.py"
```

**Common patterns to remove:**
- Commented-out code blocks (>10 lines)
- Unused imports flagged by ruff
- Dead conditional branches (if False:)
- Deprecated methods with no callers

**Files to check:**
- `ui/main_window.py`: Historical comment blocks
- `services/*`: Old integration code
- `core/commands/*`: Superseded command variants

**Verification:** Run `~/.local/bin/uv run ruff check . --select F401` (unused imports)

---

#### 1.4 Reduce Nesting (0.33 hours / 20 minutes)

**Unchanged from original plan.**

Find deeply nested code:
```bash
grep -r "        if.*:$" --include="*.py" | grep -v test
```

**Refactor patterns:**

Before:
```python
def process_data(self, data):
    if data:
        if data.is_valid():
            if data.has_points():
                # Process
                pass
```

After (guard clauses):
```python
def process_data(self, data):
    if not data:
        return
    if not data.is_valid():
        return
    if not data.has_points():
        return

    # Process (less indentation)
```

**Targets:**
- `services/interaction_service.py`: Event handlers
- `ui/controllers/*`: Action handlers

**Verification:** Manual code review

---

### Phase 1 Success Metrics

- ✅ Docstrings added to 10+ methods
- ✅ Unused code removed (check git diff)
- ✅ Nesting reduced in 5+ methods
- ✅ All tests pass: `~/.local/bin/uv run pytest tests/`
- ✅ Type checking clean: `./bpr --errors-only`

---

## Phase 1.5: Controller Tests (NEW - CRITICAL)

**Goal:** Enable Phase 2 verification by writing minimal controller tests

**Duration:** 4-6 hours
**Impact:** Risk reduction (VERY HIGH → MEDIUM for Phase 2)
**Risk:** LOW
**Priority:** **REQUIRED** before Phase 2

### Why This Phase Is Critical

**Verification Finding:**
- ✅ Controllers have **0 test files** (verified with `find tests -name "*controller*.py"`)
- ❌ Phase 2 will refactor 8 controllers with NO way to verify behavior preservation
- 🔴 Risk: Silent regressions (code breaks but tests don't catch it because tests don't exist)

**Without this phase:**
- Phase 2 risk: **VERY HIGH** (blind refactoring)
- Only validation: Manual smoke testing (error-prone)

**With this phase:**
- Phase 2 risk: **LOW-MEDIUM** (automated verification)
- Validation: 8 test files covering critical paths

---

### Tasks

#### 1.5.1 Create Controller Test Structure (1 hour)

**Create test files for 8 controllers:**

```bash
# Create directory if needed
mkdir -p tests/controllers

# Create test files (with basic structure)
touch tests/controllers/test_action_handler_controller.py
touch tests/controllers/test_frame_change_coordinator.py
touch tests/controllers/test_point_editor_controller.py
touch tests/controllers/test_signal_connection_manager.py
touch tests/controllers/test_timeline_controller.py
touch tests/controllers/test_ui_initialization_controller.py
touch tests/controllers/test_view_camera_controller.py
touch tests/controllers/test_view_management_controller.py
```

**Basic test template:**
```python
#!/usr/bin/env python
"""Tests for ActionHandlerController."""

import pytest
from unittest.mock import Mock
from ui.controllers.action_handler_controller import ActionHandlerController


class TestActionHandlerController:
    """Tests for ActionHandlerController."""

    @pytest.fixture
    def mock_state_manager(self):
        """Mock StateManager."""
        state = Mock()
        state.zoom_level = 1.0
        state.pan_offset = (0.0, 0.0)
        state.is_modified = False
        return state

    @pytest.fixture
    def mock_main_window(self):
        """Mock MainWindow."""
        window = Mock()
        window.status_label = Mock()
        window.curve_widget = Mock()
        return window

    @pytest.fixture
    def controller(self, mock_state_manager, mock_main_window):
        """Create controller with mocks."""
        return ActionHandlerController(mock_state_manager, mock_main_window)

    def test_initialization(self, controller, mock_state_manager, mock_main_window):
        """Test controller initializes correctly."""
        assert controller.state_manager == mock_state_manager
        assert controller.main_window == mock_main_window

    def test_zoom_in(self, controller, mock_state_manager):
        """Test zoom in action."""
        initial_zoom = 1.0
        mock_state_manager.zoom_level = initial_zoom

        controller.on_action_zoom_in()

        assert mock_state_manager.zoom_level == initial_zoom * 1.2

    def test_zoom_out(self, controller, mock_state_manager):
        """Test zoom out action."""
        initial_zoom = 1.0
        mock_state_manager.zoom_level = initial_zoom

        controller.on_action_zoom_out()

        assert mock_state_manager.zoom_level == initial_zoom / 1.2
```

---

#### 1.5.2 Write Critical Path Tests (3-5 hours)

**For each of 8 controllers, write 3-5 tests covering:**

1. **Initialization test** - Verify controller sets up correctly
2. **Primary action test** - Test most-used functionality
3. **State mutation test** - Verify controller changes state correctly
4. **Error handling test** (optional) - Test graceful failure

**Priority controllers (start here):**
1. **ActionHandlerController** - 5 tests (zoom, pan, reset, file operations)
2. **ViewManagementController** - 4 tests (fit, center, reset)
3. **TimelineController** - 3 tests (play, pause, frame change)

**Lower priority:**
4. **PointEditorController** - 3 tests
5. **FrameChangeCoordinator** - 3 tests
6. **SignalConnectionManager** - 2 tests (connection setup)
7. **UIInitializationController** - 2 tests (init components)
8. **ViewCameraController** - 2 tests (camera movement)

**Total test count target:** 24-30 tests (3-4 tests × 8 controllers)

**Test coverage goal:** Not 100%, but **critical paths covered** (actions that Phase 2 will refactor)

---

### Phase 1.5 Success Metrics

- ✅ 8 controller test files created
- ✅ 24-30 tests written (3-4 per controller)
- ✅ All tests pass: `~/.local/bin/uv run pytest tests/controllers/`
- ✅ Critical paths covered: zoom, pan, frame change, view management
- ✅ Enables verification for Phase 2 protocol refactoring

**Verification:**
```bash
~/.local/bin/uv run pytest tests/controllers/ -v
# Should show 24-30 tests passing
```

---

## Phase 2: Protocol Adoption (CORRECTED)

**Goal:** Update type annotations to use protocols (NO runtime changes)

**Duration:** 8-10 hours (was 10-14)
**Impact:** +10 points (70→80)
**ROI:** 1.0-1.25 points/hour
**Risk:** LOW-MEDIUM (with Phase 1.5 tests), VERY HIGH (without tests)

### Changes from Original Plan

**FIXED:**
1. ✅ Extend StateManagerProtocol with 4 missing properties (CRITICAL)
2. ✅ Use StateManagerProtocol (not FrameProvider & CurveDataProvider)
3. ✅ Type annotations ONLY (no constructor changes)
4. ✅ Removed service/command DI tasks (moved to Phase 3)

**Original plan errors:**
- ❌ Proposed `FrameProvider & CurveDataProvider` for ActionHandlerController
- ❌ Missing 4 properties: `zoom_level`, `pan_offset`, `smoothing_window_size`, `smoothing_filter_type`
- ❌ Included service constructor changes (breaking changes - that's Phase 3)

---

### Tasks

#### 2.1 Extend StateManagerProtocol (2 hours) **NEW - CRITICAL FIX**

**Problem:** StateManagerProtocol is incomplete.

**Verification Finding:**
```python
# ActionHandlerController uses these properties (from grep):
Line 163: self.state_manager.zoom_level        # ← NOT in StateManagerProtocol
Line 193: self.state_manager.pan_offset        # ← NOT in StateManagerProtocol
Line 255: self.state_manager.smoothing_window_size  # ← NOT in StateManagerProtocol
Line 256: self.state_manager.smoothing_filter_type  # ← NOT in StateManagerProtocol
```

**Current StateManagerProtocol has:**
- ✅ `is_modified: bool`
- ✅ `reset_to_defaults() -> None`
- ✅ `current_frame` property

**Must add:**
- ❌ `zoom_level` property (read/write)
- ❌ `pan_offset` property (read/write)
- ❌ `smoothing_window_size` property (read)
- ❌ `smoothing_filter_type` property (read)

**Solution:** Extend `protocols/ui.py` StateManagerProtocol:

```python
# Add to protocols/ui.py StateManagerProtocol (after line 103)

@runtime_checkable
class StateManagerProtocol(Protocol):
    """Protocol for state manager."""

    # ... existing properties ...

    # VIEW STATE PROPERTIES (NEW - added for Phase 2 correction)

    @property
    def zoom_level(self) -> float:
        """Get current zoom level."""
        ...

    @zoom_level.setter
    def zoom_level(self, value: float) -> None:
        """Set zoom level."""
        ...

    @property
    def pan_offset(self) -> tuple[float, float]:
        """Get pan offset (x, y)."""
        ...

    @pan_offset.setter
    def pan_offset(self, value: tuple[float, float]) -> None:
        """Set pan offset."""
        ...

    @property
    def smoothing_window_size(self) -> int:
        """Get smoothing window size."""
        ...

    @property
    def smoothing_filter_type(self) -> str:
        """Get smoothing filter type."""
        ...
```

**Files Modified:**
- `protocols/ui.py` (add 4 properties to StateManagerProtocol)

**Verification:**
```bash
./bpr protocols/ui.py --errors-only
# Should pass (no errors)
```

---

#### 2.2 Update ActionHandlerController Annotations (1 hour)

**Change type annotations ONLY (no runtime changes):**

**Before:**
```python
# ui/controllers/action_handler_controller.py:35
def __init__(self, state_manager: "StateManager", main_window: "MainWindow"):
    self.state_manager: StateManager = state_manager
    self.main_window: MainWindow = main_window
```

**After:**
```python
# ui/controllers/action_handler_controller.py:35
from protocols.ui import StateManagerProtocol, MainWindowProtocol

def __init__(self, state_manager: StateManagerProtocol, main_window: MainWindowProtocol):
    self.state_manager: StateManagerProtocol = state_manager
    self.main_window: MainWindowProtocol = main_window
```

**IMPORTANT:** Only change type annotations, NOT runtime behavior.

**Files Modified:**
- `ui/controllers/action_handler_controller.py`

**Verification:**
```bash
./bpr ui/controllers/action_handler_controller.py --errors-only
~/.local/bin/uv run pytest tests/controllers/test_action_handler_controller.py -v
# Both should pass
```

---

#### 2.3 Update Other Controller Annotations (3-4 hours)

**Apply same pattern to 7 other controllers:**

1. **FrameChangeCoordinator** - Use MainWindowProtocol
2. **PointEditorController** - Use StateManagerProtocol
3. **SignalConnectionManager** - Use MainWindowProtocol
4. **TimelineController** - Use StateManagerProtocol, MainWindowProtocol
5. **UIInitializationController** - Use MainWindowProtocol
6. **ViewCameraController** - Use MainWindowProtocol
7. **ViewManagementController** - Use MainWindowProtocol

**Pattern for each:**
1. Import protocols: `from protocols.ui import StateManagerProtocol, MainWindowProtocol`
2. Update `__init__` parameter types
3. Update instance attribute types
4. Keep TYPE_CHECKING imports (for concrete types if needed elsewhere)

**Files Modified:**
- `ui/controllers/frame_change_coordinator.py`
- `ui/controllers/point_editor_controller.py`
- `ui/controllers/signal_connection_manager.py`
- `ui/controllers/timeline_controller.py`
- `ui/controllers/ui_initialization_controller.py`
- `ui/controllers/view_camera_controller.py`
- `ui/controllers/view_management_controller.py`

**Verification after EACH controller:**
```bash
./bpr ui/controllers/<controller_file>.py --errors-only
~/.local/bin/uv run pytest tests/controllers/test_<controller_name>.py -v
```

---

#### ~~2.4-2.5 Service/Command Constructor Updates~~ **REMOVED - MOVED TO PHASE 3**

**Why removed:**
- ❌ Service constructor changes are **breaking changes** (parameterless → parameterful)
- ❌ This is full dependency injection (Phase 3), not type annotation (Phase 2)
- ❌ Commands have stale state timing issue (must solve before DI)

**Scope of Phase 2:** Type annotations only. No constructor changes.

---

### Phase 2 Success Metrics (CORRECTED)

**Before:**
- ❌ TYPE_CHECKING guards: <150 (down from 181) ← **WRONG BASELINE**
- ❌ Service/command signatures updated ← **WRONG SCOPE**

**After (Corrected):**
- ✅ TYPE_CHECKING guards: <550 (down from 603) - 9% reduction
- ✅ Protocol imports: 55+ (up from 51) - increased protocol adoption
- ✅ StateManagerProtocol extended with 4 properties
- ✅ 8 controllers use protocols for type annotations
- ✅ All tests pass: `~/.local/bin/uv run pytest tests/`
- ✅ Type checking clean: `./bpr --errors-only`
- ✅ Controller tests verify behavior preserved

**Verification Commands:**
```bash
# Check TYPE_CHECKING reduction
grep -r "TYPE_CHECKING" --include="*.py" --exclude-dir=.venv --exclude-dir=tests | wc -l
# Should be <550 (from 603)

# Check protocol adoption
grep -r "from protocols" --include="*.py" --exclude-dir=.venv --exclude-dir=tests | wc -l
# Should be 55+

# Run all tests
~/.local/bin/uv run pytest tests/ -v

# Type check
./bpr --errors-only
```

---

## ⚠️ RECOMMENDED STOPPING POINT ⚠️

**Phases 1 + 1.5 + 2 Complete:**
- ✅ Total effort: 13.5-17.5 hours
- ✅ Quality improvement: +18 points (62 → 80/100)
- ✅ ROI: 1.03-1.33 points/hour (EXCELLENT)
- ✅ Risk: LOW-MEDIUM (manageable)

**Why stop here:**
1. ✅ 60% of total benefit achieved efficiently
2. ✅ Codebase significantly improved (docstrings, protocols, tests, cleanup)
3. ✅ High ROI maintained throughout
4. 🔴 Phase 3 has very low ROI (0.08-0.10 pts/hr) and critical bugs
5. 🔴 Phase 4 has very low ROI (0.20-0.32 pts/hr)

**Stopping here is the pragmatic choice for a personal tool.**

---

## Phase 3: Dependency Injection (CORRECTED) - **NOT RECOMMENDED**

**Goal:** Replace service locators with dependency injection

**Duration:** 48-66 hours (was 12-16) - **4× UNDERESTIMATED**
**Impact:** +5 points (80→85)
**ROI:** 0.08-0.10 points/hour (POOR)
**Risk:** VERY HIGH

### Why This Phase Is Not Recommended

**Critical Issues Found:**

1. **🔴 SHOW-STOPPER: Command Stale State Bug**
   - Commands created at startup (`DeletePointsCommand()` at line 369)
   - If injecting ApplicationState in constructor, captures stale state
   - Timeline: App starts (empty state) → User loads data → User presses Delete → **Command has stale state from startup**
   - **Impact:** Data corruption, wrong curve operations

2. **🔴 Wrong Service Dependencies in Original Plan**
   - Plan claims DataService needs ApplicationState → **WRONG** (0 calls verified)
   - Plan claims InteractionService needs DataService → **WRONG** (needs TransformService)

3. **🔴 Effort Severely Underestimated**
   - Plan: 12-16 hours
   - Actual: 48-66 hours (service locator count: 946, not 730)
   - **4× underestimate**

4. **🔴 Very Low ROI**
   - 48-66 hours for +5 points = 0.08-0.10 pts/hr
   - Compare: Phases 1-2 = 1.0-1.3 pts/hr (10-15× better)

**Recommendation:** **SKIP PHASE 3** unless critical architectural need.

---

### IF Proceeding Despite Risks (Corrected Approach)

**Only proceed if:**
- Converting to multi-maintainer team project
- Have 48-66 hours available
- Willing to accept very low ROI (0.08-0.10 pts/hr)
- Critical need for dependency injection

---

#### 3.1 Service Dependency Mapping (CORRECTED)

**Correct Service Dependencies:**

```python
ApplicationState (no deps)
    ↓
TransformService (no deps)
    ↓
DataService (no service deps - only optional protocol deps)
    ↓
InteractionService (needs: ApplicationState, TransformService)
    ↓
UIService (needs: ApplicationState)
```

**Correct ServiceContainer:**

```python
# core/dependency_container.py (new file)

class ServiceContainer:
    """Centralized dependency injection container."""

    def __init__(self):
        # State first (no dependencies)
        self._state = ApplicationState()

        # Services in dependency order
        self._transform = TransformService()  # No deps
        self._data = DataService()  # NO state dependency (plan was wrong)
        self._ui = UIService(state=self._state)
        self._interaction = InteractionService(
            state=self._state,
            transform_service=self._transform  # CORRECTED from data_service
        )
```

**Original plan errors:**
- ❌ `DataService(state=self._state)` - DataService doesn't use ApplicationState
- ❌ `InteractionService(..., data_service=self._data)` - needs transform_service

---

#### 3.2 Hybrid Approach - Services + Command Solution (CORRECTED)

**Problem:** Commands have mixed lifecycle (startup + per-action).

**Solution: HYBRID APPROACH**

**What gets DI:**
- ✅ Services (DataService, InteractionService, TransformService, UIService)
- ✅ Controllers (already using protocols from Phase 2)
- ✅ Long-lived objects

**What keeps service locator:**
- ✅ Commands (need fresh ApplicationState at execute() time, not constructor time)
- ✅ Short-lived objects created frequently

**Command Pattern (NO CHANGES from current):**

```python
# core/commands/curve_commands.py - KEEP CURRENT PATTERN

class SmoothCommand(CurveDataCommand):
    def __init__(self, description: str, window_size: int):
        super().__init__(description)
        self.window_size = window_size
        # NO state injection - will call get_application_state() in execute()

    def execute(self, main_window: MainWindowProtocol) -> bool:
        app_state = get_application_state()  # Fresh state at execute() time ✅
        # ... use app_state safely
```

**Why hybrid works:**
- Services: Singletons, injected once → DI safe
- Commands: Created at varying times → service locator safe
- Reduces migration scope by 35% (331 command calls stay as-is)

---

#### 3.3 Service Constructor Updates (4-8 hours)

**Update service constructors to accept dependencies:**

```python
# services/interaction_service.py

class InteractionService:
    def __init__(
        self,
        state: ApplicationState,
        transform_service: TransformService  # CORRECTED from data_service
    ):
        self._state = state
        self._transform_service = transform_service

        # Remove module-level _get_transform_service() calls
        # Use self._transform_service instead
```

**Services to update:**
- `services/interaction_service.py` - Add state + transform_service params
- `services/ui_service.py` - Add state param
- `services/data_service.py` - NO CHANGES (already has optional protocol params)
- `services/transform_service.py` - NO CHANGES (no dependencies)

**Update service locator in `services/__init__.py`:**

```python
# services/__init__.py

_container: ServiceContainer | None = None

def get_data_service() -> DataService:
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container.data

# Similar for other services...
```

**Files Modified:**
- `services/interaction_service.py`
- `services/ui_service.py`
- `services/__init__.py`
- `core/dependency_container.py` (new)

**Effort:** 4-8 hours (only 5 instantiation sites in services/__init__.py)

---

#### 3.4 Replace Service Locators (40-50 hours) **MASSIVE EFFORT**

**Scope:** ~615 service locator calls (excluding commands)

**Breakdown:**
- get_application_state(): ~567 calls (constructor injection)
- get_data_service(): 5 calls
- get_interaction_service(): 2 calls
- get_transform_service(): 10 calls (remove from interaction_service.py)
- get_ui_service(): 1 call

**Pattern for each call site:**

Before:
```python
def some_method(self):
    state = get_application_state()
    data = state.get_curve_data(...)
```

After:
```python
def __init__(self, state: ApplicationState):
    self._state = state

def some_method(self):
    data = self._state.get_curve_data(...)
```

**Files to update:** ~100+ files across:
- `ui/` - MainWindow, widgets, controllers
- `services/` - Internal methods
- `rendering/` - Renderer classes
- `core/` - Various utilities

**Effort estimate:** 40-50 hours (615 calls × 3-5 min each)

**This is why Phase 3 is not recommended - massive manual migration.**

---

#### 3.5 Test Fixture Updates (4-8 hours)

**Update 10+ service test files:**

Before:
```python
def test_data_service():
    service = get_data_service()  # Service locator
```

After:
```python
@pytest.fixture
def service_container():
    return ServiceContainer()

def test_data_service(service_container):
    service = service_container.data  # DI from container
```

**Files to update:**
- All 10+ service test files in `tests/`

---

### Phase 3 Success Metrics (CORRECTED)

- ✅ ServiceContainer created with correct dependencies
- ✅ 4 services use dependency injection
- ✅ ~615 service locator calls replaced (excluding commands)
- ✅ Commands UNCHANGED (keep get_application_state())
- ✅ All tests pass: `~/.local/bin/uv run pytest tests/`
- ✅ Type checking clean: `./bpr --errors-only`

**Estimated Total Effort:** 48-66 hours (NOT 12-16)

**Verification:**
```bash
# Check remaining service locators (should be ~331 in commands only)
grep -r "get_application_state()" --include="*.py" --exclude-dir=tests | wc -l

# Should be ~331 (commands only, services migrated)
```

---

## Phase 4: God Class Refactoring - **NOT RECOMMENDED**

**Goal:** Split ApplicationState into domain stores with facade

**Duration:** 25-40 hours
**Impact:** +8 points (85→93, or 80→88 if skipped Phase 3)
**ROI:** 0.20-0.32 points/hour (POOR)
**Risk:** VERY HIGH

### Why This Phase Is Not Recommended

**Verification Findings:**

✅ **Plan is architecturally sound:**
- Metrics 100% accurate (1,160 lines confirmed)
- Clean domain boundaries (79% single-domain methods)
- Facade pattern viable

🔴 **But ROI too low for personal tool:**
- 25-40 hours for +8 points = 0.20-0.32 pts/hr
- Compare: Phases 1-2 = 1.0-1.3 pts/hr (4-6× better)
- Diminishing returns: 20% of benefit for 50% of effort

**When to reconsider:**
- ApplicationState grows to 2,000+ lines
- Team size increases (multiple maintainers)
- State synchronization bugs emerge repeatedly
- Performance issues related to state management

**For personal tool:** ApplicationState at 1,160 lines is manageable. **Don't fix what isn't broken.**

---

### Phase 4-Lite Alternative (If Must Proceed)

**Instead of full split, extract simplest domains:**

**Option A: FrameStore + ImageStore (10-12 hours, LOW RISK)**
- 7 methods, 2 signals total
- Zero cross-domain coupling
- Reduces ApplicationState by 18%
- Proves facade pattern with minimal risk

**Option B: SelectionStore (10-15 hours, MEDIUM RISK)**
- 11 methods, 2 signals
- Medium coupling (reacts to curve deletions)
- Reduces ApplicationState by 22%

**Effort:** 40% of full Phase 4, lower risk, incremental approach.

---

## Baseline Metrics (CORRECTED)

**Original plan had significant metric errors. Corrected baselines:**

| Metric | Original Claim | Actual (Verified) | Correction |
|--------|----------------|-------------------|------------|
| ApplicationState lines | 1,160 | 1,160 | ✅ Correct |
| InteractionService lines | 1,761 | 1,761 | ✅ Correct |
| MainWindow lines | 1,315 | 1,315 | ✅ Correct |
| get_application_state() | 730 | 695 | 🔴 -4.8% error |
| **TYPE_CHECKING** | **181** | **603** | **🔴 -233% error** |
| Protocol definitions | 50 | 41 | 🔴 -18% error |
| Protocol imports | 37 | 51 | 🟡 +38% (higher) |
| Internal classes | 4 | 4 | ✅ Correct |

**Key correction:** TYPE_CHECKING baseline is 603 (not 181). Success targets revised accordingly.

---

## Success Tracking (CORRECTED)

| Metric | Baseline | Phase 1 | Phase 1.5 | Phase 2 | Phase 3 | Phase 4 |
|--------|----------|---------|-----------|---------|---------|---------|
| **Quality Score** | 62 | 70 | 70 | 80 | 85 | 93 |
| ApplicationState lines | 1,160 | 1,160 | 1,160 | 1,160 | 1,160 | ~900 |
| TYPE_CHECKING | **603** | ~600 | ~600 | **<550** | <400 | <300 |
| Protocol imports | 51 | 51 | 51 | **55+** | 80+ | 80+ |
| Controller tests | **0** | 0 | **24-30** | 24-30 | 24-30 | 24-30 |
| Service locators | 946 | 946 | 946 | 946 | **<350** | <350 |
| Risk Level | - | LOW | LOW | LOW-MED | VERY HIGH | VERY HIGH |
| Cumulative Effort | 0h | 1.5h | 5.5-7.5h | 13.5-17.5h | 61.5-83.5h | 86.5-123.5h |
| Cumulative Benefit | 0 | +8 | +8 | +18 | +23 | +31 |
| ROI | - | 5.3 | 1.5 | 1.33 | 0.37 | 0.36 |

**Bold** = Corrected values (different from original plan)

---

## Checkpoint Validation Script (CORRECTED)

```bash
#!/bin/bash
# checkpoint_validation.sh - Run after each phase

echo "=== Checkpoint Validation ==="

# 1. Tests
echo -e "\n[1/5] Running tests..."
~/.local/bin/uv run pytest tests/ -v --tb=short || { echo "❌ Tests failed"; exit 1; }

# 2. Type checking
echo -e "\n[2/5] Type checking..."
./bpr --errors-only || { echo "❌ Type checking failed"; exit 1; }

# 3. Linting
echo -e "\n[3/5] Linting..."
~/.local/bin/uv run ruff check . || { echo "⚠️  Linting issues found"; }

# 4. Code metrics (CORRECTED BASELINES)
echo -e "\n[4/5] Code metrics..."
echo "ApplicationState lines: $(wc -l stores/application_state.py | awk '{print $1}')"
echo "TYPE_CHECKING count: $(grep -r "TYPE_CHECKING" --include="*.py" --exclude-dir=.venv --exclude-dir=tests --exclude-dir=__pycache__ | wc -l)"
echo "Protocol imports: $(grep -r "from protocols" --include="*.py" --exclude-dir=.venv --exclude-dir=tests | wc -l)"
echo "Controller tests: $(find tests/controllers -name "test_*.py" -type f 2>/dev/null | wc -l)"

# 5. Build test
echo -e "\n[5/5] Build test..."
python -m py_compile main.py || { echo "❌ Build failed"; exit 1; }

echo -e "\n✅ All validation passed!"
```

---

## Rollback Strategy

**If phase fails validation:**

```bash
# Immediate rollback
git reset --hard
git clean -fd

# If committed
git log --oneline -5  # Find commit before phase
git reset --hard <commit-hash>

# Verify rollback
~/.local/bin/uv run pytest tests/
./bpr --errors-only
```

**Feature flag alternative** (for Phase 3 if proceeding):
```python
# Enable gradual migration
USE_DEPENDENCY_INJECTION = False  # Toggle per module
```

---

## Recommended Implementation Path

**EXECUTE: Phases 1 + 1.5 + 2**

```bash
# Phase 1: Quick Wins (1.5 hours)
# - Add docstrings
# - Remove dead code
# - Reduce nesting
git checkout -b phase-1-quick-wins
# ... implement ...
./checkpoint_validation.sh
git commit -m "Phase 1: Quick wins (docstrings, cleanup)"

# Phase 1.5: Controller Tests (4-6 hours)
git checkout -b phase-1.5-controller-tests
# ... write 24-30 tests ...
./checkpoint_validation.sh
git commit -m "Phase 1.5: Add controller tests"

# Phase 2: Protocol Adoption (8-10 hours)
git checkout -b phase-2-protocols
# ... extend StateManagerProtocol, update annotations ...
./checkpoint_validation.sh
git commit -m "Phase 2: Protocol adoption in controllers"

# Merge to main
git checkout main
git merge phase-1-quick-wins
git merge phase-1.5-controller-tests
git merge phase-2-protocols
```

**Total: 13.5-17.5 hours, +18 points, ROI 1.03-1.33 pts/hr** ✅

**SKIP: Phases 3-4**
- Too much effort (73+ hours more)
- Too low ROI (0.08-0.32 pts/hr)
- Too high risk (stale state bug, architectural complexity)

---

## Summary of Corrections

**What Was Fixed:**

1. ✅ **Phase 1:** Removed internal class extraction (not viable, 85% incomplete)
2. ✅ **Phase 1.5:** Added controller tests (enables Phase 2 verification)
3. ✅ **Phase 2:** Fixed protocols (extend StateManagerProtocol, use correct protocols)
4. ✅ **Phase 3:** Fixed dependencies, hybrid approach, realistic effort (48-66h not 12-16h)
5. ✅ **Metrics:** Corrected TYPE_CHECKING baseline (603 not 181)
6. ✅ **Dependencies:** Acknowledged phases are independent (not strict linear)

**Confidence:** VERY HIGH (95%+) - all corrections verified against actual codebase

---

## Next Steps

1. ✅ Review this corrected plan
2. ✅ Decide: Execute Phases 1+1.5+2 (recommended) or all phases (not recommended)
3. ✅ Create feature branch
4. ✅ Begin implementation
5. ✅ Run checkpoint validation after each phase
6. ✅ Celebrate wins!

**Recommended decision:** Execute Phases 1+1.5+2, stop there. Enjoy 60% benefit at high ROI.

---

*Plan corrected based on comprehensive agent verification - 2025-10-25*
*Original plan: REFACTORING_IMPLEMENTATION_PLAN.md*
*Verification reports: PLAN_VERIFICATION_REPORT.md, AGENT_VERIFICATION_SYNTHESIS.md*
