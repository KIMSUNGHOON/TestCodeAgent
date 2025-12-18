"""
Shared Context for Parallel Agent Execution

Thread-safe context that allows parallel agents to share information
and reference each other's outputs.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass
class ContextEntry:
    """A single entry in the shared context."""
    agent_id: str
    agent_type: str
    key: str
    value: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""


@dataclass
class SharedContext:
    """Thread-safe shared context for parallel agent execution.

    Allows agents to share information and reference each other's outputs
    during parallel execution.

    All methods are thread-safe using asyncio.Lock.
    """
    entries: Dict[str, ContextEntry] = field(default_factory=dict)
    access_log: List[Dict[str, Any]] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def set(
        self,
        agent_id: str,
        agent_type: str,
        key: str,
        value: Any,
        description: str = ""
    ) -> None:
        """Set a value in the shared context.

        Args:
            agent_id: ID of the agent setting the value
            agent_type: Type/role of the agent
            key: Key name for the value
            value: The value to store
            description: Optional description of the value
        """
        async with self._lock:
            full_key = f"{agent_id}:{key}"
            self.entries[full_key] = ContextEntry(
                agent_id=agent_id,
                agent_type=agent_type,
                key=key,
                value=value,
                description=description
            )
            self.access_log.append({
                "action": "set",
                "agent_id": agent_id,
                "agent_type": agent_type,
                "key": key,
                "timestamp": datetime.now().isoformat()
            })

    async def get(
        self,
        requesting_agent: str,
        key: str,
        from_agent: str = None
    ) -> Optional[Any]:
        """Get a value from the shared context.

        Args:
            requesting_agent: ID of the agent requesting the value
            key: Key name to retrieve
            from_agent: Optional specific agent to get the value from

        Returns:
            The value if found, None otherwise
        """
        async with self._lock:
            if from_agent:
                full_key = f"{from_agent}:{key}"
            else:
                # Search for key across all agents
                for fk, entry in self.entries.items():
                    if entry.key == key:
                        full_key = fk
                        break
                else:
                    return None

            entry = self.entries.get(full_key)
            if entry:
                self.access_log.append({
                    "action": "get",
                    "requesting_agent": requesting_agent,
                    "source_agent": entry.agent_id,
                    "key": key,
                    "timestamp": datetime.now().isoformat()
                })
                return entry.value
            return None

    async def get_all_from_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get all entries from a specific agent.

        Args:
            agent_id: ID of the agent to get entries from

        Returns:
            Dictionary mapping keys to values for the specified agent
        """
        async with self._lock:
            return {
                entry.key: entry.value
                for fk, entry in self.entries.items()
                if entry.agent_id == agent_id
            }

    async def list_keys(self, agent_id: str) -> List[str]:
        """List all keys for a specific agent.

        Args:
            agent_id: ID of the agent to list keys for

        Returns:
            List of key names for the specified agent
        """
        async with self._lock:
            return [
                entry.key
                for fk, entry in self.entries.items()
                if entry.agent_id == agent_id
            ]

    async def get_all(self) -> Dict[str, ContextEntry]:
        """Get all entries from all agents.

        Returns:
            Dictionary mapping full_keys (agent_id:key) to ContextEntry objects
        """
        async with self._lock:
            return self.entries.copy()

    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get the access log for visualization.

        Returns:
            Copy of the access log with all set/get operations
        """
        return self.access_log.copy()

    def get_entries_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of all entries for UI display.

        Returns:
            List of entry summaries with truncated values
        """
        return [
            {
                "agent_id": entry.agent_id,
                "agent_type": entry.agent_type,
                "key": entry.key,
                "value_preview": (
                    str(entry.value)[:200] + "..."
                    if len(str(entry.value)) > 200
                    else str(entry.value)
                ),
                "description": entry.description,
                "timestamp": entry.timestamp
            }
            for entry in self.entries.values()
        ]
