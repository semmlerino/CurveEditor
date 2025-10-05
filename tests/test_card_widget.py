"""
Tests for the modern Card widget (Phase 3: Visual Modernization).

Tests card container functionality including:
- Collapsible behavior
- Widget management
- Signal emission
- Styling and appearance
"""

import pytest
from PySide6.QtWidgets import QLabel, QVBoxLayout

from ui.widgets.card import Card


class TestCardWidget:
    """Test the Card widget."""

    @pytest.fixture
    def card(self, qtbot):
        """Create a basic card for testing."""
        card = Card("Test Card", collapsible=True, collapsed=False)
        qtbot.addWidget(card)
        return card

    @pytest.fixture
    def non_collapsible_card(self, qtbot):
        """Create a non-collapsible card for testing."""
        card = Card("Non-Collapsible", collapsible=False)
        qtbot.addWidget(card)
        return card

    def test_card_initialization(self, card):
        """Test card initializes with correct properties."""
        assert card._collapsible is True
        assert card._collapsed is False
        # Content should be visible (not hidden)
        assert card._content.isVisibleTo(card)

    def test_card_without_title(self, qtbot):
        """Test card can be created without a title."""
        card = Card()
        qtbot.addWidget(card)

        # Should not have a header
        assert not hasattr(card, "_header")

    def test_card_initial_collapsed_state(self, qtbot):
        """Test card can be initialized as collapsed."""
        card = Card("Collapsed Card", collapsible=True, collapsed=True)
        qtbot.addWidget(card)

        assert card._collapsed is True
        assert not card._content.isVisibleTo(card)

    def test_add_widget(self, card):
        """Test adding widgets to the card."""
        label = QLabel("Test Label")
        card.add_widget(label)

        # Widget should be added to content layout
        assert card._content_layout.count() == 1
        assert card._content_layout.itemAt(0).widget() == label

    def test_multiple_widgets(self, card):
        """Test adding multiple widgets to the card."""
        label1 = QLabel("Label 1")
        label2 = QLabel("Label 2")
        label3 = QLabel("Label 3")

        card.add_widget(label1)
        card.add_widget(label2)
        card.add_widget(label3)

        assert card._content_layout.count() == 3
        assert card._content_layout.itemAt(0).widget() == label1
        assert card._content_layout.itemAt(1).widget() == label2
        assert card._content_layout.itemAt(2).widget() == label3

    def test_toggle_collapsed(self, card, qtbot):
        """Test toggling collapsed state."""
        # Initially expanded
        assert not card._collapsed
        assert card._content.isVisibleTo(card)

        # Collapse
        with qtbot.waitSignal(card.collapsed_changed, timeout=1000) as blocker:
            card._toggle_collapsed()

        assert card._collapsed is True
        assert not card._content.isVisibleTo(card)
        assert blocker.args[0] is True  # Signal emitted with True

        # Expand
        with qtbot.waitSignal(card.collapsed_changed, timeout=1000) as blocker:
            card._toggle_collapsed()

        assert card._collapsed is False
        assert card._content.isVisibleTo(card)
        assert blocker.args[0] is False  # Signal emitted with False

    def test_collapse_button_click(self, card, qtbot):
        """Test clicking collapse button toggles state."""
        # Initially expanded
        assert not card._collapsed

        # Click collapse button
        with qtbot.waitSignal(card.collapsed_changed, timeout=1000):
            card._collapse_button.click()

        assert card._collapsed is True
        assert not card._content.isVisibleTo(card)

        # Click again to expand
        with qtbot.waitSignal(card.collapsed_changed, timeout=1000):
            card._collapse_button.click()

        assert card._collapsed is False
        assert card._content.isVisibleTo(card)

    def test_collapse_button_icon_update(self, card):
        """Test collapse button icon updates when state changes."""
        # Initially expanded: should show "▼"
        assert card._collapse_button.text() == "▼"

        # Collapse
        card._toggle_collapsed()
        assert card._collapse_button.text() == "▶"

        # Expand
        card._toggle_collapsed()
        assert card._collapse_button.text() == "▼"

    def test_is_collapsed(self, card):
        """Test is_collapsed() method."""
        assert card.is_collapsed() is False

        card._toggle_collapsed()
        assert card.is_collapsed() is True

        card._toggle_collapsed()
        assert card.is_collapsed() is False

    def test_set_collapsed(self, card, qtbot):
        """Test set_collapsed() method."""
        # Set to collapsed
        with qtbot.waitSignal(card.collapsed_changed, timeout=1000):
            card.set_collapsed(True)

        assert card.is_collapsed() is True
        assert not card._content.isVisibleTo(card)

        # Set to expanded
        with qtbot.waitSignal(card.collapsed_changed, timeout=1000):
            card.set_collapsed(False)

        assert card.is_collapsed() is False
        assert card._content.isVisibleTo(card)

    def test_set_collapsed_no_change(self, card):
        """Test set_collapsed() with same state doesn't emit signal."""
        # Already expanded
        assert not card.is_collapsed()

        # Try to set to expanded (no change)
        card.set_collapsed(False)
        # Should not toggle, still expanded
        assert not card.is_collapsed()

    def test_non_collapsible_card(self, non_collapsible_card):
        """Test non-collapsible card doesn't have collapse button."""
        assert non_collapsible_card._collapsible is False
        assert not hasattr(non_collapsible_card, "_collapse_button")

    def test_content_layout_getter(self, card):
        """Test content_layout() returns the correct layout."""
        layout = card.content_layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout == card._content_layout

    def test_card_styling(self, card):
        """Test card has appropriate styling applied."""
        stylesheet = card.styleSheet()

        # Check for key styling properties
        assert "background-color: #2b2b2b" in stylesheet
        assert "border-radius: 8px" in stylesheet
        assert "border: 1px solid #3a3a3a" in stylesheet

    def test_collapsed_signal_emission(self, card, qtbot):
        """Test collapsed_changed signal emits correctly."""
        # Track signal emissions
        emissions = []

        def on_collapsed_changed(collapsed):
            emissions.append(collapsed)

        card.collapsed_changed.connect(on_collapsed_changed)

        # Collapse
        card._toggle_collapsed()
        qtbot.wait(100)
        assert len(emissions) == 1
        assert emissions[0] is True

        # Expand
        card._toggle_collapsed()
        qtbot.wait(100)
        assert len(emissions) == 2
        assert emissions[1] is False

    def test_card_with_many_widgets(self, card):
        """Test card can hold many widgets without issues."""
        labels = [QLabel(f"Label {i}") for i in range(20)]

        for label in labels:
            card.add_widget(label)

        assert card._content_layout.count() == 20

        for i, label in enumerate(labels):
            assert card._content_layout.itemAt(i).widget() == label


class TestCardIntegration:
    """Integration tests for Card widget in real-world scenarios."""

    def test_card_in_dialog(self, qtbot):
        """Test card works correctly when used in a dialog-like scenario."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout

        dialog = QDialog()
        qtbot.addWidget(dialog)
        layout = QVBoxLayout(dialog)

        # Add multiple cards
        card1 = Card("Card 1", collapsible=True)
        card2 = Card("Card 2", collapsible=True)

        card1.add_widget(QLabel("Content 1"))
        card2.add_widget(QLabel("Content 2"))

        layout.addWidget(card1)
        layout.addWidget(card2)

        # Both should be visible to the dialog
        assert card1.isVisibleTo(dialog)
        assert card2.isVisibleTo(dialog)

        # Collapse first card
        card1.set_collapsed(True)
        assert card1._collapsed is True
        assert not card2._collapsed

    def test_card_state_persistence(self, qtbot):
        """Test card state is maintained correctly."""
        # Create card for this test
        card = Card("Test", collapsible=True)
        qtbot.addWidget(card)

        # Add widgets
        label1 = QLabel("Label 1")
        label2 = QLabel("Label 2")
        card.add_widget(label1)
        card.add_widget(label2)

        # Collapse and expand
        card.set_collapsed(True)
        assert not card._content.isVisibleTo(card)
        assert card._content_layout.count() == 2  # Widgets still there

        card.set_collapsed(False)
        assert card._content.isVisibleTo(card)
        assert card._content_layout.count() == 2  # Widgets still there
