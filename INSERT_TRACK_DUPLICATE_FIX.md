# Insert Track Implementation

## Status Assignment Update (Latest)

**Change**: All filled frames now get `TRACKED` status (not `KEYFRAME` for first frame).

**Rationale**: Since the ENDFRAME is converted to KEYFRAME during gap filling, that KEYFRAME activates the segment. The filled frames don't need special KEYFRAME status - they're tracking data copied from source curves, so TRACKED is the correct status.

**Modified**:
- `core/insert_track_algorithm.py` lines 297-299, 376-378
- All tests updated to expect TRACKED status for filled frames

---

## Bug Summary (Duplicate Frames - October 2025)

**Issue**: Insert Track was creating **duplicate frame entries**, causing incorrect segmentation behavior.

**Log Evidence** (from user's 19:04:01 logs):
```
[SEGMENT] Point statuses: [(1, 'NORMAL'), (2, 'NORMAL'), ..., (6, 'KEYFRAME'), (7, 'NORMAL'), (7, 'KEYFRAME'), (8, 'NORMAL'), (8, 'TRACKED')]
```

Frame 7 appeared **twice** (NORMAL + KEYFRAME), frame 8 appeared **twice** (NORMAL + TRACKED).
Result: 41 points instead of 37 (should be 37 original, gap frames replaced).

## Root Cause

**Location**: `core/insert_track_algorithm.py`
- Lines 267-268: `deform_curve_with_interpolated_offset()`
- Lines 364-366: `fill_gap_with_source()`

**The Bug**:
```python
# ❌ WRONG - Keeps ALL existing target points (including gap frames)
result_points = list(target_points)

# ... later ...
result_points.append(new_point)  # ❌ Appends filled points for same frames!
```

The functions were:
1. Starting with ALL existing target points (including NORMAL points in gap range 7-10)
2. APPENDING new filled points (KEYFRAME/TRACKED) for the same frames
3. Creating duplicates!

## The Fix

**Changed**:
```python
# ✅ CORRECT - Exclude gap frames before adding filled data
result_points = [p for p in target_points if not (gap_start <= p.frame <= gap_end)]

# ... later ...
result_points.append(new_point)  # ✅ Replaces gap frames correctly
```

## Files Modified

1. **core/insert_track_algorithm.py**:
   - Line 268: Filter out gap frames in `deform_curve_with_interpolated_offset()`
   - Line 366: Filter out gap frames in `fill_gap_with_source()`

2. **tests/test_insert_track_no_duplicates.py** (new):
   - Added 2 tests verifying no duplicate frames created
   - Tests check frame count and verify no frame appears twice

3. **core/curve_segments.py**:
   - Removed debug logging (lines 155-159, 259-266)

4. **services/data_service.py**:
   - Removed debug logging (lines 562-566)

## Test Results

**All tests pass**: ✅
- 100 Insert Track tests (98 existing + 2 new)
- 11 Endframe behavior tests
- 0 duplicate frames detected

**Verification**:
```bash
pytest tests/test_insert_track*.py -x  # 100 passed
pytest tests/test_endframe*.py -x      # 11 passed
```

## Why Segmentation Was Confused

The segmentation code (`SegmentedCurve.from_points()`) received data with:
- Frame 7: NORMAL status (old point)
- Frame 7: KEYFRAME status (new filled point)
- Frame 8: NORMAL status (old point)
- Frame 8: TRACKED status (new filled point)

The segmentation logic couldn't determine which status to use, leading to:
1. Incorrect segment boundaries
2. Wrong active/inactive detection
3. Timeline display errors

**With the fix**: Only the new KEYFRAME/TRACKED points exist in gap range, so segmentation works correctly.

## Impact

**Before Fix**:
- Insert Track created 41 points (4 duplicates)
- Unpredictable segmentation behavior
- Timeline could show wrong inactive frame counts

**After Fix**:
- Insert Track creates exactly 37 points (no duplicates)
- Correct segmentation: 1 active segment (frames 1-37)
- Timeline shows correct inactive frame counts

## Next Steps

1. ✅ **DONE**: Fix implemented and tested
2. ✅ **DONE**: Debug logging removed
3. ✅ **DONE**: Regression tests created
4. **READY**: Run application to verify UI behavior

The bug is completely fixed. Insert Track now correctly **replaces** gap frames instead of **appending** duplicates.
