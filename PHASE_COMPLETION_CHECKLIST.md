# Phase Completion Checklist

**Before proceeding to Phase 4, complete these tasks:**

---

## ⚠️ CRITICAL: Phase 1 Task 1.3 (4-6 hours)

**Objective:** Remove all 22 remaining hasattr() calls in production code

### Files to Fix (in priority order):

1. **ui/controllers/signal_connection_manager.py** (5 instances in `__del__`)
   ```python
   # Pattern to fix:
   if hasattr(self, "main_window") and hasattr(self.main_window, "file_operations"):

   # Replace with:
   if self.main_window is not None and self.main_window.file_operations is not None:
   ```

2. **ui/controllers/ui_initialization_controller.py** (4 instances)
   ```python
   # Pattern to fix:
   if hasattr(self, "main_window") and hasattr(self.main_window, "ui"):

   # Replace with:
   if self.main_window is not None and self.main_window.ui is not None:
   ```

3. **ui/file_operations.py** (1 instance)
4. **ui/tracking_points_panel.py** (~2 instances)
5. **ui/session_manager.py** (~1 instance)
6. **ui/global_event_filter.py** (~1 instance)
7. **ui/curve_view_widget.py** (~1 instance)
8. **ui/main_window_builder.py** (~1 instance)
9. **ui/widgets/card.py** (~1 instance)
10. **Others** (~5 instances)

### Verification Commands:

```bash
# Find all hasattr() in production code
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l
# Expected: 0

# Run type checker
~/.local/bin/uv run ./bpr --errors-only

# Run full test suite
~/.local/bin/uv run pytest tests/ -x
```

### Success Criteria:
- ✅ 0 hasattr() in production code (ui/, services/, core/)
- ✅ All tests pass
- ✅ Type checker errors = 0
- ✅ CLAUDE.md compliance achieved

---

## Optional: Phase 2 Quick Wins (Can be done during Phase 4)

### Task 2.2: Remove deepcopy(list()) - 30 minutes

**File:** `core/commands/curve_commands.py` (5 instances)

```python
# Lines to fix:
Line 48:  self.new_data = copy.deepcopy(list(new_data))
Line 49:  self.old_data = copy.deepcopy(list(old_data)) if old_data is not None else None
Line 133: self.old_points = copy.deepcopy(list(old_points)) if old_points else None
Line 134: self.new_points = copy.deepcopy(list(new_points)) if new_points else None

# Replace with:
self.new_data = copy.deepcopy(new_data)
self.old_data = copy.deepcopy(old_data) if old_data is not None else None
# etc.
```

**Verification:**
```bash
grep -r "deepcopy(list(" core/commands/ --include="*.py"
# Expected: 0 results
```

### Task 2.3: Add FrameStatus NamedTuple - 2-3 hours

**File:** `core/models.py`

**Add:**
```python
from typing import NamedTuple

class FrameStatus(NamedTuple):
    """Status information for a single frame in timeline."""
    keyframe_count: int
    interpolated_count: int
    tracked_count: int
    endframe_count: int
    normal_count: int
    is_startframe: bool
    is_inactive: bool
    has_selected: bool

    @property
    def total_points(self) -> int:
        return (self.keyframe_count + self.interpolated_count +
                self.tracked_count + self.endframe_count + self.normal_count)
```

**Update consumers:** Find tuple unpacking in `ui/timeline_tabs.py` and convert to named access

### Task 2.5: Deprecate SelectionContext Enum - 2-3 hours

**File:** `ui/controllers/multi_point_tracking_controller.py`

**Current state:** Enum exists with backward-compatible wrapper

**Options:**
1. Keep backward-compatible wrapper (current state is acceptable)
2. Add deprecation warning
3. Fully remove and update all callers

**Recommended:** Add deprecation warning, remove in future cleanup

---

## Phase 4 Readiness Assessment

**Once Phase 1 Task 1.3 is complete:**

```bash
# Run verification script
cat > verify_phase4_readiness.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "=== Phase 4 Readiness Check ==="

# Critical: hasattr() removal
echo "1. Checking hasattr() count..."
COUNT=$(grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS: 0 hasattr() in production code"
else
    echo "❌ FAIL: Found $COUNT hasattr() instances"
    echo "   BLOCKING: Must complete Phase 1 Task 1.3"
    exit 1
fi

# Architecture verification
echo "2. Verifying Phase 3 architecture..."
if [ -f "ui/controllers/tracking_data_controller.py" ] && \
   [ -f "services/interaction_service.py" ] && \
   grep -q "class _MouseHandler" services/interaction_service.py; then
    echo "✅ PASS: Phase 3 architecture intact"
else
    echo "❌ FAIL: Phase 3 architecture incomplete"
    exit 1
fi

# Type checking
echo "3. Running type checker..."
~/.local/bin/uv run ./bpr --errors-only
if [ $? -eq 0 ]; then
    echo "✅ PASS: Type checker clean"
else
    echo "⚠️  WARNING: Type errors found (review before Phase 4)"
fi

# Test suite
echo "4. Running test suite..."
~/.local/bin/uv run pytest tests/ -x -q
if [ $? -eq 0 ]; then
    echo "✅ PASS: All tests pass"
else
    echo "❌ FAIL: Tests failing"
    exit 1
fi

echo ""
echo "=== Phase 4 Readiness: PASS ==="
echo "✅ Ready to proceed to Phase 4"
SCRIPT

chmod +x verify_phase4_readiness.sh
./verify_phase4_readiness.sh
```

---

## Summary

**CRITICAL (must complete):**
- ✅ Phase 1 Task 1.3: Remove 22 hasattr() calls (4-6 hours)

**OPTIONAL (nice to have):**
- Task 2.2: Remove 5 deepcopy(list()) (30 min)
- Task 2.3: Add FrameStatus NamedTuple (2-3 hours)
- Task 2.5: Deprecate SelectionContext (2-3 hours)

**After Phase 1 Task 1.3 completion:**
- Run `verify_phase4_readiness.sh`
- If all checks pass → PROCEED TO PHASE 4 ✅
