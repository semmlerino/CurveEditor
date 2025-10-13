"""Tests for Phase 0A: ApplicationState infrastructure additions.

This test suite covers the Phase 0A features:
1. get_curve_data() ValueError when no active curve
2. Image sequence methods (defensive copying, validation, signals)
3. Original data methods (undo/comparison support)
4. batch_updates() context manager
5. StateManager integration with ApplicationState.get_total_frames()
"""

import pytest

from core.models import CurvePoint, PointStatus
from stores.application_state import get_application_state, reset_application_state


@pytest.fixture
def state():
    """Provide fresh ApplicationState for each test."""
    reset_application_state()
    return get_application_state()


class TestGetCurveDataValueError:
    """Test get_curve_data() ValueError when no active curve."""

    def test_raises_value_error_when_no_active_curve(self, state):
        """ValueError should be raised when curve_name=None and no active curve set."""
        with pytest.raises(ValueError):
            state.get_curve_data(curve_name=None)

    def test_error_message_mentions_both_solutions(self, state):
        """Error message should mention both set_active_curve() and curve_name parameter."""
        with pytest.raises(ValueError, match=r"set_active_curve.*curve_name"):
            state.get_curve_data()

    def test_explicit_curve_name_bypasses_active_curve_check(self, state):
        """Explicit curve_name should work even without active curve set."""
        # Set up some curve data without setting active curve
        test_data = [(1, 10.0, 20.0, "normal")]
        state.set_curve_data("Test1", test_data)

        # Should work with explicit curve_name
        result = state.get_curve_data(curve_name="Test1")
        assert len(result) == 1
        assert result[0] == (1, 10.0, 20.0, "normal")

        # Non-existent curve should return empty list
        result = state.get_curve_data(curve_name="NonExistent")
        assert result == []


class TestImageSequenceMethods:
    """Test image sequence methods: defensive copying, validation, signals."""

    def test_set_image_files_stores_defensive_copy(self, state):
        """Modifying original list after set_image_files should not affect state."""
        original_files = ["img001.png", "img002.png", "img003.png"]
        state.set_image_files(original_files)

        # Modify original list
        original_files.append("img004.png")
        original_files[0] = "modified.png"

        # State should be unchanged
        stored_files = state.get_image_files()
        assert len(stored_files) == 3
        assert stored_files[0] == "img001.png"
        assert "img004.png" not in stored_files

    def test_get_image_files_returns_defensive_copy(self, state):
        """Modifying returned list from get_image_files should not affect state."""
        original_files = ["img001.png", "img002.png"]
        state.set_image_files(original_files)

        # Get and modify returned list
        retrieved = state.get_image_files()
        retrieved.append("img003.png")
        retrieved[0] = "modified.png"

        # State should be unchanged
        stored_files = state.get_image_files()
        assert len(stored_files) == 2
        assert stored_files[0] == "img001.png"
        assert "img003.png" not in stored_files

    def test_set_image_files_validates_type(self, state):
        """set_image_files should raise TypeError for non-list input."""
        with pytest.raises(TypeError, match="files must be list"):
            state.set_image_files("not_a_list")  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="files must be list"):
            state.set_image_files(("tuple", "of", "files"))  # pyright: ignore[reportArgumentType]

    def test_set_image_files_validates_max_files_limit(self, state):
        """set_image_files should raise ValueError for > 10000 files."""
        max_files = 10_000
        too_many_files = [f"img{i:05d}.png" for i in range(max_files + 1)]

        with pytest.raises(ValueError, match=f"Too many files: {max_files + 1}"):
            state.set_image_files(too_many_files)

    def test_set_image_files_validates_element_types(self, state):
        """set_image_files should raise TypeError for non-str elements."""
        invalid_files = ["img001.png", 123, "img003.png"]  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="File path must be str"):
            state.set_image_files(invalid_files)  # pyright: ignore[reportArgumentType]

    def test_get_total_frames_derived_from_image_files(self, state):
        """get_total_frames should equal len(image_files)."""
        # Initially should be 1 (default)
        assert state.get_total_frames() == 1

        # Set 5 files
        files = [f"img{i:03d}.png" for i in range(5)]
        state.set_image_files(files)
        assert state.get_total_frames() == 5

        # Set 100 files
        files = [f"img{i:03d}.png" for i in range(100)]
        state.set_image_files(files)
        assert state.get_total_frames() == 100

        # Empty list should default to 1
        state.set_image_files([])
        assert state.get_total_frames() == 1

    def test_image_sequence_changed_signal_emitted(self, state, qtbot):
        """image_sequence_changed signal should emit when files change."""
        files = ["img001.png", "img002.png"]

        with qtbot.waitSignal(state.image_sequence_changed, timeout=1000):
            state.set_image_files(files)

        # Signal should emit again when files change
        new_files = ["img001.png", "img002.png", "img003.png"]
        with qtbot.waitSignal(state.image_sequence_changed, timeout=1000):
            state.set_image_files(new_files)

        # Signal should NOT emit when files are same
        with qtbot.assertNotEmitted(state.image_sequence_changed, wait=100):
            state.set_image_files(new_files)  # Same files

    def test_set_image_directory_emits_signal(self, state, qtbot):
        """set_image_directory should emit image_sequence_changed when changed."""
        with qtbot.waitSignal(state.image_sequence_changed, timeout=1000):
            state.set_image_directory("/path/to/images")

        # Should emit again when changed
        with qtbot.waitSignal(state.image_sequence_changed, timeout=1000):
            state.set_image_directory("/different/path")

        # Should NOT emit when set to same value
        with qtbot.assertNotEmitted(state.image_sequence_changed, wait=100):
            state.set_image_directory("/different/path")


class TestOriginalDataMethods:
    """Test original data storage for undo/comparison."""

    def test_set_original_data_stores_defensive_copy(self, state):
        """Modifying original list after set_original_data should not affect state."""
        original_data = [(1, 10.0, 20.0, "normal"), (2, 15.0, 25.0, "normal")]
        state.set_original_data("Track1", original_data)

        # Modify original list
        original_data.append((3, 20.0, 30.0, "normal"))
        original_data[0] = (999, 999.0, 999.0, "keyframe")

        # State should be unchanged
        stored_data = state.get_original_data("Track1")
        assert len(stored_data) == 2
        assert stored_data[0] == (1, 10.0, 20.0, "normal")
        assert (3, 20.0, 30.0, "normal") not in stored_data

    def test_get_original_data_returns_defensive_copy(self, state):
        """Modifying returned list from get_original_data should not affect state."""
        original_data = [(1, 10.0, 20.0, "normal"), (2, 15.0, 25.0, "normal")]
        state.set_original_data("Track1", original_data)

        # Get and modify returned list
        retrieved = state.get_original_data("Track1")
        retrieved.append((3, 20.0, 30.0, "normal"))
        retrieved[0] = (999, 999.0, 999.0, "keyframe")

        # State should be unchanged
        stored_data = state.get_original_data("Track1")
        assert len(stored_data) == 2
        assert stored_data[0] == (1, 10.0, 20.0, "normal")
        assert (3, 20.0, 30.0, "normal") not in stored_data

    def test_get_original_data_returns_empty_when_not_set(self, state):
        """get_original_data should return empty list for non-existent curve."""
        result = state.get_original_data("NonExistent")
        assert result == []
        assert isinstance(result, list)

    def test_clear_original_data_single_curve(self, state):
        """clear_original_data should clear specific curve only."""
        # Set original data for multiple curves
        state.set_original_data("Track1", [(1, 10.0, 20.0, "normal")])
        state.set_original_data("Track2", [(1, 15.0, 25.0, "normal")])
        state.set_original_data("Track3", [(1, 20.0, 30.0, "normal")])

        # Clear one curve
        state.clear_original_data("Track2")

        # Track2 should be empty, others should remain
        assert state.get_original_data("Track1") == [(1, 10.0, 20.0, "normal")]
        assert state.get_original_data("Track2") == []
        assert state.get_original_data("Track3") == [(1, 20.0, 30.0, "normal")]

    def test_clear_original_data_all_curves(self, state):
        """clear_original_data(None) should clear all curves."""
        # Set original data for multiple curves
        state.set_original_data("Track1", [(1, 10.0, 20.0, "normal")])
        state.set_original_data("Track2", [(1, 15.0, 25.0, "normal")])
        state.set_original_data("Track3", [(1, 20.0, 30.0, "normal")])

        # Clear all
        state.clear_original_data(None)

        # All should be empty
        assert state.get_original_data("Track1") == []
        assert state.get_original_data("Track2") == []
        assert state.get_original_data("Track3") == []

    def test_original_data_independent_from_curve_data(self, state):
        """Original data should be independent from curve data modifications."""
        # Set both curve data and original data
        curve_data = [(1, 10.0, 20.0, "normal"), (2, 15.0, 25.0, "normal")]
        original_data = [(1, 10.0, 20.0, "normal"), (2, 15.0, 25.0, "normal")]

        state.set_curve_data("Track1", curve_data)
        state.set_original_data("Track1", original_data)

        # Modify curve data
        state.update_point("Track1", 0, CurvePoint(1, 100.0, 200.0, PointStatus.KEYFRAME))

        # Original data should be unchanged
        original = state.get_original_data("Track1")
        assert original[0] == (1, 10.0, 20.0, "normal")

        # Curve data should be changed
        curve = state.get_curve_data("Track1")
        assert curve[0] == (1, 100.0, 200.0, "keyframe")


class TestBatchUpdatesContextManager:
    """Test batch_updates() context manager for signal deferral."""

    def test_batch_updates_defers_signals(self, state, qtbot):
        """Signals should not emit during batch, only at end."""
        state.set_curve_data("Track1", [(1, 10.0, 20.0, "normal")])

        # Track signal emissions
        signal_count = 0

        def on_curves_changed(data):
            nonlocal signal_count
            signal_count += 1

        state.curves_changed.connect(on_curves_changed)

        # Enter batch mode
        with state.batch_updates():
            # Make multiple changes
            state.set_curve_data("Track2", [(1, 15.0, 25.0, "normal")])
            state.set_curve_data("Track3", [(1, 20.0, 30.0, "normal")])

            # No signals should have been emitted yet
            assert signal_count == 0

        # After exiting batch, signal should have been emitted once
        assert signal_count == 1

    def test_batch_updates_exception_handling(self, state, qtbot):
        """Exception in batch should clear pending signals."""
        state.set_curve_data("Track1", [(1, 10.0, 20.0, "normal")])

        signal_count = 0

        def on_curves_changed(data):
            nonlocal signal_count
            signal_count += 1

        state.curves_changed.connect(on_curves_changed)

        # Exception during batch
        with pytest.raises(ValueError):
            with state.batch_updates():
                state.set_curve_data("Track2", [(1, 15.0, 25.0, "normal")])
                raise ValueError("Test exception")

        # Signals should NOT have been emitted (cleared on exception)
        assert signal_count == 0

        # State should still be functional after exception
        state.set_curve_data("Track3", [(1, 20.0, 30.0, "normal")])
        assert signal_count == 1

    def test_batch_updates_nested_batches(self, state, qtbot):
        """Nested batches should only emit at outermost end."""
        state.set_curve_data("Track1", [(1, 10.0, 20.0, "normal")])

        signal_count = 0

        def on_curves_changed(data):
            nonlocal signal_count
            signal_count += 1

        state.curves_changed.connect(on_curves_changed)

        # Nested batches
        with state.batch_updates():
            state.set_curve_data("Track2", [(1, 15.0, 25.0, "normal")])
            assert signal_count == 0

            with state.batch_updates():
                state.set_curve_data("Track3", [(1, 20.0, 30.0, "normal")])
                assert signal_count == 0

            # Inner batch ended, but still in outer batch
            assert signal_count == 0

        # Outer batch ended, signal should emit now
        assert signal_count == 1

    def test_batch_updates_signal_deduplication(self, state, qtbot):
        """Duplicate signals should be deduplicated."""
        state.set_curve_data("Track1", [(1, 10.0, 20.0, "normal")])
        state.set_active_curve("Track1")

        signal_count = 0

        def on_curves_changed(data):
            nonlocal signal_count
            signal_count += 1

        state.curves_changed.connect(on_curves_changed)

        # Multiple changes to same curve
        with state.batch_updates():
            state.set_curve_data("Track1", [(1, 15.0, 25.0, "normal")])
            state.set_curve_data("Track1", [(1, 20.0, 30.0, "normal")])
            state.set_curve_data("Track1", [(1, 25.0, 35.0, "normal")])

        # Should only emit once despite multiple changes
        assert signal_count == 1

        # Final value should be correct
        data = state.get_curve_data("Track1")
        assert data[0] == (1, 25.0, 35.0, "normal")

    def test_batch_updates_reentrancy_protection(self, state, qtbot):
        """_emitting_batch flag should prevent reentrancy during signal emission."""
        state.set_curve_data("Track1", [(1, 10.0, 20.0, "normal")])

        emission_count = 0
        reentrancy_attempted = False

        def on_curves_changed(data):
            nonlocal emission_count, reentrancy_attempted
            emission_count += 1

            # Try to trigger another change during emission
            # This should be queued, not emitted immediately
            if emission_count == 1:
                reentrancy_attempted = True
                state.set_curve_data("Track2", [(1, 15.0, 25.0, "normal")])

        state.curves_changed.connect(on_curves_changed)

        # Trigger batch emission
        with state.batch_updates():
            state.set_curve_data("Track1", [(1, 20.0, 30.0, "normal")])

        # Should have emitted once, and attempted reentrancy
        assert emission_count == 1
        assert reentrancy_attempted

        # The reentrant change should have been queued and will emit separately
        # when we're no longer in batch mode
        assert state.get_curve_data("Track2") == [(1, 15.0, 25.0, "normal")]


class TestStateManagerIntegration:
    """Test StateManager integration with ApplicationState."""

    def test_current_frame_setter_clamps_to_total_frames(self, state, qapp):
        """StateManager.current_frame should clamp to ApplicationState.get_total_frames()."""
        from ui.state_manager import StateManager

        # Set up image sequence with 10 frames
        files = [f"img{i:03d}.png" for i in range(10)]
        state.set_image_files(files)
        assert state.get_total_frames() == 10

        # Create StateManager (it uses ApplicationState internally)
        state_manager = StateManager()

        # Set frame within range
        state_manager.current_frame = 5
        assert state_manager.current_frame == 5

        # Try to set frame beyond total_frames (should clamp to 10)
        state_manager.current_frame = 999
        assert state_manager.current_frame == 10

        # Try to set frame below 1 (should clamp to 1)
        state_manager.current_frame = -5
        assert state_manager.current_frame == 1

        # Update total frames and verify clamping works
        state.set_image_files([f"img{i:03d}.png" for i in range(5)])
        assert state.get_total_frames() == 5

        # Current frame should still be valid (within new range)
        state_manager.current_frame = 100
        assert state_manager.current_frame == 5
