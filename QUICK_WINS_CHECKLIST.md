# CurveEditor KISS/DRY/YAGNI - Quick Wins Checklist

**Generated**: 2025-10-27
**Total Potential**: 2,500+ lines improved/removed
**Total Effort**: 6-9 hours for quick wins

---

## 🔴 ZERO-RISK DELETIONS (4 hours, 2,131 lines removed)

### ✅ 1. Delete Error Handler Infrastructure (1h) - **998 lines**
```bash
rm ui/error_handlers.py      # 515 lines
rm ui/error_handler.py        # 483 lines
rm tests/test_error_handler.py
grep -r "error_handler" --include="*.py"  # Verify 0 results
pytest tests/ -x
```
**Why**: 0 production imports, enterprise pattern for single-user app

---

### ✅ 2. Delete Service Infrastructure Chain (2h) - **909 lines**
```bash
rm services/coordinate_service.py  # 248 lines - 0 refs
rm services/cache_service.py       # 316 lines - only used by coordinate
rm core/monitoring.py              # 345 lines - enterprise metrics
```

**Config Cleanup**:
```python
# In core/config.py - remove these lines:
enable_cache_monitoring: bool = False
enable_performance_metrics: bool = False
```

**Verification**:
```bash
grep -r "CoordinateService\|CacheService\|monitoring" --include="*.py"
pytest tests/ -x
./bpr --errors-only
```
**Why**: Chain dependency ending at nothing, 0 production usage

---

### ✅ 3. Delete Unused State Protocols (1h) - **224 lines**
```bash
rm protocols/state.py
```

**Update Required**:
- `stores/application_state.py`: Remove docstring references to protocols

**Verification**:
```bash
grep -r ": FrameProvider\|: CurveDataProvider" --include="*.py"  # Should be 0
./bpr
```
**Why**: 9 protocols defined, 0 type annotations use them

---

## 🟠 DRY CONSOLIDATION (5-7 hours, ~300 lines reduced)

### ✅ 4. Add `_apply_status_changes()` to CurveDataCommand (1-2h) - **150 lines**

**File**: `core/commands/curve_commands.py`
**Line**: Add after line 125 (after existing base class helpers)

```python
def _apply_status_changes(
    self,
    curve_name: str,
    changes: list[tuple[int, str, str]],
    use_new: bool
) -> bool:
    """Apply status changes with gap restoration logic.

    Args:
        curve_name: Target curve
        changes: List of (index, old_status, new_status)
        use_new: If True use new_status, else use old_status

    Returns:
        True if successful
    """
    app_state = get_application_state()
    data_service = get_data_service()

    curve_data = list(app_state.get_curve_data(curve_name))
    data_service.update_curve_data(curve_data)

    # Apply changes through restoration system
    for index, old_status, new_status in changes:
        status = new_status if use_new else old_status
        if 0 <= index < len(curve_data):
            data_service.handle_point_status_change(index, status)
        else:
            logger.warning(f"Point index {index} out of range")

    # Get restored data
    if data_service.segmented_curve:
        restored_points = data_service.segmented_curve.all_points
        updated_data = [(p.frame, p.x, p.y, p.status.value) for p in restored_points]
    else:
        logger.warning("SegmentedCurve unavailable, applying directly")
        updated_data = list(curve_data)
        for index, old_status, new_status in changes:
            status = new_status if use_new else old_status
            if 0 <= index < len(updated_data):
                point = updated_data[index]
                if len(point) >= 3:
                    updated_data[index] = (point[0], point[1], point[2], status)

    app_state.set_curve_data(curve_name, updated_data)
    return True
```

**Update SetPointStatusCommand** (lines 764-907):
```python
def execute(self, main_window: MainWindowProtocol) -> bool:
    def _execute_operation() -> bool:
        if (result := self._get_active_curve_data()) is None:
            return False
        curve_name, _ = result
        return self._apply_status_changes(curve_name, self.changes, use_new=True)
    return self._safe_execute("executing", _execute_operation)

def undo(self, main_window: MainWindowProtocol) -> bool:
    def _undo_operation() -> bool:
        if not self._target_curve:
            return False
        return self._apply_status_changes(self._target_curve, self.changes, use_new=False)
    return self._safe_execute("undoing", _undo_operation)

def redo(self, main_window: MainWindowProtocol) -> bool:
    def _redo_operation() -> bool:
        if not self._target_curve:
            return False
        return self._apply_status_changes(self._target_curve, self.changes, use_new=True)
    return self._safe_execute("redoing", _redo_operation)
```

**Test**:
```bash
pytest tests/test_tracking_point_status_commands.py -xv
pytest tests/test_curve_commands.py -xv -k status
```

---

### ✅ 5. Add `_get_target_curve_data()` to CurveDataCommand (1h) - **68 lines**

**File**: `core/commands/curve_commands.py`
**Line**: Add after line 100 (near `_get_active_curve_data`)

```python
def _get_target_curve_data(self) -> tuple[str, CurveDataList] | None:
    """Get target curve data for undo/redo operations.

    Returns:
        Tuple of (curve_name, curve_data) if target exists, None otherwise.
        Logs error if target missing.
    """
    if not self._target_curve:
        logger.error(f"Missing target curve for {self.__class__.__name__}")
        return None

    app_state = get_application_state()
    curve_data = app_state.get_curve_data(self._target_curve)
    if curve_data is None:
        logger.error(f"Target curve '{self._target_curve}' not found")
        return None

    return (self._target_curve, list(curve_data))
```

**Replace Pattern** (17 occurrences in curve_commands.py):
```python
# OLD (lines 178-183, 194-199, 307-312, etc.):
if not self._target_curve:
    logger.error("Missing target curve for undo/redo")
    return False
app_state = get_application_state()
curve_data = list(app_state.get_curve_data(self._target_curve))

# NEW:
if (result := self._get_target_curve_data()) is None:
    return False
curve_name, curve_data = result
```

**Files to Update**:
- `curve_commands.py`: Lines 178, 194, 307, 330, 439, 465, 570, 596, 671, 694, etc. (17 total)

**Test**:
```bash
pytest tests/test_curve_commands.py -xv
```

---

### ✅ 6. Add `_has_point_at_current_frame()` to ShortcutCommand (1h) - **30 lines**

**File**: `core/commands/shortcut_command.py`
**Line**: Add to base class

```python
def _has_point_at_current_frame(self, context: ShortcutContext) -> bool:
    """Check if active curve has point at current frame.

    Returns:
        True if point exists, False otherwise
    """
    if context.current_frame is None:
        return False

    try:
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            return False
        _, curve_data = cd
        return any(point[0] == context.current_frame for point in curve_data)
    except ValueError:
        return False
```

**Replace Pattern** (5 occurrences in shortcut_commands.py):
```python
# OLD (lines 133-140, 167-172, 362-371, etc.):
try:
    app_state = get_application_state()
    if (cd := app_state.active_curve_data) is None:
        return False
    _, curve_data = cd
    return any(point[0] == context.current_frame for point in curve_data)
except ValueError:
    return False

# NEW:
return self._has_point_at_current_frame(context)
```

**Test**:
```bash
pytest tests/test_shortcut_commands.py -xv
```

---

### ✅ 7. Remove Smoothing Dual Implementation (1-2h) - **50 lines**

**File**: `ui/controllers/action_handler_controller.py`
**Lines**: Delete 287-336 (legacy fallback)

**Current** (lines 226-336):
```python
def apply_smooth_operation(self) -> None:
    # Try command system (lines 230-286)
    if interaction_service:
        # ... 40 lines of command logic
        if succeeded:
            return

    # Legacy fallback (lines 287-336) ← DELETE THIS SECTION
    if data_service:
        # ... 50 lines duplicate smoothing
```

**New** (simplified):
```python
def apply_smooth_operation(self) -> None:
    """Apply smoothing via command system."""
    interaction_service = get_interaction_service()
    if not interaction_service:
        logger.error("Interaction service unavailable for smoothing")
        return

    # Get filter configuration
    filter_type = self._get_selected_filter_type()
    window_size = self._get_window_size()

    # Execute through command system
    command = SmoothCommand(
        description=f"Smooth with {filter_type}",
        filter_type=filter_type,
        window_size=window_size
    )
    success = interaction_service.command_manager.execute_command(
        command,
        self.main_window
    )

    if not success:
        logger.warning("Smoothing command failed")
```

**Test**:
```bash
pytest tests/ -k smooth -xv
# Manual: Apply smoothing via UI, verify undo/redo
```

---

### ✅ 8. Simplify Double-Cast Pattern (30min) - **9 lines**

**File**: `core/commands/shortcut_commands.py`
**Lines**: 94, 101, 211, 460, etc. (9 occurrences)

**Replace**:
```python
# OLD:
cast("MainWindowProtocol", cast(object, context.main_window))

# NEW:
context.main_window  # pyright: ignore[reportArgumentType]  # Runtime type matches protocol
```

**Test**:
```bash
./bpr core/commands/shortcut_commands.py
pytest tests/test_shortcut_commands.py -xv
```

---

## 📊 Impact Summary

| Phase | Effort | Impact | Risk |
|-------|--------|--------|------|
| **Zero-Risk Deletions** | 4h | -2,131 lines | ZERO |
| **DRY Consolidation** | 5-7h | -300 lines, patterns standardized | LOW |
| **TOTAL QUICK WINS** | **9-11h** | **-2,431 lines (9.7%)** | **LOW** |

---

## ✅ Validation Checklist

After each change:

```bash
# 1. Type checking
./bpr --errors-only

# 2. Automated tests
pytest tests/ -x  # Stop at first failure

# 3. Specific test suites
pytest tests/test_curve_commands.py -xv
pytest tests/test_shortcut_commands.py -xv
pytest tests/test_tracking_point_status_commands.py -xv

# 4. Manual smoke test
# - Load file
# - Edit points (move, status changes)
# - Apply smoothing
# - Undo/redo operations
# - Save/load session
```

---

## 🎯 Recommended Execution Order

**Week 1** (4 hours):
1. ✅ Delete error handlers (1h)
2. ✅ Delete service chain (2h)
3. ✅ Delete state protocols (1h)

**Week 2** (5-7 hours):
4. ✅ Add `_apply_status_changes()` (1-2h)
5. ✅ Add `_get_target_curve_data()` (1h)
6. ✅ Add `_has_point_at_current_frame()` (1h)
7. ✅ Remove smoothing dual impl (1-2h)
8. ✅ Simplify double-cast (30min)

**Total**: 9-11 hours over 2 weeks

---

## 🔍 Verification Commands

```bash
# Grep for removed code
grep -r "error_handler\|CoordinateService\|CacheService\|monitoring" --include="*.py"

# Count lines in key files (before/after)
wc -l ui/error_handlers.py            # Before: 515 → After: deleted
wc -l services/coordinate_service.py  # Before: 248 → After: deleted
wc -l core/monitoring.py              # Before: 345 → After: deleted
wc -l protocols/state.py              # Before: 224 → After: deleted

# Test coverage
pytest tests/ --cov=core.commands --cov=ui.controllers --cov-report=term-missing

# Type safety
./bpr
```

---

## 📈 Success Metrics

**Before**:
- Total lines: ~25,000
- Commands with duplication: 17+
- Unused services: 3
- Unused protocols: 9
- Duplicate implementations: 3

**After Quick Wins**:
- Total lines: ~22,500 (-10%)
- Commands with duplication: 0
- Unused services: 0
- Unused protocols: 0
- Duplicate implementations: 0

**Quality Gains**:
- Command base class: 4 new helpers
- Pattern standardization: 100% of commands use helpers
- Dead code removed: 2,131 lines
- Test coverage maintained: 100%

---

*Generated by multi-agent analysis (DRY, KISS, YAGNI, Architecture)*
*For full analysis see: CONSOLIDATION_SYNTHESIS.md*
