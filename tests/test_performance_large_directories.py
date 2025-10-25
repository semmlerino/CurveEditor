#!/usr/bin/env python
"""
Performance tests for large directory handling.

Tests thumbnail generation, directory scanning, and memory usage
with large numbers of image sequences.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from core.directory_scan_worker import DirectoryScanWorker, ThumbnailCache
from ui.widgets.sequence_preview_widget import ThumbnailLoader


class TestPerformanceLargeDirectories:
    """Performance tests for large directory operations."""
    
    @pytest.fixture
    def qapp(self):
        """Ensure QApplication exists."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def large_image_directory(self):
        """Create directory with many image sequences for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple sequences with many frames each
            for seq_num in range(10):  # 10 sequences
                for frame in range(1, 101):  # 100 frames each = 1000 total files
                    image_file = temp_path / f"seq_{seq_num:02d}_{frame:04d}.jpg"
                    # Create small fake image files
                    image_file.write_bytes(b"fake_image_data" * 100)  # ~1.5KB each
            
            yield str(temp_path)
    
    @pytest.mark.performance
    def test_directory_scan_performance(self, large_image_directory):
        """Test directory scanning performance with 1000+ files."""
        start_time = time.perf_counter()
        
        # Create and run directory scanner
        scanner = DirectoryScanWorker(large_image_directory)
        
        sequences_found = []
        errors = []
        
        def on_sequences_found(sequences):
            sequences_found.extend(sequences)
        
        def on_error(error):
            errors.append(error)
        
        scanner.sequences_found.connect(on_sequences_found, Qt.DirectConnection)
        scanner.error_occurred.connect(on_error)
        
        # Run scanner synchronously for testing
        scanner.run()
        
        end_time = time.perf_counter()
        scan_duration = end_time - start_time
        
        # Performance assertions
        assert scan_duration < 5.0, f"Directory scan took too long: {scan_duration:.2f}s"
        assert len(errors) == 0, f"Scan errors occurred: {errors}"
        assert len(sequences_found) == 10, f"Expected 10 sequences, found {len(sequences_found)}"
        
        # Verify sequences were detected correctly
        for sequence in sequences_found:
            assert len(sequence['frames']) == 100, f"Expected 100 frames, got {len(sequence['frames'])}"
        
        print(f"Scanned {len(sequences_found)} sequences with 1000 files in {scan_duration:.2f}s")
    
    @pytest.mark.performance
    @pytest.mark.performance
    def test_thumbnail_generation_performance(self, qapp):
        """Test thumbnail generation performance with many images."""
        # Create mock image files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create 50 test images
            image_files = []
            for i in range(50):
                image_file = temp_path / f"test_{i:03d}.jpg"
                
                # Create a small test image using QPixmap
                pixmap = QPixmap(100, 100)
                pixmap.fill()
                pixmap.save(str(image_file), "JPEG")
                image_files.append(str(image_file))
            
            # Test thumbnail loading performance
            loader = ThumbnailLoader()
            
            thumbnails_loaded = []
            errors = []
            
            def on_thumbnail_loaded(frame_num, pixmap):
                thumbnails_loaded.append((frame_num, pixmap))
            
            def on_thumbnail_error(frame_num, error):
                errors.append((frame_num, error))
            
            loader.thumbnail_loaded.connect(on_thumbnail_loaded, Qt.DirectConnection)
            loader.thumbnail_error.connect(on_thumbnail_error, Qt.DirectConnection)
            
            start_time = time.perf_counter()
            
            # Add all images to loading queue
            for i, image_file in enumerate(image_files):
                loader.add_thumbnail_request(i, image_file)
            
            # Start loading
            loader.start()
            
            # Wait for completion while processing Qt events
            # (required for Python signal callbacks to be invoked)
            timeout_ms = 10000
            elapsed = 0
            interval = 10  # Process events every 10ms
            
            while loader.isRunning() and elapsed < timeout_ms:
                qapp.processEvents()
                time.sleep(interval / 1000.0)
                elapsed += interval
            
            # Ensure thread finished
            loader.wait(1000)
            
            end_time = time.perf_counter()
            load_duration = end_time - start_time
            
            # Performance assertions
            assert load_duration < 5.0, f"Thumbnail loading took too long: {load_duration:.2f}s"
            assert len(errors) == 0, f"Thumbnail errors occurred: {errors}"
            assert len(thumbnails_loaded) == 50, f"Expected 50 thumbnails, got {len(thumbnails_loaded)}"
            
            # Verify thumbnails are valid
            for frame_num, pixmap in thumbnails_loaded:
                assert not pixmap.isNull(), f"Invalid thumbnail for frame {frame_num}"
            
            avg_time_per_thumbnail = load_duration / len(thumbnails_loaded)
            print(f"Generated {len(thumbnails_loaded)} thumbnails in {load_duration:.2f}s "
                  f"({avg_time_per_thumbnail*1000:.1f}ms per thumbnail)")

    @pytest.mark.performance
    def test_thumbnail_cache_performance(self):
        """Test thumbnail cache performance with many items."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "cache"
            cache = ThumbnailCache(cache_dir=cache_dir, max_items=1000)
            
            # Create test pixmaps
            test_pixmaps = []
            for i in range(100):
                pixmap = QPixmap(150, 150)
                pixmap.fill()
                test_pixmaps.append(pixmap)
            
            # Test cache write performance
            start_time = time.perf_counter()
            
            for i, pixmap in enumerate(test_pixmaps):
                cache.put(f"/test/image_{i:03d}.jpg", pixmap)
            
            write_time = time.perf_counter() - start_time
            
            # Test cache read performance
            start_time = time.perf_counter()
            
            cache_hits = 0
            for i in range(100):
                result = cache.get(f"/test/image_{i:03d}.jpg")
                if result is not None:
                    cache_hits += 1
            
            read_time = time.perf_counter() - start_time
            
            # Performance assertions
            assert write_time < 2.0, f"Cache writes took too long: {write_time:.2f}s"
            assert read_time < 0.5, f"Cache reads took too long: {read_time:.2f}s"
            assert cache_hits == 100, f"Expected 100 cache hits, got {cache_hits}"
            
            print(f"Cache write: {write_time:.2f}s, read: {read_time:.2f}s, hits: {cache_hits}/100")
    
    @pytest.mark.performance
    def test_memory_usage_large_sequences(self, qapp):
        """Test memory usage with large sequence lists."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many sequences
        from ui.image_sequence_browser import ImageSequence
        
        sequences = []
        for seq_num in range(100):  # 100 sequences
            sequence = ImageSequence(
                base_name=f"seq_{seq_num:03d}_",
                padding=4,
                extension=".exr",
                frames=list(range(1, 101)),  # 100 frames each
                file_list=[f"seq_{seq_num:03d}_{frame:04d}.exr" for frame in range(1, 101)],
                directory=f"/test/sequences/seq_{seq_num:03d}",
                resolution=(1920, 1080),
                total_size_bytes=100 * 1024 * 1024  # 100MB per sequence
            )
            sequences.append(sequence)
        
        # Create sequence list widget and populate it
        from ui.widgets.sequence_list_widget import SequenceListWidget
        
        sequence_widget = SequenceListWidget()
        sequence_widget.set_sequences(sequences)
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        # Memory usage assertions
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.1f}MB increase"
        assert len(sequence_widget._sequences) == 100, "Not all sequences were loaded"
        
        print(f"Memory usage with 100 sequences (10,000 frames): {memory_increase:.1f}MB increase")
        
        # Test filtering performance with large dataset
        start_time = time.perf_counter()
        sequence_widget.filter_sequences("seq_05")
        filter_time = time.perf_counter() - start_time
        
        assert filter_time < 0.1, f"Filtering took too long: {filter_time:.3f}s"
        
        visible_count = sequence_widget.get_visible_sequence_count()
        assert visible_count == 10, f"Expected 10 filtered sequences, got {visible_count}"  # seq_050-059
        
        print(f"Filtered 100 sequences in {filter_time*1000:.1f}ms")
    
    @pytest.mark.performance
    @pytest.mark.performance
    def test_concurrent_operations_performance(self, qapp):
        """Test performance with concurrent scanning and thumbnail generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test directory with sequences
            for seq_num in range(5):
                for frame in range(1, 21):  # 20 frames per sequence
                    image_file = temp_path / f"seq_{seq_num:02d}_{frame:04d}.jpg"
                    
                    # Create small test image
                    pixmap = QPixmap(100, 100)
                    pixmap.fill()
                    pixmap.save(str(image_file), "JPEG")
            
            start_time = time.perf_counter()
            
            # Start directory scanner
            scanner = DirectoryScanWorker(str(temp_path))
            
            sequences_found = []
            scan_complete = False
            
            def on_sequences_found(sequences):
                sequences_found.extend(sequences)
            
            def on_scan_finished():
                nonlocal scan_complete
                scan_complete = True
            
            scanner.sequences_found.connect(on_sequences_found, Qt.DirectConnection)
            scanner.finished.connect(on_scan_finished, Qt.DirectConnection)
            
            scanner.start()
            
            # Start thumbnail loader concurrently
            loader = ThumbnailLoader()
            thumbnails_loaded = []
            
            def on_thumbnail_loaded(frame_num, pixmap):
                thumbnails_loaded.append((frame_num, pixmap))
            
            loader.thumbnail_loaded.connect(on_thumbnail_loaded, Qt.DirectConnection)
            
            # Add some thumbnail requests
            for i in range(10):
                image_file = temp_path / f"seq_00_{i+1:04d}.jpg"
                loader.add_thumbnail_request(i, str(image_file))
            
            loader.start()
            
            # Wait for both operations while processing Qt events
            # (required for Python signal callbacks to be invoked)
            timeout_ms = 5000
            elapsed = 0
            interval = 10  # Process events every 10ms
            
            while (scanner.isRunning() or loader.isRunning()) and elapsed < timeout_ms:
                qapp.processEvents()
                time.sleep(interval / 1000.0)
                elapsed += interval
            
            # Ensure both threads finished
            scanner.wait(1000)
            loader.wait(1000)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Performance assertions
            assert total_time < 3.0, f"Concurrent operations took too long: {total_time:.2f}s"
            assert len(sequences_found) == 5, f"Expected 5 sequences, found {len(sequences_found)}"
            assert len(thumbnails_loaded) == 10, f"Expected 10 thumbnails, got {len(thumbnails_loaded)}"
            
            print(f"Concurrent scan + thumbnail generation: {total_time:.2f}s")

    @pytest.mark.performance
    def test_ui_responsiveness_large_dataset(self, qapp):
        """Test UI responsiveness with large datasets."""
        from ui.widgets.simple_sequence_browser import SimpleSequenceBrowser
        from ui.image_sequence_browser import ImageSequence
        
        # Create large dataset
        sequences = []
        for i in range(200):  # 200 sequences
            sequence = ImageSequence(
                base_name=f"large_seq_{i:03d}_",
                padding=4,
                extension=".dpx",
                frames=list(range(1, 51)),  # 50 frames each
                file_list=[f"large_seq_{i:03d}_{frame:04d}.dpx" for frame in range(1, 51)],
                directory=f"/large/dataset/seq_{i:03d}",
                resolution=(2048, 1556),
                total_size_bytes=50 * 10 * 1024 * 1024  # 500MB per sequence
            )
            sequences.append(sequence)
        
        browser = SimpleSequenceBrowser()
        
        # Test UI update performance
        start_time = time.perf_counter()
        browser.set_sequences(sequences)
        update_time = time.perf_counter() - start_time
        
        assert update_time < 1.0, f"UI update took too long: {update_time:.2f}s"
        
        # Test filtering performance
        start_time = time.perf_counter()
        browser.filter_sequences("seq_1")  # Should match seq_100-199
        filter_time = time.perf_counter() - start_time
        
        assert filter_time < 0.2, f"Filtering took too long: {filter_time:.3f}s"
        
        visible_count = browser.sequence_list.get_visible_sequence_count()
        expected_matches = len([s for s in sequences if "seq_1" in s.base_name])
        assert visible_count == expected_matches, f"Filter results incorrect: {visible_count} vs {expected_matches}"
        
        print(f"UI update with 200 sequences: {update_time:.2f}s, filter: {filter_time*1000:.1f}ms")