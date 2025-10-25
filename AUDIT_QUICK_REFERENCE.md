# Best Practices Audit - Quick Reference

## Overall Score: 72/100 → Target: 88/100

---

## 🔴 CRITICAL (Fix Immediately)

### 1. Type Errors (5 found)
**Location**: Test files  
**Time to Fix**: 1 hour

```bash
# Run this to see errors:
~/.local/bin/uv run basedpyright tests/controllers/

# Files with errors:
- tests/controllers/test_timeline_controller.py:15
- tests/controllers/test_view_camera_controller.py:14-16  
- tests/controllers/test_view_management_controller.py:16
```

**Quick Fixes**:
1. `test_timeline_controller.py:15` - Remove `main_window=` parameter
2. `test_view_camera_controller.py:14` - Add `widget` parameter
3. `test_view_management_controller.py:16` - Remove `state_manager=` parameter

---

### 2. Missing Type Annotations on Fixtures (42 warnings)
**Location**: All test files  
**Time to Fix**: 1 hour

**Pattern to Fix**:
```python
# BEFORE
@pytest.fixture
def controller(mock_main_window):
    return ActionHandlerController(mock_main_window, ...)

# AFTER
@pytest.fixture
def controller(mock_main_window: MockMainWindow) -> ActionHandlerController:
    return ActionHandlerController(mock_main_window, ...)
```

**Files**:
- tests/controllers/test_action_handler_controller.py
- tests/controllers/test_frame_change_coordinator.py
- tests/controllers/test_point_editor_controller.py
- tests/controllers/test_signal_connection_manager.py
- tests/controllers/test_timeline_controller.py
- tests/controllers/test_ui_initialization_controller.py
- tests/controllers/test_view_camera_controller.py
- tests/controllers/test_view_management_controller.py

---

## 🟠 IMPORTANT (Complete Phase 1)

### 3. Protocol Migration (7 Controllers, 87.5%)
**Location**: ui/controllers/  
**Time to Fix**: 4-6 hours  
**Exemplar**: ActionHandlerController (✓ Complete)

**Controllers to Migrate**:
1. ✗ ViewManagementController → Use `MainWindowProtocol`
2. ✗ TimelineController → Use `StateManagerProtocol`
3. ✗ PointEditorController → Use `MainWindowProtocol + StateManagerProtocol`
4. ✗ UIInitializationController → Use `MainWindowProtocol`
5. ✗ Signal connection manager → Use appropriate protocols
6. ✗ Frame change coordinator → Use protocols
7. ✗ Base tracking controller → Use protocols

**Pattern**:
```python
# BEFORE (concrete type)
class ViewManagementController:
    def __init__(self, main_window: "MainWindow"):

# AFTER (protocol)
from protocols.ui import MainWindowProtocol

class ViewManagementController:
    def __init__(self, main_window: MainWindowProtocol):
```

---

### 4. Test Implementation (20 of 24 Stubs)
**Location**: tests/controllers/  
**Time to Fix**: 12-18 hours  
**Current**: 4 implemented, 20 stubs (17% coverage)

**Stub Tests by File**:
- test_action_handler_controller.py: 1 stub
- test_timeline_controller.py: 3 stubs
- test_view_management_controller.py: 4 stubs
- test_point_editor_controller.py: 3 stubs
- test_view_camera_controller.py: 2 stubs
- test_ui_initialization_controller.py: 2 stubs
- test_signal_connection_manager.py: 2 stubs
- test_frame_change_coordinator.py: 2 stubs

**Test Template**:
```python
def test_behavior_description(self, controller: ControllerType, mock_main_window):
    """Test that [action] results in [outcome]."""
    # Arrange
    mock_main_window.state = initial_state
    
    # Act
    controller.method()
    
    # Assert
    assert mock_main_window.state == expected_state
```

---

## 🟡 NICE-TO-HAVE (Polish)

### 5. Type Annotation Gaps (8 class attributes)
**Time**: 30 minutes

Files:
- ui/controllers/curve_view/curve_data_facade.py:53-54
- ui/controllers/curve_view/render_cache_controller.py:55
- ui/controllers/curve_view/state_sync_controller.py:53,56,57
- ui/controllers/tracking_data_controller.py:40-42

### 6. Large Method Refactoring
**Time**: 2 hours  
**File**: ui/controllers/action_handler_controller.py:232

`apply_smooth_operation()` (110 lines) → Split into:
- `_validate_smooth_inputs()` (20 lines)
- `_apply_smooth_via_command()` (30 lines)
- `_apply_smooth_via_service()` (40 lines)
- `_update_smooth_status()` (10 lines)

### 7. Unsafe Code Patterns
**Time**: 1 hour

**Pattern 1** - Unsafe getattr (action_handler_controller.py:244):
```python
# UNSAFE
curve_data = getattr(self.main_window.curve_widget, "curve_data", [])

# SAFE
if self.main_window.curve_widget:
    curve_data = self.main_window.curve_widget.curve_data
else:
    curve_data = []
```

**Pattern 2** - Protected member access (2 files):
- frame_change_coordinator.py:227
- signal_connection_manager.py:195,218
→ Make `_update_point_status_label()` public or expose through protocol

---

## Implementation Roadmap

### Week 1 (Priority: Type Safety)
- [ ] Fix 5 type errors in tests (1 hour)
- [ ] Add type annotations to all test fixtures (1 hour)
- [ ] Create tests/controllers/conftest.py (30 min)
- [ ] Run basedpyright → verify 0 errors (30 min)

### Week 2-3 (Priority: Architecture)
- [ ] Migrate 7 controllers to protocols (4-6 hours)
  - Start with ViewManagementController (template)
  - Follow with TimelineController
  - End with PointEditorController
- [ ] Implement critical tests (4-6 hours, prioritize by controller complexity)

### Week 4+ (Polish)
- [ ] Implement remaining tests (6-8 hours)
- [ ] Fix type annotation gaps (30 min)
- [ ] Refactor large methods (2 hours)
- [ ] Clean up unsafe patterns (1 hour)

---

## Quality Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Type errors | 5 | 0 | 🔴 CRITICAL |
| Type warnings | 77 | <20 | 🟠 IMPORTANT |
| Test coverage | 17% | 70%+ | 🟠 IMPORTANT |
| Protocol adoption | 12.5% | 100% | 🟠 IMPORTANT |
| Code documentation | 85% | 95% | 🟡 NICE |

**Estimated improvement path**:
- After Week 1: 72 → 75 (type safety)
- After Week 2-3: 75 → 82 (architecture + tests)
- After Week 4: 82 → 88 (polish)

---

## Key Files

**Protocol Definitions** (Good baseline):
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/protocols/ui.py` (1208 lines)

**Exemplar Implementation** (Follow this pattern):
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/action_handler_controller.py`

**Priority Fixes**:
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/tests/controllers/test_*.py` (All 8 files)
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/view_management_controller.py`
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/controllers/timeline_controller.py`

---

## Success Criteria

✓ All basedpyright type errors resolved (0 errors)  
✓ Type warnings reduced to <20  
✓ All test fixtures have proper type annotations  
✓ 7 controllers migrated to protocol usage  
✓ Test coverage >70% (20+ tests implemented)  
✓ Code quality score: 88/100+  

---

## Resources

**Full Report**: See `BEST_PRACTICES_AUDIT_REPORT.md` (618 lines)

**Configuration**:
- Type checking: `pyproject.toml` [tool.basedpyright]
- Linting: `pyproject.toml` [tool.ruff]
- Testing: `pyproject.toml` [tool.pytest.ini_options]

**Commands**:
```bash
# Type checking
~/.local/bin/uv run basedpyright protocols/ ui/controllers/ tests/controllers/

# Linting
~/.local/bin/uv run ruff check ui/controllers/ tests/controllers/

# Testing
~/.local/bin/uv run pytest tests/controllers/ -v

# Quick audit
~/.local/bin/uv run basedpyright --stats protocols/ ui/controllers/ tests/controllers/
```

