# Refactoring Plan: Consolidate Curve Data Operations

## Background

Analysis of the codebase reveals that core curve data operations—such as smoothing, filtering, filling, and extrapolation—are currently scattered across multiple files and implemented as both standalone functions and class methods. This fragmentation leads to code duplication, inconsistent behavior, and maintenance overhead.

## Refactoring Priority

**Top Priority:**  
Consolidate all curve data operations into a single, canonical module/class (e.g., `CurveDataOperations`).  
All UI, batch, and preset logic should call this canonical implementation.

---

## Proposed Refactoring Plan

### 1. Inventory and Map Operations

- List all smoothing, filtering, filling, extrapolation, and batch operations across:
  - `curve_operations.py` (standalone functions and `CurveOperations` class)
  - `batch_edit.py` (batch operation functions)
  - `quick_filter_presets.py` (filter preset logic)
  - `dialog_operations.py` (dialog triggers)

- Identify duplicates and inconsistencies.

### 2. Design Canonical API

- Define a single class (e.g., `CurveDataOperations`) with clear, well-documented methods for each operation.
- Ensure all parameter handling is consistent and extensible.

### 3. Refactor Implementations

- Move all core logic into the canonical class/module.
- Replace all standalone functions and duplicate logic with calls to the canonical implementation.

### 4. Update UI and Preset Integration

- Refactor `batch_edit.py`, `quick_filter_presets.py`, and `dialog_operations.py` to use the new canonical API.
- Remove any redundant wrappers or logic.

### 5. Test and Document

- Ensure all UI and batch operations work as before.
- Update documentation to reflect the new architecture.

---

## Architecture Diagrams

### Current (Fragmented)

```mermaid
graph TD
    A[DialogOperations] -->|calls| B[curve_operations.py (functions)]
    A -->|calls| C[batch_edit.py (batch functions)]
    A -->|calls| D[quick_filter_presets.py]
    C -->|calls| B
    D -->|calls| B
    B -->|has| E[CurveOperations class]
    B -->|has| F[Standalone functions]
```

### Proposed (Centralized)

```mermaid
graph TD
    A[DialogOperations] -->|calls| Z[CurveDataOperations (canonical)]
    C[batch_edit.py] -->|calls| Z
    D[quick_filter_presets.py] -->|calls| Z
    Z -->|has| E[All curve ops: smooth, filter, fill, extrapolate, etc.]
```

---

## Benefits

- **Reduced duplication:** All logic in one place.
- **Consistent behavior:** Single source of truth for all curve operations.
- **Easier maintenance:** Updates and bug fixes are localized.
- **Extensibility:** New operations can be added cleanly.

---

## Next Steps

1. Inventory all relevant operations and map their current locations.
2. Design the canonical API and class structure.
3. Refactor codebase to use the new implementation.
4. Test thoroughly and update documentation.