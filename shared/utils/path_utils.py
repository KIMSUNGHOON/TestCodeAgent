"""Cross-platform path normalization utilities

Provides consistent path handling across Windows, Linux, and macOS.
All functions normalize paths to use forward slashes internally.
"""

import os
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def normalize_path(path: str) -> str:
    """Normalize a path to use forward slashes consistently.

    Args:
        path: Input path (may use backslashes on Windows)

    Returns:
        Normalized path with forward slashes

    Examples:
        >>> normalize_path("C:\\Users\\test\\file.py")
        'C:/Users/test/file.py'
        >>> normalize_path("/home/user/file.py")
        '/home/user/file.py'
        >>> normalize_path("src\\components\\App.tsx")
        'src/components/App.tsx'
    """
    if not path:
        return path

    # Convert backslashes to forward slashes
    normalized = path.replace("\\", "/")

    # Remove duplicate slashes (except for protocol like http://)
    while "//" in normalized and not normalized.startswith("//"):
        normalized = normalized.replace("//", "/")

    # Remove trailing slash unless it's the root
    if len(normalized) > 1 and normalized.endswith("/"):
        normalized = normalized.rstrip("/")

    return normalized


def get_relative_path(file_path: str, workspace_root: str) -> str:
    """Get the relative path from workspace root.

    Handles edge cases like:
    - Paths starting with backslash on Windows
    - Mixed path separators
    - Paths already relative

    Args:
        file_path: The file path (absolute or relative)
        workspace_root: The workspace root directory

    Returns:
        Relative path from workspace root

    Examples:
        >>> get_relative_path("C:/project/src/file.py", "C:/project")
        'src/file.py'
        >>> get_relative_path("\\src\\file.py", "C:/project")
        'src/file.py'
        >>> get_relative_path("src/file.py", "C:/project")
        'src/file.py'
    """
    # Normalize both paths
    normalized_file = normalize_path(file_path)
    normalized_workspace = normalize_path(workspace_root)

    # Handle paths starting with separator (common issue on Windows)
    # e.g., "\calculator.py" should become "calculator.py"
    if normalized_file.startswith("/") and not normalized_file.startswith(normalized_workspace):
        # Check if it's just a leading slash without drive letter
        if len(normalized_file) > 1 and normalized_file[1] != ":":
            normalized_file = normalized_file.lstrip("/")

    # If file path starts with workspace root, make it relative
    if normalized_file.startswith(normalized_workspace):
        relative = normalized_file[len(normalized_workspace):].lstrip("/")
        return relative if relative else "."

    # If already relative or doesn't contain workspace, return as-is (normalized)
    return normalized_file


def is_path_within_workspace(file_path: str, workspace_root: str) -> Tuple[bool, str]:
    """Check if a path is within the workspace boundary.

    Args:
        file_path: The file path to check
        workspace_root: The workspace root directory

    Returns:
        Tuple of (is_within, error_message)

    Examples:
        >>> is_path_within_workspace("src/file.py", "/project")
        (True, '')
        >>> is_path_within_workspace("../etc/passwd", "/project")
        (False, 'Path traversal detected: ../etc/passwd')
    """
    # Normalize paths
    normalized_file = normalize_path(file_path)
    normalized_workspace = normalize_path(workspace_root)

    # Check for path traversal attempts
    if ".." in normalized_file:
        # Resolve the path to check if it escapes workspace
        try:
            workspace_path = Path(workspace_root).resolve()

            # Handle relative paths
            if not os.path.isabs(file_path):
                full_path = (workspace_path / file_path).resolve()
            else:
                full_path = Path(file_path).resolve()

            # Check if resolved path is within workspace
            try:
                full_path.relative_to(workspace_path)
                return True, ""
            except ValueError:
                return False, f"Path traversal detected: {file_path}"
        except Exception as e:
            return False, f"Path validation error: {e}"

    # Check for absolute paths outside workspace
    if os.path.isabs(normalized_file):
        if not normalized_file.startswith(normalized_workspace):
            # Allow paths that are relative to workspace when normalized
            relative = get_relative_path(normalized_file, normalized_workspace)
            if relative == normalized_file:
                return False, f"Absolute path outside workspace: {file_path}"

    return True, ""


def safe_join_path(base: str, *parts: str) -> str:
    """Safely join path components.

    Unlike os.path.join, this function:
    - Always normalizes the result
    - Prevents path traversal
    - Works consistently across platforms

    Args:
        base: Base path
        *parts: Path components to join

    Returns:
        Joined and normalized path

    Raises:
        ValueError: If the result would escape the base path

    Examples:
        >>> safe_join_path("/project", "src", "file.py")
        '/project/src/file.py'
        >>> safe_join_path("C:/project", "src\\utils", "helper.py")
        'C:/project/src/utils/helper.py'
    """
    # Normalize base
    normalized_base = normalize_path(base)

    # Normalize and join parts
    normalized_parts = [normalize_path(p).lstrip("/") for p in parts if p]

    # Check for path traversal in parts
    for part in normalized_parts:
        if ".." in part:
            # Allow .. only if it doesn't escape base
            test_path = "/".join([normalized_base] + normalized_parts)
            is_safe, error = is_path_within_workspace(test_path, base)
            if not is_safe:
                raise ValueError(f"Path would escape base directory: {error}")

    # Join paths
    result = "/".join([normalized_base] + normalized_parts)

    return normalize_path(result)


def get_filename(path: str) -> str:
    """Extract filename from a path (cross-platform).

    Args:
        path: File path

    Returns:
        Filename without directory

    Examples:
        >>> get_filename("C:\\Users\\test\\file.py")
        'file.py'
        >>> get_filename("/home/user/file.py")
        'file.py'
        >>> get_filename("file.py")
        'file.py'
    """
    normalized = normalize_path(path)
    return normalized.split("/")[-1] if "/" in normalized else normalized


def get_directory(path: str) -> str:
    """Extract directory from a path (cross-platform).

    Args:
        path: File path

    Returns:
        Directory without filename

    Examples:
        >>> get_directory("C:\\Users\\test\\file.py")
        'C:/Users/test'
        >>> get_directory("/home/user/file.py")
        '/home/user'
        >>> get_directory("file.py")
        ''
    """
    normalized = normalize_path(path)
    if "/" in normalized:
        return "/".join(normalized.split("/")[:-1])
    return ""
