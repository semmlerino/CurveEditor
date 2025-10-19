# CurveEditor Documentation Index

**Last Updated**: October 2025

---

## 📘 Primary Documentation (Read First)

### **CLAUDE.md**
Main development guide for CurveEditor project.

**Contents**:
- Project scope and philosophy
- Code quality standards
- Architecture overview (4 services, state management)
- Multi-curve support patterns
- State management (`ApplicationState` vs `StateManager`)
- Core data models and terminology
- Development environment setup
- Type safety guidelines
- Common patterns and examples
- Keyboard shortcuts

**Audience**: All developers
**Status**: ✅ Active - Updated continuously

---

## 🎯 Current Focus: KISS/DRY Refactoring

### **VERIFIED_KISS_DRY_ASSESSMENT.md**
Comprehensive analysis of KISS/DRY violations in the codebase.

**Contents**:
- 4-agent parallel analysis (verified 95% accurate)
- 5 multi-agent consensus findings (100% verified)
- Quantitative metrics: 326 lines potential savings
- Verification methodology and confidence levels
- Prioritized recommendations (P0-P2)

**Key Findings**:
1. Command pattern boilerplate (150 lines, P0)
2. Duplicate navigation methods (60 lines, P0)
3. Active curve data pattern inconsistency (36 lines, P1)
4. Deep nesting in UI updates (28 lines + complexity, P1)
5. Error handling inconsistency (robustness, P1)

**Audience**: Developers planning refactoring work
**Status**: ✅ Active - Reference for implementation

---

### **KISS_DRY_IMPLEMENTATION_PLAN.md**
Step-by-step implementation plan for KISS/DRY improvements.

**Contents**:
- 4 phases, 10 tasks, 18 hours estimated effort
- Specific code changes (before/after with line numbers)
- Success metrics (quantitative + qualitative)
- Verification steps (automated + manual tests)
- Rollback procedures
- Progress tracking template
- 4-week timeline

**Quick Wins**: Task 1.2 (30 min, 60 lines saved) ⭐

**Audience**: Developers implementing refactoring
**Status**: ✅ Active - Ready for execution

---

## 📊 Historical Context

### **PHASE4_EXECUTIVE_SUMMARY.txt**
Summary of Phase 4: StateManager Simplification Migration (completed October 2025).

**Contents**:
- Phase 4 objectives and outcomes
- Migration from mixed state to single source of truth
- ApplicationState owns all data
- StateManager owns all UI preferences

**Audience**: Context for current architecture
**Status**: ✅ Active - Historical reference

---

### **PERFORMANCE_BASELINE_REPORT.txt**
Performance baseline measurements.

**Contents**:
- Baseline performance metrics
- Optimization targets
- Measurement methodology

**Audience**: Performance optimization work
**Status**: ✅ Active - Reference for performance work

---

## 📁 Archived Documentation

### **docs/archive/2025-10-phase4-reviews/**

Archived October 2025 - Phase 4 completion reports and preliminary reviews.

**Contents**:
- 6 Phase 4 task completion reports (4.1-4.5)
- Preliminary code quality reviews
- TAU pattern planning docs (superseded by "Pattern A")
- Decision frameworks and checklists

**See**: `docs/archive/2025-10-phase4-reviews/README.md` for details

**Status**: 📦 Archived - Historical record only

---

## 🗂️ Documentation by Purpose

### For New Developers
1. **Start here**: `CLAUDE.md`
2. **Understand architecture**: `PHASE4_EXECUTIVE_SUMMARY.txt`
3. **Current work**: `KISS_DRY_IMPLEMENTATION_PLAN.md`

### For Active Development
1. **Reference guide**: `CLAUDE.md`
2. **Code quality**: `VERIFIED_KISS_DRY_ASSESSMENT.md`
3. **Implementation**: `KISS_DRY_IMPLEMENTATION_PLAN.md`

### For Performance Work
1. **Baseline**: `PERFORMANCE_BASELINE_REPORT.txt`
2. **Architecture**: `CLAUDE.md` (services section)

### For Code Reviews
1. **Standards**: `CLAUDE.md` (Code Quality Standards section)
2. **Known issues**: `VERIFIED_KISS_DRY_ASSESSMENT.md`
3. **Patterns**: `CLAUDE.md` (Common Patterns section)

---

## 🔄 Documentation Maintenance

### Update Frequency

| Document | Update Frequency | Last Updated |
|----------|------------------|--------------|
| CLAUDE.md | As needed (architectural changes) | October 2025 |
| VERIFIED_KISS_DRY_ASSESSMENT.md | Static (point-in-time analysis) | October 2025 |
| KISS_DRY_IMPLEMENTATION_PLAN.md | Static (implementation guide) | October 2025 |
| PHASE4_EXECUTIVE_SUMMARY.txt | Static (historical) | October 2025 |
| PERFORMANCE_BASELINE_REPORT.txt | Quarterly (re-baseline) | TBD |

### Archive Policy

**When to archive**:
- Task completion reports: Archive after 3 months
- Planning documents: Archive when superseded
- Review reports: Archive when consolidated
- Decision documents: Archive when decisions implemented

**Retention**: Keep archived docs for 6-12 months, then safe to delete

---

## 📝 Creating New Documentation

### Guidelines

1. **Add to CLAUDE.md**: For permanent architectural patterns, standards, conventions
2. **Create separate file**: For point-in-time analysis, planning, reports
3. **Update this index**: When adding new top-level documentation
4. **Archive when done**: Move completed work to `docs/archive/`

### Naming Convention

```
<TYPE>_<TOPIC>_<VARIANT>.md

Types: PLAN, REPORT, ASSESSMENT, SUMMARY, INDEX, GUIDE
Examples:
- KISS_DRY_IMPLEMENTATION_PLAN.md
- VERIFIED_KISS_DRY_ASSESSMENT.md
- PERFORMANCE_BASELINE_REPORT.txt
```

---

## 🔍 Finding Information

### By Topic

| Topic | Document | Section |
|-------|----------|---------|
| Architecture | CLAUDE.md | Architecture Overview |
| State Management | CLAUDE.md | State Management |
| Code Quality | VERIFIED_KISS_DRY_ASSESSMENT.md | - |
| Commands | CLAUDE.md | Command Pattern |
| Multi-curve | CLAUDE.md | Multi-Curve Support |
| Testing | CLAUDE.md | Development Tips |
| Type Safety | CLAUDE.md | Type Safety |
| Performance | PERFORMANCE_BASELINE_REPORT.txt | - |

### Quick Links

```bash
# View main guide
cat CLAUDE.md

# View KISS/DRY assessment
cat VERIFIED_KISS_DRY_ASSESSMENT.md

# View implementation plan
cat KISS_DRY_IMPLEMENTATION_PLAN.md

# View archived docs
ls docs/archive/2025-10-phase4-reviews/
```

---

**Maintained by**: Development team
**Questions**: Refer to CLAUDE.md or archived docs README
