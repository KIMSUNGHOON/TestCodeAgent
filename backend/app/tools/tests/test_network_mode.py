"""
Test Network Mode Functionality (Phase 2)

Tests for online/offline mode support in ToolRegistry and BaseTool.
"""

import pytest
import os
from unittest.mock import patch

# Import after setting up the environment
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.tools.base import BaseTool, ToolCategory, ToolResult, NetworkType
from app.tools.web_tools import WebSearchTool
from app.tools.search_tools import CodeSearchTool
from app.tools.git_tools import GitCommitTool, GitStatusTool
from app.tools.file_tools import ReadFileTool


class TestNetworkType:
    """Test NetworkType enum"""

    def test_network_type_values(self):
        """Test all network type values exist"""
        assert NetworkType.LOCAL.value == "local"
        assert NetworkType.INTERNAL.value == "internal"
        assert NetworkType.EXTERNAL_API.value == "external_api"
        assert NetworkType.EXTERNAL_DOWNLOAD.value == "external_download"

    def test_network_type_count(self):
        """Test we have exactly 4 network types"""
        assert len(NetworkType) == 4


class TestBaseToolNetworkSupport:
    """Test BaseTool network mode support"""

    def test_default_network_type_is_local(self):
        """Test that default network type is LOCAL"""
        tool = ReadFileTool()
        assert tool.network_type == NetworkType.LOCAL
        assert tool.requires_network is False

    def test_web_search_tool_is_external_api(self):
        """Test WebSearchTool is marked as EXTERNAL_API"""
        tool = WebSearchTool()
        assert tool.network_type == NetworkType.EXTERNAL_API
        assert tool.requires_network is True

    def test_code_search_tool_is_local(self):
        """Test CodeSearchTool is marked as LOCAL"""
        tool = CodeSearchTool()
        assert tool.network_type == NetworkType.LOCAL
        assert tool.requires_network is False

    def test_git_tools_are_local(self):
        """Test Git tools are marked as LOCAL"""
        git_commit = GitCommitTool()
        git_status = GitStatusTool()

        assert git_commit.network_type == NetworkType.LOCAL
        assert git_commit.requires_network is False

        assert git_status.network_type == NetworkType.LOCAL
        assert git_status.requires_network is False


class TestIsAvailableInMode:
    """Test is_available_in_mode() method"""

    def test_local_tool_available_in_online_mode(self):
        """Test LOCAL tools are available in online mode"""
        tool = ReadFileTool()
        assert tool.is_available_in_mode("online") is True

    def test_local_tool_available_in_offline_mode(self):
        """Test LOCAL tools are available in offline mode"""
        tool = ReadFileTool()
        assert tool.is_available_in_mode("offline") is True

    def test_external_api_available_in_online_mode(self):
        """Test EXTERNAL_API tools are available in online mode"""
        tool = WebSearchTool()
        assert tool.is_available_in_mode("online") is True

    def test_external_api_blocked_in_offline_mode(self):
        """Test EXTERNAL_API tools are blocked in offline mode"""
        tool = WebSearchTool()
        assert tool.is_available_in_mode("offline") is False

    def test_external_download_available_in_online_mode(self):
        """Test EXTERNAL_DOWNLOAD type would be available in online mode"""
        # Create a mock tool with EXTERNAL_DOWNLOAD type
        tool = ReadFileTool()
        tool.network_type = NetworkType.EXTERNAL_DOWNLOAD
        tool.requires_network = True
        assert tool.is_available_in_mode("online") is True

    def test_external_download_available_in_offline_mode(self):
        """Test EXTERNAL_DOWNLOAD type is allowed in offline mode (wget/curl)"""
        # Create a mock tool with EXTERNAL_DOWNLOAD type
        tool = ReadFileTool()
        tool.network_type = NetworkType.EXTERNAL_DOWNLOAD
        tool.requires_network = True
        assert tool.is_available_in_mode("offline") is True


class TestGetUnavailableMessage:
    """Test get_unavailable_message() method"""

    def test_local_tool_has_no_message(self):
        """Test LOCAL tools return empty unavailable message"""
        tool = ReadFileTool()
        assert tool.get_unavailable_message() == ""

    def test_external_api_tool_has_message(self):
        """Test EXTERNAL_API tools return informative message"""
        tool = WebSearchTool()
        message = tool.get_unavailable_message()

        assert "web_search" in message
        assert "offline mode" in message
        assert "NETWORK_MODE=online" in message


class TestToolRegistryNetworkMode:
    """Test ToolRegistry network mode functionality"""

    def test_online_mode_all_tools_available(self):
        """Test that all tools are available in online mode"""
        with patch.dict(os.environ, {"NETWORK_MODE": "online"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()
            stats = registry.get_statistics()

            assert stats["network_mode"] == "online"
            assert stats["available_tools"] == stats["total_tools"]
            assert stats["disabled_tools"] == 0

    def test_offline_mode_filters_external_api(self):
        """Test that EXTERNAL_API tools are filtered in offline mode"""
        with patch.dict(os.environ, {"NETWORK_MODE": "offline"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()
            stats = registry.get_statistics()

            assert stats["network_mode"] == "offline"
            # WebSearchTool should be disabled
            assert stats["disabled_tools"] >= 1
            assert stats["available_tools"] < stats["total_tools"]

    def test_offline_mode_web_search_unavailable(self):
        """Test WebSearchTool is unavailable in offline mode"""
        with patch.dict(os.environ, {"NETWORK_MODE": "offline"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()
            tool = registry.get_tool("web_search")

            assert tool is None

    def test_offline_mode_code_search_available(self):
        """Test CodeSearchTool is available in offline mode"""
        with patch.dict(os.environ, {"NETWORK_MODE": "offline"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()
            tool = registry.get_tool("code_search")

            assert tool is not None
            assert tool.name == "code_search"

    def test_offline_mode_git_tools_available(self):
        """Test Git tools are available in offline mode"""
        with patch.dict(os.environ, {"NETWORK_MODE": "offline"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()

            assert registry.get_tool("git_status") is not None
            assert registry.get_tool("git_diff") is not None
            assert registry.get_tool("git_log") is not None
            assert registry.get_tool("git_branch") is not None
            assert registry.get_tool("git_commit") is not None

    def test_offline_mode_file_tools_available(self):
        """Test File tools are available in offline mode"""
        with patch.dict(os.environ, {"NETWORK_MODE": "offline"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()

            assert registry.get_tool("read_file") is not None
            assert registry.get_tool("write_file") is not None
            assert registry.get_tool("search_files") is not None
            assert registry.get_tool("list_directory") is not None

    def test_invalid_mode_defaults_to_online(self):
        """Test invalid NETWORK_MODE defaults to online"""
        with patch.dict(os.environ, {"NETWORK_MODE": "invalid_mode"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()

            assert registry.get_network_mode() == "online"

    def test_list_tools_filters_by_mode(self):
        """Test list_tools() respects network mode"""
        with patch.dict(os.environ, {"NETWORK_MODE": "offline"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()
            tools = registry.list_tools()
            tool_names = [t.name for t in tools]

            # web_search should not be in the list
            assert "web_search" not in tool_names
            # Local tools should be in the list
            assert "code_search" in tool_names
            assert "git_commit" in tool_names

    def test_list_tools_include_unavailable(self):
        """Test list_tools() can include unavailable tools"""
        with patch.dict(os.environ, {"NETWORK_MODE": "offline"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()
            all_tools = registry.list_tools(include_unavailable=True)
            available_tools = registry.list_tools(include_unavailable=False)

            assert len(all_tools) > len(available_tools)

            all_names = [t.name for t in all_tools]
            assert "web_search" in all_names

    def test_get_statistics_network_info(self):
        """Test get_statistics() includes network information"""
        with patch.dict(os.environ, {"NETWORK_MODE": "online"}):
            # Reset singleton
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()
            stats = registry.get_statistics()

            assert "network_mode" in stats
            assert "available_tools" in stats
            assert "disabled_tools" in stats
            assert "by_network_type" in stats

            # Check network type breakdown
            assert "local" in stats["by_network_type"]
            assert "external_api" in stats["by_network_type"]


class TestToolNetworkTypeDeclarations:
    """Test that all tools have correct network type declarations"""

    def test_all_file_tools_are_local(self):
        """Test all file tools are LOCAL"""
        from app.tools.file_tools import (
            ReadFileTool, WriteFileTool, SearchFilesTool, ListDirectoryTool
        )

        tools = [ReadFileTool(), WriteFileTool(), SearchFilesTool(), ListDirectoryTool()]

        for tool in tools:
            assert tool.network_type == NetworkType.LOCAL, f"{tool.name} should be LOCAL"
            assert tool.requires_network is False, f"{tool.name} should not require network"

    def test_all_code_tools_are_local(self):
        """Test all code tools are LOCAL"""
        from app.tools.code_tools import (
            ExecutePythonTool, RunTestsTool, LintCodeTool
        )

        tools = [ExecutePythonTool(), RunTestsTool(), LintCodeTool()]

        for tool in tools:
            assert tool.network_type == NetworkType.LOCAL, f"{tool.name} should be LOCAL"
            assert tool.requires_network is False, f"{tool.name} should not require network"

    def test_all_git_tools_are_local(self):
        """Test all git tools are LOCAL"""
        from app.tools.git_tools import (
            GitStatusTool, GitDiffTool, GitLogTool, GitBranchTool, GitCommitTool
        )

        tools = [GitStatusTool(), GitDiffTool(), GitLogTool(), GitBranchTool(), GitCommitTool()]

        for tool in tools:
            assert tool.network_type == NetworkType.LOCAL, f"{tool.name} should be LOCAL"
            assert tool.requires_network is False, f"{tool.name} should not require network"

    def test_web_search_is_external_api(self):
        """Test WebSearchTool is EXTERNAL_API"""
        tool = WebSearchTool()
        assert tool.network_type == NetworkType.EXTERNAL_API
        assert tool.requires_network is True

    def test_code_search_is_local(self):
        """Test CodeSearchTool is LOCAL (uses local ChromaDB)"""
        tool = CodeSearchTool()
        assert tool.network_type == NetworkType.LOCAL
        assert tool.requires_network is False


class TestNetworkModeSecurityPolicy:
    """Test network mode security policy enforcement"""

    def test_offline_mode_blocks_external_api(self):
        """Test that offline mode blocks all EXTERNAL_API tools"""
        # This ensures no data can be sent to external services
        tool = WebSearchTool()

        # In offline mode, this tool should be blocked
        assert tool.is_available_in_mode("offline") is False

        # The message should explain why
        message = tool.get_unavailable_message()
        assert "external API" in message.lower() or "offline mode" in message.lower()

    def test_offline_mode_allows_downloads(self):
        """Test that offline mode allows EXTERNAL_DOWNLOAD (one-way downloads)"""
        # Create a tool with EXTERNAL_DOWNLOAD type
        # This simulates wget/curl which only downloads, doesn't send local data
        tool = ReadFileTool()
        tool.network_type = NetworkType.EXTERNAL_DOWNLOAD
        tool.requires_network = True

        # Downloads should be allowed even in offline mode
        # because they don't send local data externally
        assert tool.is_available_in_mode("offline") is True

    def test_local_tools_always_available(self):
        """Test that LOCAL tools are always available"""
        tools = [
            ReadFileTool(),
            GitStatusTool(),
            CodeSearchTool(),
        ]

        for tool in tools:
            assert tool.is_available_in_mode("online") is True
            assert tool.is_available_in_mode("offline") is True


# Clean up singleton after tests
@pytest.fixture(autouse=True)
def cleanup_registry():
    """Reset ToolRegistry singleton after each test"""
    yield
    from app.tools.registry import ToolRegistry
    ToolRegistry._instance = None
