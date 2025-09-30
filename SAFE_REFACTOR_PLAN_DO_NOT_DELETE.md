# Safe MainWindow Refactoring Plan

## Executive Summary
Reduce MainWindow from 1482 to <600 lines through systematic, test-driven extraction while maintaining 100% backward compatibility and test coverage.

## Current State Analysis

### Metrics
- **Total Lines**: 1482
- **Methods**: 88
- **Init Method**: 369 lines (25% of file!)
- **Event Handlers**: 44 methods (~600 lines)
- **Update Methods**: 8 methods (~100 lines)
- **Test Coverage**: 1102 tests passing

### Breakdown by Category
```
__init__:           369 lines (25%)
Event handlers:     ~600 lines (40%)
Update methods:     ~100 lines (7%)
Other methods:      ~413 lines (28%)
```

## Risk Assessment & Mitigation

### Critical Risks
1. **Breaking Functionality**
   - Mitigation: Run full test suite after each change
   - Validation: 1102 tests must pass

2. **Circular Dependencies**
   - Mitigation: Use TYPE_CHECKING imports
   - Validation: ./bpr must run clean

3. **Performance Regression**
   - Mitigation: Run benchmarks before/after
   - Validation: No >5% performance degradation

4. **Lost Encapsulation**
   - Mitigation: Use proper interfaces and protocols
   - Validation: Code review for access patterns

5. **Debugging Complexity**
   - Mitigation: Clear ownership documentation
   - Validation: Stack traces remain clear

## Extraction Strategy

### Phase 0: Preparation (1 hour)
```python
# 1. Create baseline metrics
pytest tests/ --benchmark-only > baseline_performance.txt
wc -l ui/main_window.py > baseline_lines.txt
./bpr > baseline_types.txt

# 2. Create safety net
git checkout -b safe-refactor-mainwindow
git tag pre-refactor-baseline

# 3. Add feature flag
# In main_window.py:
USE_NEW_INIT = os.environ.get('USE_NEW_INIT', 'false').lower() == 'true'
```

### Phase 1: Extract Initialization (369 → 30 lines)

#### 1.1 Create MainWindowInitializer
```python
# ui/main_window_initializer.py
class MainWindowInitializer:
    """Handles all MainWindow initialization logic."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window

    def setup_window_properties(self) -> None:
        """Set basic window properties."""
        self.main_window.setWindowTitle("CurveEditor")
        self.main_window.setMinimumSize(1024, 768)
        self.main_window.resize(1400, 900)

    def setup_managers(self) -> None:
        """Initialize core managers."""
        # Move manager initialization here

    def setup_ui_components(self) -> None:
        """Initialize UI components."""
        # Move UI setup here

    def setup_controllers(self) -> None:
        """Initialize all controllers."""
        # Move controller setup here

    def connect_signals(self) -> None:
        """Connect all signals."""
        # Move signal connections here
```

#### 1.2 Refactor __init__
```python
def __init__(self, parent=None, initial_data_file=None):
    super().__init__(parent)
    self._initial_data_file = initial_data_file

    if USE_NEW_INIT:
        # New streamlined initialization
        self._initializer = MainWindowInitializer(self)
        self._initializer.setup_window_properties()
        self._initializer.setup_managers()
        self._initializer.setup_ui_components()
        self._initializer.setup_controllers()
        self._initializer.connect_signals()
    else:
        # Keep old initialization for rollback
        self._old_init()

    self._finalize_setup()
```

#### 1.3 Testing Strategy
```bash
# Test both paths
USE_NEW_INIT=false pytest tests/test_main_window_critical.py
USE_NEW_INIT=true pytest tests/test_main_window_critical.py

# Compare results
diff old_results.txt new_results.txt
```

### Phase 2: Consolidate Event Handlers (44 methods → delegates)

#### 2.1 Handler Distribution Plan
| Controller | Methods to Move | Count |
|------------|----------------|-------|
| FileOperationsManager | _on_action_new/open/save/save_as/load_images | 5 |
| PlaybackController | _on_play_pause/playback_timer/fps_changed | 6 |
| FrameNavigationController | _on_frame_changed/first/prev/next/last | 5 |
| ZoomController | Already done | 3 |
| PointEditController | _on_point_selected/moved/x_changed/y_changed | 8 |
| TrackingPanelController | _on_tracking_points_selected/visibility/color/deleted/renamed | 5 |
| **NEW: TimelineController** | _on_timeline_tab_clicked/hovered | 3 |
| **NEW: StateChangeController** | _on_selection/view_state/curve_view_changed | 9 |

#### 2.2 Implementation Pattern
```python
# Instead of:
def _on_action_open(self) -> None:
    """Handle open action."""
    # 20 lines of code here

# Replace with:
def _on_action_open(self) -> None:
    """Handle open action."""
    self.file_operations_manager.handle_open()
```

### Phase 3: Extract Update Methods

#### 3.1 Move to ViewUpdateManager
All `update_*` methods move to existing ViewUpdateManager:
- update_status → already there
- update_background_image_for_frame → frame_navigation_controller
- update_ui_state → view_update_manager
- update_cursor_position → view_update_manager
- update_tracking_panel → tracking_panel_controller
- update_curve_display → view_update_manager
- update_curve_view_options → view_update_manager
- update_timeline_tabs → timeline_controller

### Phase 4: Create Thin Delegation Layer

#### 4.1 Property Delegation
```python
# Replace direct access with properties
@property
def current_frame(self) -> int:
    return self.frame_navigation_controller.current_frame

@current_frame.setter
def current_frame(self, value: int) -> None:
    self.frame_navigation_controller.current_frame = value
```

### Phase 5: Final Cleanup

#### 5.1 Remove Dead Code
- Remove commented old implementations
- Remove unused imports
- Remove redundant state tracking

#### 5.2 Consolidate Remaining Methods
- Group related methods
- Extract utility methods to helpers
- Inline single-use methods

## Testing Plan

### Test Execution Matrix
| Phase | Tests to Run | Expected Result | Rollback Trigger |
|-------|-------------|-----------------|-------------------|
| Baseline | Full suite | 1102 pass | N/A |
| Phase 1 | test_main_window_* | 100% pass | Any failure |
| Phase 2 | Full suite | 1102 pass | >5 failures |
| Phase 3 | Full suite | 1102 pass | >5 failures |
| Phase 4 | Full suite + integration | 100% pass | Any regression |
| Phase 5 | Full suite + benchmarks | No regression | >5% perf loss |

### Validation Checkpoints
```bash
# After each phase:
1. pytest tests/ -x  # Stop on first failure
2. ./bpr  # Type check
3. ruff check .  # Lint
4. wc -l ui/main_window.py  # Verify reduction
5. git diff --stat  # Review changes
```

## Implementation Timeline

| Phase | Duration | Lines Saved | Running Total | Target |
|-------|----------|-------------|---------------|--------|
| Current | - | 0 | 1482 | 500 |
| Phase 1 | 2 hours | 339 | 1143 | 500 |
| Phase 2 | 3 hours | 400 | 743 | 500 |
| Phase 3 | 1 hour | 100 | 643 | 500 |
| Phase 4 | 1 hour | 80 | 563 | 500 |
| Phase 5 | 1 hour | 63 | **500** | 500 |

## Rollback Strategy

### Immediate Rollback
```bash
# If tests fail:
git reset --hard pre-refactor-baseline
```

### Gradual Rollback
```bash
# If specific phase fails:
USE_NEW_INIT=false python main.py  # Use environment flags
```

### Feature Flag Control
```python
# In production:
REFACTOR_FLAGS = {
    'USE_NEW_INIT': False,
    'USE_NEW_HANDLERS': False,
    'USE_DELEGATED_UPDATES': False
}

# Gradual rollout:
if user_id % 100 < rollout_percentage:
    REFACTOR_FLAGS['USE_NEW_INIT'] = True
```

## Success Criteria

### Must Have
- [ ] MainWindow < 600 lines
- [ ] All 1102 tests passing
- [ ] No performance regression >5%
- [ ] Type checking passes (./bpr)
- [ ] Linting passes (ruff)

### Should Have
- [ ] Improved code organization
- [ ] Better separation of concerns
- [ ] Easier debugging
- [ ] Clear ownership model

### Nice to Have
- [ ] Performance improvement
- [ ] Reduced memory usage
- [ ] Faster startup time
- [ ] Better test coverage

## Post-Refactor Tasks

1. **Documentation Update**
   - Update architecture diagrams
   - Document new class responsibilities
   - Update developer guide

2. **Team Communication**
   - Code review with team
   - Knowledge transfer session
   - Update coding standards

3. **Monitoring**
   - Track error rates
   - Monitor performance metrics
   - Gather developer feedback

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Test failures | Medium | High | Feature flags | Dev |
| Performance regression | Low | Medium | Benchmarks | Dev |
| Circular imports | Medium | High | TYPE_CHECKING | Dev |
| Lost functionality | Low | Critical | Test coverage | QA |
| Merge conflicts | Medium | Low | Small PRs | Dev |

## Alternative Approaches Considered

1. **Complete Rewrite**: Rejected - too risky
2. **Microservices**: Rejected - overkill for desktop app
3. **Multiple Windows**: Rejected - poor UX
4. **Inheritance Chain**: Rejected - increases complexity

## Conclusion

This plan provides a safe, incremental path to reduce MainWindow from 1482 to <500 lines while maintaining all functionality and test coverage. The use of feature flags and parallel implementation ensures we can rollback at any point without disruption.

---
*Plan Created: 2025-01-13*
*Estimated Duration: 8 hours*
*Risk Level: Medium (with mitigations: Low)*
