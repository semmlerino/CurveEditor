# Task 3.3 Implementation Blockers - MUST FIX BEFORE STARTING

**Status**: 🔴 **BLOCKED** - Do not start implementation until resolved

---

## 🔴 BLOCKER #1: Signal Migration Not Inventoried (CRITICAL)

**Problem**: Inventory only checked property access, NOT signal connections.

**Impact**: UI will break if signals aren't migrated (components won't receive updates).

**Fix Required**:
```bash
# Add to phase3_task33_inventory.txt:
echo "" >> phase3_task33_inventory.txt
echo "## Signal connections requiring migration:" >> phase3_task33_inventory.txt

echo "### frame_changed signal:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.frame_changed\.\(connect\|disconnect\)" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

echo "### selection_changed signal:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.selection_changed\.\(connect\|disconnect\)" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt

echo "### total_frames_changed signal:" >> phase3_task33_inventory.txt
grep -rn "state_manager\.total_frames_changed\.\(connect\|disconnect\)" ui/ services/ core/ --include="*.py" >> phase3_task33_inventory.txt
```

**Expected Results**: 8 signal connections/disconnections across 3 files:
1. `ui/controllers/frame_change_coordinator.py` - 3 usages
2. `ui/controllers/signal_connection_manager.py` - 2 usages
3. `ui/timeline_tabs.py` - 3 usages

**Migration Pattern**:
```python
# Before:
self.main_window.state_manager.frame_changed.connect(self.on_frame_changed)

# After:
from stores.application_state import get_application_state
get_application_state().frame_changed.connect(self.on_frame_changed)
```

---

## 🟡 BLOCKER #2: total_frames API Inconsistency (HIGH)

**Problem**: Analysis document says `total_frames` is a property, but ApplicationState uses `get_total_frames()` METHOD.

**Impact**: Migration will fail with AttributeError if pattern is followed as documented.

**Fix Option A** (Quick - update documentation):
```python
# Update phase3_task33_analysis.txt migration pattern:
# WRONG (current docs):
state_manager.total_frames → get_application_state().total_frames

# CORRECT:
state_manager.total_frames → get_application_state().get_total_frames()
```

**Fix Option B** (Better - add property for API consistency):
```python
# Add to stores/application_state.py:
@property
def total_frames(self) -> int:
    """Get total frames (derived from image files)."""
    return self.get_total_frames()
```

**Recommendation**: Option B - Provides API consistency with `current_frame` property.

---

## 🟡 ISSUE #3: selected_points Type Mismatch (MEDIUM)

**Problem**: StateManager returns `list[int]`, ApplicationState returns `set[int]`.

**Impact**: Code expecting list operations (indexing) will break.

**Fix**: Use `sorted()` for backward compatibility:
```python
# Migration pattern (update phase3_task33_analysis.txt):
state = get_application_state()
active = state.active_curve
selection = sorted(state.get_selection(active)) if active else []
# Returns list[int] for backward compatibility
```

---

## 🟡 ISSUE #4: data_bounds Business Logic (MEDIUM)

**Problem**: StateManager.data_bounds contains 17 lines of calculation logic, NOT simple delegation.

**Impact**: Logic will be lost if migration treats this as "just change the call".

**Fix**: Move logic to ApplicationState:
```python
# Add to stores/application_state.py:
def get_data_bounds(self, curve_name: str | None = None) -> tuple[float, float, float, float]:
    """Get data bounds as (min_x, min_y, max_x, max_y) for a curve."""
    if curve_name is None:
        curve_name = self.active_curve

    if not curve_name:
        return (0.0, 0.0, 1.0, 1.0)

    curve_data = self.get_curve_data(curve_name)
    if not curve_data:
        return (0.0, 0.0, 1.0, 1.0)

    x_coords = [float(point[1]) for point in curve_data]
    y_coords = [float(point[2]) for point in curve_data]
    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
```

Then migrate the 1 callsite to use `get_application_state().get_data_bounds()`.

---

## ✅ Resolution Checklist

- [ ] Complete signal inventory (Blocker #1)
- [ ] Resolve total_frames API (Blocker #2) - Choose Option A or B
- [ ] Update selected_points pattern (Issue #3)
- [ ] Add get_data_bounds to ApplicationState (Issue #4)
- [ ] Update phase3_task33_analysis.txt with corrected patterns
- [ ] Review updated inventory and confirm all callsites captured

**Once all items checked**: Task 3.3 is ready for implementation.

---

## Time Impact

**Original Estimate**: 1-1.5 days (based on 9 files)
**Adjusted Estimate**: 1.5-2 days (adding signal migration)

**Breakdown**:
- Property migration: 6 hours
- Signal migration: 1.5 hours (NEW)
- Testing: 2 hours
- Cleanup: 1 hour
- Buffer: 1 hour
- **Total**: ~11.5 hours ≈ 1.5 days

---

**See full analysis**: `PLAN_TAU_TASK33_ARCHITECTURAL_ASSESSMENT.md`
