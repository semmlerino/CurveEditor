# 🤖 AGENT QUICK REFERENCE CARD

## **IMPLEMENTATION AGENTS**

### Phase 1: Critical Safety Fixes
```bash
# Agent: plan-tau-phase1-implementer
# Tasks: Race conditions, Qt signals, hasattr removal

claude-code --agent plan-tau-phase1-implementer \
  "Implement Task 1.1: Fix Property Setter Race Conditions"
```
**Key Skills:** Signal connections, race condition patterns, CLAUDE.md compliance

---

### Phase 2: Quick Wins
```bash
# Agent: plan-tau-phase2-implementer
# Tasks: Utilities, deduplication, NamedTuples

claude-code --agent plan-tau-phase2-implementer \
  "Implement Task 2.1: Frame Clamping Utility"
```
**Key Skills:** Utility creation, TDD, pattern replacement

---

### Phase 3: Architectural Refactoring
```bash
# Agent: plan-tau-phase3-architect
# Tasks: Controller splitting, facade patterns

claude-code --agent plan-tau-phase3-architect \
  "Implement Task 3.1: Split MultiPointTrackingController"
```
**Key Skills:** Architectural refactoring, SRP, backward compatibility

---

### Phase 4: Polish & Optimization
```bash
# Agent: plan-tau-phase4-polisher
# Tasks: Decorators, batch simplification, cleanup

claude-code --agent plan-tau-phase4-polisher \
  "Implement Task 4.2: Widget Destruction Guard Decorator"
```
**Key Skills:** Decorator patterns, incremental cleanup, type safety

---

## **REVIEW AGENTS**

### Phase 1 Review
```bash
# Agent: plan-tau-phase1-reviewer
# Validates: Race fixes, signals, hasattr removal

claude-code --agent plan-tau-phase1-reviewer \
  "Review Phase 1 implementation and create report"
```
**Checks:** 0 hasattr, 50+ Qt.QueuedConnection, all tests pass

---

### Phase 2 Review
```bash
# Agent: plan-tau-phase2-reviewer
# Validates: Utilities, test coverage, DRY compliance

claude-code --agent plan-tau-phase2-reviewer \
  "Review Phase 2 implementation and create report"
```
**Checks:** 100% test coverage, 60+ duplications removed

---

### Phase 3 Review
```bash
# Agent: plan-tau-phase3-reviewer
# Validates: Architecture, SRP, backward compatibility

claude-code --agent plan-tau-phase3-reviewer \
  "Review Phase 3 implementation and create report"
```
**Checks:** God objects split, each file < 500 lines

---

### Phase 4 Review
```bash
# Agent: plan-tau-phase4-reviewer
# Validates: Decorators, cleanup, quality metrics

claude-code --agent plan-tau-phase4-reviewer \
  "Review Phase 4 implementation and create report"
```
**Checks:** Decorators applied, type ignores reduced 35%

---

## **CROSS-PHASE AGENTS**

### Integration Testing
```bash
# Agent: plan-tau-integration-tester
# Purpose: End-to-end integration verification

claude-code --agent plan-tau-integration-tester \
  "Run integration tests across all phases"
```
**Tests:** Timeline, tracking, undo/redo, signal timing

---

### Final Verification
```bash
# Agent: plan-tau-final-verifier
# Purpose: Complete plan verification

claude-code --agent plan-tau-final-verifier \
  "Perform final verification and create completion report"
```
**Certifies:** All metrics achieved, plan complete

---

## **WORKFLOW CHEATSHEET**

### Per-Phase Workflow
```bash
# 1. Implement
claude-code --agent plan-tau-phase[N]-implementer "Task X.Y"

# 2. Review
claude-code --agent plan-tau-phase[N]-reviewer "Review Phase N"

# 3. Fix issues (if any)
# Re-run implementation agent with fixes

# 4. Re-review
# Run review agent again

# 5. Proceed when review passes
```

### Complete Plan Workflow
```bash
# Phase 1
plan-tau-phase1-implementer → plan-tau-phase1-reviewer → ✅

# Phase 2
plan-tau-phase2-implementer → plan-tau-phase2-reviewer → ✅

# Phase 3
plan-tau-phase3-architect → plan-tau-phase3-reviewer → ✅

# Phase 4
plan-tau-phase4-polisher → plan-tau-phase4-reviewer → ✅

# Integration
plan-tau-integration-tester → ✅

# Final
plan-tau-final-verifier → 🎉 COMPLETE
```

---

## **VERIFICATION COMMANDS**

```bash
# Per-phase verification
./verify_phase1.sh  # After Phase 1
./verify_phase2.sh  # After Phase 2
./verify_phase3.sh  # After Phase 3
./verify_phase4.sh  # After Phase 4

# Full verification
./verify_all.sh     # After all phases
```

---

## **COMMON AGENT COMMANDS**

### Check Progress
```bash
# Show current task status
grep -r "TODO\|FIXME" plan_tau/*.md

# Count remaining issues
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l
grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | wc -l
```

### Run Tests
```bash
# Quick test (stop on first failure)
~/.local/bin/uv run pytest tests/ -x -q

# Full test suite
~/.local/bin/uv run pytest tests/ -v --tb=short

# Specific phase tests
~/.local/bin/uv run pytest tests/test_frame_change_coordinator.py -v
```

### Type Checking
```bash
# Errors only
~/.local/bin/uv run ./bpr --errors-only

# Full report
~/.local/bin/uv run ./bpr
```

---

## **AGENT TIPS**

### For Implementation:
- ✅ Use TodoWrite to track progress
- ✅ Test after EVERY change
- ✅ Commit after each subtask
- ✅ Run verification scripts continuously
- ✅ Ask questions if unclear

### For Review:
- 🔍 Check EVERY success criterion
- 🔍 Provide specific locations for failures
- 🔍 Include statistics and metrics
- 🔍 Don't approve until ALL criteria met
- 🔍 Create detailed reports

---

**See [AGENTS.md](AGENTS.md) for complete agent specifications**

**Navigation:**
- [← Back to Overview](README.md)
- [Complete Agents Guide](AGENTS.md)
