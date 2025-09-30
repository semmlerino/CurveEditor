#!/usr/bin/env python
"""
Central registry for keyboard shortcuts.

This module provides a centralized registry for managing all keyboard shortcuts
in the application, ensuring consistent handling regardless of widget focus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QKeySequence

if TYPE_CHECKING:
    from core.commands.shortcut_command import ShortcutCommand

from core.logger_utils import get_logger

logger = get_logger("shortcut_registry")


class ShortcutRegistry:
    """Central registry for all keyboard shortcuts.

    Manages registration, lookup, and documentation of keyboard shortcuts,
    providing a single source of truth for all shortcuts in the application.
    """

    def __init__(self) -> None:
        """Initialize the shortcut registry."""
        self._shortcuts: dict[str, ShortcutCommand] = {}
        self._key_to_normalized: dict[str, str] = {}
        logger.info("ShortcutRegistry initialized")

    def register(self, command: ShortcutCommand) -> None:
        """Register a shortcut command.

        Args:
            command: The shortcut command to register
        """
        key = command.key_sequence
        normalized_key = self._normalize_key_sequence(key)

        if normalized_key in self._shortcuts:
            logger.warning(f"Overwriting existing shortcut: {key} (was: {self._shortcuts[normalized_key].description})")

        self._shortcuts[normalized_key] = command
        self._key_to_normalized[key] = normalized_key

        logger.info(f"Registered shortcut: {key} -> {command.description}")

    def unregister(self, key_sequence: str) -> bool:
        """Unregister a shortcut.

        Args:
            key_sequence: The key sequence to unregister

        Returns:
            True if the shortcut was unregistered, False if not found
        """
        normalized_key = self._normalize_key_sequence(key_sequence)

        if normalized_key in self._shortcuts:
            del self._shortcuts[normalized_key]
            # Clean up key_to_normalized mapping
            keys_to_remove = [k for k, v in self._key_to_normalized.items() if v == normalized_key]
            for k in keys_to_remove:
                del self._key_to_normalized[k]
            logger.info(f"Unregistered shortcut: {key_sequence}")
            return True

        return False

    def get_command(self, event: QKeyEvent) -> ShortcutCommand | None:
        """Get command for a key event.

        Args:
            event: The key event to look up

        Returns:
            The associated command, or None if no command is registered
        """
        key_sequence = self._event_to_key_sequence(event)
        normalized_key = self._normalize_key_sequence(key_sequence)

        command = self._shortcuts.get(normalized_key)
        if command:
            logger.debug(f"Found command for {key_sequence}: {command.description}")
        else:
            logger.debug(f"No command found for key sequence: {key_sequence}")

        # Keep minimal logging for symbol key lookups to help with debugging international keyboards
        if event.key() in {Qt.Key.Key_Exclam, Qt.Key.Key_QuoteDbl, Qt.Key.Key_At}:
            status = "FOUND" if command else "NOT FOUND"
            logger.info(f"Symbol key lookup: {event.key()} -> '{key_sequence}' -> {status}")
        return command

    def list_shortcuts(self) -> dict[str, str]:
        """List all registered shortcuts.

        Returns:
            Dictionary mapping key sequences to descriptions
        """
        return {cmd.key_sequence: cmd.description for cmd in self._shortcuts.values()}

    def get_shortcuts_by_category(self) -> dict[str, list[tuple[str, str]]]:
        """Get shortcuts organized by category.

        Returns:
            Dictionary mapping categories to lists of (key, description) tuples
        """
        categories: dict[str, list[tuple[str, str]]] = {
            "Navigation": [],
            "Selection": [],
            "Editing": [],
            "View": [],
            "Tracking": [],
            "Other": [],
        }

        for cmd in self._shortcuts.values():
            desc_lower = cmd.description.lower()

            # Categorize based on description
            if any(word in desc_lower for word in ["navigate", "frame", "next", "prev", "first", "last"]):
                category = "Navigation"
            elif any(word in desc_lower for word in ["select", "deselect"]):
                category = "Selection"
            elif any(word in desc_lower for word in ["delete", "add", "edit", "endframe", "nudge"]):
                category = "Editing"
            elif any(word in desc_lower for word in ["zoom", "center", "fit", "view"]):
                category = "View"
            elif any(word in desc_lower for word in ["tracking", "direction"]):
                category = "Tracking"
            else:
                category = "Other"

            categories[category].append((cmd.key_sequence, cmd.description))

        # Sort within each category
        for category in categories:
            categories[category].sort(key=lambda x: x[0])

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _normalize_key_sequence(self, key_sequence: str) -> str:
        """Normalize a key sequence string for consistent lookup.

        Args:
            key_sequence: The key sequence to normalize

        Returns:
            Normalized key sequence string
        """
        # Convert to QKeySequence and back to ensure consistency
        seq = QKeySequence(key_sequence)
        return seq.toString()

    def _event_to_key_sequence(self, event: QKeyEvent) -> str:
        """Convert a QKeyEvent to a key sequence string.

        Args:
            event: The key event to convert

        Returns:
            Key sequence string representation
        """
        key = event.key()
        modifiers = event.modifiers()

        # Special handling for symbol keys that represent shifted numbers on international keyboards
        # These keys come WITHOUT the Shift modifier when generated by Shift+number
        symbol_key_map: dict[int, str] = {
            Qt.Key.Key_Exclam: "!",  # Shift+1 on many layouts
            Qt.Key.Key_QuoteDbl: '"',  # Shift+2 on German layout
            Qt.Key.Key_At: "@",  # Shift+2 on US layout
        }

        if key in symbol_key_map:
            # Symbol keys are registered without modifiers
            return symbol_key_map[key]

        # Build modifier string
        mod_strs = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mod_strs.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mod_strs.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mod_strs.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            mod_strs.append("Meta")

        # Get key string
        key_str = QKeySequence(key).toString()

        # Combine modifiers and key
        if mod_strs:
            return "+".join(mod_strs + [key_str])
        return key_str

    def has_conflicts(self) -> list[tuple[str, list[ShortcutCommand]]]:
        """Check for conflicting shortcuts.

        Returns:
            List of (key_sequence, [commands]) for any conflicts found
        """
        # Check for duplicate normalized keys
        key_to_commands: dict[str, list[ShortcutCommand]] = {}

        for original_key, normalized_key in self._key_to_normalized.items():
            if normalized_key not in key_to_commands:
                key_to_commands[normalized_key] = []
            if self._shortcuts[normalized_key] not in key_to_commands[normalized_key]:
                key_to_commands[normalized_key].append(self._shortcuts[normalized_key])

        # Find conflicts (same normalized key with different commands)
        conflicts = []
        for key, commands in key_to_commands.items():
            if len(commands) > 1:
                conflicts.append((key, commands))

        return conflicts

    def clear(self) -> None:
        """Clear all registered shortcuts."""
        self._shortcuts.clear()
        self._key_to_normalized.clear()
        logger.info("Cleared all shortcuts from registry")
