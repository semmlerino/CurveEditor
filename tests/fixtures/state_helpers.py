"""
Test state management helpers.

Provides proper reset functions for services and application state
with error tracking instead of silent exception swallowing.
"""

# Per-file type checking relaxations for test code
# pyright: reportAny=none
# pyright: reportPrivateUsage=none

import logging
from collections.abc import Generator

logger = logging.getLogger(__name__)


def reset_services_safely() -> list[str]:
    """Reset all services with proper error tracking.

    Clears service caches before resetting singletons to ensure clean state.

    Returns:
        List of warning messages for any issues encountered
    """
    warnings: list[str] = []

    try:
        import services

        # 1. Clear caches first (before resetting instances)
        for service_name in ["_transform_service", "_data_service", "_interaction_service"]:
            service = getattr(services, service_name, None)
            if service is not None:
                # Clear service cache
                clear_cache = getattr(service, "clear_cache", None)
                if clear_cache is not None:
                    try:
                        clear_cache()
                    except Exception as e:
                        warnings.append(f"Cache clear failed for {service_name}: {e}")

                # Special handling for data service image cache
                if service_name == "_data_service":
                    safe_cache = getattr(service, "_safe_image_cache", None)
                    if safe_cache is not None:
                        cleanup = getattr(safe_cache, "cleanup", None)
                        if cleanup is not None:
                            try:
                                cleanup()
                            except Exception as e:
                                warnings.append(f"Image cache cleanup failed: {e}")

        # 2. Use public reset function
        services.reset_all_services()

    except Exception as e:
        warnings.append(f"Service reset error: {e}")

    return warnings


def reset_application_state_safely() -> list[str]:
    """Reset ApplicationState with proper error tracking.

    Returns:
        List of warning messages for any issues encountered
    """
    warnings: list[str] = []

    try:
        from stores.application_state import reset_application_state

        reset_application_state()
    except Exception as e:
        warnings.append(f"ApplicationState reset error: {e}")

    return warnings


def reset_store_manager_safely() -> list[str]:
    """Reset StoreManager with proper error tracking.

    Returns:
        List of warning messages for any issues encountered
    """
    warnings: list[str] = []

    try:
        from stores.store_manager import StoreManager

        StoreManager.reset()
    except Exception as e:
        warnings.append(f"StoreManager reset error: {e}")

    return warnings


def reset_config_safely() -> list[str]:
    """Reset global config with proper error tracking.

    Returns:
        List of warning messages for any issues encountered
    """
    warnings: list[str] = []

    try:
        from core.config import reset_config

        reset_config()
    except Exception as e:
        warnings.append(f"Config reset error: {e}")

    return warnings


def process_qt_events_safely() -> list[str]:
    """Process Qt events to clean up QObjects with proper error tracking.

    Returns:
        List of warning messages for any issues encountered
    """
    warnings: list[str] = []

    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            # Process deleteLater() calls
            app.processEvents()
            # Additional event processing for nested deletions
            app.processEvents()
    except Exception as e:
        warnings.append(f"Qt event processing error: {e}")

    return warnings


def force_garbage_collection() -> list[str]:
    """Force Python garbage collection with proper error tracking.

    Returns:
        List of warning messages for any issues encountered
    """
    warnings: list[str] = []

    try:
        import gc

        gc.collect()
        # Process Qt events again after gc to handle any Qt cleanup from __del__
        warnings.extend(process_qt_events_safely())
    except Exception as e:
        warnings.append(f"Garbage collection error: {e}")

    return warnings


def reset_all_test_state(log_warnings: bool = True) -> list[str]:
    """Reset all test state in correct order with error tracking.

    Order matters:
    1. Clear service caches (while services exist)
    2. Reset services
    3. Reset ApplicationState
    4. Reset StoreManager
    5. Reset config
    6. Process Qt events
    7. Force garbage collection

    Args:
        log_warnings: Whether to log warnings (vs return silently)

    Returns:
        List of all warning messages encountered
    """
    all_warnings: list[str] = []

    # Order matters: services -> app state -> store manager -> config -> Qt -> gc
    all_warnings.extend(reset_services_safely())
    all_warnings.extend(reset_application_state_safely())
    all_warnings.extend(reset_store_manager_safely())
    all_warnings.extend(reset_config_safely())
    all_warnings.extend(process_qt_events_safely())
    all_warnings.extend(force_garbage_collection())

    if log_warnings:
        for warning in all_warnings:
            logger.warning(warning)

    return all_warnings
