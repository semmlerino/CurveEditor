"""
Accessibility and UX tests for ImageSequenceBrowserDialog.

Tests keyboard navigation, accessible names, mnemonics, focus management,
and other accessibility features added for WCAG 2.1 compliance.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none
# pyright: reportUnknownLambdaType=none

from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from ui.image_sequence_browser import ImageSequenceBrowserDialog


class TestAccessibleNames:
    """Test that all interactive widgets have accessible names and descriptions."""

    def test_navigation_buttons_have_accessible_names(self, qtbot: QtBot):
        """Test navigation buttons have proper accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Back button
        assert dialog.back_button.accessibleName() == "Go back"
        assert "Navigate back" in dialog.back_button.accessibleDescription()

        # Forward button
        assert dialog.forward_button.accessibleName() == "Go forward"
        assert "Navigate forward" in dialog.forward_button.accessibleDescription()

        # Up button
        assert dialog.up_button.accessibleName() == "Go up"
        assert "parent directory" in dialog.up_button.accessibleDescription()

        # Home button
        assert dialog.home_button.accessibleName() == "Go to home"
        assert "home directory" in dialog.home_button.accessibleDescription()

    def test_address_bar_has_accessible_name(self, qtbot: QtBot):
        """Test address bar has accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        assert dialog.address_bar.accessibleName() == "Address bar"
        assert "directory path" in dialog.address_bar.accessibleDescription()

    def test_favorite_button_has_accessible_name(self, qtbot: QtBot):
        """Test favorite button has accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        assert dialog.favorite_button.accessibleName() == "Add to favorites"
        assert "Ctrl+D" in dialog.favorite_button.accessibleDescription()

    def test_lists_have_accessible_names(self, qtbot: QtBot):
        """Test list widgets have accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Favorites list
        assert dialog.favorites_list.accessibleName() == "Favorite directories"
        assert "favorite directories" in dialog.favorites_list.accessibleDescription()

        # Directory tree
        assert dialog.tree_view.accessibleName() == "Directory tree"
        assert "directories" in dialog.tree_view.accessibleDescription()

        # Sequence list
        assert dialog.sequence_list.accessibleName() == "Image sequences"
        assert "sequences" in dialog.sequence_list.accessibleDescription()

    def test_filter_and_sort_have_accessible_names(self, qtbot: QtBot):
        """Test filter and sort controls have accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Sequence filter
        assert dialog.sequence_filter.accessibleName() == "Sequence filter"
        assert "filter sequences" in dialog.sequence_filter.accessibleDescription()
        # Should NOT contain "Press Ctrl+F to focus" (redundant for screen reader)
        assert "Press Ctrl+F" not in dialog.sequence_filter.accessibleDescription()

        # Sort combo
        assert dialog.sort_combo.accessibleName() == "Sort by"
        assert "sort" in dialog.sort_combo.accessibleDescription()

        # Sort order button
        assert dialog.sort_order_button.accessibleName() == "Sort order"
        assert (
            "ascending" in dialog.sort_order_button.accessibleDescription()
            or "descending" in dialog.sort_order_button.accessibleDescription()
        )

    def test_action_buttons_have_accessible_names(self, qtbot: QtBot):
        """Test action buttons have accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Load button
        assert dialog.load_button.accessibleName() == "Load sequence"
        assert "sequence" in dialog.load_button.accessibleDescription()

        # Cancel button is created inline, tested indirectly through dialog behavior

    def test_progress_widgets_have_accessible_names(self, qtbot: QtBot):
        """Test progress bar and cancel scan button have accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Progress bar
        assert dialog.progress_bar.accessibleName() == "Scan progress"
        assert "progress" in dialog.progress_bar.accessibleDescription()

        # Cancel scan button
        assert dialog.cancel_scan_button.accessibleName() == "Cancel scan"
        assert "scanning" in dialog.cancel_scan_button.accessibleDescription()

    def test_info_label_has_accessible_name(self, qtbot: QtBot):
        """Test info label has accessible properties."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        assert dialog.info_label.accessibleName() == "Status message"
        assert "status" in dialog.info_label.accessibleDescription()


class TestMnemonics:
    """Test keyboard mnemonics (Alt+letter shortcuts)."""

    def test_directories_label_has_mnemonic(self, qtbot: QtBot):
        """Test 'All Directories' label has Alt+A mnemonic."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Find the label by searching through widgets
        tree_label = None
        for widget in dialog.findChildren(type(dialog.info_label).__bases__[0]):
            if hasattr(widget, "text") and "All Directories" in widget.text():
                tree_label = widget
                break

        assert tree_label is not None, "Could not find 'All Directories' label"
        assert "&" in tree_label.text(), "Label should contain mnemonic marker"
        # Verify buddy relationship
        assert tree_label.buddy() == dialog.tree_view

    def test_sequences_label_has_mnemonic(self, qtbot: QtBot):
        """Test 'Sequences' label has Alt+S mnemonic."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Find the sequences label
        from PySide6.QtWidgets import QLabel

        sequence_label = None
        for widget in dialog.findChildren(QLabel):
            if hasattr(widget, "text") and widget.text() == "&Sequences:":
                sequence_label = widget
                break

        assert sequence_label is not None, "Could not find 'Sequences' label"
        assert "&" in sequence_label.text(), "Label should contain mnemonic marker"
        # Verify buddy relationship
        assert sequence_label.buddy() == dialog.sequence_filter


class TestInitialFocus:
    """Test that dialog opens with focus on appropriate widget."""

    def test_initial_focus_on_tree_view(self, qtbot: QtBot):
        """Test that tree_view receives focus when dialog opens."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Process events to ensure focus is set
        qtbot.wait(100)

        # Verify tree_view has focus
        assert dialog.tree_view.hasFocus(), "tree_view should have initial focus"


class TestKeyboardShortcuts:
    """Test keyboard shortcuts for accessibility."""

    def test_escape_closes_dialog(self, qtbot: QtBot):
        """Test that Escape key closes the dialog."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Simulate Escape key press
        qtbot.keyClick(dialog, Qt.Key.Key_Escape)

        # Verify dialog was rejected (closed)
        assert dialog.result() == QDialog.DialogCode.Rejected

    def test_ctrl_shift_a_clears_selection(self, qtbot: QtBot, tmp_path: Path):
        """Test that Ctrl+Shift+A clears sequence selection."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Add a test sequence to the list
        from PySide6.QtWidgets import QListWidgetItem

        item = QListWidgetItem("Test Sequence")
        dialog.sequence_list.addItem(item)

        # Select the item
        dialog.sequence_list.setCurrentItem(item)
        assert dialog.sequence_list.currentItem() is not None

        # Give focus to sequence list (shortcut is global to dialog)
        dialog.sequence_list.setFocus()
        qtbot.wait(50)

        # Press Ctrl+Shift+A
        qtbot.keyClick(
            dialog.sequence_list, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        )

        # Wait for event processing
        qtbot.wait(100)

        # Verify selection is cleared
        assert dialog.sequence_list.currentRow() == -1

    def test_ctrl_f_focuses_sequence_filter(self, qtbot: QtBot):
        """Test that Ctrl+F focuses the sequence filter."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Wait for initial focus to be set
        qtbot.wait(100)

        # Ensure tree_view has focus (it gets focus on init)
        if not dialog.tree_view.hasFocus():
            dialog.tree_view.setFocus()
            qtbot.wait(50)

        # Press Ctrl+F on the focused widget
        qtbot.keyClick(dialog.tree_view, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)

        # Wait for event processing
        qtbot.wait(100)

        # Verify sequence_filter has focus
        assert dialog.sequence_filter.hasFocus(), "Ctrl+F should focus sequence filter"

    def test_ctrl_d_adds_to_favorites(self, qtbot: QtBot, monkeypatch, tmp_path: Path):
        """Test that Ctrl+D triggers add to favorites."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Navigate to a test directory
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Set current directory and trigger directory selection
        index = dialog.file_model.index(str(test_dir))
        dialog.tree_view.setCurrentIndex(index)
        dialog._on_directory_selected(index)
        qtbot.wait(100)

        # Mock the input dialog to provide a name
        from PySide6.QtWidgets import QInputDialog

        monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("Test Favorite", True))

        # Give focus to tree_view and press Ctrl+D
        dialog.tree_view.setFocus()
        qtbot.wait(50)
        qtbot.keyClick(dialog.tree_view, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)

        # Wait for event processing
        qtbot.wait(200)

        # Verify favorite was added
        assert dialog.favorites_manager.is_favorite(str(test_dir))


class TestTabOrder:
    """Test that tab order follows logical flow."""

    @staticmethod
    def _find_next_user_widget(widget, max_steps: int = 10):
        """Find the next user-visible widget in focus chain, skipping Qt internal widgets.

        Qt widgets like QListWidget and QTreeView have internal viewport widgets
        (qt_scrollarea_viewport, qt_scrollarea_hcontainer) that are part of the focus chain
        but not directly user-visible. This helper traverses past these to find the next
        user-facing widget.

        Args:
            widget: Starting widget
            max_steps: Maximum number of steps to traverse (prevents infinite loops)

        Returns:
            The next user-visible widget, or the immediate next widget if no user widget found
        """
        current = widget.nextInFocusChain()
        for _ in range(max_steps):
            # Qt internal widgets typically have "qt_" prefix in object name
            obj_name = current.objectName()
            if not obj_name.startswith("qt_"):
                return current
            current = current.nextInFocusChain()
        # Fallback: return whatever we found
        return widget.nextInFocusChain()

    @staticmethod
    def _find_prev_user_widget(widget, max_steps: int = 10):
        """Find the previous user-visible widget in focus chain, skipping Qt internal widgets."""
        current = widget.previousInFocusChain()
        for _ in range(max_steps):
            obj_name = current.objectName()
            if not obj_name.startswith("qt_"):
                return current
            current = current.previousInFocusChain()
        return widget.previousInFocusChain()

    def test_tab_order_starts_with_navigation(self, qtbot: QtBot):
        """Test that tab order begins with navigation buttons.

        Uses nextInFocusChain() to verify tab order configuration
        without requiring focus management (which is unreliable in headless environments).
        """
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        qtbot.wait(100)  # Wait for dialog to be fully initialized

        # Verify tab order using focus chain introspection
        # back_button -> forward_button
        assert dialog.back_button.nextInFocusChain() is dialog.forward_button, "Tab from back should go to forward"

        # forward_button -> up_button
        assert dialog.forward_button.nextInFocusChain() is dialog.up_button, "Tab from forward should go to up"

        # Verify reverse direction
        assert (
            dialog.forward_button.previousInFocusChain() is dialog.back_button
        ), "Shift+Tab from forward should go to back"

    def test_tab_order_includes_main_panels(self, qtbot: QtBot):
        """Test that tab order includes favorites, tree, and sequence list.

        Uses nextInFocusChain() to verify tab order configuration,
        skipping Qt internal viewport widgets.
        """
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        qtbot.wait(100)

        # Verify tab order using focus chain introspection
        # favorite_button -> favorites_list
        assert (
            dialog.favorite_button.nextInFocusChain() is dialog.favorites_list
        ), "Tab from favorite button should go to favorites list"

        # favorites_list -> tree_view (may have viewport widgets in between)
        next_widget = self._find_next_user_widget(dialog.favorites_list)
        assert next_widget is dialog.tree_view, "Tab from favorites list should eventually reach tree view"

        # tree_view -> sequence_filter (may have viewport widgets in between)
        next_widget = self._find_next_user_widget(dialog.tree_view)
        assert next_widget is dialog.sequence_filter, "Tab from tree view should eventually reach sequence filter"

    def test_tab_order_ends_with_action_buttons(self, qtbot: QtBot):
        """Test that tab order ends with Load button.

        Uses nextInFocusChain() to verify tab order configuration,
        skipping Qt internal viewport widgets.
        """
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        qtbot.wait(100)

        # Verify tab order using focus chain introspection
        # sequence_list -> load_button (may have viewport widgets in between)
        next_widget = self._find_next_user_widget(dialog.sequence_list)
        assert next_widget is dialog.load_button, "Tab from sequence list should eventually reach load button"

        # Verify reverse direction (may have viewport widgets in between)
        prev_widget = self._find_prev_user_widget(dialog.load_button)
        assert prev_widget is dialog.sequence_list, "Shift+Tab from load button should eventually reach sequence list"


class TestBreadcrumbAccessibility:
    """Test that BreadcrumbBar buttons have accessible properties."""

    def test_breadcrumb_buttons_have_accessible_names(self, qtbot: QtBot, tmp_path: Path):
        """Test that dynamically created breadcrumb buttons have accessible names."""
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Create a nested directory structure
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)

        # Navigate to trigger breadcrumb creation
        dialog._navigate_to_path(str(nested_dir))
        qtbot.wait(100)

        # Find breadcrumb buttons
        from PySide6.QtWidgets import QToolButton

        breadcrumb_buttons = dialog.breadcrumb_bar.findChildren(QToolButton)

        # Verify at least some buttons were created
        assert len(breadcrumb_buttons) > 0, "Breadcrumb buttons should be created"

        # Verify each button has accessible properties
        for button in breadcrumb_buttons:
            assert button.accessibleName(), f"Breadcrumb button '{button.text()}' should have accessible name"
            assert (
                button.accessibleDescription()
            ), f"Breadcrumb button '{button.text()}' should have accessible description"
            # Accessible name should mention navigation
            assert "Navigate" in button.accessibleName()


class TestConfirmationDialogs:
    """Test confirmation dialogs for destructive actions."""

    def test_favorite_removal_requires_confirmation(self, qtbot: QtBot, monkeypatch, tmp_path: Path):
        """Test that removing a favorite shows confirmation dialog.

        Note: Full removal flow is tested in test_image_sequence_browser_favorites.py.
        This test verifies the accessibility aspect - that confirmation is shown.
        """
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

        # Add a test favorite
        test_path = tmp_path / "test"
        test_path.mkdir()
        dialog.favorites_manager.add("Test", str(test_path))
        dialog._populate_favorites()

        # Verify it exists and item was created
        assert dialog.favorites_manager.is_favorite(str(test_path))
        assert dialog.favorites_list.count() >= 1, "Should have at least one favorite"

        # Track if QMessageBox.question was called
        from PySide6.QtWidgets import QMessageBox

        question_called = []

        def mock_question(*args, **kwargs):
            question_called.append(True)
            # Return Yes to proceed with removal
            return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(QMessageBox, "question", mock_question)

        # Create mock menu that returns remove action
        mock_menu = Mock()
        rename_action = Mock()
        remove_action = Mock()
        move_up_action = Mock()
        move_down_action = Mock()

        mock_menu.addAction = Mock(side_effect=[rename_action, remove_action, move_up_action, move_down_action])
        mock_menu.addSeparator = Mock()
        # Mock exec to return remove_action without blocking
        mock_menu.exec = Mock(return_value=remove_action)

        monkeypatch.setattr("PySide6.QtWidgets.QMenu", lambda parent: mock_menu)

        # Trigger context menu
        dialog._show_favorites_context_menu(QPoint(0, 0))

        # Verify confirmation dialog was shown
        assert len(question_called) > 0, "Confirmation dialog should have been shown before removal"


def test_dialog_accessibility_completeness(qtbot: QtBot):
    """Integration test verifying overall accessibility completeness."""
    dialog = ImageSequenceBrowserDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    # Count widgets with accessible names
    from PySide6.QtWidgets import QWidget

    all_widgets = dialog.findChildren(QWidget)

    # Interactive widgets that should have accessible names
    interactive_types = {
        "QPushButton",
        "QToolButton",
        "QComboBox",
        "QLineEdit",
        "QListWidget",
        "QTreeView",
        "QProgressBar",
    }

    interactive_widgets = [w for w in all_widgets if type(w).__name__ in interactive_types]

    widgets_with_names = [w for w in interactive_widgets if w.accessibleName()]

    # We should have high coverage (at least 80% of interactive widgets)
    coverage = len(widgets_with_names) / len(interactive_widgets) if interactive_widgets else 0
    assert coverage >= 0.8, f"Accessible name coverage is {coverage:.1%}, should be >= 80%"
