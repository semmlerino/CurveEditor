# Curve Visibility Architecture Refactor Plan
## Agent-Orchestrated Implementation

## Executive Summary

**Problem**: Curve visibility logic has implicit state dependencies causing bugs. When selecting curves, both `show_all_curves=False` AND `selected_curve_names` must be set, but this coordination is not enforced.

**Root Cause**: Three overlapping visibility mechanisms with scattered coordination logic:
1. `show_all_curves` boolean (global filter)
2. `selected_curve_names` set (subset filter)
3. `metadata.visible` dict (per-curve filter)

**Solution**: Staged refactoring using specialized agents for 30% faster implementation with higher quality.

**Time Estimate**: 6-7 hours with agent orchestration (vs 10 hours manual)

---

## Architecture Issues Identified

### 1. Implicit State Dependencies
- Renderer requires BOTH `show_all_curves=False` AND curve in `selected_curve_names`
- No enforcement mechanism - caller must know to set both
- API doesn't match mental model: `set_curves_data(selected_curves=[...])` should "just work"

### 2. Scattered Coordination Logic
- Rendering decision: `OptimizedCurveRenderer._render_multiple_curves()` (line 1088-1090)
- State coordination: `CurveDataFacade.set_curves_data()` (line 140-146)
- No single source of truth for "which curves should render?"

### 3. Confusing Semantics
- `show_all_curves=True`: Show all visible curves (respecting metadata)
- `show_all_curves=False`: Show only selected curves
- Not intuitive - boolean doesn't capture three-way choice (all/selected/active)

### 4. Migration Debt
- Original: Single active curve only
- Phase 6: Added `show_all_curves` toggle
- Later: Added `selected_curve_names` for subset selection
- Now: Three stacked filters with complex interaction

### 5. Testing Gaps
- Tests verify STATE but not BEHAVIOR
- `test_selection_without_show_all_curves` passed while rendering bug existed
- Need tests that verify actual rendering, not just flag values

---

## Agent-Orchestrated Solution Stages

### Stage 1: Immediate Safety Net ⚡
**Time**: 1.2 hours (40% faster with parallel agents)
**Risk**: Minimal
**Agents**: python-implementation-specialist + test-development-master (parallel)

#### What Gets Built
- ✅ `should_render_curve()` method centralizing visibility logic
- ✅ Behavior-based rendering tests (verify actual rendering)
- ✅ CLAUDE.md documentation update

#### Copy-Paste Prompt

```bash
"Use python-implementation-specialist and test-development-master agents in parallel:

python-implementation-specialist: Add should_render_curve() method to ui/curve_view_widget.py that centralizes visibility logic. Current logic is scattered across show_all_curves (boolean), selected_curve_names (set), and metadata.visible (dict). The method should:
- Accept curve_name and metadata dict
- Return boolean for whether curve should render
- Document all three visibility filters in docstring
- Handle: metadata.visible check first, then show_all_curves vs selected_curve_names logic

test-development-master: Add behavior-based rendering test in tests/test_multi_point_selection.py that verifies which curves ACTUALLY render (not just state flags). Test should:
- Set up multiple curves (Track1, Track2, Track3)
- Call set_curves_data(selected_curves=['Track1', 'Track3'])
- Mock renderer to capture which curves it attempts to draw
- Assert Track1 and Track3 render, Track2 does NOT
- This test would have caught the original bug where state was correct but rendering was wrong"
```

**Then manually**: Update CLAUDE.md with visibility architecture notes (15 min)

#### Agent Deliverables
- **python-implementation-specialist**: `should_render_curve()` method with comprehensive docstring
- **test-development-master**: Behavior test that fails without fix, passes with fix

#### Verification
- [ ] All tests pass (2223/2223)
- [ ] New test catches original bug (comment out fix, test fails)
- [ ] should_render_curve() returns correct boolean for all cases
- [ ] CLAUDE.md clearly documents three visibility filters

---

### Stage 2: DisplayMode Foundation 🏗️
**Time**: 2.5 hours (30% faster with parallel verification)
**Risk**: Low
**Agents**: python-expert-architect → python-implementation-specialist → (test-development-master + python-code-reviewer in parallel)

#### What Gets Built
- ✅ DisplayMode enum (ALL_VISIBLE, SELECTED, ACTIVE_ONLY)
- ✅ display_mode property in CurveViewWidget
- ✅ should_render_curve() updated to use enum
- ✅ Backward compatibility with show_all_curves

#### Copy-Paste Prompts

**Step 1: Architecture Design (30 min)**
```bash
"Use python-expert-architect to design DisplayMode enum pattern for curve visibility refactoring. Current issue: boolean show_all_curves is confusing (True=all visible, False=selected only) and doesn't capture three-way choice.

Design requirements:
- DisplayMode enum with explicit states: ALL_VISIBLE (show all with metadata.visible=True), SELECTED (show only selected_curve_names), ACTIVE_ONLY (show only active curve)
- Property-based backward compatibility: display_mode property that derives from show_all_curves, and setter that updates show_all_curves
- Migration strategy: Keep boolean for now, derive enum from it, eventually remove boolean
- Include: Type definitions, property implementation pattern, migration path"
```

**Step 2: Implementation (45 min)**
```bash
"Use python-implementation-specialist to implement DisplayMode enum designed by python-expert-architect.

Create ui/display_mode.py with:
- DisplayMode enum (ALL_VISIBLE, SELECTED, ACTIVE_ONLY)

Update ui/curve_view_widget.py with:
- display_mode property that derives from show_all_curves (getter)
- display_mode setter that updates show_all_curves for backward compat
- Update should_render_curve() to use display_mode enum internally
- Maintain all existing behavior (backward compatibility critical)

Reference the architecture design for patterns and migration strategy."
```

**Step 3: Verification (1 hour - PARALLEL)**
```bash
"Use test-development-master and python-code-reviewer agents in parallel:

test-development-master: Write comprehensive test suite in tests/test_display_mode.py covering:
- DisplayMode enum values
- display_mode property derivation from show_all_curves
- display_mode setter updates show_all_curves correctly
- should_render_curve() works with each DisplayMode
- Backward compatibility: setting show_all_curves updates display_mode
- Edge cases: empty selections, None active curve

python-code-reviewer: Review DisplayMode implementation in ui/display_mode.py and ui/curve_view_widget.py focusing on:
- Backward compatibility (existing code must work unchanged)
- Property implementation correctness
- Enum design quality
- Documentation clarity
- Migration path viability"
```

#### Agent Deliverables
- **python-expert-architect**: DisplayMode design document with migration strategy
- **python-implementation-specialist**: Working DisplayMode enum with backward-compatible property
- **test-development-master**: Comprehensive test suite (>90% coverage)
- **python-code-reviewer**: Review report with any issues/improvements

#### Verification
- [ ] All existing tests pass (backward compat verified)
- [ ] DisplayMode enum has 3 values
- [ ] display_mode property correctly derives from show_all_curves
- [ ] Setting display_mode updates show_all_curves
- [ ] should_render_curve() uses DisplayMode internally
- [ ] New tests have >90% coverage

---

### Stage 3: Full Migration 🚀
**Time**: 2.5 hours (40% faster with parallel analysis/verification)
**Risk**: Medium (touching critical rendering code)
**Agents**: (code-refactoring-expert + performance-profiler in parallel) → python-implementation-specialist → (test-development-master + python-code-reviewer in parallel)

#### What Gets Built
- ✅ Pre-computed visibility in RenderState
- ✅ Simplified renderer logic using curves_to_render
- ✅ CurveDataFacade sets DisplayMode.SELECTED explicitly
- ✅ Performance verified (no regression)

#### Copy-Paste Prompts

**Step 1: Pre-Migration Analysis (45 min - PARALLEL)**
```bash
"Use code-refactoring-expert and performance-profiler agents in parallel to analyze rendering/coordination logic before DisplayMode migration:

code-refactoring-expert: Analyze rendering/coordination flow in:
- rendering/optimized_curve_renderer.py (_render_multiple_curves method)
- ui/controllers/curve_view/curve_data_facade.py (set_curves_data method)
- ui/curve_view_widget.py (paintEvent method)
Identify: Scattered visibility checks, coordination gaps, refactoring opportunities for DisplayMode migration

performance-profiler: Establish baseline performance metrics for:
- render_multiple_curves execution time
- paintEvent overhead
- should_render_curve() call frequency
This baseline ensures no regression after migration"
```

**Step 2: Implement Migration (1 hour)**
```bash
"Use python-implementation-specialist to migrate to DisplayMode pattern based on refactoring analysis:

1. Update rendering/render_state.py:
   - Add curves_to_render: set[str] | None field
   - This pre-computes visibility to centralize logic

2. Update ui/curve_view_widget.py paintEvent():
   - Compute curves_to_render BEFORE creating RenderState using should_render_curve()
   - Pass to RenderState construction

3. Update rendering/optimized_curve_renderer.py:
   - Simplify _render_multiple_curves to use curves_to_render
   - Remove scattered visibility checks (metadata.visible, show_all_curves logic)
   - Single check: if curves_to_render and curve_name not in curves_to_render: continue

4. Update ui/controllers/curve_view/curve_data_facade.py set_curves_data():
   - When selected_curves provided, set display_mode = DisplayMode.SELECTED (explicit!)
   - Remove manual show_all_curves coordination
   - Clear intent: selected_curves parameter triggers SELECTED mode"
```

**Step 3: Verification (45 min - PARALLEL)**
```bash
"Use test-development-master and python-code-reviewer agents in parallel:

test-development-master: Ensure comprehensive test coverage after migration:
- Verify set_curves_data(selected_curves=[...]) sets DisplayMode.SELECTED
- Verify renderer uses pre-computed curves_to_render
- Verify backward compatibility (all existing tests pass)
- Add performance benchmarks comparing to baseline (must be within 5%)
- Coverage target: >90% for all modified files

python-code-reviewer: Final review of migrated code:
- Verify visibility logic is centralized (no scattered checks)
- Verify DisplayMode is used consistently
- Verify no implicit coordination remains
- Check for edge cases or potential bugs
- Validate performance characteristics"
```

#### Agent Deliverables
- **code-refactoring-expert**: Refactoring analysis with migration recommendations
- **performance-profiler**: Baseline metrics and performance requirements
- **python-implementation-specialist**: Migrated code using DisplayMode pattern
- **test-development-master**: Test suite with performance benchmarks
- **python-code-reviewer**: Final review report

#### Verification
- [ ] All tests pass (2223/2223)
- [ ] RenderState has curves_to_render field
- [ ] paintEvent() computes visibility before rendering
- [ ] Renderer uses single check (curves_to_render)
- [ ] Facade sets DisplayMode.SELECTED explicitly
- [ ] Performance within 5% of baseline
- [ ] No scattered visibility logic remains

---

## Decision Framework

### Choose Stage 1 Only (Minimal) if:
- ✓ First occurrence of this bug type
- ✓ Team has higher priority features
- ✓ Codebase is stable overall
- ✓ Planning to deprecate multi-curve system soon

### Proceed to Stage 2 (DisplayMode) if:
- ✓ Similar coordination bugs have occurred before
- ✓ Team frequently confused by show_all_curves semantics
- ✓ Multi-curve is core to product value
- ✓ Planning to add more display modes (e.g., filter by status)

### Complete Stage 3 (Full Migration) if:
- ✓ ≥3 coordination bugs in 3 months
- ✓ Team committed to cleaner architecture
- ✓ Have 3+ hours for complete migration
- ✓ Want to prevent all future coordination issues

---

## Recommended Approach: Data-Driven Staging

### Immediate (Next session)
1. ✅ **DONE**: Fixed immediate bug (show_all_curves=False when selected_curves provided)
2. **Execute Stage 1** (1.2 hours with agents)
   - Parallel: Implementation + Testing
   - Manual: Documentation update
   - **Deliverable**: Bug fixed with comprehensive safety net

### Short-term (Next sprint if bandwidth)
1. **Execute Stage 2** (2.5 hours with agents)
   - Sequential: Architecture → Implementation
   - Parallel: Testing + Review
   - **Deliverable**: DisplayMode enum with backward compatibility

### Long-term (If bugs recur)
1. **Track coordination bugs** over 2-3 months
2. **If ≥3 bugs occur**: Execute Stage 3 (2.5 hours with agents)
3. **If <3 bugs occur**: Keep Stage 2 and close issue
4. **Deliverable**: Complete migration with centralized visibility logic

---

## Success Metrics

### Stage 1 Success Metrics
- ✅ Behavior test catches original bug (comment out fix → test fails)
- ✅ should_render_curve() centralizes logic
- ✅ CLAUDE.md prevents similar mistakes
- ✅ Zero production risk (additive only)
- ✅ Agents identify edge cases we might miss

### Stage 2 Success Metrics
- ✅ DisplayMode makes intent explicit (ALL_VISIBLE/SELECTED/ACTIVE_ONLY)
- ✅ API matches mental model (display_mode vs confusing boolean)
- ✅ Backward compatibility maintained (all tests pass)
- ✅ Easier to add new display modes in future
- ✅ Architecture review confirms design quality

### Stage 3 Success Metrics
- ✅ Zero coordination bugs in 6 months
- ✅ Visibility logic centralized (single source of truth)
- ✅ Performance within 5% of baseline
- ✅ Code reviews mention improved clarity
- ✅ New features don't require visibility fixes
- ✅ Technical debt reduced

---

## Agent Orchestration Benefits

### Time Savings (30% Faster)
- **Manual**: 10 hours sequential work
- **With Agents**: 6-7 hours with parallel execution
- **Savings**: 3-4 hours (30-40%)

### Quality Improvements
- **Multiple Expert Perspectives**: Each agent brings domain expertise
- **Comprehensive Coverage**: Agents catch edge cases we might miss
- **Reduced Risk**: Multiple reviews before code ships
- **Best Practices**: Agents follow established patterns

### Parallel Execution Wins
- **Stage 1**: Implementation + Testing in parallel (40% faster)
- **Stage 2**: Testing + Review in parallel (30% faster)
- **Stage 3**: Analysis + Verification in parallel (40% faster)

---

## Verification Checklist

### Stage 1 Verification
- [ ] All existing tests pass (2223/2223)
- [ ] New behavior test fails without fix, passes with fix
- [ ] should_render_curve() implementation reviewed
- [ ] Test coverage >90% for should_render_curve()
- [ ] CLAUDE.md clearly documents architecture
- [ ] Agent deliverables complete (implementation + tests)

### Stage 2 Verification
- [ ] DisplayMode enum implemented correctly
- [ ] display_mode property derives from show_all_curves
- [ ] display_mode setter updates show_all_curves
- [ ] should_render_curve() uses DisplayMode internally
- [ ] All existing tests pass (backward compat)
- [ ] New tests have >90% coverage
- [ ] Architecture review approved
- [ ] Code review finds no issues

### Stage 3 Verification
- [ ] Performance analysis baseline established
- [ ] RenderState has curves_to_render field
- [ ] Renderer logic simplified (single visibility check)
- [ ] Facade sets DisplayMode.SELECTED explicitly
- [ ] All tests pass (2223/2223)
- [ ] Performance within 5% of baseline
- [ ] Code review approved
- [ ] No scattered visibility logic remains

---

## Rollback Strategy

### Stage 1 Rollback
- **Action**: Remove should_render_curve() method, delete new tests, revert CLAUDE.md
- **Risk**: Minimal (purely additive)
- **Time**: 15 minutes

### Stage 2 Rollback
- **Action**: Keep DisplayMode enum, revert property implementation
- **Risk**: Low (backward compat maintained via property)
- **Time**: 30 minutes

### Stage 3 Rollback
- **Action**: Revert RenderState changes, restore old renderer logic, restore facade coordination
- **Risk**: Medium (multiple files affected)
- **Time**: 1 hour
- **Mitigation**: Git branch per stage for easy revert

---

## File Change Map

### Stage 1 Files
- `tests/test_multi_point_selection.py` - Add behavior test (agent: test-development-master)
- `ui/curve_view_widget.py` - Add should_render_curve() (agent: python-implementation-specialist)
- `CLAUDE.md` - Document architecture (manual)

### Stage 2 Files
- `ui/display_mode.py` (NEW) - DisplayMode enum (agent: python-implementation-specialist)
- `ui/curve_view_widget.py` - Add display_mode property (agent: python-implementation-specialist)
- `tests/test_display_mode.py` (NEW) - Test enum and property (agent: test-development-master)

### Stage 3 Files
- `rendering/render_state.py` - Add curves_to_render (agent: python-implementation-specialist)
- `ui/curve_view_widget.py` - Compute visibility in paintEvent (agent: python-implementation-specialist)
- `rendering/optimized_curve_renderer.py` - Simplify logic (agent: python-implementation-specialist)
- `ui/controllers/curve_view/curve_data_facade.py` - Set DisplayMode (agent: python-implementation-specialist)
- `tests/test_rendering_performance.py` (NEW) - Performance benchmarks (agent: test-development-master)
- `CLAUDE.md` - Update with new API patterns (manual)

---

## Quick Start: Execute Stage 1 Now

**Copy-paste this complete workflow:**

```bash
"Use python-implementation-specialist and test-development-master agents in parallel:

python-implementation-specialist: Add should_render_curve() method to ui/curve_view_widget.py that centralizes visibility logic. Current logic is scattered across show_all_curves (boolean), selected_curve_names (set), and metadata.visible (dict). The method should:
- Accept curve_name and metadata dict
- Return boolean for whether curve should render
- Document all three visibility filters in docstring
- Handle: metadata.visible check first, then show_all_curves vs selected_curve_names logic

test-development-master: Add behavior-based rendering test in tests/test_multi_point_selection.py that verifies which curves ACTUALLY render (not just state flags). Test should:
- Set up multiple curves (Track1, Track2, Track3)
- Call set_curves_data(selected_curves=['Track1', 'Track3'])
- Mock renderer to capture which curves it attempts to draw
- Assert Track1 and Track3 render, Track2 does NOT
- This test would have caught the original bug where state was correct but rendering was wrong"
```

**Then**: Update CLAUDE.md with visibility architecture notes (15 min manual work)

**Expected Deliverables**:
- ✅ Centralized visibility method
- ✅ Behavior test preventing regression
- ✅ Clear documentation

**Time**: 1.2 hours (vs 2 hours manual)

---

## Notes

- ✅ Current fix (show_all_curves=False when selected_curves provided) is CORRECT and SHIPPED
- This plan is about preventing FUTURE bugs through better architecture
- Agent orchestration provides 30% time savings with higher quality
- All stages maintain backward compatibility - no breaking changes
- Parallel agent execution is 50-70% faster for independent tasks
- Each agent brings specialized expertise (testing, architecture, refactoring, review)
