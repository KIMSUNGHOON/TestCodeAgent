"""
Base classes and types for the Tool Execution System

Phase 2: Network Mode Support
- NetworkType enum for declaring network requirements
- Online/Offline mode support for secure networks
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum
import time


class ToolCategory(Enum):
    """Categories of tools available in the system"""
    FILE = "file"
    CODE = "code"
    GIT = "git"
    WEB = "web"
    SEARCH = "search"


class NetworkType(Enum):
    """
    Network requirement types for tools.

    Used to determine tool availability in different network modes.

    Types:
    - LOCAL: No network needed (file system, git, local execution)
    - INTERNAL: Internal network only (company intranet APIs)
    - EXTERNAL_API: External API calls (Tavily, REST APIs) - BLOCKED in offline mode
    - EXTERNAL_DOWNLOAD: File downloads (wget, curl) - ALLOWED in offline mode

    Security Policy:
    - EXTERNAL_API: Interactive APIs that may leak data (blocked in offline)
    - EXTERNAL_DOWNLOAD: One-way downloads that don't send local data (allowed in offline)
    """
    LOCAL = "local"
    INTERNAL = "internal"
    EXTERNAL_API = "external_api"
    EXTERNAL_DOWNLOAD = "external_download"


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """
    Base class for all tools in the system.

    All tools must inherit from this class and implement:
    - execute(): Main execution logic
    - validate_params(): Parameter validation

    Network Mode Support (Phase 2):
    - requires_network: Whether the tool needs any network access
    - network_type: Type of network access required (LOCAL, INTERNAL, EXTERNAL_API, EXTERNAL_DOWNLOAD)
    - is_available_in_mode(): Check if tool is available in current network mode
    - get_unavailable_message(): Get message when tool is unavailable
    """

    def __init__(self, name: str, category: ToolCategory):
        self.name = name
        self.category = category
        self.description = ""
        self.parameters = {}

        # Phase 2: Network requirement declaration
        # Default: offline-capable (no network required)
        self.requires_network = False
        self.network_type = NetworkType.LOCAL

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult: Result of the execution
        """
        pass

    @abstractmethod
    def validate_params(self, **kwargs) -> bool:
        """
        Validate parameters before execution.

        Args:
            **kwargs: Parameters to validate

        Returns:
            bool: True if valid, False otherwise
        """
        pass

    def get_schema(self) -> Dict:
        """
        Return JSON schema for tool parameters.

        Returns:
            Dict: Tool schema including name, category, description, parameters
        """
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "parameters": self.parameters
        }

    async def _execute_with_timing(self, **kwargs) -> ToolResult:
        """
        Internal method to execute with timing.

        Args:
            **kwargs: Parameters for execution

        Returns:
            ToolResult: Result with execution time
        """
        start_time = time.time()
        result = await self.execute(**kwargs)
        result.execution_time = time.time() - start_time
        return result

    # Phase 2: Network Mode Methods

    def is_available_in_mode(self, network_mode: str) -> bool:
        """
        Check if tool is available in current network mode.

        Network Mode Policy:
        - online: All tools available
        - offline: Block EXTERNAL_API, allow EXTERNAL_DOWNLOAD, allow LOCAL

        Security Rationale:
        - EXTERNAL_API (blocked): Interactive APIs may send local data externally
        - EXTERNAL_DOWNLOAD (allowed): One-way downloads don't send local data
        - LOCAL (allowed): No network access needed

        Args:
            network_mode: 'online' or 'offline'

        Returns:
            True if tool can be used in this mode
        """
        if network_mode == "offline":
            # Block interactive external APIs in offline mode
            if self.network_type == NetworkType.EXTERNAL_API:
                return False
            # Allow downloads (wget/curl) even in offline mode
            # Downloads are one-way (data IN only, no local data OUT)
            if self.network_type == NetworkType.EXTERNAL_DOWNLOAD:
                return True
            # LOCAL and INTERNAL are always allowed
        return True

    def get_unavailable_message(self) -> str:
        """
        Get message when tool is unavailable due to network mode.

        Returns:
            User-friendly message explaining why tool is unavailable
        """
        if self.network_type == NetworkType.EXTERNAL_API:
            return (
                f"Tool '{self.name}' requires external API access and is disabled in offline mode. "
                f"This tool uses interactive APIs that may send data externally. "
                f"Set NETWORK_MODE=online to enable this tool."
            )
        elif self.requires_network:
            return (
                f"Tool '{self.name}' requires network access and is disabled in offline mode. "
                f"Set NETWORK_MODE=online to enable."
            )
        return ""
