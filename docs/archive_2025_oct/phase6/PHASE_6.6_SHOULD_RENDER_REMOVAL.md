# Phase 6.6: should_render_curve() Removal

[← Previous: Phase 6.5](PHASE_6.5_TIMELINE_SIGNAL_REMOVAL.md) | [Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) | [Next: Phase 6.7 →](PHASE_6.7_UI_COMPONENTS_REMOVAL.md)

---

## Goal

Remove legacy `should_render_curve()` method.

## Prerequisites

- [Phase 6.5](PHASE_6.5_TIMELINE_SIGNAL_REMOVAL.md) complete (timeline signal removed)

---

## Migration

```python
# OLD:
if widget.should_render_curve(curve_name):
    render_curve(curve_name)

# NEW:
render_state = RenderState.compute(widget)
if curve_name in render_state.visible_curves:
    render_curve(curve_name)
```

---

## Files to Modify

- 3 files with 5 references to `should_render_curve()`

---

## Validation

```bash
grep -rn "should_render_curve" --include="*.py" . --exclude-dir=tests --exclude-dir=docs
# Expected: 0 results
```

---

## Exit Criteria

- [ ] Method removed
- [ ] All calls migrated to RenderState
- [ ] All tests passing

---

**Next**: [Phase 6.7 - ui_components Removal →](PHASE_6.7_UI_COMPONENTS_REMOVAL.md)
