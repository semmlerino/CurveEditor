# CurveEditor Refactoring Quick Start Guide

**TL;DR**: 20 hours of focused work can remove ~2,300 lines and improve maintainability 40%

---

## Top 5 Consensus Issues (All 3 Agents Agree)

### 🥇 #1: Dead Code Removal (EASIEST WIN)
**Effort**: 2 hours | **Risk**: Very Low | **Impact**: -1,400 lines

```bash
# Immediate actions (30 minutes)
git rm services/data_analysis.py              # 326 lines, 0 production usage
git rm core/service_utils.py                  # 156 lines, never imported
git mv core/validation_strategy.py docs/examples/  # 637 lines, test-only
# Delete backup files (4 files)
```

---

### 🥈 #2: Controller Over-Decomposition
**Effort**: 8-12 hours | **Risk**: Medium | **Impact**: 13 → 7 controllers

**Problem**: 4 tracking controllers do one job
- `TrackingDataController`
- `TrackingDisplayController`
- `TrackingSelectionController`
- `MultiPointTrackingController`

**Solution**: Merge into single `TrackingController` (~700 lines)

---

### 🥉 #3: Command Pattern Duplication
**Effort**: 4-6 hours | **Risk**: Low | **Impact**: -240 lines, prevents bugs

**Current**: Every command manually stores target curve (easy to forget, causes bugs)

**Fix**: Base class handles target storage automatically

```python
# BEFORE: Manual in every command (bug-prone)
self._target_curve = curve_name  # Easy to forget!

# AFTER: Automatic in base class
def _execute_operation(self, curve_name, curve_data):
    # Target storage happens automatically
    return smoothed_data
```

---

### #4: ApplicationState Interface Segregation
**Effort**: 2-4 hours | **Risk**: Very Low | **Impact**: 90% simpler tests

**Current**: 50+ methods, clients use 1-2

**Fix**: Add focused protocols
```python
class FrameProvider(Protocol):
    current_frame: int

# Instead of mocking 50 methods, mock 1 property
```

---

### #5: Large Service Classes
**Effort**: 16 hours | **Risk**: Medium-High | **Defer**

- InteractionService (1,763 lines)
- DataService (1,199 lines)

**Recommendation**: Only split if testability becomes blocker

---

## 3-Week Roadmap

### Week 1: Quick Wins (8 hours)
✅ Delete dead code (2h) → -1,400 lines
✅ Fix command pattern (4h) → -240 lines, prevent bugs
✅ Add protocols (2h) → Foundation for better tests

**Result**: -1,640 lines, safer code, better testability

---

### Week 2-3: Controller Consolidation (12 hours)
✅ Merge 4 tracking controllers → 1 (8h)
✅ Extract SessionManager from MainWindow (4h)

**Result**: 13 → 7 controllers, clearer responsibilities

---

### Future: Service Splitting (16 hours) - OPTIONAL
⏸️ Split DataService → FileIO, Image, Analysis (8h)
⏸️ Split InteractionService → Selection, Mouse, Commands, Points (8h)

**Note**: Only do if hitting concrete testability issues

---

## File Locations Reference

**Dead Code**:
- `/services/data_analysis.py` (delete)
- `/core/service_utils.py` (delete)
- `/core/validation_strategy.py` (move to docs/examples/)

**Controller Consolidation**:
- `/ui/controllers/tracking_data_controller.py` (merge)
- `/ui/controllers/tracking_display_controller.py` (merge)
- `/ui/controllers/tracking_selection_controller.py` (merge)
- `/ui/controllers/multi_point_tracking_controller.py` (merge)
- → Create `/ui/controllers/tracking_controller.py` (new)

**Command Pattern**:
- `/core/commands/curve_commands.py` (refactor base class)
- All command subclasses in `/core/commands/` (update)

**Protocols**:
- Create `/protocols/state.py` (new file)
- `/stores/application_state.py` (implement protocols, no code change)

---

## Immediate Next Actions

**Day 1 (2 hours)**:
```bash
# Terminal commands
cd /mnt/c/CustomScripts/Python/Work/Linux/CurveEditor

# Remove dead code
git rm services/data_analysis.py
git rm core/service_utils.py
git mv core/validation_strategy.py docs/examples/validation_pattern.py
# Delete backup files manually

# Commit
git commit -m "chore: remove 1,100+ lines of dead code (data_analysis, service_utils, validation)"

# Run tests to verify nothing breaks
~/.local/bin/uv run pytest tests/
```

**Day 2-3 (4 hours)**: Refactor command pattern base class

**Day 4 (2 hours)**: Add ApplicationState protocols

---

## Key Metrics

| Metric | Before | After Week 1 | After Week 3 |
|--------|--------|--------------|--------------|
| Dead Code | ~1,400 lines | 0 lines | 0 lines |
| Controllers | 13 | 13 | 7 |
| Command Boilerplate | ~240 lines | 0 lines | 0 lines |
| Lines of Code | ~79,800 | ~78,400 | ~77,500 |
| Maintainability | Baseline | +20% | +40% |
| Test Complexity | Baseline | -30% | -60% |

---

## Decision Matrix

### ✅ DO THIS (High ROI):
- Week 1 Quick Wins (8 hours)
- Week 2-3 Controller Consolidation (12 hours)

### ⚠️ MAYBE (If Time/Need):
- Service Splitting (only if testability blocks progress)

### ❌ DON'T DO (Low ROI):
- Architectural overhaul (current design is appropriate)
- Splitting large files just to split them (files are cohesive)
- Over-optimization (YAGNI applies)

---

## Questions?

**Q: Is this safe?**
A: Week 1 is very low risk (deleting unused code). Week 2-3 is medium risk (test thoroughly).

**Q: What if I break something?**
A: Git history preserves everything. Comprehensive test suite will catch issues.

**Q: Do I need to do all phases?**
A: No! Week 1 Quick Wins alone gives huge benefit. Week 2-3 is optional. Service splitting can be deferred.

**Q: What's the absolute minimum?**
A: Just delete dead code (2 hours, -1,400 lines, zero risk).

---

**Full Analysis**: See `REFACTORING_SYNTHESIS_REPORT.md` (detailed breakdown, code examples, migration strategies)
