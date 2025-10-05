# Selection State Refactoring - Overview

**Date**: October 2025
**Status**: Ready for Implementation (Revised)
**Based On**: SELECTION_STATE_ARCHITECTURE_SOLUTION.md + Three Independent Reviews
**Revision**: Incorporates fixes for 8 critical/high-priority issues

---

## Navigation

- **Next**: [Phases 1-3: Core Infrastructure](01_PHASES_1_TO_3.md)
- **See Also**: [Phases 4-6](02_PHASES_4_TO_6.md) | [Phases 7-8 & Completion](03_PHASES_7_TO_8_AND_COMPLETION.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 1: Add Selection State to ApplicationState](01_PHASES_1_TO_3.md#phase-1-add-selection-state-to-applicationstate)
3. [Phase 2: Update TrackingPointsPanel](01_PHASES_1_TO_3.md#phase-2-update-trackingpointspanel)
4. [Phase 2.5: Comprehensive Migration Audit](01_PHASES_1_TO_3.md#phase-25-comprehensive-migration-audit-new)
5. [Phase 3: Update CurveViewWidget with Deprecation](01_PHASES_1_TO_3.md#phase-3-update-curveviewwidget-with-deprecation)
6. [Phase 4: Update MultiCurveManager](02_PHASES_4_TO_6.md#phase-4-update-multicurvemanager)
7. [Phase 5: Update Controllers](02_PHASES_4_TO_6.md#phase-5-update-controllers)
8. [Phase 6: Update Tests](02_PHASES_4_TO_6.md#phase-6-update-tests)
9. [Phase 7: Documentation and Session Persistence](03_PHASES_7_TO_8_AND_COMPLETION.md#phase-7-documentation-and-session-persistence)
10. [Phase 8: Final Cleanup - Remove All Backward Compatibility](03_PHASES_7_TO_8_AND_COMPLETION.md#phase-8-final-cleanup---remove-all-backward-compatibility-new)
11. [Rollback Instructions](03_PHASES_7_TO_8_AND_COMPLETION.md#rollback-instructions)

---

## Overview

### Problem Being Solved

**Bug**: Selecting multiple curves in tracking panel only shows one curve in the viewport.

**Root Cause**: Selection state is fragmented across three locations with manual synchronization:
1. `TrackingPointsPanel` - checkbox state and table selection
2. `MultiCurveManager.selected_curve_names` - stored selection
3. `CurveViewWidget._display_mode` - stored display mode

When `selected_curve_names` is updated but `display_mode` is not set to `SELECTED`, only the active curve renders.

### Solution Architecture

**Centralize ALL selection inputs in ApplicationState** and make `display_mode` a computed property:

```
ApplicationState (Single Source of Truth):
├─ _selected_curves: set[str]           # Authoritative input
├─ _show_all_curves: bool               # Authoritative input
└─ display_mode: @property → DisplayMode  # Computed (never stored)
```

**Key Insight**: Derived state should NEVER be stored. Compute it fresh every time.

### Critical Fixes in This Revision

This revised plan addresses **8 critical and high-priority issues** identified by independent reviews:

1. ✅ **Phase ordering fixed** - Deprecation wrapper added before breaking changes
2. ✅ **Widget field synchronization** - Updates `selected_curve_names` and `selected_curves_ordered`
3. ✅ **Comprehensive audit phase** - Phase 2.5 finds ALL affected locations before changes
4. ✅ **Validation added** - Warns about non-existent curves without breaking initialization
5. ✅ **Redundant updates removed** - Controller doesn't re-update what Panel already did
6. ✅ **Backward compatibility** - Temporary compatibility layer for smooth migration
7. ✅ **Complete test coverage** - All edge cases covered
8. ✅ **Session persistence** - Selection state survives restart

---

## Implementation Phases

### Phase 1-3: Core Infrastructure ([Details](01_PHASES_1_TO_3.md))
- **Phase 1**: Add selection state to ApplicationState
- **Phase 2**: Update TrackingPointsPanel to use ApplicationState
- **Phase 2.5**: Comprehensive migration audit (finds all affected code)
- **Phase 3**: Add deprecation wrapper to CurveViewWidget

### Phase 4-6: Integration & Testing ([Details](02_PHASES_4_TO_6.md))
- **Phase 4**: Update MultiCurveManager with backward-compat properties
- **Phase 5**: Update controllers, remove synchronization loop
- **Phase 6**: Update all tests with comprehensive edge case coverage

### Phase 7-8: Documentation & Cleanup ([Details](03_PHASES_7_TO_8_AND_COMPLETION.md))
- **Phase 7**: Add documentation and session persistence
- **Phase 8**: Remove all backward compatibility (final cleanup)

---

## Agent Deployment Strategy

This refactoring uses **specialized agents** for implementation and review. Based on `ORCHESTRATOR_QUICK_REFERENCE.md`:

### 🤖 Primary Implementation Agent

**`python-implementation-specialist`** - Used for Phases 1-7
- **Why**: Requirements are crystal clear, straightforward implementation
- **Not architect**: No complex design decisions needed (design already done)
- **Scope**: Each phase explicitly defines file(s) to modify

### 🔄 Orchestration Workflow

#### **Iteration 1: Phases 1-3 (Core Infrastructure)**
```
1. python-implementation-specialist → Phase 1 (stores/application_state.py)
2. python-implementation-specialist → Phase 2 (ui/tracking_points_panel.py)
3. Manual grep audit → Phase 2.5
4. python-implementation-specialist → Phase 3 (ui/curve_view_widget.py)

5. ✅ Launch in parallel (review team - read-only, always safe):
   - python-code-reviewer
   - type-system-expert
```

#### **Iteration 2: Phases 4-5 (Integration)**
```
6. python-implementation-specialist → Phase 4 (ui/multi_curve_manager.py)
7. python-implementation-specialist → Phase 5 (controllers - 3 files)

8. ✅ Launch in parallel (verification team):
   - python-code-reviewer
   - type-system-expert
   - deep-debugger (verify race condition fix)
```

#### **Iteration 3: Phase 6 (Testing)**
```
9. ✅ Launch in parallel (separate test files - safe):
   - test-development-master (integration tests)
   - test-type-safety-specialist (type fixes in existing tests)

10. Manual test run verification
```

#### **Iteration 4: Phases 7-8 (Documentation & Cleanup)**
```
11. ✅ Launch in parallel (different files - safe):
    - api-documentation-specialist (docs)
    - python-implementation-specialist (session persistence)

12. ❌ code-refactoring-expert → Phase 8 (runs alone - exclusive access)

13. ✅ Launch in parallel (final verification):
    - python-code-reviewer
    - type-system-expert
    - best-practices-checker
```

### 🎯 Key Decisions

**Sequential vs Parallel:**
- ✅ **Review teams always parallel** (read-only, always safe)
- ✅ **Testing parallel** if separate test files
- ⚠️ **Implementation sequential** (safer for complex synchronization)
- ❌ **Phase 8 runs alone** (refactoring-expert requires exclusive access)

**Context Passing:**
- Each agent receives findings from previous phases
- Orchestrator synthesizes multi-agent outputs
- Critical fixes explicitly mentioned in prompts

**See individual phase documents** for specific agent deployment notes.

---

## Quick Start

1. **Read this overview** to understand the problem and solution
2. **Review agent deployment strategy** above to understand orchestration
3. **Start with [Phase 1](01_PHASES_1_TO_3.md)** - Follow phases sequentially
4. **Use recommended agents** for each phase (noted in each section)
5. **Verify at each step** - Each phase has verification commands
6. **Use rollback if needed** - Each phase has rollback instructions

---

## Benefits

- ✅ Fixes multi-curve selection bug
- ✅ Eliminates race conditions
- ✅ Prevents future synchronization bugs
- ✅ Cleaner, more maintainable architecture
- ✅ Smooth migration path with backward compatibility
- ✅ Complete test coverage of edge cases
- ✅ Clean final state with no backward-compat cruft
- ✅ **Agent-assisted implementation** with clear orchestration strategy

---

**Next**: Start with [Phase 1: Add Selection State to ApplicationState](01_PHASES_1_TO_3.md)
