# Insert Track Multiple ENDFRAMEs Fix

## Bug Description

**Problem:** When using Insert Track with multiple ENDFRAMEs in a single curve, the gap detection algorithm only considered the outermost boundaries (first ENDFRAME and last KEYFRAME), ignoring any intermediate ENDFRAMEs. This caused Insert Track to overwrite tracking data between multiple gaps.

**Example scenario:**
```
Frame 9:  ENDFRAME  ← Gap 1 starts
Frame 18: ENDFRAME  ← Should end Gap 1 and start Gap 2 (IGNORED!)
Frame 26: KEYFRAME  ← Gap boundary detected
```

**Buggy behavior:**
- Detected ONE gap: frames 10-25
- Filled all frames 10-25, overwriting the ENDFRAME at frame 18

**Expected behavior:**
- Gap 1: frames 10-17 (between ENDFRAME at 9 and ENDFRAME at 18)
- Gap 2: frames 19-25 (between ENDFRAME at 18 and KEYFRAME at 26)
- Fill each gap separately, preserving the ENDFRAME at frame 18

## Root Cause

In `core/insert_track_algorithm.py`, the `find_gap_around_frame()` function's status-based gap detection only searched for the next **KEYFRAME** after an ENDFRAME:

```python
# OLD CODE (lines 99-104):
# Find the next KEYFRAME after the ENDFRAME (this is the STARTFRAME)
next_keyframe = None
for p in points:
    if p.frame > prev_endframe.frame and p.status == PointStatus.KEYFRAME:
        next_keyframe = p
        break
```

This ignored any ENDFRAMEs between the starting ENDFRAME and the next KEYFRAME.

## Fix

**Changed line 99** to search for the next **ENDFRAME OR KEYFRAME** (whichever comes first):

```python
# NEW CODE:
# Find the next KEYFRAME or ENDFRAME after the previous ENDFRAME
# (both can terminate a gap)
next_boundary = None
for p in points:
    if p.frame > prev_endframe.frame and p.status in (
        PointStatus.KEYFRAME,
        PointStatus.ENDFRAME,
    ):
        next_boundary = p
        break
```

**Key insight:** ENDFRAMEs serve dual purposes:
1. End the current active segment (create a gap)
2. Can also terminate a previous gap (start a new gap)

Multiple consecutive ENDFRAMEs create multiple separate gaps, each bounded by adjacent ENDFRAMEs.

## Test Coverage

Created `tests/test_insert_track_multiple_endframes.py` with 5 comprehensive tests:

1. **test_multiple_endframes_create_separate_gaps** - Core bug scenario
2. **test_endframe_terminates_gap_even_with_keyframe_later** - Nearest boundary wins
3. **test_three_consecutive_endframes** - Chain of ENDFRAMEs
4. **test_endframe_keyframe_endframe_pattern** - Reactivation patterns
5. **test_adjacent_endframes_create_zero_length_gap** - Edge case

All 107 Insert Track tests pass (102 existing + 5 new).

## Impact

**Before fix:**
- Insert Track with multiple ENDFRAMEs corrupted tracking data
- Intermediate ENDFRAMEs were overwritten
- Gap structure was destroyed

**After fix:**
- Each gap between ENDFRAMEs handled independently
- ENDFRAME markers preserved
- Tracking data protected
- Correct 3DEqualizer-style gap semantics

## Files Changed

1. `core/insert_track_algorithm.py` - Fixed gap detection logic (1 line)
2. `tests/test_insert_track_multiple_endframes.py` - New test file (5 tests)

---

**Date:** October 28, 2025
**Issue:** Multiple ENDFRAMEs ignored during gap detection
**Resolution:** ENDFRAMEs now correctly terminate gaps
