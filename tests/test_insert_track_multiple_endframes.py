"""Test Insert Track behavior with multiple ENDFRAMEs (gap boundaries)."""

# Per-file type checking relaxations for test code
# pyright: reportArgumentType=none

from core.insert_track_algorithm import find_gap_around_frame


def test_multiple_endframes_create_separate_gaps():
    """Multiple ENDFRAMEs should create separate gaps, not one large gap.

    Scenario from user bug report:
    - Frame 9: ENDFRAME (creates gap 1)
    - Frame 18: ENDFRAME (ends gap 1, creates gap 2)
    - Frame 26: KEYFRAME (ends gap 2)

    Expected:
    - Gap 1: frames 10-17 (between ENDFRAME at 9 and ENDFRAME at 18)
    - Gap 2: frames 19-25 (between ENDFRAME at 18 and KEYFRAME at 26)

    Bug was: Treated 10-25 as ONE gap, ignoring ENDFRAME at 18
    """
    curve_data = [
        (1, 100.0, 100.0, "keyframe"),
        (9, 200.0, 200.0, "endframe"),  # ENDFRAME - starts gap 1
        (18, 300.0, 300.0, "endframe"),  # ENDFRAME - ends gap 1, starts gap 2
        (26, 400.0, 400.0, "keyframe"),  # KEYFRAME - ends gap 2
        (37, 500.0, 500.0, "tracked"),
    ]

    # Frame 15 is in gap 1 (between frame 9 and frame 18)
    gap = find_gap_around_frame(curve_data, 15)
    assert gap is not None, "Frame 15 should be in a gap"
    assert gap == (10, 17), f"Gap 1 should be frames 10-17, got {gap}"

    # Frame 20 is in gap 2 (between frame 18 and frame 26)
    gap = find_gap_around_frame(curve_data, 20)
    assert gap is not None, "Frame 20 should be in a gap"
    assert gap == (19, 25), f"Gap 2 should be frames 19-25, got {gap}"


def test_endframe_terminates_gap_even_with_keyframe_later():
    """ENDFRAME should terminate a gap even if a KEYFRAME exists later.

    The gap should end at the NEAREST boundary (ENDFRAME or KEYFRAME),
    not skip to a later KEYFRAME.
    """
    curve_data = [
        (5, 100.0, 100.0, "endframe"),  # Starts gap
        (10, 200.0, 200.0, "endframe"),  # Should terminate gap (nearest boundary)
        (20, 300.0, 300.0, "keyframe"),  # Later KEYFRAME (should NOT be gap boundary)
    ]

    # Frame 7 is between the two ENDFRAMEs
    gap = find_gap_around_frame(curve_data, 7)
    assert gap is not None, "Frame 7 should be in a gap"
    assert gap == (6, 9), f"Gap should end at ENDFRAME (frame 10), got {gap}"


def test_three_consecutive_endframes():
    """Three consecutive ENDFRAMEs should create two separate gaps."""
    curve_data = [
        (1, 100.0, 100.0, "keyframe"),
        (5, 150.0, 150.0, "endframe"),  # Gap 1: 6-9
        (10, 200.0, 200.0, "endframe"),  # Gap 2: 11-14
        (15, 250.0, 250.0, "endframe"),  # Gap 3: 16-24 (missing-frame gap until frame 25)
        (25, 300.0, 300.0, "tracked"),
    ]

    # Gap 1: between frames 5 and 10
    gap = find_gap_around_frame(curve_data, 7)
    assert gap == (6, 9), f"Gap 1 should be 6-9, got {gap}"

    # Gap 2: between frames 10 and 15
    gap = find_gap_around_frame(curve_data, 12)
    assert gap == (11, 14), f"Gap 2 should be 11-14, got {gap}"

    # Gap 3: after frame 15 (missing-frame gap until tracked point at frame 25)
    gap = find_gap_around_frame(curve_data, 20)
    assert gap == (16, 24), f"Gap 3 should be 16-24, got {gap}"


def test_endframe_keyframe_endframe_pattern():
    """ENDFRAME → KEYFRAME → ENDFRAME should create gaps at status boundaries AND missing frames."""
    curve_data = [
        (5, 100.0, 100.0, "endframe"),  # Gap 1: 6-9 (status-based)
        (10, 150.0, 150.0, "keyframe"),  # Reactivates curve
        (15, 200.0, 200.0, "endframe"),  # Gap 3: 16-19 (status-based)
        (20, 250.0, 250.0, "keyframe"),  # Reactivates again
    ]

    # Gap 1: status-based gap after ENDFRAME at 5
    gap = find_gap_around_frame(curve_data, 7)
    assert gap == (6, 9), f"Gap 1 should be 6-9, got {gap}"

    # Gap 2: missing-frame gap between frame 10 and frame 15 (no data at 11-14)
    gap = find_gap_around_frame(curve_data, 12)
    assert gap == (11, 14), f"Gap 2 should be 11-14 (missing frames), got {gap}"

    # Gap 3: status-based gap after ENDFRAME at 15
    gap = find_gap_around_frame(curve_data, 17)
    assert gap == (16, 19), f"Gap 3 should be 16-19, got {gap}"


def test_adjacent_endframes_create_zero_length_gap():
    """Two ENDFRAMEs in consecutive frames create a zero-length gap."""
    curve_data = [
        (5, 100.0, 100.0, "endframe"),
        (6, 150.0, 150.0, "endframe"),
        (10, 200.0, 200.0, "keyframe"),
    ]

    # No frames between 5 and 6, so gap_start=6, gap_end=5 (invalid)
    # Should return None (no gap) since gap_start > gap_end
    # Actually, gap would be (6, 5) which fails the check gap_start <= current_frame <= gap_end

    # Let me recalculate: gap_start = 5+1 = 6, gap_end = 6-1 = 5
    # So gap is (6, 5) which is invalid, so no current_frame can be in it

    # Try a frame that WOULD be in the gap if it existed
    gap = find_gap_around_frame(curve_data, 6)
    # Frame 6 has actual data, so it goes to TYPE 2 detection
    # Looks for prev ENDFRAME before 6 -> finds frame 5
    # Looks for next boundary after 5 -> finds frame 6 (ENDFRAME)
    # Gap would be (6, 5) which is invalid, so current_frame=6 is NOT in gap
    # Returns None
    assert gap is None, "Adjacent ENDFRAMEs create no gap"
