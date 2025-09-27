#!/usr/bin/env python3
"""
Test the FrameStore for managing frame state.
"""

import pytest

from core.type_aliases import CurveDataList
from stores import get_store_manager
from stores.store_manager import StoreManager


class TestFrameStore:
    """Test FrameStore functionality."""

    def setup_method(self):
        """Reset stores before each test."""
        StoreManager.reset()

    def test_frame_store_syncs_with_curve_data(self):
        """Test that frame store syncs with curve data."""
        # Get stores
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()
        frame_store = store_manager.get_frame_store()

        # Initially should be at default
        assert frame_store.min_frame == 1
        assert frame_store.max_frame == 1
        assert frame_store.current_frame == 1

        # Set curve data
        test_data: CurveDataList = [
            (5, 100.0, 100.0, "keyframe"),
            (10, 110.0, 110.0, "interpolated"),
            (15, 120.0, 120.0, "keyframe"),
        ]
        curve_store.set_data(test_data)

        # Frame store should have updated automatically
        assert frame_store.min_frame == 5
        assert frame_store.max_frame == 15
        assert frame_store.current_frame == 5  # Should clamp to min

    def test_frame_navigation(self):
        """Test frame navigation methods."""
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()
        curve_store = store_manager.get_curve_store()

        # Set up test data
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 110.0, 110.0, "interpolated"),
            (10, 120.0, 120.0, "keyframe"),
        ]
        curve_store.set_data(test_data)

        # Test navigation
        assert frame_store.current_frame == 1

        frame_store.next_frame()
        assert frame_store.current_frame == 2

        frame_store.last_frame()
        assert frame_store.current_frame == 10

        frame_store.previous_frame()
        assert frame_store.current_frame == 9

        frame_store.first_frame()
        assert frame_store.current_frame == 1

        # Test clamping
        frame_store.set_current_frame(100)
        assert frame_store.current_frame == 10  # Clamped to max

        frame_store.set_current_frame(-5)
        assert frame_store.current_frame == 1  # Clamped to min

    def test_playback_state(self):
        """Test playback state management."""
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()

        assert frame_store.is_playing is False

        frame_store.set_playback_state(True)
        assert frame_store.is_playing is True

        frame_store.set_playback_state(False)
        assert frame_store.is_playing is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
