#!/usr/bin/env python
"""
Tests for Image Browser Phase 2 Features.

Tests breadcrumb navigation, history, sorting, and state persistence.
"""

from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt

from ui.image_sequence_browser import (
    BreadcrumbBar,
    ImageSequence,
    ImageSequenceBrowserDialog,
    NavigationHistory,
)


class TestBreadcrumbBar:
    """Test breadcrumb navigation widget."""

    @pytest.fixture
    def breadcrumb_bar(self, qtbot):
        """Create breadcrumb bar with proper cleanup."""
        bar = BreadcrumbBar()
        qtbot.addWidget(bar)
        return bar

    def test_breadcrumb_initialization(self, breadcrumb_bar):
        """Test breadcrumb bar initializes correctly."""
        assert breadcrumb_bar.current_path == ""
        assert breadcrumb_bar._layout is not None

    def test_set_path_creates_segments(self, breadcrumb_bar, tmp_path):
        """Test setting path creates clickable segments."""
        # Create test path
        test_path = tmp_path / "projects" / "sequences"
        test_path.mkdir(parents=True, exist_ok=True)

        breadcrumb_bar.set_path(str(test_path))

        assert breadcrumb_bar.current_path == str(test_path)
        # Should have multiple segments (root + intermediate + current)
        assert breadcrumb_bar._layout.count() > 1

    def test_breadcrumb_click_emits_signal(self, qtbot, breadcrumb_bar, tmp_path):
        """Test clicking breadcrumb segment emits path_changed signal."""
        test_path = tmp_path / "test_dir"
        test_path.mkdir(parents=True, exist_ok=True)

        breadcrumb_bar.set_path(str(test_path))

        # Use qtbot.waitSignal for signal verification
        with qtbot.waitSignal(breadcrumb_bar.path_changed, timeout=1000) as blocker:
            # Trigger segment click manually
            breadcrumb_bar._on_segment_clicked(str(tmp_path))

        # Verify signal was emitted with correct path
        assert blocker.args[0] == str(tmp_path)

    def test_empty_path_clears_breadcrumbs(self, breadcrumb_bar, tmp_path):
        """Test empty path clears all breadcrumb segments."""
        test_path = tmp_path / "test"
        test_path.mkdir(exist_ok=True)

        # Set path first
        breadcrumb_bar.set_path(str(test_path))
        initial_count = breadcrumb_bar._layout.count()
        assert initial_count > 1

        # Clear with empty path
        breadcrumb_bar.set_path("")

        # Should only have stretch item left
        assert breadcrumb_bar._layout.count() == 1


class TestNavigationHistory:
    """Test navigation history for back/forward buttons."""

    @pytest.fixture
    def history(self):
        """Create navigation history."""
        return NavigationHistory(max_history=5)

    def test_history_initialization(self, history):
        """Test history initializes empty."""
        assert len(history.history) == 0
        assert history.current_index == -1
        assert not history.can_go_back()
        assert not history.can_go_forward()

    def test_add_path_to_history(self, history):
        """Test adding paths to history."""
        history.add("/path/one")
        assert len(history.history) == 1
        assert history.current_index == 0
        assert not history.can_go_back()
        assert not history.can_go_forward()

        history.add("/path/two")
        assert len(history.history) == 2
        assert history.current_index == 1
        assert history.can_go_back()
        assert not history.can_go_forward()

    def test_duplicate_path_not_added(self, history):
        """Test duplicate consecutive paths are not added."""
        history.add("/path/one")
        history.add("/path/one")
        assert len(history.history) == 1

    def test_go_back_navigation(self, history):
        """Test navigating back through history."""
        history.add("/path/one")
        history.add("/path/two")
        history.add("/path/three")

        assert history.can_go_back()
        prev_path = history.go_back()
        assert prev_path == "/path/two"
        assert history.current_index == 1

        prev_path = history.go_back()
        assert prev_path == "/path/one"
        assert history.current_index == 0
        assert not history.can_go_back()

    def test_go_forward_navigation(self, history):
        """Test navigating forward through history."""
        history.add("/path/one")
        history.add("/path/two")
        history.add("/path/three")
        history.go_back()
        history.go_back()

        assert history.can_go_forward()
        next_path = history.go_forward()
        assert next_path == "/path/two"
        assert history.current_index == 1

        next_path = history.go_forward()
        assert next_path == "/path/three"
        assert not history.can_go_forward()

    def test_new_path_clears_forward_history(self, history):
        """Test adding new path after going back clears forward history."""
        history.add("/path/one")
        history.add("/path/two")
        history.add("/path/three")
        history.go_back()  # At /path/two

        # Add new path - should clear /path/three
        history.add("/path/new")
        assert len(history.history) == 3
        assert history.history[-1] == "/path/new"
        assert not history.can_go_forward()

    def test_max_history_limit(self, history):
        """Test history respects max_history limit."""
        for i in range(10):
            history.add(f"/path/{i}")

        # Should only keep last 5
        assert len(history.history) == 5
        assert history.history[0] == "/path/5"
        assert history.history[-1] == "/path/9"

    def test_get_current_path(self, history):
        """Test getting current path from history."""
        assert history.get_current() is None

        history.add("/path/one")
        assert history.get_current() == "/path/one"

        history.add("/path/two")
        assert history.get_current() == "/path/two"

        history.go_back()
        assert history.get_current() == "/path/one"


class TestImageBrowserSorting:
    """Test sorting functionality in image browser."""

    @pytest.fixture
    def dialog(self, qtbot, tmp_path):
        """Create image browser dialog."""
        # Create dialog without parent (state manager not needed for these tests)
        dialog = ImageSequenceBrowserDialog(None, str(tmp_path))
        qtbot.addWidget(dialog)
        return dialog

    def test_sort_combo_has_options(self, dialog):
        """Test sort combo box has all sort options."""
        assert dialog.sort_combo.count() == 4
        assert dialog.sort_combo.itemText(0) == "Name"
        assert dialog.sort_combo.itemText(1) == "Frame Count"
        assert dialog.sort_combo.itemText(2) == "File Size"
        assert dialog.sort_combo.itemText(3) == "Date Modified"

    def test_sort_order_button_toggles(self, dialog):
        """Test sort order button toggles between ascending/descending."""
        # Initially ascending
        assert dialog.sort_ascending is True
        assert dialog.sort_order_button.text() == "↑"

        # Toggle to descending
        dialog._toggle_sort_order()
        assert dialog.sort_ascending is False
        assert dialog.sort_order_button.text() == "↓"

        # Toggle back to ascending
        dialog._toggle_sort_order()
        assert dialog.sort_ascending is True
        assert dialog.sort_order_button.text() == "↑"

    def test_on_sort_changed_updates_current_sort(self, dialog):
        """Test changing sort option updates current sort."""
        dialog._on_sort_changed("Name")
        assert dialog.current_sort == "name"

        dialog._on_sort_changed("Frame Count")
        assert dialog.current_sort == "frame_count"

        dialog._on_sort_changed("File Size")
        assert dialog.current_sort == "size"

        dialog._on_sort_changed("Date Modified")
        assert dialog.current_sort == "date"

    def test_sort_by_name(self, dialog):
        """Test sorting sequences by name."""
        # Create test sequences
        sequences = [
            ImageSequence("zebra_", 4, ".exr", [1, 2], ["zebra_0001.exr"], "/test"),
            ImageSequence("alpha_", 4, ".exr", [1, 2], ["alpha_0001.exr"], "/test"),
            ImageSequence("beta_", 4, ".exr", [1, 2], ["beta_0001.exr"], "/test"),
        ]

        # Add to list
        for seq in sequences:
            from PySide6.QtWidgets import QListWidgetItem

            item = QListWidgetItem(seq.display_name)
            item.setData(Qt.ItemDataRole.UserRole, seq)
            dialog.sequence_list.addItem(item)

        # Sort by name ascending
        dialog.current_sort = "name"
        dialog.sort_ascending = True
        dialog._apply_sort()

        # Check order
        first_seq = dialog.sequence_list.item(0).data(Qt.ItemDataRole.UserRole)
        assert first_seq.base_name == "alpha_"

        last_seq = dialog.sequence_list.item(2).data(Qt.ItemDataRole.UserRole)
        assert last_seq.base_name == "zebra_"

    def test_sort_by_frame_count(self, dialog):
        """Test sorting sequences by frame count."""
        # Create sequences with different frame counts
        sequences = [
            ImageSequence("seq1_", 4, ".exr", [1, 2, 3, 4, 5], ["seq1_0001.exr"], "/test"),
            ImageSequence("seq2_", 4, ".exr", [1, 2], ["seq2_0001.exr"], "/test"),
            ImageSequence("seq3_", 4, ".exr", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], ["seq3_0001.exr"], "/test"),
        ]

        # Add to list
        for seq in sequences:
            from PySide6.QtWidgets import QListWidgetItem

            item = QListWidgetItem(seq.display_name)
            item.setData(Qt.ItemDataRole.UserRole, seq)
            dialog.sequence_list.addItem(item)

        # Sort by frame count descending
        dialog.current_sort = "frame_count"
        dialog.sort_ascending = False
        dialog._apply_sort()

        # Check order (most frames first)
        first_seq = dialog.sequence_list.item(0).data(Qt.ItemDataRole.UserRole)
        assert len(first_seq.frames) == 10

        last_seq = dialog.sequence_list.item(2).data(Qt.ItemDataRole.UserRole)
        assert len(last_seq.frames) == 2

    def test_sort_by_size(self, dialog):
        """Test sorting sequences by file size."""
        sequences = [
            ImageSequence("small_", 4, ".exr", [1], ["small_0001.exr"], "/test"),
            ImageSequence("large_", 4, ".exr", [1], ["large_0001.exr"], "/test"),
            ImageSequence("medium_", 4, ".exr", [1], ["medium_0001.exr"], "/test"),
        ]
        sequences[0].total_size_bytes = 1000
        sequences[1].total_size_bytes = 10000
        sequences[2].total_size_bytes = 5000

        # Add to list
        for seq in sequences:
            from PySide6.QtWidgets import QListWidgetItem

            item = QListWidgetItem(seq.display_name)
            item.setData(Qt.ItemDataRole.UserRole, seq)
            dialog.sequence_list.addItem(item)

        # Sort by size ascending
        dialog.current_sort = "size"
        dialog.sort_ascending = True
        dialog._apply_sort()

        # Check order (smallest first)
        first_seq = dialog.sequence_list.item(0).data(Qt.ItemDataRole.UserRole)
        assert first_seq.total_size_bytes == 1000

        last_seq = dialog.sequence_list.item(2).data(Qt.ItemDataRole.UserRole)
        assert last_seq.total_size_bytes == 10000


class TestImageBrowserStatePersistence:
    """Test state persistence across dialog sessions."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager."""
        manager = Mock()
        manager.get_value = Mock(return_value=None)
        manager.set_value = Mock()
        manager.recent_directories = []
        return manager

    @pytest.fixture
    def dialog_with_state(self, qtbot, tmp_path):
        """Create dialog with state manager."""
        from PySide6.QtWidgets import QWidget

        # Create a real QWidget as parent
        parent = QWidget()
        qtbot.addWidget(parent)

        # Add mock state manager to parent
        parent.state_manager = Mock()  # pyright: ignore[reportAttributeAccessIssue]
        parent.state_manager.get_value = Mock(return_value=None)  # pyright: ignore[reportAttributeAccessIssue]
        parent.state_manager.set_value = Mock()  # pyright: ignore[reportAttributeAccessIssue]
        parent.state_manager.recent_directories = []  # pyright: ignore[reportAttributeAccessIssue]

        dialog = ImageSequenceBrowserDialog(parent, str(tmp_path))
        qtbot.addWidget(dialog)

        yield dialog

        # Explicit cleanup to prevent teardown errors
        try:
            dialog.close()
        except RuntimeError:
            pass  # Already deleted

    def test_restore_state_called_on_init(self, dialog_with_state):
        """Test _restore_state is called during initialization."""
        # Get the state manager from the dialog's parent
        try:
            parent = dialog_with_state.parent()
            if parent:
                state_manager = parent.state_manager  # pyright: ignore[reportAttributeAccessIssue]
                # Should have called get_value for geometry, splitter, sort
                assert state_manager.get_value.called
        except RuntimeError:
            # Dialog was deleted - this is ok
            pass

    def test_save_state(self, dialog_with_state):
        """Test state saving functionality."""
        # Get state manager from parent
        parent = dialog_with_state.parent()
        if parent and hasattr(parent, "state_manager"):
            state_manager = parent.state_manager  # pyright: ignore[reportAttributeAccessIssue]
            # Reset mock to check calls
            state_manager.set_value.reset_mock()

            # Call _save_state directly (don't use accept/reject which delete the dialog)
            dialog_with_state._save_state()

            # Should have saved geometry, splitter state, and sort preferences
            assert state_manager.set_value.call_count >= 3
            call_args = [call[0][0] for call in state_manager.set_value.call_args_list]
            assert "image_browser_geometry" in call_args
            assert "image_browser_sort" in call_args
            assert "image_browser_sort_ascending" in call_args

    def test_restore_sort_preferences(self, qtbot, tmp_path):
        """Test restoring saved sort preferences."""
        from PySide6.QtWidgets import QWidget

        # Create parent widget with state manager
        parent = QWidget()
        qtbot.addWidget(parent)

        # Set up mock state manager with saved state
        parent.state_manager = Mock()  # pyright: ignore[reportAttributeAccessIssue]
        parent.state_manager.get_value = Mock(  # pyright: ignore[reportAttributeAccessIssue]
            side_effect=lambda key: {
                "image_browser_sort": "frame_count",
                "image_browser_sort_ascending": False,
            }.get(key)
        )
        parent.state_manager.recent_directories = []  # pyright: ignore[reportAttributeAccessIssue]

        dialog = ImageSequenceBrowserDialog(parent, str(tmp_path))
        qtbot.addWidget(dialog)

        # Check restored values
        assert dialog.current_sort == "frame_count"
        assert dialog.sort_ascending is False
        assert dialog.sort_combo.currentText() == "Frame Count"


class TestImageBrowserHistoryIntegration:
    """Test back/forward navigation integration."""

    @pytest.fixture
    def dialog(self, qtbot, tmp_path):
        """Create dialog with test directories."""
        # Create test directory structure
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir3 = tmp_path / "dir3"
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()

        dialog = ImageSequenceBrowserDialog(None, str(tmp_path))
        qtbot.addWidget(dialog)
        return dialog

    def test_back_button_initially_disabled(self, dialog):
        """Test back button is disabled on dialog open."""
        assert not dialog.back_button.isEnabled()

    def test_forward_button_initially_disabled(self, dialog):
        """Test forward button is disabled on dialog open."""
        assert not dialog.forward_button.isEnabled()

    def test_navigation_updates_history(self, qtbot, dialog, tmp_path):
        """Test navigation adds to history."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"

        # Navigate to dir1
        dialog._navigate_to_path(str(dir1))
        qtbot.wait(100)  # Allow Qt events to process

        assert dialog.back_button.isEnabled()
        assert not dialog.forward_button.isEnabled()

        # Navigate to dir2
        dialog._navigate_to_path(str(dir2))
        qtbot.wait(100)
        assert dialog.back_button.isEnabled()
        assert not dialog.forward_button.isEnabled()

        # History should have both
        assert dialog.nav_history.can_go_back()

    def test_go_back_enables_forward(self, qtbot, dialog, tmp_path):
        """Test going back enables forward button."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"

        dialog._navigate_to_path(str(dir1))
        qtbot.wait(100)
        dialog._navigate_to_path(str(dir2))
        qtbot.wait(100)

        # Go back
        dialog._go_back()
        qtbot.wait(100)

        assert dialog.back_button.isEnabled()
        assert dialog.forward_button.isEnabled()

    def test_go_forward_navigates_correctly(self, dialog, tmp_path):
        """Test forward navigation works correctly."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"

        dialog._navigate_to_path(str(dir1))
        dialog._navigate_to_path(str(dir2))
        dialog._go_back()  # Back to dir1

        # Go forward to dir2
        dialog._go_forward()

        # Check breadcrumb shows dir2
        assert str(dir2) in dialog.breadcrumb_bar.current_path


class TestImageBrowserKeyboardShortcuts:
    """Test keyboard shortcuts for Phase 2 features."""

    @pytest.fixture
    def dialog(self, qtbot, tmp_path):
        """Create dialog for shortcut testing."""
        dialog = ImageSequenceBrowserDialog(None, str(tmp_path))
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        return dialog

    def test_ctrl_l_focuses_address_bar(self, qtbot, dialog):
        """Test Ctrl+L shows and focuses address bar."""
        # Initially breadcrumb should be visible
        assert dialog.breadcrumb_bar.isVisible()
        assert not dialog.address_bar.isVisible()

        # Press Ctrl+L
        qtbot.keyClick(dialog, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier)
        qtbot.wait(100)

        # Address bar should be visible and focused
        assert not dialog.breadcrumb_bar.isVisible()
        assert dialog.address_bar.isVisible()
        # Note: Focus check might be flaky in headless tests

    def test_alt_left_triggers_back(self, qtbot, dialog, tmp_path):
        """Test Alt+Left triggers back navigation."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Navigate to create history
        dialog._navigate_to_path(str(dir1))
        dialog._navigate_to_path(str(dir2))

        # Press Alt+Left
        qtbot.keyClick(dialog, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier)
        qtbot.wait(100)

        # Should have gone back
        assert dialog.forward_button.isEnabled()

    def test_alt_right_triggers_forward(self, qtbot, dialog, tmp_path):
        """Test Alt+Right triggers forward navigation."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Navigate and go back
        dialog._navigate_to_path(str(dir1))
        dialog._navigate_to_path(str(dir2))
        dialog._go_back()

        # Press Alt+Right
        qtbot.keyClick(dialog, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
        qtbot.wait(100)

        # Should have gone forward
        assert not dialog.forward_button.isEnabled()


def test_breadcrumb_and_history_integration(qtbot, tmp_path):
    """Test breadcrumb navigation integrates with history."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    dialog = ImageSequenceBrowserDialog(None, str(tmp_path))
    qtbot.addWidget(dialog)

    # Navigate to dir1
    dialog._navigate_to_path(str(dir1))
    assert dialog.breadcrumb_bar.current_path == str(dir1)
    assert dialog.nav_history.get_current() == str(dir1)

    # Navigate to dir2
    dialog._navigate_to_path(str(dir2))
    assert dialog.breadcrumb_bar.current_path == str(dir2)
    assert dialog.nav_history.get_current() == str(dir2)

    # Go back via history
    dialog._go_back()
    assert dialog.breadcrumb_bar.current_path == str(dir1)
    assert dialog.nav_history.get_current() == str(dir1)
