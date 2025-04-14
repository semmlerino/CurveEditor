# Hotkey Reassignment Plan

**Goal:** Reassign arrow keys for frame navigation and Numpad keys for nudging, ensuring all hotkey logic is managed centrally via `ShortcutManager`.

**Plan:**

1.  **Modify `keyboard_shortcuts.py`:**
    *   Update the `SHORTCUTS` dictionary within the `ShortcutManager` class:
        *   Change `prev_frame` key from "," to "Left".
        *   Change `next_frame` key from "." to "Right".
        *   Change `nudge_up` key from "Up" to "Num+8".
        *   Change `nudge_down` key from "Down" to "Num+2".
        *   Change `nudge_left` key from "Left" to "Num+4".
        *   Change `nudge_right` key from "Right" to "Num+6".
    *   Update the `populate_shortcuts_table` method in the `ShortcutsDialog` class to reflect these new key assignments in the help dialog.

2.  **Verification:**
    *   Confirm that the actions associated with these shortcuts (`prev_frame`, `next_frame`, `nudge_up`, `nudge_down`, `nudge_left`, `nudge_right`) are correctly connected to their respective functions using `ShortcutManager.connect_shortcut` (likely in `main_window.py`).
    *   Ensure no residual direct handling of these keys exists in `keyPressEvent` methods.

3.  **Memory Bank Update (Post-Implementation):**
    *   Add an entry to `decisionLog.md` detailing the hotkey reassignment.
    *   Update `activeContext.md` under "Recent Changes".
    *   Update `progress.md` to mark the task as completed.

**Diagram:**

```mermaid
graph TD
    A[User Request: Arrows for Frames, Numpad for Nudge] --> B{Modify keyboard_shortcuts.py};
    B --> C[Update SHORTCUTS Dictionary];
    B --> D[Update ShortcutsDialog UI];
    C --> E{Verify Connections};
    D --> E;
    E --> F{Update Memory Bank};
    F --> G[Implementation (Code Mode)];

    subgraph "keyboard_shortcuts.py"
        C
        D
    end

    subgraph "Memory Bank"
        F
    end
```

**Summary of Key Changes:**

*   **Left Arrow:** Previous Frame (was Nudge Left)
*   **Right Arrow:** Next Frame (was Nudge Right)
*   **Numpad 4:** Nudge Left (was Left Arrow)
*   **Numpad 6:** Nudge Right (was Right Arrow)
*   **Numpad 8:** Nudge Up (was Up Arrow)
*   **Numpad 2:** Nudge Down (was Down Arrow)
*   **, (Comma):** No longer assigned (was Previous Frame)
*   **. (Period):** No longer assigned (was Next Frame)
*   **Up Arrow:** No longer assigned (was Nudge Up)
*   **Down Arrow:** No longer assigned (was Nudge Down)