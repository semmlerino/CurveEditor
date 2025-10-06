# Phase 6.5: timeline_tabs.frame_changed Removal

[← Previous: Phase 6.4](PHASE_6.4_CURVE_VIEW_REMOVAL.md) | [Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) | [Next: Phase 6.6 →](PHASE_6.6_SHOULD_RENDER_REMOVAL.md)

---

## Goal

Remove deprecated `timeline_tabs.frame_changed` signal.

## Prerequisites

- [Phase 6.4](PHASE_6.4_CURVE_VIEW_REMOVAL.md) complete (curve_view removed)

---

## Current Status

- Signal exists with `DeprecationWarning` (verified at ui/timeline_tabs.py:151)
- StateManager.frame_changed is the correct API
- **0 production connections** (grep verification: no files connect to this signal)
- Signal is only emitted at line 683 when deprecated usage detected

---

## Migration

**No migration needed** - verified no production code connects to `timeline_tabs.frame_changed`.

The signal internally connects to `StateManager.frame_changed` (line 276) and emits when accessed for backward compatibility (lines 677-683).

---

## Files to Modify

1. **ui/timeline_tabs.py** - Remove:
   - Line 151: Signal definition `frame_changed: Signal = Signal(int)`
   - Line 276: Connection to StateManager `state_manager.frame_changed.connect(self._on_state_frame_changed)`
   - Line 286: Handler method `_on_state_frame_changed`
   - Lines 677-683: Deprecation warning and emission

---

## Validation

```bash
# Verify no timeline_tabs.frame_changed references:
grep -rn "timeline_tabs\.frame_changed" --include="*.py" . --exclude-dir=tests --exclude-dir=docs
# Expected: 0 results

pytest tests/ -v
# Expected: 2105/2105 passing
```

---

## Exit Criteria

- [ ] Signal definition removed from timeline_tabs.py
- [ ] All connections migrated to StateManager.frame_changed
- [ ] All tests passing

---

**Next**: [Phase 6.6 - should_render Removal →](PHASE_6.6_SHOULD_RENDER_REMOVAL.md)
