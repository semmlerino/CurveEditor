from typing import Any, Callable
from PySide6.QtWidgets import QWidget

class ShortcutManager:
    @staticmethod
    def connect_shortcut(window: QWidget, shortcut_id: str, slot_function: Callable[..., Any]) -> None: ...
