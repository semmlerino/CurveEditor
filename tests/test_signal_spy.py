"""Test to check qtbot.spy availability."""


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


def test_qtbot_spy_availability(qtbot):
    """Check if qtbot has required signal testing methods.

    Verifies that qtbot provides the necessary methods for testing Qt signals.
    """
    # Assert that waitSignal is available (required for signal testing)
    assert hasattr(qtbot, "waitSignal"), "qtbot.waitSignal is required for signal testing"

    # Assert that waitSignals is available (bulk signal testing)
    assert hasattr(qtbot, "waitSignals"), "qtbot.waitSignals is required for bulk signal testing"
