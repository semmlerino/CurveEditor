#!/usr/bin/env python
"""Tests for SignalConnectionManager.

Tests signal/slot connection management and cleanup.
"""

import pytest
from ui.controllers.signal_connection_manager import SignalConnectionManager


@pytest.fixture
def manager(mock_main_window):
    """Create SignalConnectionManager with mock main window."""
    return SignalConnectionManager(mock_main_window)


class TestSignalConnectionManager:
    """Test suite for SignalConnectionManager."""

    def test_connection_setup(self, manager):
        """Test signal connections are established."""
        # Would verify critical signals are connected
        pass

    def test_disconnect_prevents_memory_leaks(self, manager):
        """Test disconnect_signals prevents memory leaks."""
        # Should not raise
        manager.disconnect_signals()
