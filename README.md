# TestCodeAgent - Full Stack AI Coding Assistant

A production-ready AI coding assistant implementing **Unified Workflow Architecture** similar to Claude Code and OpenAI Codex.

[한국어 문서 (Korean Documentation)](README_KO.md)

---

## Overview

TestCodeAgent is an enterprise-grade AI-powered coding assistant that provides:

- **Intelligent Code Generation** - Multi-step code generation with planning and review
- **Multi-Model Support** - DeepSeek-R1, Qwen3-Coder, GPT-OSS, and more
- **Agent Tools** - 20 specialized tools for file, git, code, web, and sandbox operations
- **Network Mode** - Online/Offline mode for secure air-gapped environments
- **Sandbox Execution** - Docker-based isolated code execution

---

## Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Unified Chat Endpoint                         │
│                    POST /chat/unified                            │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    UnifiedAgentManager                           │
│  - Session context management                                    │
│  - Supervisor analysis request                                   │
│  - Response type routing                                         │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SupervisorAgent                               │
│  - Request analysis (Reasoning LLM)                             │
│  - Response type determination                                   │
│  - Complexity evaluation                                         │
└─────────────────────────────────────────────────────────────────┘
    │
    ├─► QUICK_QA ─────────► Direct LLM Response
    ├─► PLANNING ─────────► PlanningHandler (plan + file save)
    ├─► CODE_GENERATION ──► CodeGenerationHandler (workflow)
    ├─► CODE_REVIEW ──────► CodeReviewHandler
    └─► DEBUGGING ────────► DebuggingHandler
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ResponseAggregator                            │
│  - UnifiedResponse generation                                    │
│  - Next Actions suggestions                                      │
│  - Context DB storage                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Unified Workflow** | Single entry point with intelligent routing |
| **Multi-Model Support** | DeepSeek-R1, Qwen3-Coder, GPT-OSS with auto-detection |
| **Context Persistence** | Conversation and task context stored in DB |
| **Real-time Streaming** | Code generation with live progress display |
| **Korean Language Support** | Native Korean NLP with verb stem pattern matching |

### Agent Tools (20 Tools)

| Phase | Tools | Description |
|-------|-------|-------------|
| **Phase 1** | 14 tools | File, Git, Code, Search operations |
| **Phase 2** | 2 tools | HTTP requests, File downloads with network mode |
| **Phase 2.5** | 3 tools | Code formatting, Shell commands, Docstring generation |
| **Phase 4** | 1 tool | Sandbox execution (Docker-based isolation) |

### Network Mode System

| Mode | Description | EXTERNAL_API Tools |
|------|-------------|--------------------|
| `online` | All tools available | Enabled |
| `offline` | Secure/air-gapped mode | Blocked |

---

## Quick Start

### Prerequisites

1. **vLLM Server** (start before app):
   ```bash
   # Terminal 1: Reasoning Model
   vllm serve deepseek-ai/DeepSeek-R1 --port 8001

   # Terminal 2: Coding Model
   vllm serve Qwen/Qwen3-8B-Coder --port 8002
   ```

2. **Python 3.12+** and **Node.js 20+**

3. **Docker** (for sandbox execution)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-org/TestCodeAgent.git
cd TestCodeAgent

# 2. Environment setup
cp .env.example .env
# Edit .env with your configuration

# 3. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Frontend setup
cd ../frontend
npm install

# 5. (Optional) Pull sandbox image for isolated execution
docker pull ghcr.io/agent-infra/sandbox:latest
```

### Running the Application

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

Access the application at: http://localhost:5173

### Mock Mode (Testing without vLLM)

```bash
./RUN_MOCK.sh  # Linux/Mac
RUN_MOCK.bat   # Windows
```

---

## Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_ENDPOINT=http://localhost:8001/v1
LLM_MODEL=deepseek-ai/DeepSeek-R1

# Task-specific models
VLLM_REASONING_ENDPOINT=http://localhost:8001/v1
VLLM_CODING_ENDPOINT=http://localhost:8002/v1
REASONING_MODEL=deepseek-ai/DeepSeek-R1
CODING_MODEL=Qwen/Qwen3-8B-Coder

# Network Mode (online/offline)
NETWORK_MODE=online

# Sandbox Configuration
SANDBOX_IMAGE=ghcr.io/agent-infra/sandbox:latest
SANDBOX_HOST=localhost
SANDBOX_PORT=8080
SANDBOX_TIMEOUT=60
```

See [.env.example](.env.example) for full configuration options.

---

## Agent Tools

### Tool Categories

| Category | Tools | Network Type |
|----------|-------|--------------|
| **FILE** | read_file, write_file, search_files, list_directory | LOCAL |
| **GIT** | git_status, git_diff, git_log, git_branch, git_commit | LOCAL |
| **CODE** | execute_python, run_tests, lint_code, format_code, shell_command, generate_docstring, sandbox_execute | LOCAL |
| **SEARCH** | code_search, web_search | LOCAL / EXTERNAL_API |
| **WEB** | http_request, download_file | EXTERNAL_API / EXTERNAL_DOWNLOAD |

### Tool Availability by Network Mode

| Tool | Online | Offline | Phase |
|------|--------|---------|-------|
| read_file | ✅ | ✅ | 1 |
| write_file | ✅ | ✅ | 1 |
| git_* (5 tools) | ✅ | ✅ | 1 |
| code_search | ✅ | ✅ | 1 |
| web_search | ✅ | ❌ | 1 |
| http_request | ✅ | ❌ | 2 |
| download_file | ✅ | ✅ | 2 |
| format_code | ✅ | ✅ | 2.5 |
| shell_command | ✅ | ✅ | 2.5 |
| generate_docstring | ✅ | ✅ | 2.5 |
| sandbox_execute | ✅ | ✅ | 4 |

### Sandbox Execution

Execute code in isolated Docker containers:

```python
from app.tools.registry import ToolRegistry

registry = ToolRegistry()
sandbox = registry.get_tool("sandbox_execute")

# Python execution
result = await sandbox.execute(
    code="print('Hello, World!')",
    language="python",
    timeout=60
)

# Shell execution
result = await sandbox.execute(
    code="ls -la && cat /etc/os-release",
    language="shell"
)
```

**Offline Setup:**
```bash
# Pull image once (requires internet)
docker pull ghcr.io/agent-infra/sandbox:latest

# Image is cached locally - works offline after first pull
```

---

## API Endpoints

### Unified Chat (Non-streaming)

```
POST /chat/unified
```

```json
{
  "message": "Create a calculator in Python",
  "session_id": "session-123",
  "workspace": "/home/user/workspace"
}
```

**Response:**
```json
{
  "response_type": "code_generation",
  "content": "## Code Generation Complete\n\n...",
  "artifacts": [...],
  "next_actions": ["Run tests", "Request code review"],
  "session_id": "session-123",
  "success": true
}
```

### Unified Chat (Streaming)

```
POST /chat/unified/stream
```

---

## Project Structure

```
TestCodeAgent/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── agent/
│   │   │   ├── unified_agent_manager.py
│   │   │   └── handlers/              # Response type handlers
│   │   ├── tools/                     # Agent tools (20 tools)
│   │   │   ├── base.py                # BaseTool, ToolResult
│   │   │   ├── registry.py            # ToolRegistry
│   │   │   ├── file_tools.py          # File operations
│   │   │   ├── git_tools.py           # Git operations
│   │   │   ├── code_tools.py          # Code operations
│   │   │   ├── code_tools_phase25.py  # Phase 2.5 tools
│   │   │   ├── search_tools.py        # Search tools
│   │   │   ├── web_tools.py           # HTTP/download tools
│   │   │   ├── sandbox_tools.py       # Sandbox execution
│   │   │   └── performance.py         # Connection pool, caching
│   │   └── api/
│   │       └── main_routes.py         # API endpoints
│   ├── core/
│   │   ├── supervisor.py              # SupervisorAgent
│   │   ├── response_aggregator.py     # UnifiedResponse
│   │   └── context_store.py           # Context storage
│   └── shared/
│       └── llm/
│           ├── base.py                # LLMProvider interface
│           └── adapters/              # Model-specific adapters
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── WorkflowInterface.tsx  # Unified mode UI
│       │   ├── NextActionsPanel.tsx   # Action buttons
│       │   └── PlanFileViewer.tsx     # Plan file viewer
│       └── api/
│           └── client.ts              # API client
├── docs/                              # Documentation
├── .env.example                       # Configuration template
└── README.md                          # This file
```

---

## Testing

### Run All Tests

```bash
cd backend
pytest app/tools/tests/ -v

# Results: 262 passed, 6 skipped
```

### Test Modules

| Module | Tests | Description |
|--------|-------|-------------|
| test_network_mode.py | 44 | Network mode system |
| test_web_tools_phase2.py | 41 | HTTP and download tools |
| test_code_tools_phase25.py | 53 | Code formatting, shell, docstring |
| test_sandbox_tools.py | 38 | Sandbox execution |
| test_performance.py | 24 | Connection pool, caching |
| test_e2e.py | 21 | End-to-end integration |
| test_integration.py | 17 | Tool integration |

---

## Documentation

| Document | Description |
|----------|-------------|
| [AGENT_TOOLS_PHASE2_README.md](docs/AGENT_TOOLS_PHASE2_README.md) | Complete Agent Tools documentation |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture details |
| [MOCK_MODE.md](docs/MOCK_MODE.md) | Mock mode testing guide |
| [CLI_PHASE3_USER_GUIDE.md](docs/CLI_PHASE3_USER_GUIDE.md) | CLI interface guide |

---

## Development History

### Phase 4 (Current) - Sandbox Execution
- **SandboxExecuteTool** - Docker-based isolated code execution
- **AIO Sandbox integration** - Uses pre-built development environment
- **Multi-language support** - Python, Node.js, TypeScript, Shell
- **Offline-ready** - Works with locally cached Docker images

### Phase 3 - Performance Optimization
- **Connection Pooling** - Shared HTTP connections
- **Result Caching** - LRU cache with TTL
- **Progress Tracking** - Real-time download progress

### Phase 2.5 - Code Tools
- **FormatCodeTool** - Black/autopep8/yapf formatting
- **ShellCommandTool** - Safe shell execution with blocklist
- **DocstringGeneratorTool** - Auto-generate docstrings

### Phase 2 - Network Mode
- **Network Mode System** - Online/Offline control
- **HttpRequestTool** - REST API calls
- **DownloadFileTool** - File downloads with progress

### Phase 1 - Foundation
- 14 core tools (file, git, code, search)
- Tool registry system
- Basic tool execution framework

---

## Supported LLM Models

| Model | Characteristics | Prompt Format |
|-------|-----------------|---------------|
| DeepSeek-R1 | Reasoning model | `<think></think>` tags |
| Qwen3-Coder | Coding specialized | Standard prompts |
| GPT-OSS | OpenAI Harmony | Structured reasoning |

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Maintained by**: TestCodeAgent Team
**Last Updated**: 2026-01-08
