# 🎯 PLAN TAU: Comprehensive Code Quality Improvement Plan
## **DO NOT DELETE**

**Created:** 2025-10-14
**Status:** 🚨 AWAITING IMPLEMENTATION (6-agent review confirmed 0% implementation)
**Last Agent Review:** 2025-10-15 (See: `../PLAN_TAU_CONSOLIDATED_AGENT_REVIEW.md`)
**Total Estimated Effort:** 160-226 hours (4-6 weeks full-time, 8-12 weeks part-time)
**Verified Issues:** 24/24 independently confirmed by 6 agents
**Expected Impact:** ~3,000 lines eliminated, 3 critical bugs fixed, architecture simplified

---

## 📂 **DOCUMENT STRUCTURE**

This plan has been organized into focused sections for easier navigation:

### **Overview & Planning**
- [Executive Summary](00_executive_summary.md) - Overview of issues and expected outcomes

### **Implementation Phases**
- [Phase 1: Critical Safety Fixes](phase1_critical_safety_fixes.md) - Week 1 (25-35 hours)
  - Fix property setter race conditions
  - Add explicit Qt.QueuedConnection
  - Replace hasattr() with None checks
  - Verify FrameChangeCoordinator implementation

- [Phase 2: Quick Wins](phase2_quick_wins.md) - Week 2 (15 hours)
  - Frame clamping utility
  - Remove redundant list() in deepcopy()
  - Frame status NamedTuple
  - Frame range extraction utility
  - Remove SelectionContext enum

- [Phase 3: Architectural Refactoring](phase3_architectural_refactoring.md) - Weeks 3-4 (10-12 days)
  - Split MultiPointTrackingController
  - Split InteractionService
  - Remove StateManager data delegation

- [Phase 4: Polish & Optimization](phase4_polish_optimization.md) - Weeks 5-6 (1-2 weeks)
  - Simplify batch update system
  - Widget destruction guard decorator
  - Active curve data helper
  - Type ignore incremental cleanup

### **Support Documentation**
- [Verification & Testing Strategy](verification_and_testing.md) - Testing approach for each phase
- [Risk Mitigation & Success Metrics](risk_and_rollback.md) - Risk management and rollback procedures
- [Implementation Guide](implementation_guide.md) - Timeline, commit templates, checklist
- [**🤖 Specialized Agents Guide**](AGENTS.md) - **Implementation and review agents for each phase**

---

## 🎯 **QUICK REFERENCE**

### **Critical Issues TO BE Fixed**
- ⏳ 2 property setter race conditions (ui/state_manager.py:454, 536 - timeline desync bugs)
- ⏳ 16-20 hasattr() type safety violations (~26-30 legitimate uses remain)
- ⏳ 0 explicit Qt.QueuedConnection → need 50+ (documentation mismatch)
- ⏳ 2 god objects (2,645 lines → target ~1,200 lines in 7 focused services)

### **Expected Code Reduction**
- Target: ~3,000 lines of unnecessary code to be eliminated
- Duplications to remove: ~208 verified patterns
  - 46 hasattr() type safety violations
  - 49 RuntimeError exception handlers
  - 53 transform service getter calls
  - 50 active curve access patterns
  - 10 other (frame clamping, deepcopy, etc.)
- Deprecated delegation to remove: ~350 lines (StateManager)

### **Expected Quality Improvements**
- Type ignore count: 2,151 → ~1,500 (30% reduction target)
- CLAUDE.md compliance: Target 100%
- Code-documentation alignment: To be restored
- Single Responsibility Principle: To be enforced

---

## 📋 **PREREQUISITES**

Before starting implementation, ensure you have:

### **Required Software:**
- **Python:** 3.11+ (modern union syntax `X | None` required)
- **PySide6:** 6.6.0+ (for Qt.QueuedConnection and Signal behavior)
- **uv:** 0.1.0+ or use `.venv/bin/python3` directly (see CLAUDE.md)
- **pytest:** 8.0+ (for running test suite)
- **basedpyright:** 1.8.0+ (for type checking)

### **System Requirements:**
- ~500MB disk space for dependencies
- Git installed (for version control)
- WSL2 (if on Windows) or Linux/macOS

### **Verification:**
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Check if uv is available
which uv || echo "Use .venv/bin/python3 instead"

# Verify test suite works
~/.local/bin/uv run pytest --collect-only -q 2>/dev/null | tail -1
# Should show: 2345 tests collected

# Verify type checker works
./bpr --errors-only
# Should complete without errors
```

---

## 🚀 **GETTING STARTED**

**⚠️ IMPORTANT:** 6-agent review (2025-10-15) confirmed Plan TAU is NOT yet implemented. All tasks remain to be done.

1. **Read Agent Review**: `../PLAN_TAU_CONSOLIDATED_AGENT_REVIEW.md` - Critical findings
2. **Verify Prerequisites**: Check all requirements above
3. **Read**: [Executive Summary](00_executive_summary.md) for overview
4. **🤖 Use Agents**: [Specialized Agents Guide](AGENTS.md) - **Implementation & review agents for each phase**
5. **Begin**: [Phase 1: Critical Safety Fixes](phase1_critical_safety_fixes.md)
6. **Verify BEFORE Committing**: Run `./plan_tau/verify_implementation.sh`
7. **Track**: Use [Implementation Guide](implementation_guide.md) for timeline

### **🤖 RECOMMENDED WORKFLOW**

```bash
# For each phase:
1. Use implementation agent to do the work
2. Use review agent to verify completion
3. Fix any issues found
4. Proceed to next phase when review passes

# Example for Phase 1:
claude-code --agent plan-tau-phase1-implementer \
  "Implement Task 1.1 from plan_tau/phase1_critical_safety_fixes.md"

# Then review:
claude-code --agent plan-tau-phase1-reviewer \
  "Review Phase 1 and create report"
```

---

## 📊 **OVERALL SUCCESS METRICS**

This plan is COMPLETE when `./plan_tau/verify_implementation.sh` passes:
- ⏳ All 4 phases verified
- ⏳ 0 critical bugs remain (currently: 2 property setter races)
- ⏳ ~3,000 lines of unnecessary code removed (currently: 0 removed)
- ⏳ CLAUDE.md 100% compliance (hasattr violations remain)
- ⏳ All 2,345 tests passing (currently passing, must remain so)
- ⏳ Type checker clean (0 errors - currently clean)
- ⏳ Architecture simplified (god objects still 2,645 lines)
- ⏳ Code-documentation alignment restored (currently divergent)

---

**Status:** 🚨 AWAITING IMPLEMENTATION (6-agent review: 0% complete)
**Last Updated:** 2025-10-15 (Post 6-agent review)
**Last Agent Review:** See `../PLAN_TAU_CONSOLIDATED_AGENT_REVIEW.md`
**Next Action:**
1. Read agent review findings
2. Run `./plan_tau/verify_implementation.sh` to see current status
3. Begin Phase 1, Task 1.1 (property setter races - 30 min)
4. Verify BEFORE marking complete
