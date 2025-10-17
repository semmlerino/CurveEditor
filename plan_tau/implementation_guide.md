## 📅 **IMPLEMENTATION TIMELINE**

### **Week 1: Critical Safety (Phase 1)**
- **Mon-Tue:** Task 1.1 + 1.2 (Race conditions + Qt.QueuedConnection)
- **Wed-Thu:** Task 1.3 (hasattr() replacement)
- **Fri:** Task 1.4 + Phase 1 verification

### **Week 2: Quick Wins (Phase 2)**
- **Mon:** Tasks 2.1 + 2.2 (Frame utils + deepcopy)
- **Tue:** Tasks 2.3 + 2.4 (NamedTuple + frame range)
- **Wed:** Task 2.5 (SelectionContext removal)
- **Thu-Fri:** Phase 2 verification + documentation

### **Week 3: Architecture Part 1 (Phase 3)**
- **Mon-Wed:** Task 3.1 (Split MultiPointTrackingController)
- **Thu-Fri:** Start Task 3.2 (Split InteractionService)

### **Week 4: Architecture Part 2 (Phase 3)**
- **Mon-Wed:** Finish Task 3.2 (InteractionService split)
- **Thu:** Task 3.3 (StateManager delegation removal)
- **Fri:** Phase 3 verification

### **Week 5: Polish Part 1 (Phase 4)**
- **Mon:** Task 4.1 (Batch system simplification)
- **Tue-Wed:** Task 4.2 (Safe slot decorator)
- **Thu-Fri:** Tasks 4.3 + 4.4 (Helper methods)

### **Week 6: Polish Part 2 & Final Verification (Phase 4)**
- **Mon-Wed:** Task 4.5 (Type ignore cleanup)
- **Thu:** Full verification suite
- **Fri:** Documentation updates + merge to main

---

## 📝 **COMMIT MESSAGE TEMPLATE**

Use consistent commit messages:

```bash
# Format:
<phase>(<task>): <description>

# Examples:
phase1(race-conditions): Fix property setter race in StateManager
phase1(qt-signals): Add explicit Qt.QueuedConnection to 50+ connections
phase1(hasattr): Replace hasattr() with None checks (15 files)

phase2(frame-utils): Extract frame clamping utility (60 duplications eliminated)
phase2(selection): Remove SelectionContext enum, add explicit methods

phase3(tracking-controller): Split MultiPointTrackingController into 3 controllers
phase3(interaction-service): Split InteractionService into 4 services
phase3(state-manager): Remove deprecated data delegation (~350 lines)

phase4(batch): Simplify batch update system (105 → 32 lines)
phase4(decorator): Add @safe_slot decorator (49 uses)
```

---

## 🎓 **POST-IMPLEMENTATION CHECKLIST**

After completing all phases:

- [ ] All verification scripts pass (`verify_all.sh`)
- [ ] Full test suite passes (2,345 tests)
- [ ] Type checker clean (0 errors)
- [ ] Code review completed
- [ ] Documentation updated
- [ ] CLAUDE.md compliance verified
- [ ] Performance benchmarks run (no regression)
- [ ] Branch merged to main
- [ ] Tag created: `plan-tau-complete`
- [ ] Retrospective document created

---

## 📚 **DOCUMENTATION UPDATES**

After completion, update:

1. **CLAUDE.md:**
   - Add examples using new utilities
   - Document split controller architecture
   - Update best practices section

2. **README.md:**
   - Update architecture diagram
   - Document new service structure
   - Add utility function examples

3. **TESTING_ROADMAP_ASSESSMENT.md:**
   - Update with new controller tests
   - Note improved coverage

4. **Create PLAN_TAU_RETROSPECTIVE.md:**
   - What went well
   - What was challenging
   - Lessons learned
   - Metrics achieved

---

## 🎯 **FINAL NOTES**

### **Key Principles:**

1. **Test After Every Change:** Never proceed with failing tests
2. **Small Commits:** Commit after each task completion
3. **Verify Continuously:** Run verification scripts frequently
4. **Document as You Go:** Update comments and docs during implementation
5. **Ask for Help:** If stuck, consult team or pause for review

### **Success Criteria Summary:**

This plan is COMPLETE when:
- ✅ All 4 phases verified
- ✅ 0 critical bugs remain
- ✅ ~3,000 lines of unnecessary code removed
- ✅ CLAUDE.md 100% compliance
- ✅ All 2,345 tests passing
- ✅ Type checker clean (0 errors)
- ✅ Architecture simplified (god objects split)
- ✅ Code-documentation alignment restored

### **Expected Outcome:**

A cleaner, more maintainable codebase with:
- Fewer bugs (race conditions eliminated)
- Better architecture (SRP enforced)
- Improved type safety (35% fewer ignores)
- Enhanced readability (DRY compliance)
- Faster development velocity (simpler code)

---

**END OF PLAN TAU**

**Status:** ✅ READY FOR IMPLEMENTATION
**Last Updated:** 2025-10-14
**Next Action:** Begin Phase 1, Task 1.1

---

**Navigation:**
- [← Back to Overview](README.md)
- [Risk & Rollback](risk_and_rollback.md)
- [Verification & Testing](verification_and_testing.md)
