# CurveEditor TODO

This list consolidates remaining actionable refactoring and cleanup tasks identified in previous project reviews and plans. For historical details, see `REFACTORING_PLAN.md` and code review documents in the project root.

---

## 1. Refactor `ui_components.py`
- Split the large `ui_components.py` file into logical, smaller component modules:
    - `timeline_components.py` (Timeline UI)
    - `point_edit_components.py` (Point editing UI)
    - `toolbar_components.py` (Toolbar UI)
    - `status_components.py` (Status bar components)
- Create a facade in the original `ui_components.py` for backward compatibility.
- Gradually update imports across the codebase to use the new modules.

## 2. Service Layer Rationalization
- Analyze the service dependency graph to identify natural groupings.
- Consider merging related services:
    - `image_service.py` + `visualization_service.py`
- Enforce consistent interfaces and protocol definitions across all services.

## 3. Import Organization and Cleanup
- Standardize import organization in all files:
    1. Standard library imports first
    2. Third-party imports second
    3. Local application imports third
- Refactor to avoid circular imports.
- Remove commented-out or unused imports.

---

**Note:**
- Most previous high-priority refactoring (unified transformation system, type safety, DRY/KISS/YAGNI) is complete and reflected in the main docs.
- This list is for remaining technical debt and codebase cleanup.
