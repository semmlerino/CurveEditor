# Endframe Rendering Fix

**Bug**: Endframes were not visible on the curve when they occurred within inactive segments (gaps between endframes).

**Date**: 2025-10-28

## Problem Description

When multiple endframes exist in a curve without keyframes between them:
- Frame 9: ENDFRAME (creates gap)
- Frame 18: ENDFRAME (also in the gap)
- Frame 26: KEYFRAME (ends gap)

**Before Fix**:
- Timeline correctly showed both endframes as red markers
- Curve view only showed the first endframe at frame 9
- Second endframe at frame 18 was invisible (not rendered)

## Root Cause

The renderer (`rendering/optimized_curve_renderer.py`) had logic to skip rendering points in inactive segments (gaps). However, it was also skipping **endframes** in those inactive segments.

**Lines 909-914 (before fix)**:
```python
# Skip rendering points in inactive segments (show only dashed line)
if segmented_curve and frame != -1:
    segment = segmented_curve.get_segment_at_frame(frame)
    if segment and not segment.is_active:
        continue  # Don't render points in inactive gap segments
```

This logic was correct for regular tracked/interpolated points (they should not render in gaps), but incorrect for **endframes** which are gap boundaries and must always be visible.

## Correct Behavior

**Segmentation semantics**:
- Frames between two endframes ARE a gap (inactive segment)
- Only the FIRST endframe's segment is active
- Subsequent endframes before a keyframe are IN the gap (inactive segments)

**Rendering semantics**:
- Endframes are **boundary markers** and must ALWAYS render
- Regular points (tracked/interpolated/normal) in inactive segments should NOT render
- This creates visual distinction: active segments show all points, gaps show only dashed lines + endframe markers

## Fix

Changed the renderer skip condition to exclude endframes:

**Lines 909-914 (after fix)**:
```python
# Skip rendering points in inactive segments EXCEPT endframes
# (endframes are gap boundaries and must always be visible)
if segmented_curve and frame != -1 and status != "endframe":
    segment = segmented_curve.get_segment_at_frame(frame)
    if segment and not segment.is_active:
        continue  # Don't render non-endframe points in inactive gap segments
```

**Key change**: Added `and status != "endframe"` condition before checking segment activity.

## Files Changed

1. **rendering/optimized_curve_renderer.py** (lines 909-914)
   - Added exception for endframes in inactive segment skip logic

2. **tests/test_endframe_segment_boundaries.py** (new file)
   - 4 comprehensive tests verifying correct segmentation behavior
   - Tests verify endframes can be in inactive segments but should still render

## Test Coverage

**New tests** (4 tests):
- `test_multiple_endframes_renderer_shows_all`: Verifies segmentation of multiple endframes
- `test_three_consecutive_endframes_segmentation`: Three endframes create continuous gap
- `test_endframe_always_last_point_in_segment`: Endframes terminate segments
- `test_endframes_render_even_in_inactive_segments`: Documents the fix

**All existing tests pass**:
- 544 gap/endframe/segment tests: ✅ PASS
- 107 Insert Track tests: ✅ PASS (from previous fix)

## Impact

**Before**: Multiple endframes appeared "blank" in curve view (missing red dots)
**After**: All endframes visible on curve, matching timeline display

**User-visible change**:
- Endframes now render correctly in all scenarios
- Visual consistency between timeline and curve view restored
- Gap boundaries clearly marked even when multiple endframes exist

## Related Fixes

This is the second fix for multiple endframe handling:

1. **INSERT_TRACK_MULTIPLE_ENDFRAMES_FIX.md**: Fixed Insert Track gap detection to respect intermediate endframes (don't overwrite them)
2. **ENDFRAME_RENDERING_FIX.md** (this fix): Fixed renderer to always show endframes, even in gaps

Both fixes ensure multiple endframes are correctly preserved and visible throughout the application.
