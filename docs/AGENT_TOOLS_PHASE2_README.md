# Agent Tools Phase 2 - Network Mode & New Tools

**Version**: 2.0.0
**Date**: 2026-01-08
**Status**: Production Ready

---

## Overview

Agent Tools Phase 2 introduces **Network Mode** for secure network environments and adds **2 new web tools**. This enables controlled tool access in air-gapped or security-restricted networks.

### Key Features

1. **Network Mode System** - Online/Offline mode control
2. **HttpRequestTool** - REST API calls (EXTERNAL_API)
3. **DownloadFileTool** - File downloads via wget/curl (EXTERNAL_DOWNLOAD)

**Total Tools**: 16 (14 Phase 1 + 2 new)

---

## Network Mode System

### Concept

Network Mode allows administrators to control which tools can access external networks, critical for secure/air-gapped environments.

### Network Types

| Type | Description | Offline Mode |
|------|-------------|--------------|
| `LOCAL` | No network needed (file, git, code tools) | Allowed |
| `INTERNAL` | Internal network only | Allowed |
| `EXTERNAL_API` | External API calls (may leak data) | **Blocked** |
| `EXTERNAL_DOWNLOAD` | One-way file downloads | Allowed |

### Security Policy

```
Offline Mode Policy:
- BLOCK: Tools that send data externally (EXTERNAL_API)
- ALLOW: Tools that only receive data (EXTERNAL_DOWNLOAD)
- ALLOW: Tools that work locally (LOCAL)

Rationale: Prevent local data leakage while allowing file downloads
```

### Configuration

```bash
# .env
NETWORK_MODE=online   # All tools available
NETWORK_MODE=offline  # Block EXTERNAL_API tools only
```

### Tool Availability by Mode

| Tool | Network Type | Online | Offline |
|------|--------------|--------|---------|
| read_file | LOCAL | Yes | Yes |
| write_file | LOCAL | Yes | Yes |
| search_files | LOCAL | Yes | Yes |
| list_directory | LOCAL | Yes | Yes |
| execute_python | LOCAL | Yes | Yes |
| run_tests | LOCAL | Yes | Yes |
| lint_code | LOCAL | Yes | Yes |
| git_status | LOCAL | Yes | Yes |
| git_diff | LOCAL | Yes | Yes |
| git_log | LOCAL | Yes | Yes |
| git_branch | LOCAL | Yes | Yes |
| git_commit | LOCAL | Yes | Yes |
| code_search | LOCAL | Yes | Yes |
| web_search | EXTERNAL_API | Yes | **No** |
| http_request | EXTERNAL_API | Yes | **No** |
| download_file | EXTERNAL_DOWNLOAD | Yes | Yes |

---

## New Tools

### 1. HttpRequestTool

Make HTTP requests to REST APIs.

**Network Type**: `EXTERNAL_API` (blocked in offline mode)

**Capabilities**:
- HTTP methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- Custom headers support
- Request body for POST/PUT/PATCH
- Automatic JSON parsing
- Configurable timeout

**Example Usage**:
```python
from app.tools.registry import ToolRegistry

registry = ToolRegistry()
http_tool = registry.get_tool("http_request")

# GET request
result = await http_tool.execute(
    url="https://api.example.com/users",
    method="GET",
    timeout=30
)

# POST request with JSON body
result = await http_tool.execute(
    url="https://api.example.com/users",
    method="POST",
    headers={"Authorization": "Bearer token123"},
    body='{"name": "John", "email": "john@example.com"}'
)

# Response structure
# result.output = {
#     "status_code": 200,
#     "status_text": "OK",
#     "headers": {...},
#     "body": {...} or "string",
#     "is_json": True/False,
#     "message": "HTTP GET https://... -> 200 OK"
# }
```

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Target URL (http/https) |
| method | string | No | GET | HTTP method |
| headers | object | No | {} | Request headers |
| body | string | No | null | Request body |
| timeout | integer | No | 30 | Timeout in seconds (max 300) |

**Error Handling**:
- Timeout: Returns error with timeout message
- Connection errors: Returns detailed error message
- HTTP errors (4xx, 5xx): success=False with response data

---

### 2. DownloadFileTool

Download files from URLs using wget or curl.

**Network Type**: `EXTERNAL_DOWNLOAD` (allowed in offline mode)

**Why Allowed in Offline Mode?**
- One-way data flow (data IN only)
- Does not send local data externally
- Safe for air-gapped networks

**Capabilities**:
- Automatic downloader detection (wget/curl)
- Resume and retry support (3 retries)
- Parent directory auto-creation
- File overwrite protection
- Download size reporting

**Example Usage**:
```python
from app.tools.registry import ToolRegistry

registry = ToolRegistry()
download_tool = registry.get_tool("download_file")

# Download a file
result = await download_tool.execute(
    url="https://example.com/data.zip",
    output_path="/tmp/data.zip",
    timeout=120,
    overwrite=False
)

# Result structure
# result.output = {
#     "url": "https://example.com/data.zip",
#     "output_path": "/tmp/data.zip",
#     "file_size_bytes": 1048576,
#     "file_size_mb": 1.0,
#     "downloader": "wget",
#     "message": "Downloaded 1.00 MB to /tmp/data.zip"
# }
```

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | Yes | - | Download URL (http/https/ftp) |
| output_path | string | Yes | - | Local save path |
| timeout | integer | No | 60 | Timeout in seconds (max 3600) |
| overwrite | boolean | No | false | Overwrite existing file |

**Prerequisites**:
- `wget` or `curl` must be installed on the system
- Tool auto-detects available downloader

---

## API Reference

### Check Tool Availability

```python
from app.tools.registry import ToolRegistry

registry = ToolRegistry()

# Get tool (returns None if unavailable in current mode)
tool = registry.get_tool("http_request")
if tool is None:
    print("Tool unavailable in current network mode")

# Check availability explicitly
tool = registry.get_tool("http_request", check_availability=False)
if not tool.is_available_in_mode("offline"):
    print(tool.get_unavailable_message())
```

### Get Statistics

```python
registry = ToolRegistry()
stats = registry.get_statistics()

# stats = {
#     "total_tools": 16,
#     "available_tools": 14,  # in offline mode
#     "disabled_tools": 2,
#     "network_mode": "offline",
#     "categories": {...}
# }
```

### List Available Tools

```python
# List only available tools (respects network mode)
available_tools = registry.list_tools()

# List all tools including unavailable
all_tools = registry.list_tools(include_unavailable=True)
```

---

## Installation

### Dependencies

```bash
# Required for HttpRequestTool
pip install aiohttp

# Required for DownloadFileTool (system packages)
# Ubuntu/Debian:
apt-get install wget curl

# macOS:
brew install wget curl
```

### Environment Setup

```bash
# Copy example environment
cp .env.example .env

# Edit network mode
# NETWORK_MODE=online   # Development (all tools)
# NETWORK_MODE=offline  # Production/Secure network
```

---

## Testing

### Run Phase 2 Tests

```bash
# Network mode tests (44 tests)
pytest backend/app/tools/tests/test_network_mode.py -v

# Web tools tests (41 tests)
pytest backend/app/tools/tests/test_web_tools_phase2.py -v

# All tests (85 tests)
pytest backend/app/tools/tests/test_network_mode.py \
       backend/app/tools/tests/test_web_tools_phase2.py -v
```

### Manual Testing

```python
import asyncio
from app.tools.web_tools import HttpRequestTool, DownloadFileTool

async def test_http():
    tool = HttpRequestTool()
    result = await tool.execute(
        url="https://httpbin.org/get",
        method="GET"
    )
    print(f"Success: {result.success}")
    print(f"Status: {result.output['status_code']}")

async def test_download():
    tool = DownloadFileTool()
    result = await tool.execute(
        url="https://httpbin.org/robots.txt",
        output_path="/tmp/robots.txt"
    )
    print(f"Success: {result.success}")
    print(f"Size: {result.output['file_size_mb']} MB")

# Run tests
asyncio.run(test_http())
asyncio.run(test_download())
```

---

## Troubleshooting

### HttpRequestTool Issues

**Problem**: `aiohttp package not installed`
```bash
pip install aiohttp
```

**Problem**: Tool returns None
```python
# Check if in offline mode
import os
print(os.getenv("NETWORK_MODE"))  # Should be "online"
```

**Problem**: Timeout errors
```python
# Increase timeout for slow APIs
result = await tool.execute(url="...", timeout=120)
```

### DownloadFileTool Issues

**Problem**: `Neither wget nor curl found`
```bash
# Install wget
apt-get install wget  # Linux
brew install wget     # macOS
```

**Problem**: `File already exists`
```python
# Use overwrite option
result = await tool.execute(
    url="...",
    output_path="...",
    overwrite=True
)
```

**Problem**: Permission denied
```bash
# Check directory permissions
ls -la /path/to/directory
chmod 755 /path/to/directory
```

---

## Migration Guide

### From Phase 1 to Phase 2

1. **No breaking changes** - All Phase 1 tools work unchanged
2. **Environment variable** - Add `NETWORK_MODE=online` to .env
3. **New dependencies** - Install `aiohttp` for HttpRequestTool

### Updating Code

```python
# Before (Phase 1)
registry = ToolRegistry()
tool = registry.get_tool("web_search")

# After (Phase 2) - Same API, now with network mode checking
registry = ToolRegistry()
tool = registry.get_tool("web_search")  # Returns None in offline mode

# Safe pattern
tool = registry.get_tool("web_search")
if tool:
    result = await tool.execute(query="...")
else:
    print("Tool unavailable in current network mode")
```

---

## Best Practices

### 1. Check Tool Availability

```python
tool = registry.get_tool("http_request")
if tool is None:
    # Handle unavailability gracefully
    logger.warning("HttpRequestTool unavailable, using fallback")
    return fallback_result()
```

### 2. Use Appropriate Timeouts

```python
# Short timeout for quick APIs
await http_tool.execute(url="...", timeout=10)

# Long timeout for file downloads
await download_tool.execute(url="...", timeout=300)
```

### 3. Handle Errors

```python
result = await tool.execute(...)
if not result.success:
    logger.error(f"Tool failed: {result.error}")
    # Handle error appropriately
```

---

## Related Documentation

- [Phase 1 README](./AGENT_TOOLS_PHASE1_README.md) - Original tools documentation
- [Network Mode Design](./AGENT_TOOLS_NETWORK_MODE_DESIGN.md) - Architecture details
- [Session Handover](./SESSION_HANDOVER_AGENT_TOOLS_PHASE2.md) - Implementation summary

---

**Author**: Claude (Agent Tools Phase 2)
**Last Updated**: 2026-01-08
