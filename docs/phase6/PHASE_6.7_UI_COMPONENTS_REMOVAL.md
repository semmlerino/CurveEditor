# Phase 6.7: ui_components Removal (TRIVIAL)

[← Previous: Phase 6.6](PHASE_6.6_SHOULD_RENDER_REMOVAL.md) | [Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md)

---

## Goal

Remove `main_window.ui_components` alias (trivial cleanup).

## Prerequisites

- [Phase 6.6](PHASE_6.6_SHOULD_RENDER_REMOVAL.md) complete (should_render removed)

---

## Migration

```python
# OLD:
main_window.ui_components.timeline.frame_spinbox.value()

# NEW:
main_window.ui.timeline.frame_spinbox.value()
```

---

## Files to Modify

- 1 file with 2 references

---

## Validation

```bash
grep -rn "\.ui_components\b" --include="*.py" . --exclude-dir=tests --exclude-dir=docs
# Expected: 0 results
```

---

## Exit Criteria

- [ ] Alias removed
- [ ] References migrated to `.ui`
- [ ] All tests passing

---

**Phase 6 Complete!** 🎉

Return to [Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) for post-migration verification.
