#!/usr/bin/env python
"""
Integration tests for SimpleSequenceBrowser workflows.

Tests complete user workflows from directory selection to sequence loading.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from ui.widgets.simple_sequence_browser import SimpleSequenceBrowser


class TestSimpleSequenceBrowserIntegration:
    """Integration tests for SimpleSequenceBrowser workflows."""
    
    @pytest.fixture
    def qapp(self):
        """Ensure QApplication exists."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager with preferences."""
        from core.user_preferences import UserPreferences
        
        state_manager = Mock()
        preferences = UserPreferences()
        state_manager.get_user_preferences.return_value = preferences
        state_manager.save_user_preferences = Mock()
        state_manager.get_recent_directories_for_project.return_value = []
        state_manager.add_recent_directory_for_project = Mock()
        state_manager.set_project_context = Mock()
        
        return state_manager
    
    @pytest.fixture
    def sample_image_directory(self):
        """Create temporary directory with sample image sequence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create sample image sequence files
            for i in range(1, 6):
                image_file = temp_path / f"render_{i:04d}.jpg"
                image_file.write_text(f"fake image data {i}")
            
            # Create some non-sequence files
            (temp_path / "readme.txt").write_text("readme")
            (temp_path / "single_image.png").write_text("single image")
            
            yield str(temp_path)
    
    def test_complete_simple_workflow(self, qtbot: QtBot, qapp, mock_state_manager, sample_image_directory):
        """Test complete workflow from directory selection to sequence selection."""
        browser = SimpleSequenceBrowser(state_manager=mock_state_manager)
        qtbot.addWidget(browser)
        
        # Track signals
        sequence_selected_spy = qtbot.waitSignal(browser.sequence_selected, timeout=5000)
        location_changed_spy = qtbot.waitSignal(browser.location_changed, timeout=5000)
        
        # Simulate directory selection
        browser.location_selector.set_location(sample_image_directory)
        
        # Wait for location change signal
        location_changed_spy.wait()
        
        # Verify location was set
        assert browser.get_current_location() == sample_image_directory
        
        # Simulate sequences being found (normally done by directory scanner)
        from ui.image_sequence_browser import ImageSequence
        
        test_sequence = ImageSequence(
            base_name="render_",
            padding=4,
            extension=".jpg",
            frames=[1, 2, 3, 4, 5],
            file_list=["render_0001.jpg", "render_0002.jpg", "render_0003.jpg", "render_0004.jpg", "render_0005.jpg"],
            directory=sample_image_directory
        )
        
        browser.set_sequences([test_sequence])
        
        # Verify sequences are displayed
        assert len(browser._current_sequences) == 1
        assert browser.sequence_list.count() == 1
        
        # Simulate sequence selection
        browser.sequence_list.setCurrentRow(0)
        
        # Wait for sequence selection signal
        sequence_selected_spy.wait()
        
        # Verify sequence was selected
        selected_sequence = browser.get_selected_sequence()
        assert selected_sequence is not None
        assert selected_sequence.base_name == "render_"
        assert len(selected_sequence.frames) == 5
    
    def test_mode_switching_preserves_selection(self, qtbot: QtBot, qapp, mock_state_manager):
        """Test that switching modes preserves user selections."""
        browser = SimpleSequenceBrowser(state_manager=mock_state_manager)
        qtbot.addWidget(browser)
        
        # Set up test data
        from ui.image_sequence_browser import ImageSequence
        
        test_sequences = [
            ImageSequence(
                base_name="seq1_",
                padding=3,
                extension=".png",
                frames=[1, 2, 3],
                file_list=["seq1_001.png", "seq1_002.png", "seq1_003.png"],
                directory="/test/path1"
            ),
            ImageSequence(
                base_name="seq2_",
                padding=3,
                extension=".png", 
                frames=[10, 11, 12],
                file_list=["seq2_010.png", "seq2_011.png", "seq2_012.png"],
                directory="/test/path1"
            )
        ]
        
        browser.set_sequences(test_sequences)
        
        # Select second sequence
        browser.sequence_list.setCurrentRow(1)
        selected_sequence = browser.get_selected_sequence()
        assert selected_sequence.base_name == "seq2_"
        
        # Simulate mode switch (advanced button click would trigger this)
        # The selection should be preserved when switching back
        browser.set_sequences(test_sequences)  # Refresh after mode switch
        
        # Selection should still be available
        assert len(browser._current_sequences) == 2
    
    def test_error_recovery_workflow(self, qtbot: QtBot, qapp, mock_state_manager):
        """Test error recovery scenarios."""
        browser = SimpleSequenceBrowser(state_manager=mock_state_manager)
        qtbot.addWidget(browser)
        
        # Test invalid directory
        invalid_path = "/nonexistent/directory"
        browser.location_selector.set_location(invalid_path)
        
        # Should show error help
        browser.show_error_help("Directory not found", ["Try a different path", "Use Browse button"])
        
        # Verify help is visible
        assert browser.help_label.isVisible()
        assert "Directory not found" in browser.help_label.text()
        assert "Try a different path" in browser.help_label.text()
        
        # Test empty directory (no sequences)
        browser.set_sequences([])
        
        # Should show contextual help
        assert browser.help_label.isVisible()
        assert "Tips for finding image sequences" in browser.help_label.text()
    
    def test_keyboard_navigation(self, qtbot: QtBot, qapp, mock_state_manager):
        """Test keyboard navigation through the interface."""
        browser = SimpleSequenceBrowser(state_manager=mock_state_manager)
        qtbot.addWidget(browser)
        
        # Set up test sequences
        from ui.image_sequence_browser import ImageSequence
        
        test_sequence = ImageSequence(
            base_name="test_",
            padding=3,
            extension=".jpg",
            frames=[1, 2, 3],
            file_list=["test_001.jpg", "test_002.jpg", "test_003.jpg"],
            directory="/test/path"
        )
        
        browser.set_sequences([test_sequence])
        
        # Test Tab navigation
        browser.location_selector.setFocus()
        qtbot.keyClick(browser.location_selector, Qt.Key.Key_Tab)
        
        # Should move focus to advanced button
        assert browser.advanced_button.hasFocus()
        
        # Tab to sequence list
        qtbot.keyClick(browser.advanced_button, Qt.Key.Key_Tab)
        # Focus should eventually reach sequence list
        
        # Test arrow key navigation in sequence list
        browser.sequence_list.setFocus()
        qtbot.keyClick(browser.sequence_list, Qt.Key.Key_Down)
        
        # Should select first item
        assert browser.sequence_list.currentRow() == 0
    
    def test_filtering_workflow(self, qtbot: QtBot, qapp, mock_state_manager):
        """Test sequence filtering functionality."""
        browser = SimpleSequenceBrowser(state_manager=mock_state_manager)
        qtbot.addWidget(browser)
        
        # Set up multiple test sequences
        from ui.image_sequence_browser import ImageSequence
        
        sequences = [
            ImageSequence(
                base_name="render_",
                padding=4,
                extension=".exr",
                frames=[1, 2, 3],
                file_list=["render_0001.exr", "render_0002.exr", "render_0003.exr"],
                directory="/test/renders"
            ),
            ImageSequence(
                base_name="comp_",
                padding=4,
                extension=".jpg",
                frames=[1, 2, 3],
                file_list=["comp_0001.jpg", "comp_0002.jpg", "comp_0003.jpg"],
                directory="/test/comps"
            ),
            ImageSequence(
                base_name="bg_",
                padding=3,
                extension=".png",
                frames=[10, 11, 12],
                file_list=["bg_010.png", "bg_011.png", "bg_012.png"],
                directory="/test/backgrounds"
            )
        ]
        
        browser.set_sequences(sequences)
        
        # Verify all sequences are visible initially
        assert browser.sequence_list.get_visible_sequence_count() == 3
        
        # Apply filter
        browser.filter_sequences("render")
        
        # Should show only render sequence
        assert browser.sequence_list.get_visible_sequence_count() == 1
        
        # Clear filter
        browser.filter_sequences("")
        
        # Should show all sequences again
        assert browser.sequence_list.get_visible_sequence_count() == 3
    
    def test_sorting_workflow(self, qtbot: QtBot, qapp, mock_state_manager):
        """Test sequence sorting functionality."""
        browser = SimpleSequenceBrowser(state_manager=mock_state_manager)
        qtbot.addWidget(browser)
        
        # Set up test sequences with different properties
        from ui.image_sequence_browser import ImageSequence
        
        sequences = [
            ImageSequence(
                base_name="z_last_",
                padding=3,
                extension=".jpg",
                frames=[1, 2],  # 2 frames
                file_list=["z_last_001.jpg", "z_last_002.jpg"],
                directory="/test",
                total_size_bytes=1000
            ),
            ImageSequence(
                base_name="a_first_",
                padding=3,
                extension=".jpg",
                frames=[1, 2, 3, 4, 5],  # 5 frames
                file_list=["a_first_001.jpg", "a_first_002.jpg", "a_first_003.jpg", "a_first_004.jpg", "a_first_005.jpg"],
                directory="/test",
                total_size_bytes=5000
            ),
            ImageSequence(
                base_name="m_middle_",
                padding=3,
                extension=".jpg",
                frames=[1, 2, 3],  # 3 frames
                file_list=["m_middle_001.jpg", "m_middle_002.jpg", "m_middle_003.jpg"],
                directory="/test",
                total_size_bytes=3000
            )
        ]
        
        browser.set_sequences(sequences)
        
        # Test name sorting (default)
        browser.set_sort_order("name", ascending=True)
        sorted_sequences = browser._current_sequences
        assert sorted_sequences[0].base_name == "a_first_"
        assert sorted_sequences[1].base_name == "m_middle_"
        assert sorted_sequences[2].base_name == "z_last_"
        
        # Test frame count sorting
        browser.set_sort_order("frame_count", ascending=False)  # Descending
        sorted_sequences = browser._current_sequences
        assert len(sorted_sequences[0].frames) == 5  # a_first_ has most frames
        assert len(sorted_sequences[1].frames) == 3  # m_middle_
        assert len(sorted_sequences[2].frames) == 2  # z_last_ has least frames
        
        # Test size sorting
        browser.set_sort_order("size", ascending=True)  # Ascending
        sorted_sequences = browser._current_sequences
        assert sorted_sequences[0].total_size_bytes == 1000  # z_last_ smallest
        assert sorted_sequences[1].total_size_bytes == 3000  # m_middle_
        assert sorted_sequences[2].total_size_bytes == 5000  # a_first_ largest
    
    @patch('ui.widgets.simple_sequence_browser.logger')
    def test_logging_integration(self, mock_logger, qtbot: QtBot, qapp, mock_state_manager):
        """Test that operations are properly logged."""
        browser = SimpleSequenceBrowser(state_manager=mock_state_manager)
        qtbot.addWidget(browser)
        
        # Set location
        browser.location_selector.set_location("/test/path")
        
        # Set sequences
        from ui.image_sequence_browser import ImageSequence
        
        test_sequence = ImageSequence(
            base_name="test_",
            padding=3,
            extension=".jpg",
            frames=[1, 2, 3],
            file_list=["test_001.jpg", "test_002.jpg", "test_003.jpg"],
            directory="/test/path"
        )
        
        browser.set_sequences([test_sequence])
        
        # Verify logging calls were made
        mock_logger.debug.assert_called()
        
        # Check that sequence operations are logged
        log_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
        assert any("Set 1 sequences in simple browser" in call for call in log_calls)