# Phase 6.2: Read-Only Enforcement & Validation Tests

[← Previous: Phase 6.1](PHASE_6.1_SELECTED_INDICES_MIGRATION.md) | [Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) | [Next: Phase 6.3 →](PHASE_6.3_CURVEDATASTORE_REMOVAL.md)

---

## Goal

Add read-only property setters and create comprehensive validation test suite.

## Prerequisites

- [Phase 6.0](PHASE_6.0_PRE_MIGRATION_VALIDATION.md) complete (all audits done)
- [Phase 6.1](PHASE_6.1_SELECTED_INDICES_MIGRATION.md) complete (2 production call sites migrated)

## Critical Sequencing

⚠️ **Setters must be implemented BEFORE tests** (tests expect AttributeError from setters)

---

## Part A: Implement Read-Only Property Setters

### ⚠️ IMPORTANT: Remove Existing Setter Logic

The current `selected_indices` setter (lines 313-334 in `ui/curve_view_widget.py`) has sync logic that:
- Calls `_curve_store.clear_selection()` and `_curve_store.select(idx, add_to_selection=True)`
- Syncs to ApplicationState for active curve

**This logic must be REMOVED and replaced with bare `raise AttributeError`.**

Similarly, if `curve_data` has a setter with logic, remove it.

### Why Setters Are Needed

Without explicit setters, Python allows assignment which creates instance attribute:
```python
widget.curve_data = []  # Creates widget.__dict__['curve_data'] = []
                        # Property is now SHADOWED - getter never called again!
```

With explicit setters:
```python
widget.curve_data = []  # Raises AttributeError with helpful message
```

### Implementation

**File**: `ui/curve_view_widget.py`

```python
@property
def curve_data(self) -> CurveDataList:
    """Get curve data from CurveDataStore.

    NOTE: In Phase 6.2, still using CurveDataStore (Phase 6.3 will migrate to ApplicationState).
    """
    return self._curve_store.get_data()

@curve_data.setter
def curve_data(self, value: CurveDataList) -> None:
    """Prevent writes - property is read-only.

    Raises:
        AttributeError: Always raised - property is read-only
    """
    raise AttributeError(
        "widget.curve_data is read-only. "
        "Use app_state.set_curve_data(curve_name, data) instead."
    )

@property
def selected_indices(self) -> set[int]:
    """Get selection from CurveDataStore.

    NOTE: In Phase 6.2, still using CurveDataStore (Phase 6.3 will migrate to ApplicationState).
    """
    return self._curve_store.get_selection()

@selected_indices.setter
def selected_indices(self, value: set[int]) -> None:
    """Prevent writes - property is read-only.

    Raises:
        AttributeError: Always raised - property is read-only
    """
    raise AttributeError(
        "widget.selected_indices is read-only. "
        "Use app_state.set_selection(curve_name, indices) instead."
    )
```

**IMPORTANT**: Phase 6.3 will update these getters to read from ApplicationState directly.

### What Setters Do and Don't Prevent

✅ **Prevent**: Whole-property assignment (shadowing)
```python
widget.curve_data = []  # ❌ Raises AttributeError
```

❌ **Don't Prevent**: Indexed assignments
```python
widget.curve_data[idx] = (frame, x, y)  # ✅ Still works (calls getter, modifies returned list)
```

⚠️ **Post-Phase 6.3 Impact**: After CurveDataStore removal, indexed assignments will break:
```python
# Phase 6.3+: This will BREAK (modifies copy, not ApplicationState)
widget.curve_data[idx] = new_value

# Must migrate to:
data = list(app_state.get_curve_data(curve_name))
data[idx] = new_value
app_state.set_curve_data(curve_name, data)
```

**See**: [Phase 6.3 - CurveDataStore Removal](PHASE_6.3_CURVEDATASTORE_REMOVAL.md) for indexed assignment migration.

---

## Part B: Create Validation Test Suite

### Required Tests

Create `tests/test_phase6_validation.py`:

```python
"""Phase 6 migration validation tests."""

import pytest
import threading
from stores.application_state import get_application_state
from core.models import CurvePoint
from rendering.render_state import RenderState
from core.display_mode import DisplayMode

def test_curve_data_property_is_read_only(curve_view_widget):
    """Verify widget.curve_data setter raises AttributeError."""
    with pytest.raises(AttributeError, match="read-only"):
        curve_view_widget.curve_data = []

def test_selected_indices_property_is_read_only(curve_view_widget):
    """Verify widget.selected_indices setter raises AttributeError."""
    with pytest.raises(AttributeError, match="read-only"):
        curve_view_widget.selected_indices = {1, 2, 3}

def test_curve_data_thread_safety_during_batch():
    """Verify batch updates complete without race conditions."""
    app_state = get_application_state()
    widget = create_test_widget()
    app_state.set_curve_data("test", create_test_curve())
    app_state.set_active_curve("test")

    errors = []

    def batch_update():
        try:
            app_state.begin_batch()
            for i in range(50):
                data = list(app_state.get_curve_data("test"))
                data.append(CurvePoint(i, i, i))
                app_state.set_curve_data("test", data)
        except Exception as e:
            errors.append(e)
        finally:
            app_state.end_batch()

    # Run multiple concurrent batch operations
    threads = [threading.Thread(target=batch_update) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread safety errors: {errors}"
    final_data = app_state.get_curve_data("test")
    assert isinstance(final_data, list)

def test_rendering_all_visible_no_active_curve():
    """Verify display_mode=ALL_VISIBLE works when active_curve=None.

    Gap identified: Multi-curve edge case not covered by agent reviews.
    """
    widget = create_test_widget()
    app_state = get_application_state()

    # Load 10 curves but set no active curve
    for i in range(10):
        app_state.set_curve_data(f"Track{i}", create_test_curve())
    app_state.set_active_curve(None)  # No active curve

    # Set display mode to show all
    app_state.set_show_all_curves(True)

    # Should render all 10 curves, not crash
    render_state = RenderState.compute(widget)
    assert len(render_state.visible_curves) == 10

    # widget.curve_data should return [] with warning
    data = widget.curve_data
    assert data == []

def test_frame_store_syncs_on_active_curve_switch():
    """Verify FrameStore updates when switching curves without data changes.

    Critical validation for StoreManager active_curve_changed connection.
    """
    app_state = get_application_state()
    app_state.set_curve_data("Track1", create_curve_with_frames(1, 100))
    app_state.set_curve_data("Track2", create_curve_with_frames(50, 200))

    app_state.set_active_curve("Track1")
    assert store_manager.frame_store.min_frame == 1
    assert store_manager.frame_store.max_frame == 100

    # Switch without modifying data
    app_state.set_active_curve("Track2")
    assert store_manager.frame_store.min_frame == 50  # Should update!
    assert store_manager.frame_store.max_frame == 200

def test_active_curve_none_rendering():
    """Verify rendering doesn't crash when active_curve=None."""
    widget = create_test_widget()
    app_state = get_application_state()

    app_state.set_active_curve(None)

    # Should not crash, returns empty data
    data = widget.curve_data
    assert data == []

    # Rendering should handle empty gracefully
    render_state = RenderState.compute(widget)
    # Should not crash
```

### Optional Integration Tests (Recommended)

```python
def test_batch_signal_deduplication():
    """Verify end_batch emits only 1 signal for N operations."""
    app_state = get_application_state()
    signals_received = []
    app_state.curves_changed.connect(lambda _: signals_received.append(1))

    app_state.begin_batch()
    for i in range(100):
        app_state.add_point("test", CurvePoint(i, i, i))
    app_state.end_batch()

    assert len(signals_received) == 1  # Not 100!

def test_selection_bidirectional_sync():
    """Verify selection syncs between widget and tracking controller."""
    # Test widget selection → ApplicationState → tracking controller
    # Test tracking controller selection → ApplicationState → widget
    pass

def test_undo_redo_integration_post_migration():
    """Verify CommandManager works after CurveDataStore removal."""
    # Execute command, undo, redo, verify state
    pass

def test_session_save_restore_post_migration():
    """Verify session persistence without CurveDataStore."""
    # Save session, clear state, restore, verify
    pass
```

---

## Exit Criteria

### Part A (Setters)
- [ ] Both setters implemented in `ui/curve_view_widget.py`
- [ ] Manual verification: `widget.curve_data = []` raises AttributeError
- [ ] Manual verification: `widget.selected_indices = {1}` raises AttributeError

### Part B (Tests)
- [x] File created at `tests/test_phase6_validation.py`
- [x] All 6 required tests implemented (3 passing, 3 XFAIL awaiting Phase 6.2/6.3 implementation)
- [x] 4 optional integration tests implemented (all passing)
- [x] Integrated into pytest suite

---

**Next**: [Phase 6.3 - CurveDataStore Removal →](PHASE_6.3_CURVEDATASTORE_REMOVAL.md)
