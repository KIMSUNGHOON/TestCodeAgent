"""
Tests for Phase 2 Web Tools: HttpRequestTool and DownloadFileTool

Comprehensive tests including:
- Parameter validation
- Execute method with mocks
- Error handling
- Network type verification
"""

import os
import sys
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.tools.base import NetworkType, ToolResult
from app.tools.web_tools import HttpRequestTool, DownloadFileTool


# =============================================================================
# HttpRequestTool Tests
# =============================================================================

class TestHttpRequestToolValidation:
    """Test HttpRequestTool parameter validation"""

    def test_valid_https_url(self):
        tool = HttpRequestTool()
        assert tool.validate_params(url="https://api.example.com/data") is True

    def test_valid_http_url(self):
        tool = HttpRequestTool()
        assert tool.validate_params(url="http://localhost:8000/api") is True

    def test_invalid_url_no_protocol(self):
        tool = HttpRequestTool()
        assert tool.validate_params(url="example.com/api") is False

    def test_empty_url(self):
        tool = HttpRequestTool()
        assert tool.validate_params(url="") is False

    def test_missing_url(self):
        tool = HttpRequestTool()
        assert tool.validate_params() is False

    def test_valid_methods(self):
        tool = HttpRequestTool()
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            assert tool.validate_params(url="https://api.example.com", method=method) is True

    def test_invalid_method(self):
        tool = HttpRequestTool()
        assert tool.validate_params(url="https://api.example.com", method="INVALID") is False

    def test_valid_timeout(self):
        tool = HttpRequestTool()
        assert tool.validate_params(url="https://api.example.com", timeout=30) is True
        assert tool.validate_params(url="https://api.example.com", timeout=300) is True

    def test_invalid_timeout(self):
        tool = HttpRequestTool()
        assert tool.validate_params(url="https://api.example.com", timeout=0) is False
        assert tool.validate_params(url="https://api.example.com", timeout=-1) is False
        assert tool.validate_params(url="https://api.example.com", timeout=500) is False


class TestHttpRequestToolNetworkType:
    """Test HttpRequestTool network configuration"""

    def test_is_external_api(self):
        tool = HttpRequestTool()
        assert tool.network_type == NetworkType.EXTERNAL_API

    def test_requires_network(self):
        tool = HttpRequestTool()
        assert tool.requires_network is True

    def test_blocked_in_offline_mode(self):
        tool = HttpRequestTool()
        assert tool.is_available_in_mode("offline") is False

    def test_available_in_online_mode(self):
        tool = HttpRequestTool()
        assert tool.is_available_in_mode("online") is True


class TestHttpRequestToolExecute:
    """Test HttpRequestTool execute method with mocks"""

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test timeout handling"""
        tool = HttpRequestTool()

        import aiohttp

        with patch("aiohttp.ClientSession") as mock_client:
            # Make the context manager raise TimeoutError
            mock_cm = AsyncMock()
            mock_cm.__aenter__.side_effect = asyncio.TimeoutError()
            mock_client.return_value = mock_cm

            result = await tool.execute(url="https://api.example.com/slow", timeout=1)

            assert result.success is False
            assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_client_error(self):
        """Test aiohttp ClientError handling"""
        tool = HttpRequestTool()

        import aiohttp

        with patch("aiohttp.ClientSession") as mock_client:
            mock_cm = AsyncMock()
            mock_cm.__aenter__.side_effect = aiohttp.ClientError("Connection failed")
            mock_client.return_value = mock_cm

            result = await tool.execute(url="https://api.example.com/error")

            assert result.success is False
            assert "failed" in result.error.lower()

    def test_tool_schema(self):
        """Test tool schema is properly defined"""
        tool = HttpRequestTool()
        schema = tool.get_schema()

        assert schema["name"] == "http_request"
        assert "url" in schema["parameters"]
        assert "method" in schema["parameters"]


# =============================================================================
# DownloadFileTool Tests
# =============================================================================

class TestDownloadFileToolValidation:
    """Test DownloadFileTool parameter validation"""

    def test_valid_https_url(self):
        tool = DownloadFileTool()
        assert tool.validate_params(
            url="https://example.com/file.zip",
            output_path="/tmp/file.zip"
        ) is True

    def test_valid_http_url(self):
        tool = DownloadFileTool()
        assert tool.validate_params(
            url="http://example.com/file.zip",
            output_path="/tmp/file.zip"
        ) is True

    def test_valid_ftp_url(self):
        tool = DownloadFileTool()
        assert tool.validate_params(
            url="ftp://ftp.example.com/file.zip",
            output_path="/tmp/file.zip"
        ) is True

    def test_invalid_url_no_protocol(self):
        tool = DownloadFileTool()
        assert tool.validate_params(
            url="example.com/file.zip",
            output_path="/tmp/file.zip"
        ) is False

    def test_empty_url(self):
        tool = DownloadFileTool()
        assert tool.validate_params(url="", output_path="/tmp/file.zip") is False

    def test_empty_output_path(self):
        tool = DownloadFileTool()
        assert tool.validate_params(url="https://example.com/file.zip", output_path="") is False

    def test_valid_timeout(self):
        tool = DownloadFileTool()
        assert tool.validate_params(
            url="https://example.com/file.zip",
            output_path="/tmp/file.zip",
            timeout=60
        ) is True

    def test_invalid_timeout(self):
        tool = DownloadFileTool()
        assert tool.validate_params(
            url="https://example.com/file.zip",
            output_path="/tmp/file.zip",
            timeout=0
        ) is False
        assert tool.validate_params(
            url="https://example.com/file.zip",
            output_path="/tmp/file.zip",
            timeout=5000
        ) is False


class TestDownloadFileToolNetworkType:
    """Test DownloadFileTool network configuration"""

    def test_is_external_download(self):
        tool = DownloadFileTool()
        assert tool.network_type == NetworkType.EXTERNAL_DOWNLOAD

    def test_requires_network(self):
        tool = DownloadFileTool()
        assert tool.requires_network is True

    def test_allowed_in_offline_mode(self):
        """EXTERNAL_DOWNLOAD should be allowed in offline mode"""
        tool = DownloadFileTool()
        assert tool.is_available_in_mode("offline") is True

    def test_allowed_in_online_mode(self):
        tool = DownloadFileTool()
        assert tool.is_available_in_mode("online") is True


class TestDownloadFileToolFindDownloader:
    """Test DownloadFileTool downloader detection"""

    def test_find_wget(self):
        """Test finding wget"""
        tool = DownloadFileTool()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = tool._find_downloader()
            assert result in ["wget", "curl"]

    def test_no_downloader_found(self):
        """Test when neither wget nor curl is found"""
        tool = DownloadFileTool()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = tool._find_downloader()
            assert result is None


class TestDownloadFileToolExecute:
    """Test DownloadFileTool execute method"""

    @pytest.mark.asyncio
    async def test_file_already_exists_no_overwrite(self, tmp_path):
        """Test error when file exists and overwrite=False"""
        tool = DownloadFileTool()

        # Create existing file
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("existing content")

        result = await tool.execute(
            url="https://example.com/file.txt",
            output_path=str(existing_file),
            overwrite=False
        )

        assert result.success is False
        assert "already exists" in result.error

    @pytest.mark.asyncio
    async def test_no_downloader_available(self, tmp_path):
        """Test error when no downloader is available"""
        tool = DownloadFileTool()

        output_file = tmp_path / "output.txt"

        with patch.object(tool, "_find_downloader", return_value=None):
            result = await tool.execute(
                url="https://example.com/file.txt",
                output_path=str(output_file)
            )

            assert result.success is False
            assert "wget" in result.error.lower() or "curl" in result.error.lower()

    @pytest.mark.asyncio
    async def test_successful_download_wget(self, tmp_path):
        """Test successful download with wget"""
        tool = DownloadFileTool()

        output_file = tmp_path / "downloaded.txt"

        # Create file to simulate wget success
        async def create_file(*args, **kwargs):
            output_file.write_text("downloaded content")
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            return mock_proc

        with patch.object(tool, "_find_downloader", return_value="wget"):
            with patch("asyncio.create_subprocess_exec", side_effect=create_file):
                result = await tool.execute(
                    url="https://example.com/file.txt",
                    output_path=str(output_file)
                )

                assert result.success is True
                assert result.output["downloader"] == "wget"
                assert result.output["file_size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_successful_download_curl(self, tmp_path):
        """Test successful download with curl"""
        tool = DownloadFileTool()

        output_file = tmp_path / "downloaded.txt"

        async def create_file(*args, **kwargs):
            output_file.write_text("downloaded content")
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            return mock_proc

        with patch.object(tool, "_find_downloader", return_value="curl"):
            with patch("asyncio.create_subprocess_exec", side_effect=create_file):
                result = await tool.execute(
                    url="https://example.com/file.txt",
                    output_path=str(output_file)
                )

                assert result.success is True
                assert result.output["downloader"] == "curl"

    @pytest.mark.asyncio
    async def test_download_failure(self, tmp_path):
        """Test download failure handling"""
        tool = DownloadFileTool()

        output_file = tmp_path / "failed.txt"

        async def fail_download(*args, **kwargs):
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b"Connection refused"))
            return mock_proc

        with patch.object(tool, "_find_downloader", return_value="wget"):
            with patch("asyncio.create_subprocess_exec", side_effect=fail_download):
                result = await tool.execute(
                    url="https://example.com/file.txt",
                    output_path=str(output_file)
                )

                assert result.success is False
                assert "failed" in result.error.lower() or "refused" in result.error.lower()

    @pytest.mark.asyncio
    async def test_download_timeout(self, tmp_path):
        """Test download timeout handling"""
        tool = DownloadFileTool()

        output_file = tmp_path / "timeout.txt"

        async def timeout_download(*args, **kwargs):
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_proc.kill = MagicMock()
            mock_proc.wait = AsyncMock()
            return mock_proc

        with patch.object(tool, "_find_downloader", return_value="wget"):
            with patch("asyncio.create_subprocess_exec", side_effect=timeout_download):
                result = await tool.execute(
                    url="https://example.com/file.txt",
                    output_path=str(output_file),
                    timeout=1
                )

                assert result.success is False
                assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_creates_parent_directory(self, tmp_path):
        """Test that parent directory is created"""
        tool = DownloadFileTool()

        nested_path = tmp_path / "nested" / "dir" / "file.txt"

        async def create_file(*args, **kwargs):
            nested_path.write_text("content")
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            return mock_proc

        with patch.object(tool, "_find_downloader", return_value="wget"):
            with patch("asyncio.create_subprocess_exec", side_effect=create_file):
                result = await tool.execute(
                    url="https://example.com/file.txt",
                    output_path=str(nested_path)
                )

                # Parent directory should have been created
                assert nested_path.parent.exists()


# =============================================================================
# Integration Tests
# =============================================================================

class TestWebToolsIntegration:
    """Integration tests for Phase 2 web tools"""

    def test_tools_have_correct_category(self):
        """Test both tools are in WEB category"""
        from app.tools.base import ToolCategory

        http_tool = HttpRequestTool()
        download_tool = DownloadFileTool()

        assert http_tool.category == ToolCategory.WEB
        assert download_tool.category == ToolCategory.WEB

    def test_tools_have_descriptions(self):
        """Test both tools have descriptions"""
        http_tool = HttpRequestTool()
        download_tool = DownloadFileTool()

        assert len(http_tool.description) > 0
        assert len(download_tool.description) > 0

    def test_tools_have_parameters(self):
        """Test both tools have parameter definitions"""
        http_tool = HttpRequestTool()
        download_tool = DownloadFileTool()

        assert "url" in http_tool.parameters
        assert "url" in download_tool.parameters
        assert "output_path" in download_tool.parameters

    def test_registry_contains_both_tools(self):
        """Test ToolRegistry contains both new tools"""
        with patch.dict(os.environ, {"NETWORK_MODE": "online"}):
            from app.tools.registry import ToolRegistry
            ToolRegistry._instance = None

            registry = ToolRegistry()

            http_tool = registry.get_tool("http_request")
            download_tool = registry.get_tool("download_file")

            assert http_tool is not None
            assert download_tool is not None
