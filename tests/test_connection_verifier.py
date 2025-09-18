"""
Tests for the ConnectionVerifier fail-loud system.

These tests ensure that missing signal connections are caught at startup,
preventing orphaned UI components and silent failures.
"""

import pytest
from PySide6.QtCore import QObject, Signal

from stores import ConnectionRegistry, ConnectionStatus, ConnectionVerifier


class MockSource(QObject):
    """Mock source object with signals."""

    test_signal = Signal()
    data_changed = Signal()
    value_changed = Signal(int)


class MockTarget(QObject):
    """Mock target object with slots."""

    def __init__(self):
        super().__init__()
        self.call_count = 0
        self.last_value = None

    def test_slot(self):
        """Test slot method."""
        self.call_count += 1

    def handle_data_change(self):
        """Handle data change."""
        self.call_count += 1

    def handle_value(self, value: int):
        """Handle value change."""
        self.last_value = value
        self.call_count += 1


class TestConnectionVerifier:
    """Test the ConnectionVerifier class."""

    def test_empty_verifier(self):
        """Test verifier with no connections to check."""
        verifier = ConnectionVerifier()
        all_connected, reports = verifier.verify_all()

        assert all_connected is True
        assert len(reports) == 0

    def test_verify_valid_connection(self):
        """Test verification of a valid connection."""
        source = MockSource()
        target = MockTarget()

        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "MockSource", source, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        all_connected, reports = verifier.verify_all()

        assert all_connected is True
        assert len(reports) == 1
        assert reports[0].status == ConnectionStatus.CONNECTED

    def test_verify_missing_source(self):
        """Test verification with missing source object."""
        target = MockTarget()

        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "MockSource", None, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        all_connected, reports = verifier.verify_all()

        assert all_connected is False
        assert len(reports) == 1
        assert reports[0].status == ConnectionStatus.MISSING_SOURCE
        assert "Source object 'MockSource' is None" in reports[0].error_message

    def test_verify_missing_target(self):
        """Test verification with missing target object."""
        source = MockSource()

        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "MockSource", source, "test_signal", "MockTarget", None, "test_slot", critical=True
        )

        all_connected, reports = verifier.verify_all()

        assert all_connected is False
        assert len(reports) == 1
        assert reports[0].status == ConnectionStatus.MISSING_TARGET
        assert "Target object 'MockTarget' is None" in reports[0].error_message

    def test_verify_missing_signal(self):
        """Test verification when signal doesn't exist."""
        source = MockSource()
        target = MockTarget()

        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "MockSource",
            source,
            "nonexistent_signal",  # This signal doesn't exist
            "MockTarget",
            target,
            "test_slot",
            critical=True,
        )

        all_connected, reports = verifier.verify_all()

        assert all_connected is False
        assert len(reports) == 1
        assert reports[0].status == ConnectionStatus.ERROR
        assert "has no signal 'nonexistent_signal'" in reports[0].error_message

    def test_verify_missing_slot(self):
        """Test verification when slot doesn't exist."""
        source = MockSource()
        target = MockTarget()

        verifier = ConnectionVerifier()
        verifier.add_required_connection(
            "MockSource",
            source,
            "test_signal",
            "MockTarget",
            target,
            "nonexistent_slot",  # This slot doesn't exist
            critical=True,
        )

        all_connected, reports = verifier.verify_all()

        assert all_connected is False
        assert len(reports) == 1
        assert reports[0].status == ConnectionStatus.ERROR
        assert "has no slot 'nonexistent_slot'" in reports[0].error_message

    def test_non_critical_failure(self):
        """Test that non-critical failures don't fail verification."""
        source = MockSource()
        target = MockTarget()

        verifier = ConnectionVerifier()

        # Add a critical connection that will succeed
        verifier.add_required_connection(
            "MockSource", source, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        # Add a non-critical connection that will fail
        verifier.add_required_connection(
            "MockSource",
            source,
            "missing_signal",
            "MockTarget",
            target,
            "test_slot",
            critical=False,  # Non-critical
        )

        all_connected, reports = verifier.verify_all()

        # Should still return True because only critical connections matter
        assert all_connected is True
        assert len(reports) == 2
        assert reports[0].status == ConnectionStatus.CONNECTED
        assert reports[1].status == ConnectionStatus.ERROR

    def test_get_failed_connections(self):
        """Test getting list of failed connections."""
        source = MockSource()
        target = MockTarget()

        verifier = ConnectionVerifier()

        # Add some successful connections
        verifier.add_required_connection(
            "MockSource", source, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        # Add some failing connections
        verifier.add_required_connection(
            "MockSource", source, "missing_signal", "MockTarget", target, "test_slot", critical=False
        )

        verifier.add_required_connection(
            "MockSource", None, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        verifier.verify_all()
        failed = verifier.get_failed_connections()

        assert len(failed) == 2
        assert all(report.status != ConnectionStatus.CONNECTED for report in failed)

    def test_get_critical_failures(self):
        """Test getting list of critical failures only."""
        source = MockSource()
        target = MockTarget()

        verifier = ConnectionVerifier()

        # Add non-critical failure
        verifier.add_required_connection(
            "MockSource", source, "missing_signal", "MockTarget", target, "test_slot", critical=False
        )

        # Add critical failure
        verifier.add_required_connection(
            "MockSource", None, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        verifier.verify_all()
        critical_failures = verifier.get_critical_failures()

        assert len(critical_failures) == 1
        assert critical_failures[0].connection.critical is True
        assert critical_failures[0].status == ConnectionStatus.MISSING_SOURCE

    def test_raise_if_failed(self):
        """Test that raise_if_failed raises on critical failures."""
        target = MockTarget()

        verifier = ConnectionVerifier()

        # Add a critical failure
        verifier.add_required_connection(
            "MockSource", None, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        verifier.verify_all()

        # Should raise ConnectionError
        with pytest.raises(ConnectionError) as excinfo:
            verifier.raise_if_failed()

        assert "Critical signal connections missing" in str(excinfo.value)
        assert "MockSource.test_signal -> MockTarget.test_slot" in str(excinfo.value)

    def test_raise_if_failed_no_failures(self):
        """Test that raise_if_failed doesn't raise when all connections are good."""
        source = MockSource()
        target = MockTarget()

        verifier = ConnectionVerifier()

        verifier.add_required_connection(
            "MockSource", source, "test_signal", "MockTarget", target, "test_slot", critical=True
        )

        verifier.verify_all()

        # Should not raise
        verifier.raise_if_failed()  # No exception expected

    def test_multiple_connections(self):
        """Test verification of multiple connections."""
        source1 = MockSource()
        source2 = MockSource()
        target1 = MockTarget()
        target2 = MockTarget()

        verifier = ConnectionVerifier()

        # Add multiple connections
        verifier.add_required_connection(
            "Source1", source1, "test_signal", "Target1", target1, "test_slot", critical=True
        )

        verifier.add_required_connection(
            "Source1", source1, "data_changed", "Target2", target2, "handle_data_change", critical=True
        )

        verifier.add_required_connection(
            "Source2", source2, "value_changed", "Target1", target1, "handle_value", critical=False
        )

        all_connected, reports = verifier.verify_all()

        assert all_connected is True
        assert len(reports) == 3
        assert all(report.status == ConnectionStatus.CONNECTED for report in reports)


class TestConnectionRegistry:
    """Test the ConnectionRegistry class."""

    def test_register_connection(self):
        """Test registering a connection."""
        registry = ConnectionRegistry()

        registry.register_connection("Source", "signal", "Target", "slot")

        assert registry.is_connected("Source", "signal", "Target", "slot")
        assert not registry.is_connected("Source", "signal", "Target", "other_slot")

    def test_clear_registry(self):
        """Test clearing the registry."""
        registry = ConnectionRegistry()

        registry.register_connection("Source", "signal", "Target", "slot")
        assert registry.is_connected("Source", "signal", "Target", "slot")

        registry.clear()
        assert not registry.is_connected("Source", "signal", "Target", "slot")

    def test_get_all_connections(self):
        """Test getting all registered connections."""
        registry = ConnectionRegistry()

        registry.register_connection("Source1", "signal1", "Target1", "slot1")
        registry.register_connection("Source2", "signal2", "Target2", "slot2")

        all_connections = registry.get_all_connections()

        assert len(all_connections) == 2
        assert ("Source1", "signal1", "Target1", "slot1") in all_connections
        assert ("Source2", "signal2", "Target2", "slot2") in all_connections

    def test_duplicate_registration(self):
        """Test that duplicate registrations don't cause issues."""
        registry = ConnectionRegistry()

        registry.register_connection("Source", "signal", "Target", "slot")
        registry.register_connection("Source", "signal", "Target", "slot")  # Duplicate

        all_connections = registry.get_all_connections()
        assert len(all_connections) == 1  # Should only have one entry
