# CurveEditor TODO

This list consolidates remaining actionable refactoring and cleanup tasks identified in previous project reviews and plans. For historical details, see `REFACTORING_PLAN.md` and code review documents in the project root.

---

## ~~1. Refactor `ui_components.py`~~ ✅ COMPLETED (2025-05-28)
- ✅ Split the large `ui_components.py` file into logical, smaller component modules:
    - ✅ `timeline_components.py` (Timeline UI)
    - ✅ `point_edit_components.py` (Point editing UI)
    - ✅ `toolbar_components.py` (Toolbar UI)
    - ✅ `status_components.py` (Status bar components)
    - ✅ `visualization_components.py` (Visualization controls)
    - ✅ `smoothing_components.py` (Smoothing controls)
- ✅ Created a facade in the original `ui_components.py` for backward compatibility.
- ✅ Verified imports across the codebase work correctly.

## ~~2. Service Layer Rationalization~~ ✅ COMPLETED (2025-05-28)
- ✅ Analyzed the service dependency graph to identify natural groupings.
- ✅ Merged small utility modules:
    - ✅ `curve_utils.py` merged into `curve_service.py`
- ✅ Removed deprecated services:
    - ✅ Deleted `transform.py` (deprecated)
    - ✅ Deleted `transformation_service.py` (deprecated)
- ✅ Kept services with distinct responsibilities separate (SRP principle)

## ~~3. Import Organization and Cleanup~~ ✅ COMPLETED (2025-05-29)
- ✅ Standardized import organization in all files:
    1. ✅ Standard library imports first
    2. ✅ Third-party imports second
    3. ✅ Local application imports third
- ✅ Verified no circular imports exist.
- ✅ Removed commented-out or unused imports.
- ✅ All service files properly organized (32+ files across 4 sessions)

---

**Note:**
- Most previous high-priority refactoring (unified transformation system, type safety, DRY/KISS/YAGNI) is complete and reflected in the main docs.
- This list is for remaining technical debt and codebase cleanup.
