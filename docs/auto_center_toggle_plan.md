# Plan: Implement Auto-Centering Toggle

This plan outlines the steps to add a toggle feature that automatically centers the curve view on the selected point whenever the current frame changes.

**User Requirements:**

*   **UI Placement:** View menu (checkable action)
*   **Persistence:** Toggle state should be saved between sessions.
*   **Trigger:** Auto-center should activate on all frame changes.

**Implementation Steps:**

1.  **Configuration Update (Using QSettings):**
    *   **Goal:** Add a setting to store the toggle state using `QSettings`.
    *   **Action:**
        *   In `settings_operations.py`, modify `load_settings` to read a new key, e.g., `"view/autoCenterOnFrameChange"`, defaulting to `False`. Store this value in a `main_window` attribute (e.g., `main_window.auto_center_enabled = settings.value("view/autoCenterOnFrameChange", False, type=bool)`).
        *   Modify `save_settings` to write the value of `main_window.auto_center_enabled` back to the `"view/autoCenterOnFrameChange"` key when the application closes.
    *   **Files:** `settings_operations.py`, `main_window.py` (to add the `auto_center_enabled` attribute).

2.  **UI Implementation (Menu):**
    *   **Goal:** Add a checkable menu item in the "View" menu.
    *   **Action:**
        *   In `menu_bar.py`, create a new `QAction` named "Auto-Center on Frame Change".
        *   Make this action checkable (`setCheckable(True)`).
        *   Connect its `toggled` signal to a new handler method in `MainWindow` (e.g., `self.toggle_auto_center`).
        *   In `MainWindow`, implement `toggle_auto_center(self, checked)`: This method will update the `self.auto_center_enabled` attribute based on the `checked` state.
        *   Modify the menu setup logic in `MainWindow` (or `menu_bar.py`) to set the initial checked state of the action based on the loaded `main_window.auto_center_enabled` value *after* settings are loaded during startup.
    *   **Files:** `menu_bar.py`, `main_window.py`.

3.  **Core Logic (Frame Change Trigger):**
    *   **Goal:** Trigger the centering logic when the frame changes, if the toggle is active.
    *   **Action:**
        *   Identify the methods within `ui_components.py` that handle frame changes (e.g., `next_frame`, `prev_frame`, `go_to_frame`, `set_current_frame`, `on_timeline_changed`, `on_frame_edit_changed`).
        *   Inside these methods, *after* the frame has been successfully changed and the UI updated, add logic to:
            *   Access the main window instance.
            *   Check the value of `main_window.auto_center_enabled`.
            *   If `True`:
                *   Get the active `curve_view` instance from the main window.
                *   Call `ZoomOperations.center_on_selected_point(curve_view, preserve_zoom=True)`.
    *   **Files:** `ui_components.py`, `centering_zoom_operations.py`, `main_window.py`.

4.  **Memory Bank Update:**
    *   **Goal:** Document the decision and track progress (This will be done manually or by the assistant during implementation).
    *   **Action:**
        *   Add an entry to `decisionLog.md` detailing the new feature, its UI location, persistence (using QSettings), and trigger logic.
        *   Add a task entry to `progress.md` for implementing this feature.
    *   **Files:** `memory-bank/decisionLog.md`, `memory-bank/progress.md`.

**Diagram: Component Interaction**

```mermaid
sequenceDiagram
    participant User
    participant ViewMenu
    participant MainWindow
    participant SettingsOperations
    participant QSettings
    participant SignalRegistry
    participant UIComponents
    participant CurveView
    participant ZoomOperations

    Note over MainWindow, SettingsOperations: App Startup
    MainWindow->>SettingsOperations: load_settings(main_window)
    SettingsOperations->>QSettings: value("view/autoCenterOnFrameChange", False)
    QSettings-->>SettingsOperations: Returns stored value (or default)
    SettingsOperations->>MainWindow: Sets main_window.auto_center_enabled
    MainWindow->>ViewMenu: Sets initial check state of "Auto-Center" Action

    User->>ViewMenu: Toggles "Auto-Center" Action
    ViewMenu->>MainWindow: Emits toggled(checked) signal
    MainWindow->>MainWindow: toggle_auto_center(checked)
    MainWindow->>MainWindow: Updates self.auto_center_enabled = checked

    Note over MainWindow, UIComponents: User changes frame (e.g., arrow key, slider)
    User->>UIComponents: Triggers frame change method (e.g., next_frame)
    UIComponents->>UIComponents: Updates current frame
    UIComponents->>MainWindow: Access main_window instance
    UIComponents->>MainWindow: Reads main_window.auto_center_enabled
    alt auto_center_enabled is True
        UIComponents->>CurveView: Get instance
        UIComponents->>ZoomOperations: center_on_selected_point(curve_view)
        ZoomOperations->>CurveView: Update offset_x, offset_y
        CurveView->>CurveView: update() (redraw)
    end
    UIComponents->>SignalRegistry: (Potentially emits frame_changed signal for other listeners)


    Note over MainWindow, SettingsOperations: App Shutdown
    MainWindow->>SettingsOperations: handle_close_event() -> save_settings()
    SettingsOperations->>MainWindow: Reads main_window.auto_center_enabled
    SettingsOperations->>QSettings: setValue("view/autoCenterOnFrameChange", value)