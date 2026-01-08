# Agentic Coder CLI

Interactive command-line interface for Agentic Coder - an AI-powered coding assistant.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/KIMSUNGHOON/Agentic Coder.git
cd Agentic Coder

# Install in development mode
pip install -e .

# Or install from the repository root
pip install .
```

### Basic Usage

```bash
# Start interactive mode
agentic-coder

# Or from the repository
python -m cli

# One-shot mode (single command)
agentic-coder "Create a Python calculator"

# Specify workspace
agentic-coder -w ./my-project

# Resume previous session
agentic-coder -s session-20260108-123456

# Use different model
agentic-coder -m qwen2.5-coder:32b
```

## 📖 Features

### Interactive REPL Mode

- **Conversational Interface**: Natural language interaction with AI
- **Session Persistence**: Automatically saves conversation history
- **Rich Terminal UI**: Beautiful formatting with syntax highlighting
- **Streaming Progress**: Real-time feedback on agent execution
- **Context Awareness**: Tracks files, errors, and decisions

### Slash Commands

Use special commands in interactive mode:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show current session status |
| `/history` | Show conversation history |
| `/context` | Show extracted context (files, errors, decisions) |
| `/files` | Show generated/modified files |
| `/sessions` | List all saved sessions |
| `/clear` | Clear terminal screen |
| `/exit` or `/quit` | Exit CLI (also Ctrl+D) |

### Session Management

Sessions are automatically saved to `.agentic-coder/sessions/` in your workspace:

```
.agentic-coder/
└── sessions/
    ├── session-20260108-123456.json
    └── session-20260108-134502.json
```

Each session contains:
- Conversation history
- Metadata (model, workspace, timestamps)
- Generated files and artifacts

## 🎯 Usage Examples

### Example 1: Create a New Feature

```bash
$ agentic-coder -w ./my-app

You: Create a Python function to calculate fibonacci numbers with memoization

AI: I'll create an efficient fibonacci function with memoization...

📁 Files:
CREATED  fibonacci.py  25 lines

You: /status

Session ID      session-20260108-123456
Workspace       /home/user/my-app
Model           deepseek-r1:14b
Total Messages  2
...
```

### Example 2: Resume Previous Session

```bash
$ agentic-coder -s session-20260108-123456 -w ./my-app

Resuming session: session-20260108-123456

You: Now add unit tests for the fibonacci function

AI: I'll create comprehensive unit tests...

📁 Files:
CREATED  test_fibonacci.py  45 lines
```

### Example 3: One-Shot Mode

```bash
$ agentic-coder "Add type hints to all functions in utils.py"

Executing: Add type hints to all functions in utils.py

AI: Analyzing utils.py and adding type hints...

📁 Files:
MODIFIED  utils.py  120 lines
```

## 🛠️ Command Line Options

```
usage: agentic-coder [-h] [-w WORKSPACE] [-s SESSION_ID] [-m MODEL]
                     [--version] [--debug] [--no-save] [prompt ...]

Options:
  -h, --help            Show help message and exit
  -w, --workspace DIR   Workspace directory (default: current directory)
  -s, --session-id ID   Session ID to resume (default: create new)
  -m, --model MODEL     LLM model to use (default: deepseek-r1:14b)
  --version             Show version and exit
  --debug               Enable debug logging
  --no-save             Don't save session history
```

## 📦 Architecture

### Components

```
backend/cli/
├── __main__.py         # CLI entry point with argparse
├── session_manager.py  # Session persistence and workflow integration
├── terminal_ui.py      # Rich-based terminal interface
└── test_cli_basic.py   # Unit tests
```

### Integration with Existing System

The CLI reuses the existing Agentic Coder backend:

```
Agentic Coder/
├── backend/
│   ├── app/
│   │   ├── agent/           # ✅ Reused - LangGraph agents
│   │   ├── core/            # ✅ Reused - Supervisor, config
│   │   └── utils/           # ✅ Reused - ContextManager, RAG
│   └── cli/                 # 🆕 New - CLI interface
├── bin/
│   └── agentic-coder        # Executable script
└── setup.py                 # Package configuration
```

## 🔧 Development

### Running Tests

```bash
# Basic functionality tests
python backend/cli/test_cli_basic.py

# Run with debug output
python -m cli --debug "Test prompt"
```

### Development Mode

```bash
# Install in editable mode
pip install -e .

# Run directly from source
cd backend
python -m cli
```

## 📝 Session File Format

Sessions are stored as JSON:

```json
{
  "session_id": "session-20260108-123456",
  "metadata": {
    "created_at": "2026-01-08T12:34:56",
    "updated_at": "2026-01-08T12:45:30",
    "model": "deepseek-r1:14b",
    "workspace": "/home/user/my-app",
    "message_count": 4
  },
  "conversation_history": [
    {
      "role": "user",
      "content": "Create a calculator",
      "timestamp": "2026-01-08T12:34:56"
    },
    {
      "role": "assistant",
      "content": "I'll create a calculator...",
      "timestamp": "2026-01-08T12:35:10"
    }
  ]
}
```

## 🎨 Rich Terminal Features

- **Markdown Rendering**: AI responses are formatted as Markdown
- **Syntax Highlighting**: Code blocks with language detection
- **Progress Indicators**: Spinners and progress bars for long operations
- **Color Coding**:
  - 🟢 Green: Created files
  - 🟡 Yellow: Modified files
  - 🔴 Red: Deleted files
  - 🔵 Cyan: User prompts
  - 🟣 Magenta: AI responses

## 🔄 Workflow Integration

The CLI integrates seamlessly with the existing DynamicWorkflowManager:

```python
# SessionManager.execute_streaming_workflow()
async for update in workflow_mgr.execute_streaming_workflow(
    user_request=user_request,
    workspace_dir=str(workspace),
    conversation_history=conversation_history
):
    # Stream updates:
    # - agent_start: Agent begins working
    # - agent_stream: Streaming content chunks
    # - agent_end: Agent completes
    # - artifact: File created/modified/deleted
    # - final_response: Complete response
    # - error: Error occurred
```

## 🚧 Current Status

### ✅ Phase 1 Complete (Basic CLI Structure)

- [x] CLI entry point with argparse
- [x] SessionManager for persistence
- [x] TerminalUI with Rich console
- [x] Slash command system
- [x] Session save/resume
- [x] Basic tests passing
- [x] Package configuration (setup.py)

### 🔜 Phase 2 Next (Streaming UI)

- [ ] Enhanced progress indicators with agent-specific messages
- [ ] Real-time content streaming with Live display
- [ ] Artifact display with file previews
- [ ] Markdown rendering improvements
- [ ] Code syntax highlighting

### 📅 Future Phases

- **Phase 3**: Settings system, advanced slash commands, file preview
- **Phase 4**: Packaging, documentation, cross-platform testing
- **Phase 5**: Plugin system, RAG integration, full TUI (optional)

## 🐛 Troubleshooting

### Import Errors

```bash
# Ensure backend is in Python path
export PYTHONPATH=/path/to/Agentic Coder/backend:$PYTHONPATH

# Or run from backend directory
cd backend
python -m cli
```

### Session Not Found

```bash
# List available sessions
agentic-coder
You: /sessions

# Use exact session ID
agentic-coder -s session-20260108-123456
```

### Rich Display Issues

```bash
# Check terminal supports colors
echo $TERM

# Try forcing color output
export FORCE_COLOR=1
agentic-coder
```

## 📚 Related Documentation

- [CLI Migration Plan](./CLI_MIGRATION_PLAN.md) - Detailed migration strategy
- [CLI Implementation Todos](./CLI_IMPLEMENTATION_TODOS.md) - Task breakdown
- [Main README](../README.md) - Project overview

## 📄 License

Same as Agentic Coder project (MIT License)

---

**Version**: 1.0.0
**Last Updated**: 2026-01-08
**Status**: Phase 1 Complete ✅
