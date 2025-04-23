from typing import Any, Callable, Optional, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

def safe_operation(operation_name: Optional[str] = None) -> Callable[[F], F]: ...
