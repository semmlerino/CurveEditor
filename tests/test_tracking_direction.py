#!/usr/bin/env python
"""
Tests for TrackingDirection enum functionality.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use clear test names describing what is tested
- Cover all enum values and methods
- Test edge cases and invalid inputs
"""

import pytest

from core.models import TrackingDirection


class TestTrackingDirection:
    """Test suite for TrackingDirection enum."""

    def test_enum_values(self):
        """Test that enum values are correctly defined."""
        assert TrackingDirection.TRACKING_FW.value == "forward"
        assert TrackingDirection.TRACKING_BW.value == "backward"
        assert TrackingDirection.TRACKING_FW_BW.value == "bidirectional"

    def test_abbreviation_property(self):
        """Test abbreviation property returns correct short forms."""
        assert TrackingDirection.TRACKING_FW.abbreviation == "FW"
        assert TrackingDirection.TRACKING_BW.abbreviation == "BW"
        assert TrackingDirection.TRACKING_FW_BW.abbreviation == "FW+BW"

    def test_display_name_property(self):
        """Test display_name property returns human-readable names."""
        assert TrackingDirection.TRACKING_FW.display_name == "Forward"
        assert TrackingDirection.TRACKING_BW.display_name == "Backward"
        assert TrackingDirection.TRACKING_FW_BW.display_name == "Bidirectional"

    def test_from_abbreviation_valid_inputs(self):
        """Test from_abbreviation with valid abbreviations."""
        assert TrackingDirection.from_abbreviation("FW") == TrackingDirection.TRACKING_FW
        assert TrackingDirection.from_abbreviation("BW") == TrackingDirection.TRACKING_BW
        assert TrackingDirection.from_abbreviation("FW+BW") == TrackingDirection.TRACKING_FW_BW

    def test_from_abbreviation_case_insensitive(self):
        """Test from_abbreviation handles case variations."""
        assert TrackingDirection.from_abbreviation("fw") == TrackingDirection.TRACKING_FW
        assert TrackingDirection.from_abbreviation("bw") == TrackingDirection.TRACKING_BW
        assert TrackingDirection.from_abbreviation("fw+bw") == TrackingDirection.TRACKING_FW_BW

    def test_from_abbreviation_alternative_formats(self):
        """Test from_abbreviation with alternative bidirectional formats."""
        assert TrackingDirection.from_abbreviation("FWBW") == TrackingDirection.TRACKING_FW_BW
        assert TrackingDirection.from_abbreviation("FB") == TrackingDirection.TRACKING_FW_BW

    def test_from_abbreviation_invalid_input_defaults_to_bidirectional(self):
        """Test from_abbreviation defaults to FW_BW for invalid input."""
        assert TrackingDirection.from_abbreviation("INVALID") == TrackingDirection.TRACKING_FW_BW
        assert TrackingDirection.from_abbreviation("") == TrackingDirection.TRACKING_FW_BW
        assert TrackingDirection.from_abbreviation("123") == TrackingDirection.TRACKING_FW_BW

    def test_enum_equality(self):
        """Test enum equality comparisons."""
        fw1 = TrackingDirection.TRACKING_FW
        fw2 = TrackingDirection.from_abbreviation("FW")
        assert fw1 == fw2
        assert fw1 != TrackingDirection.TRACKING_BW

    def test_enum_string_representation(self):
        """Test string representation of enum values."""
        # str() returns the enum name
        assert str(TrackingDirection.TRACKING_FW) == "TrackingDirection.TRACKING_FW"
        # repr() returns the full enum representation including value
        assert repr(TrackingDirection.TRACKING_BW) == "<TrackingDirection.TRACKING_BW: 'backward'>"

    def test_enum_membership(self):
        """Test enum membership and iteration."""
        all_directions = list(TrackingDirection)
        assert len(all_directions) == 3
        assert TrackingDirection.TRACKING_FW in all_directions
        assert TrackingDirection.TRACKING_BW in all_directions
        assert TrackingDirection.TRACKING_FW_BW in all_directions

    def test_roundtrip_abbreviation_conversion(self):
        """Test that abbreviation -> enum -> abbreviation is consistent."""
        for direction in TrackingDirection:
            abbrev = direction.abbreviation
            reconstructed = TrackingDirection.from_abbreviation(abbrev)
            assert reconstructed == direction
            assert reconstructed.abbreviation == abbrev

    def test_roundtrip_display_name_consistency(self):
        """Test that display names are consistent with enum values."""
        expected_names = {
            TrackingDirection.TRACKING_FW: "Forward",
            TrackingDirection.TRACKING_BW: "Backward",
            TrackingDirection.TRACKING_FW_BW: "Bidirectional",
        }

        for direction, expected_name in expected_names.items():
            assert direction.display_name == expected_name

    def test_enum_hashable(self):
        """Test that enum values can be used as dictionary keys."""
        direction_dict = {
            TrackingDirection.TRACKING_FW: "forward_data",
            TrackingDirection.TRACKING_BW: "backward_data",
            TrackingDirection.TRACKING_FW_BW: "bidirectional_data",
        }

        assert len(direction_dict) == 3
        assert direction_dict[TrackingDirection.TRACKING_FW] == "forward_data"
        assert direction_dict[TrackingDirection.TRACKING_BW] == "backward_data"
        assert direction_dict[TrackingDirection.TRACKING_FW_BW] == "bidirectional_data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
