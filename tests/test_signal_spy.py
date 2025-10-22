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
    """Check if qtbot has spy method."""

    # Check available qtbot methods
    print("qtbot methods:")
    for method in dir(qtbot):
        if not method.startswith("_"):
            print(f"  - {method}")

    # Check if spy exists
    if hasattr(qtbot, "spy"):
        print("\n✅ qtbot.spy is available!")
    else:
        print("\n❌ qtbot.spy is NOT available")

        # Check for alternative methods
        if hasattr(qtbot, "SignalBlocker"):
            print("  But qtbot.SignalBlocker is available")
        if hasattr(qtbot, "waitSignal"):
            print("  And qtbot.waitSignal is available for signal testing")
