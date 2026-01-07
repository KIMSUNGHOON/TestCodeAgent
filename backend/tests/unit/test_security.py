"""Unit tests for security utilities"""

import pytest
from pathlib import Path
import tempfile
import os

from app.utils.security import sanitize_path, SecurityError, validate_filename


class TestSanitizePath:
    """Test suite for sanitize_path function"""

    def test_valid_relative_path(self):
        """Test that valid relative paths are accepted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = sanitize_path("subdir/file.txt", tmpdir, allow_creation=True)
            assert str(result).startswith(tmpdir)
            assert result.name == "file.txt"

    def test_valid_absolute_path_within_base(self):
        """Test that absolute paths within base are accepted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "project")
            os.makedirs(subdir, exist_ok=True)

            result = sanitize_path(subdir, tmpdir, allow_creation=True)
            assert str(result) == str(Path(subdir).resolve())

    def test_path_traversal_attack_relative(self):
        """Test that path traversal with ../ is blocked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError) as exc_info:
                sanitize_path("../../etc/passwd", tmpdir)

            assert "outside allowed directory" in str(exc_info.value)

    def test_path_traversal_attack_absolute(self):
        """Test that absolute paths outside base are blocked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError) as exc_info:
                sanitize_path("/etc/passwd", tmpdir)

            assert "outside allowed directory" in str(exc_info.value)

    def test_path_traversal_with_symlink(self):
        """Test that symlinks pointing outside base are blocked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a symlink to /tmp (outside the base directory)
            link_path = os.path.join(tmpdir, "evil_link")
            os.symlink("/tmp", link_path)

            # Accessing the symlink should raise SecurityError
            # because it resolves to /tmp which is outside tmpdir
            with pytest.raises(SecurityError) as exc_info:
                sanitize_path("evil_link", tmpdir, allow_creation=True)

            assert "outside allowed directory" in str(exc_info.value)

    def test_empty_user_path(self):
        """Test that empty user_path raises ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError) as exc_info:
                sanitize_path("", tmpdir)

            assert "non-empty string" in str(exc_info.value)

    def test_none_user_path(self):
        """Test that None user_path raises ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                sanitize_path(None, tmpdir)

    def test_allow_creation_false_nonexistent_path(self):
        """Test that nonexistent paths are rejected when allow_creation=False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError) as exc_info:
                sanitize_path("nonexistent/file.txt", tmpdir, allow_creation=False)

            assert "does not exist" in str(exc_info.value)

    def test_allow_creation_true_nonexistent_path(self):
        """Test that nonexistent paths are allowed when allow_creation=True"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = sanitize_path("new_dir/file.txt", tmpdir, allow_creation=True)
            assert str(result).startswith(tmpdir)
            assert not result.exists()  # Path doesn't exist yet, but is allowed

    def test_nested_path_within_base(self):
        """Test that deeply nested paths within base are accepted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = sanitize_path("a/b/c/d/e/file.txt", tmpdir, allow_creation=True)
            assert str(result).startswith(tmpdir)
            assert result.name == "file.txt"

    def test_path_with_dots_in_filename(self):
        """Test that filenames with dots (not ..) are accepted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = sanitize_path("my.config.file.txt", tmpdir, allow_creation=True)
            assert str(result).startswith(tmpdir)
            assert result.name == "my.config.file.txt"

    def test_realistic_attack_scenario(self):
        """Test realistic attack scenarios"""
        with tempfile.TemporaryDirectory() as tmpdir:
            attack_paths = [
                "../../../etc/passwd",
                "../../root/.ssh/id_rsa",
                "/etc/shadow",
                "subdir/../../etc/passwd",
                "./../../../tmp/evil",
                "valid/path/../../../etc/passwd"
            ]

            for attack_path in attack_paths:
                with pytest.raises(SecurityError):
                    sanitize_path(attack_path, tmpdir)


class TestValidateFilename:
    """Test suite for validate_filename function"""

    def test_valid_filename(self):
        """Test that valid filenames are accepted"""
        assert validate_filename("file.txt") == "file.txt"
        assert validate_filename("my-file_123.py") == "my-file_123.py"

    def test_filename_with_path_traversal(self):
        """Test that filenames with .. are rejected"""
        with pytest.raises(ValueError):
            validate_filename("../etc/passwd")

        with pytest.raises(ValueError):
            validate_filename("subdir/../file.txt")

    def test_filename_with_absolute_path(self):
        """Test that absolute paths are rejected"""
        with pytest.raises(ValueError):
            validate_filename("/etc/passwd")

    def test_empty_filename(self):
        """Test that empty filename raises ValueError"""
        with pytest.raises(ValueError):
            validate_filename("")

    def test_none_filename(self):
        """Test that None filename raises ValueError"""
        with pytest.raises(ValueError):
            validate_filename(None)


class TestSecurityIntegration:
    """Integration tests for security utilities with real workspace scenarios"""

    def test_workspace_write_security(self):
        """Test that workspace write operations are secured"""
        with tempfile.TemporaryDirectory() as workspace:
            # Valid write should succeed
            file_path = sanitize_path("project/src/main.py", workspace, allow_creation=True)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("print('hello')")
            assert file_path.exists()

            # Attack should fail
            with pytest.raises(SecurityError):
                sanitize_path("../../../etc/passwd", workspace)

    def test_workspace_read_security(self):
        """Test that workspace read operations are secured"""
        with tempfile.TemporaryDirectory() as workspace:
            # Create a valid file
            test_file = Path(workspace) / "test.txt"
            test_file.write_text("content")

            # Valid read should succeed
            file_path = sanitize_path("test.txt", workspace, allow_creation=False)
            assert file_path.read_text() == "content"

            # Attack should fail
            with pytest.raises(SecurityError):
                sanitize_path("../../etc/passwd", workspace, allow_creation=False)

    def test_project_listing_security(self):
        """Test that project listing is secured"""
        with tempfile.TemporaryDirectory() as base:
            # Create some projects
            (Path(base) / "project1").mkdir()
            (Path(base) / "project2").mkdir()

            # Valid listing should succeed
            base_path = sanitize_path(base, base, allow_creation=False)
            projects = [p for p in base_path.iterdir() if p.is_dir()]
            assert len(projects) == 2

            # Attack on base path should fail
            with pytest.raises(SecurityError):
                sanitize_path("/etc", base, allow_creation=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
