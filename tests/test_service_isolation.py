#!/usr/bin/env python3
"""
Test service isolation and reset behavior.

Ensures that reset_all_test_state() properly clears all service singletons
to prevent state leakage between tests.
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportPrivateUsage=none

import pytest

import services
from services import (
    get_data_service,
    get_interaction_service,
    get_transform_service,
    get_ui_service,
)
from stores.store_manager import StoreManager
from tests.fixtures.state_helpers import reset_all_test_state


class TestServiceIsolation:
    """Verify service reset clears all singletons."""

    def setup_method(self) -> None:
        """Start with clean state."""
        reset_all_test_state(log_warnings=False)

    def teardown_method(self) -> None:
        """Clean up after test."""
        reset_all_test_state(log_warnings=False)

    def test_reset_clears_all_service_singletons(self) -> None:
        """Verify reset_all_test_state() clears all service singletons."""
        # Trigger service creation
        _ = get_data_service()
        _ = get_transform_service()
        _ = get_interaction_service()
        _ = get_ui_service()

        # Verify services were created
        assert services._data_service is not None
        assert services._transform_service is not None
        assert services._interaction_service is not None
        assert services._ui_service is not None

        # Reset
        reset_all_test_state(log_warnings=False)

        # Verify all are None after reset
        assert services._data_service is None
        assert services._transform_service is None
        assert services._interaction_service is None
        assert services._ui_service is None

    def test_reset_clears_store_manager(self) -> None:
        """Verify reset clears StoreManager instance."""
        # Create StoreManager
        _ = StoreManager.get_instance()

        # Verify it was created
        assert StoreManager._instance is not None

        # Reset
        reset_all_test_state(log_warnings=False)

        # Verify StoreManager was reset
        assert StoreManager._instance is None

    def test_services_recreated_after_reset(self) -> None:
        """Verify services can be recreated after reset."""
        # Create services
        data1 = get_data_service()
        transform1 = get_transform_service()

        # Reset
        reset_all_test_state(log_warnings=False)

        # Create new services
        data2 = get_data_service()
        transform2 = get_transform_service()

        # Verify we got new instances
        assert data2 is not data1
        assert transform2 is not transform1

    def test_service_instances_independent_after_reset(self) -> None:
        """Verify service instances are independent after reset.

        This tests that reset creates a clean break - old instances
        are not reused and new instances start fresh.
        """
        # Get initial service and store its id
        transform1 = get_transform_service()
        transform1_id = id(transform1)

        # Reset
        reset_all_test_state(log_warnings=False)

        # Get new service after reset
        transform2 = get_transform_service()
        transform2_id = id(transform2)

        # Verify we got a completely new instance
        assert transform2_id != transform1_id
        assert transform2 is not transform1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
