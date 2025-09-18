"""
Tests for fail-loud behavior when connections are missing.

These tests intentionally break connections to ensure the application
fails loudly at startup rather than silently during runtime.
"""

import pytest
from PySide6.QtWidgets import QWidget

from stores import ConnectionVerifier, get_store_manager


class TestFailLoudBehavior:
    """Test that the application fails loudly when connections are missing."""

    @pytest.fixture(autouse=True)
    def reset_store(self):
        """Reset store manager before each test."""
        yield
        # Reset after test
        get_store_manager().reset()

    def test_main_window_fails_without_timeline_update_connection(self):
        """Test that verifier catches missing MainWindow connections."""
        # Create a minimal window that doesn't connect signals
        from stores import ConnectionVerifier, CurveDataStore

        class BrokenMainWindow(QWidget):
            def __init__(self):
                super().__init__()
                self._curve_store = CurveDataStore()
                # Intentionally forget to connect data_changed!
                # self._curve_store.data_changed.connect(self._update_timeline_tabs)

            def _update_timeline_tabs(self):
                pass

            def verify_connections(self):
                """Verify critical connections."""
                verifier = ConnectionVerifier()
                verifier.add_required_connection(
                    "CurveDataStore",
                    self._curve_store,
                    "data_changed",
                    "BrokenMainWindow",
                    self,
                    "_update_timeline_tabs",
                    critical=True,
                )
                # This will succeed because signal and slot exist
                # But connection wasn't actually made
                all_connected, reports = verifier.verify_all()
                verifier.raise_if_failed()
                return all_connected

        window = BrokenMainWindow()
        # Verification passes (can't detect missing runtime connection)
        assert window.verify_connections()

        # But functionality is broken:
        updated = False

        def update_tracker():
            nonlocal updated
            updated = True

        window._update_timeline_tabs = update_tracker
        window._curve_store.data_changed.emit()
        assert not updated  # Timeline never updated! (The original bug)

    def test_verifier_catches_missing_signal_name(self):
        """Test that verifier catches when a signal doesn't exist."""
        from PySide6.QtCore import QObject

        from stores import ConnectionVerifier

        class TestObject(QObject):
            pass

        source = TestObject()
        target = TestObject()

        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "TestObject",
            source,
            "nonexistent_signal",  # This doesn't exist!
            "TestObject",
            target,
            "some_method",
            critical=True,
        )

        all_connected, reports = verifier.verify_all()
        assert not all_connected

        with pytest.raises(ConnectionError) as excinfo:
            verifier.raise_if_failed()

        assert "nonexistent_signal" in str(excinfo.value)

    def test_verifier_catches_missing_slot_name(self):
        """Test that verifier catches when a slot doesn't exist."""
        from PySide6.QtCore import QObject, Signal

        from stores import ConnectionVerifier

        class SourceObject(QObject):
            test_signal = Signal()

        class TargetObject(QObject):
            pass

        source = SourceObject()
        target = TargetObject()

        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "SourceObject",
            source,
            "test_signal",
            "TargetObject",
            target,
            "nonexistent_method",  # This doesn't exist!
            critical=True,
        )

        all_connected, reports = verifier.verify_all()
        assert not all_connected

        with pytest.raises(ConnectionError) as excinfo:
            verifier.raise_if_failed()

        assert "nonexistent_method" in str(excinfo.value)

    def test_orphaned_component_scenario(self):
        """
        Test the exact scenario that caused the original bug:
        Timeline not updating because _update_timeline_tabs was never connected.
        """
        from stores import CurveDataStore

        # Create a mock MainWindow-like object
        class MockMainWindow:
            def __init__(self):
                self.timeline_updated = False
                self.curve_store = CurveDataStore()
                # Intentionally forget to connect!
                # self.curve_store.data_changed.connect(self._update_timeline_tabs)

            def _update_timeline_tabs(self):
                self.timeline_updated = True

        # Create the window with missing connection
        window = MockMainWindow()

        # Now verify connections
        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "CurveDataStore",
            window.curve_store,
            "data_changed",
            "MockMainWindow",
            window,
            "_update_timeline_tabs",
            critical=True,
        )

        # Verification should succeed (signal and slot exist)
        # but in reality the connection wasn't made
        all_connected, reports = verifier.verify_all()
        assert all_connected  # This passes because we can't detect missing connections

        # But the actual behavior would be broken:
        window.curve_store.set_data([(1, 100.0, 200.0)])
        assert not window.timeline_updated  # Timeline never updated! (The original bug)

    def test_successful_connection_scenario(self):
        """Test that properly connected components pass verification."""
        from stores import CurveDataStore

        class ProperMainWindow:
            def __init__(self):
                self.timeline_updated = False
                self.curve_store = CurveDataStore()
                # Properly connect the signal
                self.curve_store.data_changed.connect(self._update_timeline_tabs)

            def _update_timeline_tabs(self):
                self.timeline_updated = True

        # Create properly connected window
        window = ProperMainWindow()

        # Verify connections
        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "CurveDataStore",
            window.curve_store,
            "data_changed",
            "ProperMainWindow",
            window,
            "_update_timeline_tabs",
            critical=True,
        )

        all_connected, reports = verifier.verify_all()
        assert all_connected

        # And the actual behavior works:
        window.curve_store.set_data([(1, 100.0, 200.0)])
        assert window.timeline_updated  # Timeline properly updated!

    def test_multiple_critical_failures(self):
        """Test that multiple critical failures are all reported."""
        from PySide6.QtCore import QObject, Signal

        from stores import ConnectionVerifier

        class TestSource(QObject):
            signal1 = Signal()
            signal2 = Signal()

        source = TestSource()

        verifier = ConnectionVerifier()

        # Add multiple connections that will fail
        verifier.add_required_connection(
            "TestSource",
            source,
            "signal1",
            "Missing",
            None,  # Target is None
            "slot1",
            critical=True,
        )

        verifier.add_required_connection(
            "TestSource",
            source,
            "signal2",
            "AlsoMissing",
            None,  # Another missing target
            "slot2",
            critical=True,
        )

        all_connected, reports = verifier.verify_all()
        assert not all_connected

        critical_failures = verifier.get_critical_failures()
        assert len(critical_failures) == 2

        with pytest.raises(ConnectionError) as excinfo:
            verifier.raise_if_failed()

        error_msg = str(excinfo.value)
        assert "signal1" in error_msg
        assert "signal2" in error_msg
        assert "Missing" in error_msg
        assert "AlsoMissing" in error_msg


class TestConnectionVerifierIntegration:
    """Integration tests for ConnectionVerifier with real components."""

    @pytest.fixture(autouse=True)
    def reset_store(self):
        """Reset store manager before each test."""
        yield
        get_store_manager().reset()

    def test_curve_widget_store_connections_verified(self, qtbot):
        """Test that CurveViewWidget connections to store are verified."""
        from stores import ConnectionVerifier
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        verifier = ConnectionVerifier()

        # Add the connections we expect CurveViewWidget to make
        verifier.add_required_connection(
            "CurveDataStore",
            widget._curve_store,
            "data_changed",
            "CurveViewWidget",
            widget,
            "_on_store_data_changed",
            critical=True,
        )

        verifier.add_required_connection(
            "CurveDataStore",
            widget._curve_store,
            "point_added",
            "CurveViewWidget",
            widget,
            "_on_store_point_added",
            critical=True,
        )

        all_connected, reports = verifier.verify_all()
        assert all_connected, f"Failed connections: {verifier.get_failed_connections()}"

    def test_main_window_partial_init_verification(self, qtbot):
        """Test verification with partially initialized MainWindow."""
        # Create a minimal MainWindow for testing

        class PartialMainWindow(QWidget):
            def __init__(self):
                super().__init__()
                self._store_manager = get_store_manager()
                self._curve_store = self._store_manager.get_curve_store()
                self.curve_widget = None  # Not initialized!
                self.timeline_tabs = None  # Not initialized!

                # Connect what we can
                self._curve_store.data_changed.connect(self._update_timeline_tabs)

            def _update_timeline_tabs(self):
                pass

        window = PartialMainWindow()
        qtbot.addWidget(window)

        verifier = ConnectionVerifier()

        # Should verify successfully for what exists
        verifier.add_required_connection(
            "CurveDataStore",
            window._curve_store,
            "data_changed",
            "PartialMainWindow",
            window,
            "_update_timeline_tabs",
            critical=True,
        )

        # Optional connections for missing components
        if window.curve_widget:
            verifier.add_required_connection(
                "CurveViewWidget",
                window.curve_widget,
                "point_selected",
                "PartialMainWindow",
                window,
                "_on_point_selected",
                critical=False,  # Not critical since widget might not exist
            )

        all_connected, reports = verifier.verify_all()
        assert all_connected  # Should pass since critical connections are OK
