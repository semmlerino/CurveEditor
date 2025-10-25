#!/usr/bin/env python
"""
Unit tests for ProgressiveDisclosureController.

Tests mode switching, state preservation, and animation handling.
"""

import pytest
from unittest.mock import Mock, MagicMock

from PySide6.QtWidgets import QWidget, QSplitter

from ui.controllers.progressive_disclosure_controller import ProgressiveDisclosureController


class TestProgressiveDisclosureController:
    """Test ProgressiveDisclosureController functionality."""
    
    @pytest.fixture
    def mock_widgets(self):
        """Create mock widgets for testing."""
        simple_widget = Mock(spec=QWidget)
        simple_widget.setVisible = Mock()
        simple_widget.resize = Mock()
        simple_widget.width.return_value = 800
        simple_widget.height.return_value = 600
        
        advanced_widget = Mock(spec=QWidget)
        advanced_widget.setVisible = Mock()
        advanced_widget.resize = Mock()
        advanced_widget.width.return_value = 1200
        advanced_widget.height.return_value = 800
        
        splitter = Mock(spec=QSplitter)
        splitter.sizes.return_value = [300, 400, 500]
        splitter.setSizes = Mock()
        
        return simple_widget, advanced_widget, splitter
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager."""
        from core.user_preferences import UserPreferences
        
        state_manager = Mock()
        preferences = UserPreferences()
        state_manager.get_user_preferences.return_value = preferences
        state_manager.save_user_preferences = Mock()
        state_manager.set_project_context = Mock()
        
        return state_manager
    
    def test_initialization_simple_mode(self, mock_widgets, mock_state_manager):
        """Test initialization in simple mode."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        assert controller.get_current_mode() == "simple"
        simple_widget.setVisible.assert_called_with(True)
        advanced_widget.setVisible.assert_called_with(False)
    
    def test_initialization_advanced_mode(self, mock_widgets, mock_state_manager):
        """Test initialization in advanced mode."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        # Set preference to advanced mode
        preferences = mock_state_manager.get_user_preferences.return_value
        preferences.interface_mode = "advanced"
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        assert controller.get_current_mode() == "advanced"
        simple_widget.setVisible.assert_called_with(False)
        advanced_widget.setVisible.assert_called_with(True)
    
    def test_set_mode_immediate(self, mock_widgets, mock_state_manager):
        """Test immediate mode switching without animation."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        # Switch to advanced mode
        controller.set_mode("advanced", animate=False)
        
        assert controller.get_current_mode() == "advanced"
        simple_widget.setVisible.assert_called_with(False)
        advanced_widget.setVisible.assert_called_with(True)
    
    def test_toggle_mode(self, mock_widgets, mock_state_manager):
        """Test mode toggling."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        # Start in simple mode
        assert controller.get_current_mode() == "simple"
        
        # Toggle to advanced
        controller.toggle_mode(animate=False)
        assert controller.get_current_mode() == "advanced"
        
        # Toggle back to simple
        controller.toggle_mode(animate=False)
        assert controller.get_current_mode() == "simple"
    
    def test_invalid_mode_ignored(self, mock_widgets, mock_state_manager):
        """Test that invalid mode is ignored."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        original_mode = controller.get_current_mode()
        
        # Try to set invalid mode
        controller.set_mode("invalid_mode", animate=False)
        
        # Mode should remain unchanged
        assert controller.get_current_mode() == original_mode
    
    def test_same_mode_ignored(self, mock_widgets, mock_state_manager):
        """Test that setting same mode is ignored."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        # Reset mock call counts
        simple_widget.setVisible.reset_mock()
        advanced_widget.setVisible.reset_mock()
        
        # Set to same mode (simple)
        controller.set_mode("simple", animate=False)
        
        # Should not call setVisible again
        simple_widget.setVisible.assert_not_called()
        advanced_widget.setVisible.assert_not_called()
    
    def test_preserve_and_restore_state(self, mock_widgets, mock_state_manager):
        """Test state preservation and restoration."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        # Preserve current state
        state = controller.preserve_state()
        
        assert isinstance(state, dict)
        assert "mode" in state
        assert state["mode"] == "simple"
        
        # Switch mode
        controller.set_mode("advanced", animate=False)
        assert controller.get_current_mode() == "advanced"
        
        # Restore state
        controller.restore_state(state)
        assert controller.get_current_mode() == "simple"
    
    def test_animation_duration_setting(self, mock_widgets, mock_state_manager):
        """Test setting animation duration."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        # Test valid duration
        controller.set_animation_duration(500)
        assert controller._animation_duration == 500
        
        # Test clamping to minimum
        controller.set_animation_duration(50)
        assert controller._animation_duration == 100  # Clamped to minimum
        
        # Test clamping to maximum
        controller.set_animation_duration(2000)
        assert controller._animation_duration == 1000  # Clamped to maximum
    
    def test_recommended_mode_for_context(self, mock_widgets, mock_state_manager):
        """Test recommended mode based on context."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        # Simple case: few sequences with recent dirs
        mode = controller.get_recommended_mode_for_context(
            sequence_count=3,
            has_recent_dirs=True
        )
        assert mode == "simple"
        
        # Complex case: many sequences
        mode = controller.get_recommended_mode_for_context(
            sequence_count=25,
            has_recent_dirs=True
        )
        assert mode == "advanced"
        
        # Medium case: falls back to user preference
        mode = controller.get_recommended_mode_for_context(
            sequence_count=10,
            has_recent_dirs=False
        )
        # Should return user preference (simple by default)
        assert mode == "simple"
    
    def test_mode_preference_saved(self, mock_widgets, mock_state_manager):
        """Test that mode preference is saved."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=mock_state_manager
        )
        
        # Switch mode
        controller.set_mode("advanced", animate=False)
        
        # Verify preference was saved
        mock_state_manager.save_user_preferences.assert_called()
        
        # Check that preference was updated
        preferences = mock_state_manager.get_user_preferences.return_value
        assert preferences.interface_mode == "advanced"
    
    def test_no_state_manager_works(self, mock_widgets):
        """Test that controller works without state manager."""
        simple_widget, advanced_widget, splitter = mock_widgets
        
        controller = ProgressiveDisclosureController(
            simple_widget=simple_widget,
            advanced_widget=advanced_widget,
            splitter=splitter,
            state_manager=None
        )
        
        # Should default to simple mode
        assert controller.get_current_mode() == "simple"
        
        # Mode switching should still work
        controller.set_mode("advanced", animate=False)
        assert controller.get_current_mode() == "advanced"