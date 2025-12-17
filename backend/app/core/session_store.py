"""Thread-safe session storage for managing session state"""

import asyncio
from typing import Dict, Optional, Literal
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

FrameworkType = Literal["standard", "deepagents"]


class SessionStore:
    """
    Thread-safe session storage using asyncio locks.

    Manages session-specific state including:
    - Framework selection (standard vs deepagents)
    - Workspace paths
    - Any other session-scoped configuration

    Thread Safety:
    - Uses asyncio.Lock per session for fine-grained locking
    - Prevents race conditions in concurrent requests
    - Allows parallel access to different sessions
    """

    def __init__(self):
        self._frameworks: Dict[str, FrameworkType] = {}
        self._workspaces: Dict[str, str] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._global_lock = asyncio.Lock()  # For lock management

    async def get_framework(self, session_id: str) -> FrameworkType:
        """
        Get framework for session.

        Args:
            session_id: Session identifier

        Returns:
            Framework type ("standard" or "deepagents")
        """
        async with self._locks[session_id]:
            return self._frameworks.get(session_id, "standard")

    async def set_framework(
        self,
        session_id: str,
        framework: FrameworkType
    ) -> None:
        """
        Set framework for session.

        Args:
            session_id: Session identifier
            framework: Framework type to use

        Raises:
            ValueError: If framework is invalid
        """
        if framework not in ("standard", "deepagents"):
            raise ValueError(f"Invalid framework: {framework}")

        async with self._locks[session_id]:
            self._frameworks[session_id] = framework
            logger.info(f"Session {session_id}: framework set to {framework}")

    async def get_workspace(
        self,
        session_id: str,
        default: str = "/home/user/workspace"
    ) -> str:
        """
        Get workspace path for session.

        Args:
            session_id: Session identifier
            default: Default workspace if not set

        Returns:
            Workspace path
        """
        async with self._locks[session_id]:
            return self._workspaces.get(session_id, default)

    async def set_workspace(self, session_id: str, workspace: str) -> None:
        """
        Set workspace path for session.

        Args:
            session_id: Session identifier
            workspace: Workspace path (should be validated before calling)
        """
        async with self._locks[session_id]:
            self._workspaces[session_id] = workspace
            logger.info(f"Session {session_id}: workspace set to {workspace}")

    async def delete_session(self, session_id: str) -> None:
        """
        Delete all data for a session.

        Args:
            session_id: Session identifier
        """
        async with self._global_lock:
            # Remove session data
            self._frameworks.pop(session_id, None)
            self._workspaces.pop(session_id, None)

            # Remove the lock itself
            if session_id in self._locks:
                del self._locks[session_id]

            logger.info(f"Session {session_id}: deleted")

    async def get_session_info(self, session_id: str) -> Dict[str, any]:
        """
        Get all information for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session information
        """
        async with self._locks[session_id]:
            return {
                "session_id": session_id,
                "framework": self._frameworks.get(session_id, "standard"),
                "workspace": self._workspaces.get(session_id, "/home/user/workspace"),
                "exists": session_id in self._frameworks or session_id in self._workspaces
            }

    async def list_sessions(self) -> list[str]:
        """
        List all active session IDs.

        Returns:
            List of session IDs
        """
        async with self._global_lock:
            # Combine keys from both dicts
            return list(set(self._frameworks.keys()) | set(self._workspaces.keys()))

    def __len__(self) -> int:
        """Return number of active sessions."""
        return len(set(self._frameworks.keys()) | set(self._workspaces.keys()))


# Global singleton instance
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """
    Get global SessionStore instance (singleton pattern).

    Returns:
        SessionStore instance
    """
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
