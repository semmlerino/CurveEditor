"""Tests for CurveDataCommand base class helper methods.

This module tests the base class methods that all curve commands inherit.
These helpers are critical infrastructure - bugs here affect all 8 command classes.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

from core.commands.curve_commands import SetCurveDataCommand
from core.type_aliases import LegacyPointData
from stores.application_state import get_application_state


class TestGetActiveCurveData:
    """Test _get_active_curve_data() helper method."""

    def test_returns_tuple_when_curve_exists(self):
        """_get_active_curve_data returns (name, data) tuple when curve exists."""
        app_state = get_application_state()
        app_state.set_active_curve("Track1")
        app_state.set_curve_data("Track1", [(1, 100.0, 200.0)])

        cmd = SetCurveDataCommand("test", [])
        result = cmd._get_active_curve_data()

        assert result is not None
        curve_name, curve_data = result
        assert curve_name == "Track1"
        assert curve_data == [(1, 100.0, 200.0)]

    def test_returns_none_when_no_active_curve(self):
        """_get_active_curve_data returns None when no active curve."""
        app_state = get_application_state()
        app_state.set_active_curve(None)

        cmd = SetCurveDataCommand("test", [])
        result = cmd._get_active_curve_data()

        assert result is None

    def test_accepts_empty_curve_data(self):
        """_get_active_curve_data returns empty list when curve has no points."""
        app_state = get_application_state()
        app_state.set_active_curve("Track1")
        app_state.set_curve_data("Track1", [])

        cmd = SetCurveDataCommand("test", [])
        result = cmd._get_active_curve_data()

        assert result is not None
        curve_name, curve_data = result
        assert curve_name == "Track1"
        assert curve_data == []  # Empty is valid per ApplicationState contract


class TestSafeExecute:
    """Test _safe_execute() error handling wrapper."""

    def test_returns_true_when_operation_succeeds(self):
        """_safe_execute returns True when operation succeeds."""
        cmd = SetCurveDataCommand("test", [])

        def successful_operation():
            return True

        result = cmd._safe_execute("testing", successful_operation)
        assert result is True

    def test_returns_false_when_operation_returns_false(self):
        """_safe_execute returns False when operation returns False."""
        cmd = SetCurveDataCommand("test", [])

        def failing_operation():
            return False

        result = cmd._safe_execute("testing", failing_operation)
        assert result is False

    def test_catches_exceptions_and_returns_false(self):
        """_safe_execute catches exceptions and returns False."""
        cmd = SetCurveDataCommand("test", [])

        def exploding_operation():
            raise RuntimeError("Test exception")

        result = cmd._safe_execute("testing", exploding_operation)
        assert result is False


class TestUpdatePointPosition:
    """Test _update_point_position() helper method."""

    def test_updates_3_element_tuple(self):
        """_update_point_position preserves frame, updates x/y (3-tuple)."""
        cmd = SetCurveDataCommand("test", [])
        point: LegacyPointData = (42, 100.0, 200.0)
        new_pos = (150.0, 250.0)

        result = cmd._update_point_position(point, new_pos)

        assert result == (42, 150.0, 250.0)

    def test_updates_4_element_tuple(self):
        """_update_point_position preserves frame and status (4-tuple)."""
        cmd = SetCurveDataCommand("test", [])
        point: LegacyPointData = (42, 100.0, 200.0, "keyframe")
        new_pos = (150.0, 250.0)

        result = cmd._update_point_position(point, new_pos)

        assert result == (42, 150.0, 250.0, "keyframe")

    def test_handles_invalid_tuple_gracefully(self):
        """_update_point_position returns original if tuple too small."""
        cmd = SetCurveDataCommand("test", [])
        # Create a 2-tuple that will be treated as invalid by the helper
        invalid_point = (42, 100.0)
        new_pos = (150.0, 250.0)

        result = cmd._update_point_position(invalid_point, new_pos)

        assert result == invalid_point  # Unchanged

    def test_preserves_status_in_4_tuple(self):
        """_update_point_position maintains status value exactly."""
        cmd = SetCurveDataCommand("test", [])
        point: LegacyPointData = (10, 50.0, 60.0, "endframe")
        new_pos = (75.0, 85.0)

        result = cmd._update_point_position(point, new_pos)

        assert result == (10, 75.0, 85.0, "endframe")
        # Type checker knows result is PointTuple4 because input was PointTuple4
        assert len(result) == 4
        assert result[3] == "endframe"  # Status preserved


class TestUpdatePointAtIndex:
    """Test _update_point_at_index() helper method."""

    def test_updates_point_at_valid_index(self):
        """_update_point_at_index updates point at valid index."""
        cmd = SetCurveDataCommand("test", [])
        curve_data: list[LegacyPointData] = [(1, 100.0, 200.0), (2, 150.0, 250.0)]

        def updater(point: LegacyPointData) -> LegacyPointData:
            return (point[0], point[1] + 10, point[2] + 10)

        result = cmd._update_point_at_index(curve_data, 0, updater)

        assert result is True
        assert curve_data[0] == (1, 110.0, 210.0)
        assert curve_data[1] == (2, 150.0, 250.0)  # Unchanged

    def test_returns_false_for_index_too_high(self):
        """_update_point_at_index returns False for index out of bounds."""
        cmd = SetCurveDataCommand("test", [])
        curve_data: list[LegacyPointData] = [(1, 100.0, 200.0)]

        def updater(point: LegacyPointData) -> LegacyPointData:
            return point

        result = cmd._update_point_at_index(curve_data, 999, updater)

        assert result is False
        assert curve_data == [(1, 100.0, 200.0)]  # Unchanged

    def test_returns_false_for_negative_index(self):
        """_update_point_at_index returns False for negative index."""
        cmd = SetCurveDataCommand("test", [])
        curve_data: list[LegacyPointData] = [(1, 100.0, 200.0)]

        def updater(point: LegacyPointData) -> LegacyPointData:
            return point

        result = cmd._update_point_at_index(curve_data, -1, updater)

        assert result is False
        assert curve_data == [(1, 100.0, 200.0)]  # Unchanged

    def test_returns_false_for_empty_list(self):
        """_update_point_at_index returns False for empty curve data."""
        cmd = SetCurveDataCommand("test", [])
        curve_data: list[LegacyPointData] = []

        def updater(point: LegacyPointData) -> LegacyPointData:
            return point

        result = cmd._update_point_at_index(curve_data, 0, updater)

        assert result is False
        assert curve_data == []  # Still empty

    def test_updater_receives_correct_point(self):
        """_update_point_at_index passes correct point to updater."""
        cmd = SetCurveDataCommand("test", [])
        curve_data: list[LegacyPointData] = [(5, 10.0, 20.0), (6, 30.0, 40.0)]
        received_point = None

        def capturing_updater(point: LegacyPointData) -> LegacyPointData:
            nonlocal received_point
            received_point = point
            return point

        cmd._update_point_at_index(curve_data, 1, capturing_updater)

        assert received_point == (6, 30.0, 40.0)


class TestTargetCurveStorage:
    """Test _target_curve field storage (Bug #2 fix verification)."""

    def test_target_curve_field_exists(self):
        """CurveDataCommand initializes _target_curve field."""
        cmd = SetCurveDataCommand("test", [])
        assert hasattr(cmd, "_target_curve")
        assert cmd._target_curve is None  # Initially None

    def test_target_curve_can_be_set(self):
        """_target_curve field can be assigned."""
        cmd = SetCurveDataCommand("test", [])
        cmd._target_curve = "Track1"
        assert cmd._target_curve == "Track1"
