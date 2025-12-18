"""File path validator for sandboxing and security

Prevents path traversal and ensures all file operations stay within workspace.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, List

logger = logging.getLogger(__name__)


class FileValidator:
    """Validates file paths for security and sandboxing"""

    # Dangerous patterns that could indicate attacks
    DANGEROUS_PATTERNS = [
        "..",  # Path traversal
        "~",  # Home directory expansion
        "$",  # Environment variable expansion
    ]

    # Dangerous absolute paths
    FORBIDDEN_PATHS = [
        "/etc",
        "/sys",
        "/proc",
        "/dev",
        "/root",
        "/boot",
    ]

    def __init__(self, workspace_root: str):
        """Initialize file validator

        Args:
            workspace_root: Absolute path to workspace root (sandbox boundary)
        """
        self.workspace_root = Path(workspace_root).resolve()

        if not self.workspace_root.exists():
            raise ValueError(f"Workspace root does not exist: {workspace_root}")

        if not self.workspace_root.is_dir():
            raise ValueError(f"Workspace root is not a directory: {workspace_root}")

        logger.info(f"🔒 FileValidator initialized: {self.workspace_root}")

    def validate_path(self, file_path: str) -> Tuple[bool, str, Path]:
        """Validate that file path is safe and within workspace

        Args:
            file_path: Path to validate (relative or absolute)

        Returns:
            Tuple of (is_valid, error_message, resolved_path)
            - is_valid: True if path is safe
            - error_message: Error description if invalid, empty string if valid
            - resolved_path: Resolved absolute path (only meaningful if valid)
        """
        try:
            # Check for dangerous patterns
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in file_path:
                    return (
                        False,
                        f"Path contains dangerous pattern '{pattern}': {file_path}",
                        Path()
                    )

            # Resolve to absolute path
            if os.path.isabs(file_path):
                resolved = Path(file_path).resolve()
            else:
                resolved = (self.workspace_root / file_path).resolve()

            # Check if resolved path starts with forbidden paths
            resolved_str = str(resolved)
            for forbidden in self.FORBIDDEN_PATHS:
                if resolved_str.startswith(forbidden):
                    return (
                        False,
                        f"Path points to forbidden system directory: {resolved_str}",
                        Path()
                    )

            # CRITICAL: Check if resolved path is within workspace
            try:
                resolved.relative_to(self.workspace_root)
            except ValueError:
                return (
                    False,
                    f"Path escapes workspace boundary: {resolved_str} is outside {self.workspace_root}",
                    Path()
                )

            logger.debug(f"✅ Path validated: {file_path} → {resolved}")
            return (True, "", resolved)

        except Exception as e:
            return (False, f"Path validation error: {str(e)}", Path())

    def validate_paths(self, file_paths: List[str]) -> Tuple[bool, List[str], List[Path]]:
        """Validate multiple paths

        Args:
            file_paths: List of paths to validate

        Returns:
            Tuple of (all_valid, error_messages, resolved_paths)
        """
        all_valid = True
        error_messages = []
        resolved_paths = []

        for path in file_paths:
            is_valid, error, resolved = self.validate_path(path)
            if not is_valid:
                all_valid = False
                error_messages.append(error)
                resolved_paths.append(Path())
            else:
                error_messages.append("")
                resolved_paths.append(resolved)

        return (all_valid, error_messages, resolved_paths)

    def is_within_workspace(self, file_path: str) -> bool:
        """Quick check if path is within workspace

        Args:
            file_path: Path to check

        Returns:
            True if path is within workspace
        """
        is_valid, _, _ = self.validate_path(file_path)
        return is_valid

    def get_safe_path(self, file_path: str) -> Path:
        """Get safe resolved path or raise exception

        Args:
            file_path: Path to resolve

        Returns:
            Resolved path within workspace

        Raises:
            ValueError: If path is invalid or outside workspace
        """
        is_valid, error, resolved = self.validate_path(file_path)
        if not is_valid:
            raise ValueError(f"Invalid path: {error}")
        return resolved

    def list_workspace_files(self, pattern: str = "*", recursive: bool = True) -> List[Path]:
        """List files in workspace matching pattern

        Args:
            pattern: Glob pattern (e.g., "*.py", "src/**/*.ts")
            recursive: Whether to search recursively

        Returns:
            List of file paths within workspace
        """
        try:
            if recursive:
                files = list(self.workspace_root.rglob(pattern))
            else:
                files = list(self.workspace_root.glob(pattern))

            # Filter out directories, keep only files
            files = [f for f in files if f.is_file()]

            logger.info(f"📁 Found {len(files)} files matching '{pattern}'")
            return files

        except Exception as e:
            logger.error(f"❌ Error listing files: {e}")
            return []
