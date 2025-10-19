"""Qt utility functions and decorators."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

R = TypeVar("R")


def safe_slot(func: Callable[..., R]) -> Callable[..., R | None]:
    """Decorator to guard Qt slot handlers against widget destruction.

    If the widget is being destroyed (raises RuntimeError on attribute access),
    the handler returns None without executing. Otherwise, executes normally.

    This prevents errors when signals fire during widget cleanup.

    Args:
        func: Slot handler function to guard

    Returns:
        Wrapped function that safely handles widget destruction

    Example:
        @safe_slot
        def _on_curves_changed(self, curves: dict) -> None:
            # No try/except needed - decorator handles destruction
            self.update_display(curves)
    """

    @wraps(func)
    def wrapper(self: object, *args: Any, **kwargs: Any) -> R | None:
        try:
            # Test if widget is being destroyed
            _ = self.isVisible()  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        except RuntimeError:
            # Widget being destroyed - skip handler
            logger.debug(f"Skipped {func.__name__} - widget being destroyed")
            return None
        except AttributeError:
            # Not a widget (doesn't have isVisible) - execute anyway
            pass

        # Widget OK - execute handler
        return func(self, *args, **kwargs)  # type: ignore[arg-type]

    return wrapper


def safe_slot_logging(verbose: bool = False) -> Callable[[Callable[..., R]], Callable[..., R | None]]:
    """Parameterized version of safe_slot with configurable logging.

    Args:
        verbose: If True, log every skip. If False, only log at debug level.

    Returns:
        Decorator function

    Example:
        @safe_slot_logging(verbose=True)
        def _on_data_changed(self, data): ...
    """

    def decorator(func: Callable[..., R]) -> Callable[..., R | None]:
        @wraps(func)
        def wrapper(self: object, *args: Any, **kwargs: Any) -> R | None:
            try:
                _ = self.isVisible()  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
            except RuntimeError:
                if verbose:
                    logger.info(f"Widget destroyed - skipped {func.__name__}")
                else:
                    logger.debug(f"Widget destroyed - skipped {func.__name__}")
                return None
            except AttributeError:
                pass

            return func(self, *args, **kwargs)  # type: ignore[arg-type]

        return wrapper

    return decorator
