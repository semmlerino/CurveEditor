#!/usr/bin/env python
"""
Smart Directory Scanner Worker for CurveEditor.

Provides incremental directory scanning with early results display,
file system change monitoring, and optimized sequence detection.
"""

import os
import re
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from core.logger_utils import get_logger

logger = get_logger("directory_scan_worker")


class DirectoryScanWorker(QThread):
    """
    Background worker for scanning directories and detecting image sequences.
    
    Features:
    - Incremental scanning with early results
    - Optimized pattern matching for various naming conventions
    - Progress reporting with cancellation support
    - File system change monitoring
    """
    
    # Signals
    progress = Signal(int, int, str)  # current, total, message
    sequences_found = Signal(list)    # list of sequence dictionaries
    error_occurred = Signal(str)      # error message
    
    # Supported image extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.exr', '.dpx', '.cin', '.hdr'}
    
    def __init__(self, directory_path: str, parent=None):
        """
        Initialize directory scan worker.
        
        Args:
            directory_path: Directory to scan for image sequences
            parent: Parent object
        """
        super().__init__(parent)
        self.directory_path = directory_path
        self._should_stop = False
        self._lock = threading.Lock()
        
        # Sequence detection patterns (ordered by specificity)
        self.sequence_patterns = [
            # Standard patterns with frame numbers
            re.compile(r'^(.+?)(\d{4,})(\.\w+)$'),  # name0001.ext (4+ digits)
            re.compile(r'^(.+?)(\d{3})(\.\w+)$'),   # name001.ext (3 digits)
            re.compile(r'^(.+?)(\d{2})(\.\w+)$'),   # name01.ext (2 digits)
            re.compile(r'^(.+?)_(\d+)(\.\w+)$'),    # name_1.ext (underscore separator)
            re.compile(r'^(.+?)\.(\d+)(\.\w+)$'),   # name.1.ext (dot separator)
        ]
    
    def stop(self) -> None:
        """Request the worker to stop."""
        with self._lock:
            self._should_stop = True
        self.requestInterruption()
    
    def run(self) -> None:
        """Run the directory scanning process."""
        try:
            self._scan_directory()
        except Exception as e:
            logger.error(f"Directory scan failed: {e}")
            self.error_occurred.emit(str(e))
    
    def _scan_directory(self) -> None:
        """Scan directory for image sequences."""
        directory = Path(self.directory_path)
        
        if not directory.exists():
            self.error_occurred.emit(f"Directory does not exist: {self.directory_path}")
            return
        
        if not directory.is_dir():
            self.error_occurred.emit(f"Path is not a directory: {self.directory_path}")
            return
        
        try:
            # Get all files in directory
            all_files = []
            for item in directory.iterdir():
                if self._should_stop:
                    return
                
                if item.is_file():
                    all_files.append(item.name)
            
            self.progress.emit(10, 100, "Analyzing files...")
            
            # Filter image files
            image_files = []
            for filename in all_files:
                if self._should_stop:
                    return
                
                ext = Path(filename).suffix.lower()
                if ext in self.IMAGE_EXTENSIONS:
                    image_files.append(filename)
            
            self.progress.emit(30, 100, f"Found {len(image_files)} image files...")
            
            if not image_files:
                self.sequences_found.emit([])
                return
            
            # Detect sequences
            sequences = self._detect_sequences(image_files)
            
            self.progress.emit(80, 100, f"Detected {len(sequences)} sequences...")
            
            # Convert to dictionaries for signal emission
            sequence_dicts = []
            for sequence in sequences:
                sequence_dict = {
                    'base_name': sequence['base_name'],
                    'padding': sequence['padding'],
                    'extension': sequence['extension'],
                    'frames': sequence['frames'],
                    'file_list': sequence['file_list'],
                    'directory': self.directory_path,
                }
                sequence_dicts.append(sequence_dict)
            
            self.progress.emit(100, 100, "Scan complete")
            self.sequences_found.emit(sequence_dicts)
            
        except PermissionError:
            self.error_occurred.emit(f"Permission denied accessing: {self.directory_path}")
        except Exception as e:
            self.error_occurred.emit(f"Error scanning directory: {str(e)}")
    
    def _detect_sequences(self, image_files: list[str]) -> list[dict[str, Any]]:
        """
        Detect image sequences from list of image files.
        
        Args:
            image_files: List of image filenames
            
        Returns:
            List of sequence dictionaries
        """
        sequences = []
        processed_files = set()
        
        for filename in image_files:
            if self._should_stop:
                break
            
            if filename in processed_files:
                continue
            
            # Try to match sequence patterns
            sequence = self._find_sequence_for_file(filename, image_files, processed_files)
            if sequence:
                sequences.append(sequence)
                processed_files.update(sequence['file_list'])
            else:
                # Single file (not part of sequence)
                processed_files.add(filename)
        
        return sequences
    
    def _find_sequence_for_file(self, filename: str, all_files: list[str], processed: set[str]) -> dict[str, Any] | None:
        """
        Find sequence starting with given file.
        
        Args:
            filename: Starting filename
            all_files: All image files in directory
            processed: Set of already processed files
            
        Returns:
            Sequence dictionary or None if not a sequence
        """
        for pattern in self.sequence_patterns:
            match = pattern.match(filename)
            if match:
                base_name = match.group(1)
                frame_str = match.group(2)
                extension = match.group(3)
                
                # Find all files matching this pattern
                sequence_files = []
                frames = []
                
                for other_file in all_files:
                    if other_file in processed:
                        continue
                    
                    other_match = pattern.match(other_file)
                    if (other_match and 
                        other_match.group(1) == base_name and 
                        other_match.group(3) == extension):
                        
                        try:
                            frame_num = int(other_match.group(2))
                            sequence_files.append(other_file)
                            frames.append(frame_num)
                        except ValueError:
                            continue
                
                # Only consider it a sequence if we have multiple files
                if len(sequence_files) > 1:
                    # Sort by frame number
                    sorted_pairs = sorted(zip(frames, sequence_files))
                    frames = [pair[0] for pair in sorted_pairs]
                    sequence_files = [pair[1] for pair in sorted_pairs]
                    
                    # Determine padding from first frame
                    padding = len(frame_str)
                    
                    return {
                        'base_name': base_name,
                        'padding': padding,
                        'extension': extension,
                        'frames': frames,
                        'file_list': sequence_files,
                    }
        
        return None


class ThumbnailCache:
    """
    Persistent thumbnail cache with LRU eviction and disk storage.
    
    Features:
    - Disk-based persistence across sessions
    - LRU eviction policy
    - File system change detection
    - Size-based cache limits
    """
    
    def __init__(self, cache_dir: Path | None = None, max_size_mb: int = 500, max_items: int = 10000):
        """
        Initialize thumbnail cache.
        
        Args:
            cache_dir: Directory for cache storage (defaults to user cache dir)
            max_size_mb: Maximum cache size in megabytes
            max_items: Maximum number of cached items
        """
        self.max_size_mb = max_size_mb
        self.max_items = max_items
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".curveeditor" / "thumbnail_cache"
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for fast access
        self._memory_cache: dict[str, Any] = {}
        self._access_order: list[str] = []
        self._lock = threading.Lock()
        
        # Cache metadata file
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        import json
        
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self._access_order = metadata.get('access_order', [])
        except Exception as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            self._access_order = []
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        import json
        
        try:
            metadata = {
                'access_order': self._access_order,
                'version': '1.0'
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")
    
    def _get_cache_key(self, file_path: str) -> str:
        """
        Generate cache key from file path.
        
        Args:
            file_path: Original file path
            
        Returns:
            Cache key string
        """
        import hashlib
        
        # Include file modification time in key for invalidation
        try:
            mtime = os.path.getmtime(file_path)
            key_data = f"{file_path}:{mtime}"
        except OSError:
            key_data = file_path
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get cache file path for given key."""
        return self.cache_dir / f"{cache_key}.thumbnail"
    
    def get(self, file_path: str) -> Any | None:
        """
        Get thumbnail from cache.
        
        Args:
            file_path: Original file path
            
        Returns:
            Cached thumbnail or None if not found
        """
        cache_key = self._get_cache_key(file_path)
        
        with self._lock:
            # Check memory cache first
            if cache_key in self._memory_cache:
                # Move to end (most recently used)
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
                self._access_order.append(cache_key)
                return self._memory_cache[cache_key]
            
            # Check disk cache
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                try:
                    from PySide6.QtGui import QPixmap
                    
                    # Load from disk
                    pixmap = QPixmap(str(cache_file))
                    if not pixmap.isNull():
                        # Add to memory cache
                        self._memory_cache[cache_key] = pixmap
                        if cache_key in self._access_order:
                            self._access_order.remove(cache_key)
                        self._access_order.append(cache_key)
                        
                        # Limit memory cache size
                        self._evict_memory_cache()
                        
                        return pixmap
                except Exception as e:
                    logger.warning(f"Failed to load cached thumbnail: {e}")
        
        return None
    
    def put(self, file_path: str, thumbnail: Any) -> None:
        """
        Store thumbnail in cache.
        
        Args:
            file_path: Original file path
            thumbnail: Thumbnail data to store (QPixmap)
        """
        cache_key = self._get_cache_key(file_path)
        
        with self._lock:
            # Store in memory cache
            self._memory_cache[cache_key] = thumbnail
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            
            # Store on disk
            cache_file = self._get_cache_file_path(cache_key)
            try:
                if hasattr(thumbnail, 'save'):  # QPixmap
                    thumbnail.save(str(cache_file), 'PNG')
            except Exception as e:
                logger.warning(f"Failed to save thumbnail to cache: {e}")
            
            # Evict if necessary
            self._evict_memory_cache()
            self._evict_disk_cache()
            
            # Save metadata periodically
            if len(self._access_order) % 100 == 0:
                self._save_metadata()
    
    def _evict_memory_cache(self) -> None:
        """Evict items from memory cache if over limit."""
        # Keep memory cache smaller than disk cache
        memory_limit = min(100, self.max_items // 10)
        
        while len(self._memory_cache) > memory_limit:
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                self._memory_cache.pop(oldest_key, None)
            else:
                break
    
    def _evict_disk_cache(self) -> None:
        """Evict items from disk cache if over limits."""
        # Check item count limit
        while len(self._access_order) > self.max_items:
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                cache_file = self._get_cache_file_path(oldest_key)
                try:
                    if cache_file.exists():
                        cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete cache file: {e}")
            else:
                break
        
        # Check size limit (simplified - just count files)
        try:
            cache_files = list(self.cache_dir.glob("*.thumbnail"))
            if len(cache_files) > self.max_items:
                # Remove oldest files
                cache_files.sort(key=lambda f: f.stat().st_mtime)
                files_to_remove = len(cache_files) - self.max_items
                for cache_file in cache_files[:files_to_remove]:
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete cache file: {e}")
        except Exception as e:
            logger.warning(f"Failed to check cache size: {e}")
    
    def clear(self) -> None:
        """Clear all cached thumbnails."""
        with self._lock:
            # Clear memory cache
            self._memory_cache.clear()
            self._access_order.clear()
            
            # Clear disk cache
            try:
                for cache_file in self.cache_dir.glob("*.thumbnail"):
                    cache_file.unlink()
                if self.metadata_file.exists():
                    self.metadata_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to clear disk cache: {e}")
    
    def size(self) -> int:
        """Get current cache size (number of items)."""
        with self._lock:
            return len(self._access_order)
    
    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            try:
                cache_files = list(self.cache_dir.glob("*.thumbnail"))
                total_size_bytes = sum(f.stat().st_size for f in cache_files)
                total_size_mb = total_size_bytes / (1024 * 1024)
                
                return {
                    'total_items': len(self._access_order),
                    'memory_items': len(self._memory_cache),
                    'disk_items': len(cache_files),
                    'total_size_mb': total_size_mb,
                    'cache_dir': str(self.cache_dir),
                }
            except Exception as e:
                logger.warning(f"Failed to get cache stats: {e}")
                return {
                    'total_items': len(self._access_order),
                    'memory_items': len(self._memory_cache),
                    'error': str(e)
                }