"""Security utilities for path validation and sanitization"""

from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security-related errors such as path traversal attempts"""
    pass


def sanitize_path(
    user_path: str,
    base_path: Union[str, Path],
    allow_creation: bool = False
) -> Path:
    """
    Prevent path traversal attacks by validating user-provided paths.

    This function ensures that the resolved path is within the allowed base directory,
    preventing attacks like "../../../etc/passwd".

    Args:
        user_path: User-provided path (relative or absolute, potentially malicious)
        base_path: Base directory that must contain the final path (must be absolute)
        allow_creation: If True, allows paths that don't exist yet

    Returns:
        Validated absolute Path object guaranteed to be within base_path

    Raises:
        SecurityError: If the resolved path is outside base_path
        ValueError: If paths are invalid or empty

    Examples:
        >>> sanitize_path("project1/file.py", "/home/user/workspace")
        PosixPath('/home/user/workspace/project1/file.py')

        >>> sanitize_path("../../etc/passwd", "/home/user/workspace")
        SecurityError: Path '../../etc/passwd' is outside allowed directory

        >>> sanitize_path("/tmp/evil", "/home/user/workspace")
        SecurityError: Path '/tmp/evil' is outside allowed directory
    """
    if not user_path or not isinstance(user_path, str):
        raise ValueError("user_path must be a non-empty string")

    if not base_path:
        raise ValueError("base_path must be specified")

    # Convert to Path objects and resolve to absolute paths
    base = Path(base_path).resolve()

    # Handle both absolute and relative user paths
    if Path(user_path).is_absolute():
        target = Path(user_path).resolve()
    else:
        target = (base / user_path).resolve()

    # Security check: ensure target is within base directory
    try:
        target.relative_to(base)
    except ValueError:
        logger.warning(
            f"Path traversal attempt detected: '{user_path}' "
            f"resolves outside base '{base}'"
        )
        raise SecurityError(
            f"Path '{user_path}' is outside allowed directory '{base}'"
        )

    # Check existence if required
    if not allow_creation and not target.exists():
        raise ValueError(f"Path does not exist: {target}")

    return target


def validate_filename(filename: str) -> str:
    """
    Validate filename to prevent directory traversal and special characters.

    Args:
        filename: Filename to validate

    Returns:
        Validated filename

    Raises:
        ValueError: If filename contains invalid characters
    """
    if not filename or not isinstance(filename, str):
        raise ValueError("Filename must be a non-empty string")

    # Check for path traversal attempts
    if ".." in filename or filename.startswith("/"):
        raise ValueError(f"Invalid filename: {filename}")

    # Additional character validation can be added here
    # For now, we rely on sanitize_path for full validation

    return filename
