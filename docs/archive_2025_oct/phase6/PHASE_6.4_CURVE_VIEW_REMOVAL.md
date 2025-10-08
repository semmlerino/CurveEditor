# Phase 6.4: main_window.curve_view Removal

[← Previous: Phase 6.3](PHASE_6.3_CURVEDATASTORE_REMOVAL.md) | [Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) | [Next: Phase 6.5 →](PHASE_6.5_TIMELINE_SIGNAL_REMOVAL.md)

---

## Goal

Remove `main_window.curve_view` alias, force use of `curve_widget`.

## Prerequisites

- [Phase 6.3](PHASE_6.3_CURVEDATASTORE_REMOVAL.md) complete (CurveDataStore removed)

---

## Current Usage

**Production Code (5 files)**:
1. `ui/main_window.py:252` - `self.curve_view = None` (initialization)
2. `ui/main_window.py:1087` - `set_curve_view()` method
3. `ui/menu_bar.py:364-386` - 4 menu handlers check `curve_view`
4. `services/interaction_service.py:571-1330` - 6 fallback references
5. ⚠️ `data/batch_edit.py:375, 376, 544, 546, 569` - 5 references with `cast(CurveViewProtocol, ...)` **NEWLY ADDED**

**Test Code**: 20 test files (simple find-replace in MockMainWindow fixtures)

---

## Migration Steps

### Step 1: Update MainWindow

**File**: `ui/main_window.py`

Remove:
- `self.curve_view: CurveViewWidget | None = None`
- `def set_curve_view(self, curve_view: CurveViewWidget | None) -> None`

Keep:
- `self.curve_widget: CurveViewWidget`

---

### Step 2: Update MenuBar

**File**: `ui/menu_bar.py`

Replace ALL (4 locations):
```python
# OLD:
if self.main_window and self.main_window.curve_view is not None:
    curve_view = self.main_window.curve_view

# NEW:
if self.main_window and self.main_window.curve_widget is not None:
    curve_widget = self.main_window.curve_widget
```

---

### Step 3: Update InteractionService ⚠️ CRITICAL FIX

**File**: `services/interaction_service.py`

**DO NOT DELETE** - This is history extraction code for undo/redo!

**REPLACE fallback with curve_widget** (not delete):
```python
# OLD:
elif main_window.curve_view is not None and getattr(main_window.curve_view, "curve_data", None) is not None:
    view_curve_data = getattr(main_window.curve_view, "curve_data")

# NEW:
elif main_window.curve_widget is not None and getattr(main_window.curve_widget, "curve_data", None) is not None:
    view_curve_data = getattr(main_window.curve_widget, "curve_data")
```

All 6 fallback references must REPLACE `curve_view` with `curve_widget` (not delete).

---

### Step 3.5: Update BatchEdit ⚠️ NEWLY ADDED

**File**: `data/batch_edit.py`

**Update protocol casting** (5 locations):
```python
# OLD:
if self.parent.curve_view is not None:
    curve_view = cast(CurveViewProtocol, self.parent.curve_view)

# NEW:
if self.parent.curve_widget is not None:
    curve_widget = cast(CurveViewProtocol, self.parent.curve_widget)
```

**Locations to update**:
- Line 375-376: `if self.parent.curve_view is not None` + cast
- Line 544: Inline cast
- Line 546: Conditional check
- Line 569: cast

**Also update protocol if needed**:
- Check `protocols/data.py` - `BatchEditableProtocol` may define `curve_view` attribute
- Update to `curve_widget: CurveViewWidget` if so

---

### Step 4: Update All Tests

Remove from all MockMainWindow:
- `self.curve_view = ...`
- `main_window.curve_view = view`

Use only:
- `self.curve_widget = ...`

---

### Step 5: Update Protocols LAST ⚠️ ORDER CRITICAL

**Why Last**: Must update all code FIRST, then remove from protocols. Doing protocols first breaks type checking.

**Correct Order**: Production Code (Steps 1-3) → Tests (Step 4) → Protocols (Step 5) → Validate

**Protocol Updates** (5 locations):

1. **protocols/data.py:109** (BatchEditableProtocol):
   ```python
   # DELETE:
   - curve_view: object
   ```

2. **protocols/data.py:140** (BatchEdit protocol):
   ```python
   # DELETE:
   - curve_view: object | None
   ```

3. **protocols/ui.py:417-551** (MainWindowProtocol):
   ```python
   # DELETE entire curve_view property definition (if exists)
   ```

4. **protocols/ui.py:655** (Another protocol):
   ```python
   # DELETE:
   - curve_view: CurveViewProtocol
   ```

**Validation After Protocols Updated**:
```bash
./bpr --errors-only
# Expected: 0 errors (should pass now that all code uses curve_widget)
```

---

## Files to Modify

- **Production**: 5 files (+ 1 protocol file if needed)
  - `ui/main_window.py`
  - `ui/menu_bar.py`
  - `services/interaction_service.py`
  - `data/batch_edit.py` ⚠️ NEWLY ADDED
  - `protocols/data.py` (if BatchEditableProtocol defines curve_view)
- **Tests**: 6 files (verified count)
- **Total**: 11-12 files

---

## Breaking Changes

- `main_window.curve_view` removed
  - Migration: Use `main_window.curve_widget`
- `MainWindowProtocol.curve_view` removed

---

## Validation

```bash
# Verify no curve_view references remain:
grep -rn "\.curve_view\b" --include="*.py" . --exclude-dir=tests --exclude-dir=docs
# Expected: 0 results

# All tests passing:
pytest tests/ -v
# Expected: 2105/2105 passing
```

---

## Exit Criteria

- [ ] Step 0 complete: Protocols updated (5 locations), basedpyright passes (0 errors)
- [ ] MainWindow.curve_view removed
- [ ] MenuBar updated (4 locations)
- [ ] InteractionService fallbacks updated (6 locations)
- [ ] BatchEdit updated (5 locations)
- [ ] All tests updated (6 files)
- [ ] 0 production `curve_view` references (verify: `grep -rn "\.curve_view\s*[=\[\(]" --include="*.py" . --exclude-dir=tests`)
- [ ] All tests passing

---

**Next**: [Phase 6.5 - Timeline Signal Removal →](PHASE_6.5_TIMELINE_SIGNAL_REMOVAL.md)
