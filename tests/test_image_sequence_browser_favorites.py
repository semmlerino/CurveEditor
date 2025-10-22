"""Tests for ImageSequenceBrowserDialog favorites UI functionality."""

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

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from core.favorites_manager import FavoritesManager
from ui.image_sequence_browser import ImageSequenceBrowserDialog


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def dialog(qtbot: QtBot, temp_config_dir):
    """Create ImageSequenceBrowserDialog with temp favorites."""
    # Create dialog normally
    dialog = ImageSequenceBrowserDialog()
    qtbot.addWidget(dialog)

    # Replace its favorites manager with one using temp directory
    dialog.favorites_manager = FavoritesManager(config_dir=temp_config_dir)
    dialog._populate_favorites()  # Repopulate with new manager

    return dialog


def test_dialog_has_favorites_list(dialog):
    """Test dialog has favorites list widget."""
    assert hasattr(dialog, "favorites_list")
    assert dialog.favorites_list is not None


def test_dialog_has_favorite_button(dialog):
    """Test dialog has star button for adding favorites."""
    assert hasattr(dialog, "favorite_button")
    assert dialog.favorite_button is not None
    assert dialog.favorite_button.text() == "★"


def test_favorite_button_disabled_initially(dialog):
    """Test favorite button is disabled when no directory selected."""
    assert not dialog.favorite_button.isEnabled()


def test_populate_favorites_empty(dialog):
    """Test populating favorites when list is empty."""
    dialog._populate_favorites()

    assert dialog.favorites_list.count() == 0


def test_populate_favorites_with_items(dialog, temp_config_dir):
    """Test populating favorites list with items."""
    # Add some favorites
    dialog.favorites_manager.add("Project A", "/path/a")
    dialog.favorites_manager.add("Project B", "/path/b")

    dialog._populate_favorites()

    assert dialog.favorites_list.count() == 2
    assert "Project A" in dialog.favorites_list.item(0).text()
    assert "Project B" in dialog.favorites_list.item(1).text()


def test_favorite_items_have_star_icon(dialog):
    """Test favorite items display with star icon."""
    dialog.favorites_manager.add("Project", "/path")
    dialog._populate_favorites()

    item = dialog.favorites_list.item(0)
    assert item.text().startswith("★")


def test_favorite_items_store_path_in_user_data(dialog):
    """Test favorite items store path in UserRole data."""
    test_path = "/test/path"
    dialog.favorites_manager.add("Project", test_path)
    dialog._populate_favorites()

    item = dialog.favorites_list.item(0)
    stored_path = item.data(Qt.ItemDataRole.UserRole)
    assert stored_path == test_path


def test_favorite_items_have_tooltip(dialog):
    """Test favorite items show full path as tooltip."""
    test_path = "/very/long/path/to/project"
    dialog.favorites_manager.add("Project", test_path)
    dialog._populate_favorites()

    item = dialog.favorites_list.item(0)
    assert item.toolTip() == test_path


def test_on_favorite_double_clicked_navigates(dialog, qtbot: QtBot, monkeypatch, temp_config_dir):
    """Test double-clicking favorite navigates to that directory."""
    # Use temp_config_dir which actually exists
    test_path = str(temp_config_dir)
    dialog.favorites_manager.add("Project", test_path)
    dialog._populate_favorites()

    # Mock navigation to avoid file system access
    navigate_called = []
    monkeypatch.setattr(dialog, "_navigate_to_path", lambda path: navigate_called.append(path))

    item = dialog.favorites_list.item(0)
    dialog._on_favorite_double_clicked(item)

    assert len(navigate_called) == 1
    assert navigate_called[0] == test_path


def test_on_favorite_double_clicked_nonexistent_path(dialog, qtbot: QtBot):
    """Test double-clicking non-existent path shows error."""
    dialog.favorites_manager.add("Project", "/nonexistent/path")
    dialog._populate_favorites()

    item = dialog.favorites_list.item(0)
    dialog._on_favorite_double_clicked(item)

    # Should update info label with error
    assert "no longer exists" in dialog.info_label.text().lower()


def test_update_favorite_button_state_no_selection(dialog):
    """Test favorite button disabled when no directory selected."""
    # Mock tree view with invalid index
    dialog.tree_view.currentIndex = Mock(return_value=Mock(isValid=lambda: False))

    dialog._update_favorite_button_state()

    assert not dialog.favorite_button.isEnabled()


def test_update_favorite_button_state_not_favorited(dialog, monkeypatch):
    """Test favorite button enabled and normal when directory not favorited."""
    # Mock tree view and file model
    mock_index = Mock(isValid=lambda: True)
    dialog.tree_view.currentIndex = Mock(return_value=mock_index)
    dialog.file_model.filePath = Mock(return_value="/test/path")

    # Ensure path is not favorited
    assert not dialog.favorites_manager.is_favorite("/test/path")

    dialog._update_favorite_button_state()

    assert dialog.favorite_button.isEnabled()
    assert "Add current directory" in dialog.favorite_button.toolTip()


def test_update_favorite_button_state_already_favorited(dialog, monkeypatch):
    """Test favorite button shows gold color when directory already favorited."""
    test_path = "/test/path"
    dialog.favorites_manager.add("Project", test_path)

    # Mock tree view and file model
    mock_index = Mock(isValid=lambda: True)
    dialog.tree_view.currentIndex = Mock(return_value=mock_index)
    dialog.file_model.filePath = Mock(return_value=test_path)

    dialog._update_favorite_button_state()

    assert dialog.favorite_button.isEnabled()
    assert "Already in favorites" in dialog.favorite_button.toolTip()
    assert "gold" in dialog.favorite_button.styleSheet().lower()


def test_on_add_to_favorites_invalid_index(dialog, monkeypatch):
    """Test adding favorite with no directory selected does nothing."""
    dialog.tree_view.currentIndex = Mock(return_value=Mock(isValid=lambda: False))

    # Should return early without error
    dialog._on_add_to_favorites()


def test_on_add_to_favorites_already_favorited(dialog, qtbot: QtBot, monkeypatch):
    """Test adding already favorited directory shows message."""
    test_path = "/test/path"
    dialog.favorites_manager.add("Existing", test_path)

    mock_index = Mock(isValid=lambda: True)
    dialog.tree_view.currentIndex = Mock(return_value=mock_index)
    dialog.file_model.filePath = Mock(return_value=test_path)

    dialog._on_add_to_favorites()

    assert "already in favorites" in dialog.info_label.text().lower()


def test_on_add_to_favorites_success(dialog, qtbot: QtBot, monkeypatch):
    """Test successfully adding favorite."""
    from PySide6.QtWidgets import QInputDialog

    test_path = "/test/new/path"
    mock_index = Mock(isValid=lambda: True)
    dialog.tree_view.currentIndex = Mock(return_value=mock_index)
    dialog.file_model.filePath = Mock(return_value=test_path)

    # Mock input dialog to return name
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("My Project", True))

    # Mock populate to avoid refresh issues
    populate_called = []
    monkeypatch.setattr(dialog, "_populate_favorites", lambda: populate_called.append(True))
    monkeypatch.setattr(dialog, "_update_favorite_button_state", lambda: None)

    dialog._on_add_to_favorites()

    # Verify favorite was added
    assert dialog.favorites_manager.is_favorite(test_path)
    assert len(populate_called) == 1  # Repopulated
    assert "added" in dialog.info_label.text().lower()


def test_on_add_to_favorites_cancelled(dialog, qtbot: QtBot, monkeypatch):
    """Test cancelling add favorite dialog."""
    from PySide6.QtWidgets import QInputDialog

    test_path = "/test/path"
    mock_index = Mock(isValid=lambda: True)
    dialog.tree_view.currentIndex = Mock(return_value=mock_index)
    dialog.file_model.filePath = Mock(return_value=test_path)

    # Mock input dialog cancelled (ok=False)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("", False))

    dialog._on_add_to_favorites()

    # Favorite should not be added
    assert not dialog.favorites_manager.is_favorite(test_path)


def test_favorites_list_has_context_menu_policy(dialog):
    """Test favorites list has custom context menu enabled."""
    assert dialog.favorites_list.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu


def test_show_favorites_context_menu_no_item(dialog, monkeypatch):
    """Test context menu does nothing when not on an item."""
    from PySide6.QtCore import QPoint

    # Mock itemAt to return None
    dialog.favorites_list.itemAt = Mock(return_value=None)

    # Should return early without error
    dialog._show_favorites_context_menu(QPoint(0, 0))


def test_context_menu_rename_action(dialog, qtbot: QtBot, monkeypatch):
    """Test rename action from context menu."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QInputDialog, QMenu

    test_path = "/test/path"
    dialog.favorites_manager.add("Old Name", test_path)
    dialog._populate_favorites()

    # Mock menu exec to return rename action
    mock_menu = Mock(spec=QMenu)
    rename_action = Mock()
    mock_menu.addAction = Mock(side_effect=[rename_action, Mock(), Mock(), Mock()])
    mock_menu.addSeparator = Mock()
    mock_menu.exec = Mock(return_value=rename_action)

    monkeypatch.setattr("PySide6.QtWidgets.QMenu", lambda parent: mock_menu)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("New Name", True))

    # Mock repopulate
    populate_called = []
    monkeypatch.setattr(dialog, "_populate_favorites", lambda: populate_called.append(True))

    dialog._show_favorites_context_menu(QPoint(0, 0))

    # Verify rename happened
    favorites = dialog.favorites_manager.get_all()
    assert favorites[0].name == "New Name"
    assert len(populate_called) == 1


def test_context_menu_remove_action(dialog, qtbot: QtBot, monkeypatch):
    """Test remove action from context menu."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QMenu

    test_path = "/test/path"
    dialog.favorites_manager.add("Project", test_path)
    dialog._populate_favorites()

    # Mock menu exec to return remove action
    mock_menu = Mock(spec=QMenu)
    rename_action = Mock()
    remove_action = Mock()
    mock_menu.addAction = Mock(side_effect=[rename_action, remove_action, Mock(), Mock()])
    mock_menu.addSeparator = Mock()
    mock_menu.exec = Mock(return_value=remove_action)

    monkeypatch.setattr("PySide6.QtWidgets.QMenu", lambda parent: mock_menu)

    # Mock confirmation dialog (return Yes)
    from PySide6.QtWidgets import QMessageBox

    mock_question = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "question", mock_question)

    # Mock repopulate and update button
    populate_called = []
    update_button_called = []
    monkeypatch.setattr(dialog, "_populate_favorites", lambda: populate_called.append(True))
    monkeypatch.setattr(dialog, "_update_favorite_button_state", lambda: update_button_called.append(True))

    dialog._show_favorites_context_menu(QPoint(0, 0))

    # Verify removal
    assert not dialog.favorites_manager.is_favorite(test_path)
    assert len(populate_called) == 1
    assert len(update_button_called) == 1


def test_favorites_manager_initialized_on_dialog_creation(qtbot: QtBot):
    """Test FavoritesManager is created when dialog is initialized."""
    dialog = ImageSequenceBrowserDialog()
    qtbot.addWidget(dialog)

    assert hasattr(dialog, "favorites_manager")
    assert isinstance(dialog.favorites_manager, FavoritesManager)


def test_populate_favorites_called_on_init(qtbot: QtBot, monkeypatch):
    """Test _populate_favorites is called during dialog initialization."""
    populate_called = []

    # Patch _populate_favorites before dialog creation
    original_init = ImageSequenceBrowserDialog.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        populate_called.append(True)

    with patch.object(ImageSequenceBrowserDialog, "_populate_favorites", lambda self: populate_called.append(True)):
        dialog = ImageSequenceBrowserDialog()
        qtbot.addWidget(dialog)

    # Should be called once during init
    assert len(populate_called) >= 1
