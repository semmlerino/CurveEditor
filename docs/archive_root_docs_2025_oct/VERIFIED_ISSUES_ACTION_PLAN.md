# Verified Issues Action Plan

**Date Created**: 2025-10-20
**Source**: Agent findings verification report
**Status**: Ready for implementation
**Estimated Total Effort**: 12-15 hours (2 sprints)

---

## Overview

This plan addresses 3 critical architectural issues and 2 important improvements identified through agent verification:

**Critical Issues** (Sprint 1):
1. Private method call violations (4 instances)
2. Type-unsafe getattr() usage (3 instances)
3. Inconsistent widget update pattern

**Important Issues** (Sprint 2):
4. Mock overuse in tests (reduce from 331 to ~200)
5. Test performance optimization

---

## Sprint 1: Critical Architectural Fixes (Week 1)

### Phase 1: Private Method Call Violations (4-8 hours)

**Issue**: Commands and controllers calling `_private_methods()` from UI components, breaking encapsulation

**Locations**:
1. `core/commands/shortcut_commands.py:313` - `tracking_panel._set_direction_for_points()`
2. `core/commands/shortcut_commands.py:356` - `tracking_panel._delete_points()`
3. `core/commands/shortcut_commands.py:753` - `curve_widget._select_point()`
4. `ui/controllers/frame_change_coordinator.py:220` - `timeline_tabs._on_frame_changed()`

#### Task 1.1: Add Protocol Methods (2 hours)

**File**: `ui/protocols/ui.py`

Add to existing protocols:

```python
# TrackingPointsPanelProtocol (add these methods)
class TrackingPointsPanelProtocol(Protocol):
    # ... existing methods ...

    def set_direction_for_points(self, points: list[str], direction: TrackingDirection) -> None:
        """Set tracking direction for selected points.

        Args:
            points: List of point names to update
            direction: TrackingDirection enum value (FORWARD/BACKWARD/BOTH/NONE)
        """
        ...

    def delete_points(self, points: list[str]) -> None:
        """Delete tracking points by name.

        Args:
            points: List of point names to delete
        """
        ...

# CurveViewProtocol (add this method)
class CurveViewProtocol(Protocol):
    # ... existing methods ...

    def select_point(self, point_index: int, add_to_selection: bool = False) -> None:
        """Select a point by index.

        Args:
            point_index: Index of point to select
            add_to_selection: If True, add to existing selection; if False, replace
        """
        ...

# TimelineTabsProtocol (add this method)
class TimelineTabsProtocol(Protocol):
    # ... existing methods ...

    def on_frame_changed(self, frame: int) -> None:
        """Handle frame change notification.

        Args:
            frame: New frame number
        """
        ...
```

#### Task 1.2: Implement Public Wrappers (2 hours)

**File**: `ui/tracking_points_panel.py`

```python
def set_direction_for_points(self, points: list[str], direction: TrackingDirection) -> None:
    """Public API for setting tracking direction."""
    self._set_direction_for_points(points, direction)

def delete_points(self, points: list[str]) -> None:
    """Public API for deleting tracking points."""
    self._delete_points(points)
```

**File**: `ui/curve_view_widget.py`

```python
def select_point(self, point_index: int, add_to_selection: bool = False) -> None:
    """Public API for point selection."""
    self._select_point(point_index, add_to_selection)
```

**File**: `ui/timeline_tabs.py`

```python
def on_frame_changed(self, frame: int) -> None:
    """Public API for frame change notification."""
    self._on_frame_changed(frame)
```

#### Task 1.3: Update Call Sites (2 hours)

**File**: `core/commands/shortcut_commands.py`

```python
# Line 313: Change from
tracking_panel._set_direction_for_points(selected_points, self.direction)
# To:
tracking_panel.set_direction_for_points(selected_points, self.direction)

# Line 356: Change from
tracking_panel._delete_points(context.selected_tracking_points)
# To:
tracking_panel.delete_points(context.selected_tracking_points)

# Line 753: Change from
curve_widget._select_point(point_index, add_to_selection=False)
# To:
curve_widget.select_point(point_index, add_to_selection=False)
```

**File**: `ui/controllers/frame_change_coordinator.py`

```python
# Line 220: Change from
self.timeline_tabs._on_frame_changed(frame)  # pyright: ignore[reportPrivateUsage]
# To:
self.timeline_tabs.on_frame_changed(frame)  # ✅ No more type ignore needed!
```

#### Task 1.4: Verify and Test (2 hours)

1. Run type checker:
   ```bash
   ./bpr --errors-only
   ```
   Should have zero `reportPrivateUsage` errors

2. Run protocol tests:
   ```bash
   uv run pytest tests/test_protocols.py -v
   ```

3. Run affected command tests:
   ```bash
   uv run pytest tests/test_shortcut_commands.py tests/test_frame_change_coordinator.py -v
   ```

4. Manual testing:
   - Test tracking direction changes (keyboard shortcuts)
   - Test point deletion (Delete key)
   - Test point selection (click)
   - Test frame changes (timeline scrubbing)

---

### Phase 2: Type-Unsafe getattr() Usage (2 hours)

**Issue**: Using `getattr(obj, "attr", None)` loses type safety, IDE support

**Locations**:
1. `core/commands/shortcut_commands.py:51` - `getattr(main_window, "multi_point_controller", None)`
2. `core/commands/shortcut_commands.py:56` - `getattr(main_window, "tracking_panel", None)`
3. `core/commands/shortcut_commands.py:77` - `getattr(main_window, "tracking_panel", None)`

#### Task 2.1: Add Protocol Properties (30 min)

**File**: `ui/protocols/ui.py`

Add to `MainWindowProtocol`:

```python
class MainWindowProtocol(Protocol):
    # ... existing properties ...

    @property
    def multi_point_controller(self) -> MultiPointTrackingControllerProtocol | None:
        """Get the multi-point tracking controller if available.

        Returns:
            Controller instance or None if not initialized
        """
        ...

    @property
    def tracking_panel(self) -> TrackingPointsPanelProtocol | None:
        """Get the tracking points panel if available.

        Returns:
            Panel instance or None if not initialized
        """
        ...
```

#### Task 2.2: Update Call Sites (30 min)

**File**: `core/commands/shortcut_commands.py`

```python
# Line 51: Change from
multi_point_controller = getattr(main_window, "multi_point_controller", None)
# To:
multi_point_controller = main_window.multi_point_controller

# Line 56: Change from
tracking_panel = getattr(main_window, "tracking_panel", None)
# To:
tracking_panel = main_window.tracking_panel

# Line 77: Change from
tracking_panel = getattr(main_window, "tracking_panel", None)
# To:
tracking_panel = main_window.tracking_panel
```

#### Task 2.3: Verify Type Safety (1 hour)

1. Run type checker:
   ```bash
   ./bpr core/commands/shortcut_commands.py
   ```
   Should have zero errors on the changed lines

2. Test IDE autocomplete:
   - Open `shortcut_commands.py` in IDE
   - Type `main_window.` and verify autocomplete shows `multi_point_controller` and `tracking_panel`
   - Verify hovering shows correct protocol types

3. Run tests:
   ```bash
   uv run pytest tests/test_shortcut_commands.py -v
   ```

---

### Phase 3: Inconsistent Widget Update Pattern (3 hours)

**Issue**: Some commands manually call `widget.update()`, others rely on ApplicationState signals

**Location**: `core/commands/curve_commands.py:801-805` (SetPointStatusCommand)

#### Task 3.1: Audit Manual update() Calls (30 min)

Search for manual widget updates:

```bash
grep -n "\.update()" core/commands/*.py ui/controllers/*.py
```

Document:
- Which commands have manual updates
- Which commands don't
- Check if ApplicationState signals are connected

#### Task 3.2: Remove Manual update() Calls (1 hour)

**File**: `core/commands/curve_commands.py`

```python
# SetPointStatusCommand.execute() - Remove lines 801-805:
# DELETE THIS:
# if main_window.curve_widget:
#     main_window.curve_widget.update()

# SetPointStatusCommand.undo() - Remove similar block if exists
# SetPointStatusCommand.redo() - Remove similar block if exists
```

**Rationale**: ApplicationState.curves_changed signal already triggers updates when `set_curve_data()` is called

#### Task 3.3: Verify Signal Connections (30 min)

**Check**: Ensure MainWindow connects ApplicationState signals to widget updates

```python
# In MainWindow.__init__ or setup method
app_state = get_application_state()
app_state.curves_changed.connect(self._on_curves_changed)

def _on_curves_changed(self, curve_name: str | None) -> None:
    """Handle curve data changes."""
    if self.curve_widget:
        self.curve_widget.update()
```

If this connection doesn't exist, add it.

#### Task 3.4: Test Update Behavior (1 hour)

1. Run all command tests:
   ```bash
   uv run pytest tests/test_curve_commands.py -v
   ```

2. Manual testing - verify UI updates correctly:
   - Toggle endframe status (E key)
   - Smooth points
   - Move points
   - Delete points
   - Set point status
   - Undo/Redo all operations

3. Check for double-updates (performance):
   - Add logging to `curve_widget.update()`
   - Run manual tests
   - Verify each command triggers exactly ONE update

---

### Phase 1-3 Completion Checklist

- [ ] All 4 private method calls replaced with public API
- [ ] All 3 getattr() calls replaced with protocol properties
- [ ] All manual widget.update() calls removed
- [ ] Type checker passes: `./bpr --errors-only` (zero errors)
- [ ] All tests pass: `uv run pytest tests/ -x` (2,747+ passing)
- [ ] Manual testing completed for all affected features
- [ ] No performance regressions (verify with stopwatch if needed)

**Commit Message**:
```
fix(architecture): Resolve encapsulation and type safety issues

- Add public protocol methods for 4 private method call sites
- Replace getattr() with protocol properties for type safety
- Remove manual widget.update() calls, rely on signals exclusively

Fixes verified issues from agent audit report.
Improves encapsulation, type safety, and UI update consistency.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Sprint 2: Test Quality & Performance (Week 2)

### Phase 4: Reduce Mock Overuse (1-2 days)

**Issue**: 331 mock definitions in tests, ~50-80 should use real components instead

#### Task 4.1: Audit Mock Usage (2 hours)

Create spreadsheet of all mocks:

```bash
# Find all Mock/MagicMock/patch definitions
grep -rn "Mock\|patch" tests/ --include="*.py" | grep -E "(= Mock|MagicMock|@patch)" > mock_audit.txt
```

Categorize each:
- ✅ **Keep**: System boundaries (file I/O, external libs, Qt internals)
- ⚠️ **Consider**: Internal services (could use real)
- ❌ **Remove**: State management, data models (should be real)

#### Task 4.2: Replace Internal Service Mocks (4-6 hours)

**Target**: ~50-80 mocks to replace

**Example** - Replace MockDataService with real:

```python
# BEFORE:
class MockDataService:
    def __init__(self):
        self.data = {}
    def get_curve_data(self, name):
        return self.data.get(name, [])

def test_some_feature(self):
    service = MockDataService()  # ❌ Mock
    # ...

# AFTER:
def test_some_feature(self):
    service = get_data_service()  # ✅ Real service
    # Will be reset by reset_all_services fixture
    # ...
```

**Files to Review**:
- `tests/test_curve_commands.py`
- `tests/test_data_service.py`
- `tests/test_interaction_service.py`

#### Task 4.3: Verify Test Coverage Maintained (1 hour)

```bash
# Before changes
uv run pytest --cov=. --cov-report=term-missing tests/ > coverage_before.txt

# After changes
uv run pytest --cov=. --cov-report=term-missing tests/ > coverage_after.txt

# Compare
diff coverage_before.txt coverage_after.txt
```

Coverage should remain 85% or increase.

---

### Phase 5: Test Performance Optimization (4 hours)

**Issue**: 9.7 tests/sec, could be 20-30 tests/sec with parallelization

#### Task 5.1: Add Test Markers (1 hour)

**File**: `pyproject.toml`

```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "fast: marks tests as fast (select with '-m fast')",
    "integration: marks integration tests",
    "unit: marks unit tests",
]
```

**Mark slow tests**:

```python
# tests/test_qt_threading_investigation.py
@pytest.mark.slow
def test_stylesheet_setting_safety(self):  # 3.32s
    ...

# tests/test_core_models.py
@pytest.mark.slow
def test_point_creation_invariants(self):  # 2.16s (property-based)
    ...

# tests/test_frame_change_integration.py
@pytest.mark.slow
def test_rapid_frame_changes_via_signal_chain(self):  # 1.62s
    ...
```

#### Task 5.2: Enable Parallel Execution (1 hour)

**Create**: `.github/workflows/test.yml` or update existing CI config

```yaml
- name: Run fast tests
  run: |
    uv run pytest -m "not slow" -v --tb=short

- name: Run slow tests in parallel
  run: |
    uv run pytest -m slow -n auto -v --tb=short
```

**Local Development**:

```bash
# Fast feedback loop (run these frequently)
uv run pytest -m "not slow" -v

# Full test suite (run before commit)
uv run pytest -m slow -n auto -v
uv run pytest -m "not slow" -v
```

#### Task 5.3: Optimize Fixture Scope (1 hour)

**Review fixtures** in `tests/conftest.py` and `tests/fixtures/*.py`:

```python
# BEFORE: Function-scoped (slow)
@pytest.fixture
def data_service():
    return DataService()

# AFTER: Module-scoped (fast)
@pytest.fixture(scope="module")
def data_service():
    service = DataService()
    yield service
    service.clear_cache()  # Cleanup
```

**Candidates for module scope**:
- Pure data fixtures (`sample_curve_data`, etc.)
- Stateless services (with proper cleanup)
- Configuration objects

#### Task 5.4: Measure Performance Improvement (1 hour)

```bash
# Before optimizations
time uv run pytest tests/ -q > performance_before.txt
# Record: X tests in Y seconds = Z tests/sec

# After optimizations
time uv run pytest tests/ -q -n auto > performance_after.txt
# Record: X tests in Y seconds = Z tests/sec

# Target: 20-30 tests/sec (2-3x improvement)
```

---

## Validation & Sign-Off

### Pre-Commit Checklist

- [ ] All type errors resolved: `./bpr --errors-only`
- [ ] All tests passing: `uv run pytest tests/ -x`
- [ ] Test coverage maintained: ≥85%
- [ ] No new ruff warnings: `uv run ruff check .`
- [ ] Manual testing completed for all modified features
- [ ] Performance not regressed (test execution time ≤5 minutes)

### Success Metrics

**Sprint 1**:
- [ ] Zero `reportPrivateUsage` type errors (down from 4)
- [ ] Zero getattr() in commands (down from 3)
- [ ] Consistent widget update pattern (all commands use signals)
- [ ] All 2,747+ tests passing

**Sprint 2**:
- [ ] Mock count reduced to ~200-250 (down from 331)
- [ ] Test execution speed: 20+ tests/sec (up from 9.7)
- [ ] Test coverage maintained: ≥85%

---

## Risk Mitigation

### Risk 1: Breaking Changes in Public API

**Mitigation**:
- Public wrappers delegate to existing private methods (no logic changes)
- Comprehensive test suite catches regressions
- Manual testing validates behavior unchanged

### Risk 2: Signal-Only Updates Miss Edge Cases

**Mitigation**:
- Verify ApplicationState.curves_changed is connected in MainWindow
- Add integration tests if needed
- Manual testing with UI to verify all update scenarios

### Risk 3: Parallel Testing Reveals Hidden Dependencies

**Mitigation**:
- `reset_all_services` fixture already provides isolation
- Run tests sequentially first, then enable parallelization
- Fix any race conditions revealed (benefit, not risk)

---

## Rollback Plan

If critical issues arise:

1. **Immediate**: Revert last commit
   ```bash
   git revert HEAD
   git push
   ```

2. **Investigate**: Identify failing tests or broken features

3. **Fix Forward**: Address root cause, re-apply changes with fix

4. **Last Resort**: Keep revert, document issue, plan alternative approach

---

## Timeline

**Sprint 1** (Week of 2025-10-21):
- Day 1-2: Phase 1 (Private methods) + Phase 2 (getattr)
- Day 3: Phase 3 (Widget updates) + Testing + Commit

**Sprint 2** (Week of 2025-10-28):
- Day 1-2: Phase 4 (Mock reduction)
- Day 3: Phase 5 (Performance) + Validation

**Total**: ~12-15 hours over 2 weeks

---

## Notes

- **Pair Programming**: Consider for Phase 1 (critical architectural changes)
- **Code Review**: Required for Sprint 1 commit (architectural impact)
- **Documentation**: Update CLAUDE.md if new patterns emerge
- **Agent Re-Run**: After completion, re-run agents to verify fixes

---

**Plan Status**: ✅ Ready for implementation
**Next Step**: Begin Phase 1, Task 1.1 (Add Protocol Methods)
