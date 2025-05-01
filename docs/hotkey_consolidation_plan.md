# Hotkey Logic Consolidation Plan

## Objective
Centralize all hotkey/shortcut logic—including navigation, menu actions, and dialog/subview shortcuts—using `ShortcutManager` in `keyboard_shortcuts.py`. Remove all direct key handling and deprecated code.

---

## 1. ShortcutManager Enhancements
- Ensure all actions (including navigation, visualization toggles, menu actions, and dialog-specific shortcuts) are defined in the `SHORTCUTS` dict.
- Add any missing actions (e.g., frame navigation, grid toggle, velocity vectors, etc.).
- For each shortcut, provide a unique ID, key sequence, and description.

---

## 2. Centralized Shortcut Setup
- In the main window and all relevant subviews/dialogs, call `ShortcutManager.setup_shortcuts(self)` to initialize shortcuts.
- Use `ShortcutManager.connect_shortcut(self, shortcut_id, slot_function)` to connect each shortcut to its handler.
- For dialogs and subviews, ensure they register their shortcuts with `ShortcutManager` upon initialization.

---

## 3. Migration of Direct Key Handling
- **EnhancedCurveView**: Remove `keyPressEvent` delegation to `VisualizationOperations.handle_key_press` and `CurveViewOperations.handle_key_press`. Instead, connect all relevant actions (e.g., grid toggle, velocity vectors, select all, reset view, etc.) via `ShortcutManager`.
- **VisualizationOperations & CurveViewOperations**: Remove all direct key handling logic from `handle_key_press` methods. Migrate their logic to slot functions connected via `ShortcutManager`.
- **MainWindow**: Remove direct navigation key handling from `keyPressEvent`. Register all navigation shortcuts (period, comma, home, end, shift+period, etc.) in `ShortcutManager` and connect to the appropriate UIComponents methods.
- **Dialogs/Subviews**: Register any dialog-specific shortcuts centrally.

---

## 4. Menu Actions
- Remove any explicit shortcut assignments from `QAction` objects in menu_bar.py.
- Ensure all menu actions with shortcuts are registered and connected via `ShortcutManager`.

---

## 5. Deprecated Code Cleanup
- Remove all deprecated shortcut connection methods and related comments from all files.

---

## 6. Documentation and Dialog Updates
- Update the shortcut dialog (`ShortcutsDialog`) to reflect the new, fully centralized shortcut registry.
- Update documentation to describe the new architecture and usage pattern.

---

## 7. Testing
- Use or extend `verify_signals.py` to check that all defined shortcuts are present and connected.
- Manually test all shortcuts in the UI to ensure correct behavior.

---

## Mermaid Diagram: Centralized Shortcut Architecture

```mermaid
flowchart TD
    subgraph UI_Components
        MainWindow
        EnhancedCurveView
        Dialogs
        MenuBar
    end

    ShortcutManager["ShortcutManager (keyboard_shortcuts.py)"]
    ShortcutsDialog["ShortcutsDialog"]
    Actions["Slot Functions (UI logic, e.g., UIComponents, CurveViewOperations, etc.)"]

    UI_Components -->|setup_shortcuts()| ShortcutManager
    ShortcutManager -->|connect_shortcut()| Actions
    ShortcutManager --> ShortcutsDialog
    MenuBar -->|QAction.triggered| Actions
```

---

## Summary Table: Migration Tasks

| File/Module                | Action                                                                 |
|----------------------------|------------------------------------------------------------------------|
| keyboard_shortcuts.py      | Add/verify all shortcut definitions and slot connections                |
| enhanced_curve_view.py     | Remove keyPressEvent, connect all actions via ShortcutManager           |
| visualization_operations.py| Remove handle_key_press, migrate logic to slot functions                |
| curve_view_operations.py   | Remove handle_key_press, migrate logic to slot functions                |
| main_window.py             | Remove keyPressEvent, connect navigation via ShortcutManager            |
| menu_bar.py                | Remove explicit QAction shortcuts, use ShortcutManager                  |
| dialogs.py/dialog_operations.py | Register dialog shortcuts via ShortcutManager                      |
| verify_signals.py          | Ensure all shortcuts are present and connected                         |
| documentation.md           | Update to reflect new architecture                                     |