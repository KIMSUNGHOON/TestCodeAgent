# Agentic Coder - Development Roadmap

**Last Updated**: 2026-01-09
**Current Version**: 1.2.0
**Status**: Phase 6 Complete

---

## Overview

This document tracks the development progress of Agentic Coder, including completed work, ongoing development, and future plans.

---

## Completed Phases

### Phase 1: Core Tools (14 Tools)

**Status**: Complete

Core agent tools for file operations, Git, and code execution.

| Category | Tools | Description |
|----------|-------|-------------|
| **File Operations** | `read_file`, `write_file`, `search_files`, `list_directory` | Basic file system operations |
| **Git Operations** | `git_status`, `git_diff`, `git_log`, `git_branch`, `git_commit` | Version control integration |
| **Code Execution** | `execute_python`, `run_tests`, `lint_code` | Code running and validation |
| **Search** | `code_search`, `web_search` | Semantic code and web search |

---

### Phase 2: Network Mode + Web Tools

**Status**: Complete
**Commit**: `a266500`

Added network security modes and HTTP tools for enterprise environments.

#### New Tools
| Tool | Network Type | Description |
|------|--------------|-------------|
| `http_request` | EXTERNAL_API | REST API calls (blocked in offline mode) |
| `download_file` | EXTERNAL_DOWNLOAD | File downloads (allowed in offline mode) |

#### Network Modes
| Mode | Description | Blocked Tools |
|------|-------------|---------------|
| `online` | Full functionality | None |
| `offline` | Air-gapped/secure environments | `web_search`, `http_request` |

**Security Policy**:
- **Block**: Tools that send data externally (interactive)
- **Allow**: Tools that only receive data (downloads)
- **Allow**: All local tools (file, git, code)

---

### Phase 2.5: Code Formatting Tools

**Status**: Complete
**Commit**: `7571753`

| Tool | Description |
|------|-------------|
| `format_code` | Auto-format code (Black, Prettier) |
| `shell_command` | Execute shell commands |
| `generate_docstring` | Generate docstrings for functions |

---

### Phase 3: CLI & Performance Optimization

**Status**: Complete
**Commit**: `dd4860d`

#### CLI Features
- **Interactive REPL Mode**: Conversational coding interface
- **One-shot Mode**: Single command execution
- **Session Management**: Persistent conversation history (`.agentic-coder/sessions/`)
- **Command History**: prompt_toolkit with persistent history
- **Auto-completion**: Tab completion for commands and files
- **Configuration**: YAML-based config (`~/.agentic-coder/config.yaml`)
- **Slash Commands**: `/help`, `/status`, `/history`, `/context`, `/files`, `/preview`

#### Key Files
| File | Description |
|------|-------------|
| `backend/cli/__main__.py` | CLI entry point with argparse |
| `backend/cli/session_manager.py` | Session persistence and workflow integration |
| `backend/cli/terminal_ui.py` | Rich-based terminal interface |
| `backend/cli/interactive.py` | prompt_toolkit integration |
| `backend/cli/config.py` | Configuration management |

---

### Phase 4: Sandbox Execution

**Status**: Complete
**Commit**: `6c3411e`

Docker-based isolated code execution using AIO Sandbox.

#### New Tool
| Tool | Description |
|------|-------------|
| `sandbox_execute` | Execute code in isolated Docker container |

#### Supported Languages
- Python (via Jupyter API)
- Node.js / TypeScript (via Shell API)
- Shell/Bash

#### Key Components
| Component | Description |
|-----------|-------------|
| `SandboxConfig` | Configuration with environment variable support |
| `SandboxManager` | Singleton Docker container lifecycle manager |
| `SandboxExecuteTool` | Main tool for code execution |
| `SandboxFileManager` | File operations inside sandbox |

#### Configuration (.env)
```bash
SANDBOX_IMAGE=ghcr.io/agent-infra/sandbox:latest
SANDBOX_HOST=localhost
SANDBOX_PORT=8080
SANDBOX_TIMEOUT=60
SANDBOX_MEMORY=1g
SANDBOX_CPU=2.0
# Optional for enterprise: SANDBOX_REGISTRY=harbor.company.com
```

---

### Phase 5: Plan Mode with Approval Workflow

**Status**: Complete
**Commit**: Phase 5 implementation

Implementation of a planning phase before code generation, with human-in-the-loop approval.

#### Core Concept
```
User Request
    │
    ▼
┌─────────────────────┐
│ Plan Agent          │ ← Analyzes request, creates implementation plan
│ (Reasoning LLM)     │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ User Review         │ ← Approve / Modify / Reject plan
│ (PlanApprovalModal) │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Step-by-step        │ ← Execute with checkpoints
│ Execution           │
└─────────────────────┘
```

#### Implemented Features

**Plan Schema** (`backend/app/agent/langgraph/schemas/plan.py`):
- `ExecutionPlan`: Complete plan with steps, files, and risks
- `PlanStep`: Individual step with action, target, complexity, dependencies
- Status tracking: pending, in_progress, completed, failed, skipped

**PlanningHandler Enhancement** (`backend/app/agent/handlers/planning.py`):
- `generate_structured_plan()`: JSON-based structured plan generation
- `generate_structured_plan_stream()`: Streaming plan generation
- Automatic complexity and risk assessment

**Plan API** (`backend/app/api/routes/plan_routes.py`):
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plan/generate` | POST | Generate new plan |
| `/api/plan/{plan_id}` | GET | Get plan details |
| `/api/plan/{plan_id}/approve` | POST | Approve plan |
| `/api/plan/{plan_id}/modify` | POST | Modify plan steps |
| `/api/plan/{plan_id}/reject` | POST | Reject plan |
| `/api/plan/{plan_id}/execute` | POST | Start execution |
| `/api/plan/{plan_id}/execute/stream` | GET | Stream execution (SSE) |
| `/api/plan/{plan_id}/status` | GET | Get execution status |

**Plan Executor** (`backend/app/agent/langgraph/nodes/plan_executor.py`):
- Step-by-step execution with progress tracking
- Dependency checking between steps
- HITL integration for steps requiring approval
- Error handling with rollback support

**Frontend Components**:
- `PlanApprovalModal.tsx`: Plan review and approval UI
- API client methods for all plan operations

**Plan Structure Example**:
```json
{
  "plan_id": "plan-abc12345",
  "steps": [
    {
      "step": 1,
      "action": "create_file",
      "target": "src/calculator.py",
      "description": "Create main calculator module",
      "requires_approval": false,
      "estimated_complexity": "low",
      "dependencies": []
    },
    {
      "step": 2,
      "action": "create_file",
      "target": "tests/test_calculator.py",
      "description": "Create unit tests",
      "requires_approval": false,
      "estimated_complexity": "low",
      "dependencies": [1]
    }
  ],
  "estimated_files": ["src/calculator.py", "tests/test_calculator.py"],
  "risks": ["None identified for this simple task"],
  "approval_status": "pending"
}
```

#### Available Actions
| Action | Description |
|--------|-------------|
| `create_file` | Create a new file |
| `modify_file` | Modify existing file |
| `delete_file` | Delete a file |
| `run_tests` | Run test suite |
| `run_lint` | Run linter |
| `install_deps` | Install dependencies |
| `review_code` | Review code for issues |
| `refactor` | Refactor existing code |

---

## Tool Summary

**Total: 20 Tools**

| Phase | Tools Added | Running Total |
|-------|-------------|---------------|
| Phase 1 | 14 | 14 |
| Phase 2 | 2 | 16 |
| Phase 2.5 | 3 | 19 |
| Phase 4 | 1 | 20 |

---

### Phase 6: Context Window Optimization

**Status**: Complete
**Commit**: Phase 6 implementation

Improved context management for large codebases and long conversations.

#### Implemented Features

**1. Enhanced Token Utilities** (`shared/utils/token_utils.py`):
- `count_tokens_accurate()`: Word-based token estimation with CJK support
- `check_context_budget()`: Context token budget management
- `truncate_to_budget()`: Smart text truncation
- Model-specific token limits (GPT-4, Claude, etc.)

**2. Context Compressor** (`backend/core/context_compressor.py`) - NEW:
- Smart message compression with priority-based retention
- Important content extraction (code, errors, file paths)
- Sliding window with compressed history
- ~34% token savings on test data

**3. Expanded Context Window**:
```python
# Before (Phase 5)
MAX_MESSAGES = 50
RECENT_MESSAGES_FOR_LLM = 20
RECENT_MESSAGES_FOR_CONTEXT = 10
MAX_CONTENT_PER_MESSAGE = 200  # handlers

# After (Phase 6)
MAX_MESSAGES = 100
RECENT_MESSAGES_FOR_LLM = 30
RECENT_MESSAGES_FOR_CONTEXT = 20
MAX_CONTENT_PER_MESSAGE = 2000  # handlers
MAX_CONTENT_SUPERVISOR = 4000
RECENT_ARTIFACTS_FOR_CONTEXT = 20
```

**4. RAG Integration Enhancement** (`backend/app/services/rag_context.py`):
- Expanded conversation search: 3 → 5 results
- Expanded code search: 5 → 7 results
- MAX_CONTEXT_LENGTH: 8000 → 12000
- Compressed history integration support

#### Key Files
| File | Description |
|------|-------------|
| `shared/utils/token_utils.py` | Enhanced token counting and budget management |
| `backend/core/context_compressor.py` | Context compression engine (NEW) |
| `backend/core/context_store.py` | Expanded context window settings |
| `backend/core/supervisor.py` | Improved context formatting |
| `backend/app/agent/handlers/base.py` | Handler context expansion |
| `backend/app/services/rag_context.py` | RAG integration enhancement |

#### Performance Improvements
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Context messages | 6 | 20 | 233% |
| Message content | 200 chars | 2000 chars | 900% |
| Artifacts in context | 5 | 20 | 300% |
| Conversation search | 3 results | 5 results | 67% |
| Token savings (compression) | N/A | ~34% | NEW |

---

## Planned Phases

---

### Phase 7: MCP (Model Context Protocol) Integration

**Status**: Planned
**Priority**: Medium

Integration with Anthropic's Model Context Protocol.

#### Planned Features

**MCP Server Mode**:
- Expose all 20 tools as MCP-compatible endpoints
- Standardized tool schemas
- Compatible with Claude Desktop, etc.

**MCP Client Mode**:
- Connect to external MCP servers
- Dynamic tool discovery
- Tool chaining across servers

#### Benefits
- Interoperability with MCP ecosystem
- Easy tool sharing
- Standardized context management

---

### Phase 8: Multi-Agent Collaboration

**Status**: Planned
**Priority**: Low

Enable multiple specialized agents to work together.

#### Architecture
```
┌─────────────────────────────────────────┐
│           Supervisor Agent              │
│   (Task analysis and delegation)        │
└─────────────────────────────────────────┘
         │           │           │
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │Research │ │ Coder   │ │ Tester  │
    │ Agent   │ │ Agent   │ │ Agent   │
    └─────────┘ └─────────┘ └─────────┘
         │           │           │
         └───────────┴───────────┘
                     │
                     ▼
            ┌─────────────┐
            │ Aggregator  │
            └─────────────┘
```

#### Specialized Agents
| Agent | Role | Tools |
|-------|------|-------|
| Research Agent | Web search, documentation | `web_search`, `http_request` |
| Coder Agent | Code generation | `write_file`, `execute_python` |
| Tester Agent | Test execution | `run_tests`, `sandbox_execute` |
| Reviewer Agent | Code review | `read_file`, `lint_code` |

---

## Performance Optimization Notes

### GPU Configuration (H100)
```python
# Recommended for H100 96GB NVL
max_parallel_agents = 25  # (default: 10)
```

### Session Pipelining
```
Session A: [Planning@GPU0] → [Coding@GPU1] → [Review@GPU1]
Session B:                    [Planning@GPU0] → [Coding@GPU1]
                                            ↑ GPU0 can handle Session B
```

### Expected Improvements
- GPU utilization: 40% → 80%+
- Workflow completion: 30-40% faster
- Multi-user throughput: 3x improvement

---

## Feature Backlog

### High Priority
| Feature | Description | Phase |
|---------|-------------|-------|
| Plan Mode | Pre-implementation planning | 5 |
| Context Optimization | Smart context management | 6 |
| Error Recovery | Automatic retry and correction | 5 |

### Medium Priority
| Feature | Description | Phase |
|---------|-------------|-------|
| MCP Support | Model Context Protocol | 7 |
| Plugin System | User-defined tool extensions | - |
| Git Auto-commit | Automatic commit management | - |
| File Watching | React to file changes | - |

### Low Priority
| Feature | Description | Phase |
|---------|-------------|-------|
| Multi-Agent | Parallel agent execution | 8 |
| Web UI Improvements | Enhanced frontend | - |
| RAG Enhancement | Embeddings-based search | 6 |
| Metrics Dashboard | Usage tracking | - |

---

## Known Limitations

1. **Single Model per Role**: Only one reasoning + one coding model
2. ~~**No Plan Mode**: Code generation starts immediately~~ (Resolved in Phase 5)
3. ~~**Limited Context**: 6 messages, 200 chars~~ (Resolved in Phase 6: 20 messages, 2000 chars)
4. **No MCP**: Not compatible with MCP ecosystem yet
5. **Sequential Workflow**: Limited parallelization within single session

---

## Test Coverage

```
262 passed, 8 skipped, 3 warnings
```

- Phase 4 sandbox: 38 tests
- CLI: 2 tests skipped (optional `rich` dependency)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-01-09 | Phase 6 complete, Context Window Optimization |
| 1.1.0 | 2026-01-08 | Phase 5 complete, Plan Mode with Approval Workflow |
| 1.0.0 | 2026-01-08 | Phase 1-4 complete, 20 tools, CLI ready |
| 0.9.0 | 2026-01-07 | Phase 3 CLI enhancements |
| 0.8.0 | 2026-01-06 | Phase 2 network mode |
| 0.7.0 | 2026-01-05 | Phase 1 core tools |

---

## References

- [Architecture](./ARCHITECTURE.md) - System design
- [Agent Tools](./AGENT_TOOLS_PHASE2_README.md) - Tool documentation
- [CLI Guide](./CLI_README.md) - CLI usage
- [Main README](../README.md) - Project overview

---

**Maintainer**: Agentic Coder Team
**License**: MIT
