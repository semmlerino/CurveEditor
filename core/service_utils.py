"""Service access utilities.

This module provides centralized access to services, reducing import duplication.
Previously, service imports were repeated 29+ times across the codebase.
"""

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from services.data_service import DataService
    from services.interaction_service import InteractionService
    from services.transform_service import TransformService
    from services.ui_service import UIService

T = TypeVar("T")


class ServiceProvider:
    """Centralized service provider for all application services."""

    _data_service: "DataService | None" = None
    _interaction_service: "InteractionService | None" = None
    _transform_service: "TransformService | None" = None
    _ui_service: "UIService | None" = None

    @classmethod
    def get_data_service(cls) -> "DataService":
        """Get the data service singleton.

        Returns:
            DataService instance
        """
        if cls._data_service is None:
            from services import get_data_service

            cls._data_service = get_data_service()
        return cls._data_service

    @classmethod
    def get_interaction_service(cls) -> "InteractionService":
        """Get the interaction service singleton.

        Returns:
            InteractionService instance
        """
        if cls._interaction_service is None:
            from services import get_interaction_service

            cls._interaction_service = get_interaction_service()
        return cls._interaction_service

    @classmethod
    def get_transform_service(cls) -> "TransformService":
        """Get the transform service singleton.

        Returns:
            TransformService instance
        """
        if cls._transform_service is None:
            from services import get_transform_service

            cls._transform_service = get_transform_service()
        return cls._transform_service

    @classmethod
    def get_ui_service(cls) -> "UIService":
        """Get the UI service singleton.

        Returns:
            UIService instance
        """
        if cls._ui_service is None:
            from services import get_ui_service

            cls._ui_service = get_ui_service()
        return cls._ui_service

    @classmethod
    def reset_services(cls) -> None:
        """Reset all service instances. Useful for testing."""
        cls._data_service = None
        cls._interaction_service = None
        cls._transform_service = None
        cls._ui_service = None


class ServiceContext[T]:
    """Context manager for temporary service operations.

    Example:
        with ServiceContext(mock_data_service) as data_service:
            data_service.load_file("test.json")
    """

    service: T
    original_service: T | None
    service_name: str

    def __init__(self, service: T):
        """Initialize service context.

        Args:
            service: Service instance to use in context
        """
        self.service = service
        self.original_service = None
        self.service_name = type(service).__name__

    def __enter__(self) -> T:
        """Enter context, temporarily replacing service."""
        # Store original and set temporary
        if self.service_name == "DataService":
            self.original_service = ServiceProvider._data_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
            ServiceProvider._data_service = self.service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
        elif self.service_name == "InteractionService":
            self.original_service = ServiceProvider._interaction_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
            ServiceProvider._interaction_service = self.service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
        elif self.service_name == "TransformService":
            self.original_service = ServiceProvider._transform_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
            ServiceProvider._transform_service = self.service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
        elif self.service_name == "UIService":
            self.original_service = ServiceProvider._ui_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
            ServiceProvider._ui_service = self.service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]

        return self.service

    def __exit__(self, *args: object) -> None:
        """Exit context, restoring original service."""
        # Restore original
        if self.service_name == "DataService":
            ServiceProvider._data_service = self.original_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
        elif self.service_name == "InteractionService":
            ServiceProvider._interaction_service = self.original_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
        elif self.service_name == "TransformService":
            ServiceProvider._transform_service = self.original_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
        elif self.service_name == "UIService":
            ServiceProvider._ui_service = self.original_service  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]


# Convenience functions for backward compatibility
def get_all_services() -> tuple["DataService", "InteractionService", "TransformService", "UIService"]:
    """Get all services at once.

    Returns:
        Tuple of (DataService, InteractionService, TransformService, UIService)

    Example:
        data_service, interaction_service, transform_service, ui_service = get_all_services()
    """
    return (
        ServiceProvider.get_data_service(),
        ServiceProvider.get_interaction_service(),
        ServiceProvider.get_transform_service(),
        ServiceProvider.get_ui_service(),
    )
