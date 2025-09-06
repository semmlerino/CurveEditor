# \!/usr/bin/env python
"""
Comprehensive tests for path security validation to prevent path traversal attacks.

These tests verify that all file operations properly validate paths and prevent:
- Path traversal attacks (../../../etc/passwd)
- Directory traversal outside allowed directories
- Symlink following to unauthorized locations
- Invalid file extensions
- Other security vulnerabilities
"""

import tempfile
from pathlib import Path

import pytest

from core.path_security import (
    PathSecurityConfig,
    PathSecurityError,
    add_allowed_directory,
    get_path_security_config,
    is_safe_to_read,
    is_safe_to_write,
    remove_allowed_directory,
    sanitize_filename,
    set_allow_symlinks,
    validate_directory_path,
    validate_file_path,
)


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_backup() -> PathSecurityConfig:
    """Backup and restore path security configuration."""
    config = get_path_security_config()
    original_allowed_dirs = config.allowed_directories.copy()
    original_allow_symlinks = config.allow_symlinks
    original_extensions = config.allowed_extensions.copy()

    yield config

    # Restore original settings
    config.allowed_directories = original_allowed_dirs
    config.allow_symlinks = original_allow_symlinks
    config.allowed_extensions = original_extensions


class TestPathTraversalPrevention:
    """Test prevention of path traversal attacks."""

    def test_basic_path_traversal_attack(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test that basic path traversal attacks are blocked."""
        # Add temp directory as allowed
        add_allowed_directory(temp_dir)

        # These should all be blocked
        malicious_paths = [
            "../../../etc/passwd",
            "../../etc/shadow",
            "../../../windows/system32/config/system",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "/etc/shadow",
            "\\windows\\system32\\config\\system",
        ]

        for malicious_path in malicious_paths:
            with pytest.raises(PathSecurityError):
                validate_file_path(malicious_path, allow_create=True, require_exists=False)

    def test_null_byte_injection(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test that null byte injection is prevented."""
        add_allowed_directory(temp_dir)

        malicious_paths = [
            str(temp_dir / "test.json\x00../../etc/passwd"),
            str(temp_dir / "test\x00.json"),
            f"{temp_dir}/data.csv\x00",
        ]

        for malicious_path in malicious_paths:
            with pytest.raises(PathSecurityError):
                validate_file_path(malicious_path, allow_create=True, require_exists=False)

    def test_suspicious_system_paths(self, config_backup: PathSecurityConfig) -> None:
        """Test that system paths are blocked."""
        suspicious_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "/proc/version",
            "/sys/devices",
            "/dev/null",
            "C:\\windows\\system32\\config\\system",
            "C:\\windows\\system\\config",
        ]

        for suspicious_path in suspicious_paths:
            with pytest.raises(PathSecurityError):
                validate_file_path(suspicious_path, allow_create=True, require_exists=False)

    def test_allowed_directory_restriction(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test that files outside allowed directories are blocked."""
        # Only allow temp_dir
        config = get_path_security_config()
        config.allowed_directories = [temp_dir]

        # Create paths outside allowed directory
        outside_paths = [
            "/tmp/malicious.json",
            "/home/user/data.csv",
            "/var/tmp/attack.json",
        ]

        for outside_path in outside_paths:
            with pytest.raises(PathSecurityError):
                validate_file_path(outside_path, allow_create=True, require_exists=False)

    def test_allowed_directory_traversal_within_bounds(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test that files within allowed directories are accepted."""
        add_allowed_directory(temp_dir)

        # Create subdirectories
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()

        # These should be allowed
        # Test different file types with appropriate operation types
        test_cases = [
            (temp_dir / "data.json", "data_files"),
            (temp_dir / "subdir" / "data.csv", "data_files"),
            (temp_dir / "images" / "test.png", "image_files"),
        ]

        for allowed_path, op_type in test_cases:
            # Should not raise exception when using correct operation type
            result = validate_file_path(allowed_path, operation_type=op_type, allow_create=True, require_exists=False)
            assert result.is_absolute()

    def test_file_extension_validation(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test file extension validation."""
        add_allowed_directory(temp_dir)

        test_file = temp_dir / "test.exe"  # .exe not in allowed extensions

        with pytest.raises(PathSecurityError):
            validate_file_path(test_file, operation_type="data_files", allow_create=True, require_exists=False)

        # But should work with allowed extension
        json_file = temp_dir / "test.json"
        result = validate_file_path(json_file, operation_type="data_files", allow_create=True, require_exists=False)
        assert result.suffix == ".json"


class TestSymlinkSecurity:
    """Test symlink security controls."""

    def test_symlink_blocked_by_default(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test that symlinks are blocked by default."""
        add_allowed_directory(temp_dir)

        # Create a file and a symlink to it
        real_file = temp_dir / "real_file.json"
        real_file.write_text('{"test": "data"}')

        symlink_file = temp_dir / "symlink_file.json"
        symlink_file.symlink_to(real_file)

        # Symlink should be blocked
        with pytest.raises(PathSecurityError):
            validate_file_path(symlink_file, require_exists=True)

    def test_symlink_allowed_when_enabled(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test that symlinks work when explicitly enabled."""
        add_allowed_directory(temp_dir)
        set_allow_symlinks(True)

        # Create a file and a symlink to it
        real_file = temp_dir / "real_file.json"
        real_file.write_text('{"test": "data"}')

        symlink_file = temp_dir / "symlink_file.json"
        symlink_file.symlink_to(real_file)

        # Should work when symlinks are enabled
        result = validate_file_path(symlink_file, require_exists=True)
        assert result.resolve() == real_file.resolve()

    def test_symlink_directory_blocked(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test that symlinked directories are blocked."""
        # Create directory structure
        real_dir = temp_dir / "real_dir"
        real_dir.mkdir()

        symlink_dir = temp_dir / "symlink_dir"
        symlink_dir.symlink_to(real_dir)

        file_in_symlink = symlink_dir / "data.json"

        add_allowed_directory(temp_dir)

        # Should be blocked even if file would be allowed
        with pytest.raises(PathSecurityError):
            validate_file_path(file_in_symlink, allow_create=True, require_exists=False)


class TestDirectoryValidation:
    """Test directory path validation."""

    def test_valid_directory(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test validation of valid directories."""
        add_allowed_directory(temp_dir)

        # Should work for existing directory
        result = validate_directory_path(temp_dir)
        assert result == temp_dir.resolve()

    def test_nonexistent_directory_creation_allowed(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test allowing creation of non-existent directories."""
        add_allowed_directory(temp_dir)

        new_dir = temp_dir / "new_subdir"

        # Should work when creation is allowed
        result = validate_directory_path(new_dir, allow_create=True)
        assert result == new_dir.resolve()

    def test_nonexistent_directory_creation_blocked(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test blocking non-existent directories when creation not allowed."""
        add_allowed_directory(temp_dir)

        new_dir = temp_dir / "new_subdir"

        # Should fail when creation not allowed
        with pytest.raises(PathSecurityError):
            validate_directory_path(new_dir, allow_create=False)

    def test_directory_traversal_attack(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test directory traversal attacks."""
        add_allowed_directory(temp_dir)

        malicious_dirs = [
            "../../../etc",
            "../../tmp",
            str(temp_dir / "../../../etc"),
        ]

        for malicious_dir in malicious_dirs:
            with pytest.raises(PathSecurityError):
                validate_directory_path(malicious_dir, allow_create=True)


class TestFilenameSanitization:
    """Test filename sanitization."""

    def test_dangerous_characters_removed(self):
        """Test that dangerous characters are removed."""
        dangerous_names = [
            "test\x00file.json",  # Null byte
            "test\nfile.json",  # Newline
            "test\rfile.json",  # Carriage return
            "test/file.json",  # Path separator
            "test\\file.json",  # Windows path separator
            "../test.json",  # Relative path
            "..\\test.json",  # Windows relative path
        ]

        for dangerous_name in dangerous_names:
            sanitized = sanitize_filename(dangerous_name)
            assert "\x00" not in sanitized
            assert "\n" not in sanitized
            assert "\r" not in sanitized
            assert "/" not in sanitized
            assert "\\" not in sanitized
            assert ".." not in sanitized

    def test_filename_length_limitation(self):
        """Test that overly long filenames are truncated."""
        long_name = "a" * 300 + ".json"

        sanitized = sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".json")  # Extension preserved

    def test_empty_filename_rejected(self):
        """Test that empty filenames are rejected."""
        with pytest.raises(ValueError):
            sanitize_filename("")

        with pytest.raises(ValueError):
            sanitize_filename("   ")  # Whitespace only


class TestSafetyChecks:
    """Test safety check functions."""

    def test_safe_to_write(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test is_safe_to_write function."""
        add_allowed_directory(temp_dir)

        safe_path = temp_dir / "output.json"
        unsafe_path = "../../../etc/passwd"

        assert is_safe_to_write(safe_path) is True
        assert is_safe_to_write(unsafe_path) is False

    def test_safe_to_read(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test is_safe_to_read function."""
        add_allowed_directory(temp_dir)

        # Create a test file
        test_file = temp_dir / "test.json"
        test_file.write_text('{"test": "data"}')

        unsafe_path = "../../../etc/passwd"

        assert is_safe_to_read(test_file) is True
        assert is_safe_to_read(unsafe_path) is False
        assert is_safe_to_read(temp_dir / "nonexistent.json") is False


class TestConfigurationManagement:
    """Test configuration management functions."""

    def test_add_remove_allowed_directory(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test adding and removing allowed directories."""
        config = get_path_security_config()
        initial_count = len(config.allowed_directories)

        # Add directory
        add_allowed_directory(temp_dir)
        assert len(config.allowed_directories) == initial_count + 1
        assert temp_dir.resolve() in config.allowed_directories

        # Remove directory
        remove_allowed_directory(temp_dir)
        assert len(config.allowed_directories) == initial_count
        assert temp_dir.resolve() not in config.allowed_directories

    def test_symlink_configuration(self, config_backup: PathSecurityConfig) -> None:
        """Test symlink configuration."""
        config = get_path_security_config()

        # Default should be False
        assert config.allow_symlinks is False

        # Enable symlinks
        set_allow_symlinks(True)
        assert config.allow_symlinks is True

        # Disable symlinks
        set_allow_symlinks(False)
        assert config.allow_symlinks is False


class TestPathTraversalAttackScenarios:
    """Test realistic path traversal attack scenarios."""

    def test_windows_path_traversal(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test Windows-specific path traversal attempts."""
        add_allowed_directory(temp_dir)

        windows_attacks = [
            "..\\..\\..\\windows\\system32\\config\\sam",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "C:\\windows\\system32\\config\\system",
            "data.json\x00\\..\\..\\windows\\system32",
        ]

        for attack in windows_attacks:
            with pytest.raises(PathSecurityError):
                validate_file_path(attack, allow_create=True, require_exists=False)

    def test_unix_path_traversal(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test Unix-specific path traversal attempts."""
        add_allowed_directory(temp_dir)

        unix_attacks = [
            "../../../etc/passwd",
            "../../../etc/shadow",
            "../../../root/.ssh/id_rsa",
            "/proc/self/environ",
            "/proc/version",
            "data.json\x00/../../../etc/passwd",
        ]

        for attack in unix_attacks:
            with pytest.raises(PathSecurityError):
                validate_file_path(attack, allow_create=True, require_exists=False)

    def test_mixed_separator_attacks(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test attacks using mixed path separators."""
        add_allowed_directory(temp_dir)

        mixed_attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\etc\\passwd",
            "../..\\../etc/passwd",
            "data.json\x00/../../../etc/passwd",
            "data.json\x00\\..\\..\\..\\etc\\passwd",
        ]

        for attack in mixed_attacks:
            with pytest.raises(PathSecurityError):
                validate_file_path(attack, allow_create=True, require_exists=False)

    def test_unicode_path_traversal(self, temp_dir: Path, config_backup: PathSecurityConfig) -> None:
        """Test Unicode-based path traversal attempts."""
        add_allowed_directory(temp_dir)

        # Unicode normalization attacks
        unicode_attacks = [
            "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded
            "data.json\u0000/../../../etc/passwd",  # Unicode null
            "\u002e\u002e/\u002e\u002e/\u002e\u002e/etc/passwd",  # Unicode dots and slashes
        ]

        for attack in unicode_attacks:
            with pytest.raises(PathSecurityError):
                validate_file_path(attack, allow_create=True, require_exists=False)


if __name__ == "__main__":
    pytest.main([__file__])
