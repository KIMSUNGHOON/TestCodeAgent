# CLI Phase 3 - Enhanced Interactive Mode

**Version**: 3.0.0
**Date**: 2026-01-08
**Status**: Production Ready

---

## Overview

CLI Phase 3 introduces significant improvements to the interactive command-line experience:

- **Command History** - Persistent history with search
- **Auto-Completion** - Tab completion for commands and files
- **Configuration Management** - YAML-based config files
- **New Commands** - `/config`, `/model`, `/workspace`

---

## Quick Start

```bash
# Start interactive mode
python -m cli

# With options
python -m cli --workspace ./my-project --model qwen2.5-coder:32b

# One-shot mode
python -m cli "Create a Python calculator"
```

---

## New Features

### 1. Command History

Your command history is now saved and persists across sessions.

**Keyboard Shortcuts**:
| Key | Action |
|-----|--------|
| Up Arrow | Previous command |
| Down Arrow | Next command |
| Ctrl+R | Search history |
| Ctrl+P | Previous (vim style) |
| Ctrl+N | Next (vim style) |

**History File Location**:
```
~/.testcodeagent/history
```

**Configuration**:
```yaml
# ~/.testcodeagent/config.yaml
history:
  file: ~/.testcodeagent/history
  max_lines: 10000
  save: true
```

---

### 2. Auto-Completion

Press **Tab** to auto-complete commands and file paths.

**Slash Commands**:
```
/he<Tab>  ->  /help
/pr<Tab>  ->  /preview
/co<Tab>  ->  /config
```

**File Paths** (after `/preview`):
```
/preview sr<Tab>  ->  /preview src/
/preview src/ma<Tab>  ->  /preview src/main.py
```

**Completion Display**:
```
/p<Tab>
  /preview    Preview file with syntax highlighting
  /password   (if exists)
```

---

### 3. Configuration Management

Manage settings via YAML configuration files.

**Configuration Hierarchy** (highest to lowest priority):
1. Environment variables
2. Project config (`.testcodeagent/config.yaml`)
3. User config (`~/.testcodeagent/config.yaml`)
4. Default values

#### Create Default Config

```bash
# In CLI
/config init        # Creates ~/.testcodeagent/config.yaml
/config init project  # Creates .testcodeagent/config.yaml
```

#### View Configuration

```bash
/config             # Show current config
/config show        # Same as above
/config path        # Show config file locations
```

#### Update Configuration

```bash
/config set llm.model qwen2.5-coder:32b
/config set network.mode offline
/config set ui.theme dracula
/config set history.save false
```

#### Configuration File Format

```yaml
# ~/.testcodeagent/config.yaml
llm:
  model: deepseek-r1:14b
  api_endpoint: http://localhost:8001/v1
  max_tokens: 4096
  temperature: 0.7

ui:
  theme: monokai
  syntax_theme: monokai
  show_line_numbers: true
  word_wrap: false

history:
  file: ~/.testcodeagent/history
  max_lines: 10000
  save: true

session:
  auto_save: true
  dir: .testcodeagent/sessions

workspace:
  default: "."
  ignore_patterns:
    - .git
    - __pycache__
    - node_modules
    - .venv

network:
  mode: online
  timeout: 30

debug:
  enabled: false
  verbose: false
```

---

### 4. New Commands

#### `/config` - Configuration Management

```bash
/config              # Show current configuration
/config init         # Create default user config
/config init project # Create default project config
/config set KEY VALUE # Set configuration value
/config path         # Show config file paths
```

**Configuration Keys**:
| Key | Type | Description |
|-----|------|-------------|
| llm.model | string | LLM model name |
| llm.api_endpoint | string | API endpoint URL |
| llm.temperature | float | Temperature (0.0-1.0) |
| ui.theme | string | UI theme name |
| network.mode | string | online or offline |
| network.timeout | int | Request timeout |
| history.save | bool | Save command history |
| debug.enabled | bool | Enable debug mode |

---

#### `/model` - Model Management

```bash
/model               # Show current model
/model deepseek-r1:14b  # Change model
/model qwen2.5-coder:32b  # Change to different model
```

---

#### `/workspace` - Workspace Management

```bash
/workspace           # Show current workspace with stats
/workspace ./other   # Change workspace
/workspace /path/to/project  # Change to absolute path
```

**Output Example**:
```
Current Workspace: /home/user/TestCodeAgent
Files: 234, Directories: 45

To change: /workspace <path>
```

---

## All Available Commands

### Session Management
| Command | Description |
|---------|-------------|
| `/status` | Show session status |
| `/sessions` | List saved sessions |
| `/history` | Show conversation history |
| `/context` | Show extracted context |

### Workspace
| Command | Description |
|---------|-------------|
| `/files` | Show generated files |
| `/preview <file>` | Preview with syntax highlighting |
| `/workspace [path]` | Show or change workspace |
| `/clear` | Clear terminal |

### Configuration
| Command | Description |
|---------|-------------|
| `/config` | Show configuration |
| `/config init` | Create config file |
| `/config set <key> <value>` | Update setting |
| `/model [name]` | Show or change model |

### Utility
| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/exit`, `/quit` | Exit CLI |

---

## Keyboard Shortcuts

### Navigation
| Key | Action |
|-----|--------|
| Tab | Auto-complete |
| Up/Down | History navigation |
| Ctrl+R | Reverse history search |
| Ctrl+A | Move to line start |
| Ctrl+E | Move to line end |
| Ctrl+W | Delete word backward |
| Ctrl+K | Delete to end of line |

### Control
| Key | Action |
|-----|--------|
| Ctrl+C | Cancel current input |
| Ctrl+D | Exit CLI |
| Ctrl+L | Clear screen |

### Vi Mode (optional)
The CLI supports vi-style keybindings if configured in prompt_toolkit.

---

## Installation

### Dependencies

```bash
# Required for enhanced features
pip install prompt_toolkit pyyaml

# Already included
pip install rich
```

### Fallback Mode

If `prompt_toolkit` is not installed, the CLI falls back to basic input mode with limited features:
- No command history
- No auto-completion
- Basic input only

---

## Environment Variables

Override configuration via environment variables:

```bash
# Model
export TESTCODEAGENT_MODEL=qwen2.5-coder:32b
export LLM_MODEL=qwen2.5-coder:32b

# API endpoint
export TESTCODEAGENT_API_ENDPOINT=http://localhost:8001/v1
export LLM_ENDPOINT=http://localhost:8001/v1

# Network mode
export TESTCODEAGENT_NETWORK_MODE=offline
export NETWORK_MODE=offline

# Debug
export TESTCODEAGENT_DEBUG=true
```

---

## Tips and Tricks

### 1. Quick Model Switching

```bash
# Save typing with /model
/model deepseek-r1:14b

# Instead of
/config set llm.model deepseek-r1:14b
```

### 2. Preview Multiple Files

```bash
/preview src/main.py
/preview src/utils.py
/preview tests/test_main.py
```

### 3. Search History

Press `Ctrl+R` and type to search:
```
(reverse-i-search)`calc': Create a Python calculator
```

### 4. Clear and Start Fresh

```bash
/clear          # Clear screen
/status         # Check current state
```

### 5. Project-Specific Config

Create `.testcodeagent/config.yaml` in your project:
```yaml
llm:
  model: qwen2.5-coder:32b  # Override for this project

workspace:
  ignore_patterns:
    - build/
    - dist/
    - *.pyc
```

---

## Troubleshooting

### History Not Saving

1. Check config:
```bash
/config  # Look for history.save: true
```

2. Check permissions:
```bash
ls -la ~/.testcodeagent/
# Should be writable
```

3. Check file:
```bash
cat ~/.testcodeagent/history
```

### Auto-Completion Not Working

1. Check prompt_toolkit:
```python
python -c "import prompt_toolkit; print('OK')"
```

2. Reinstall:
```bash
pip install --upgrade prompt_toolkit
```

### Config Not Loading

1. Check syntax:
```bash
python -c "import yaml; yaml.safe_load(open('~/.testcodeagent/config.yaml'))"
```

2. Check path:
```bash
/config path
```

---

## Migration from Phase 2

No breaking changes. New features are additive:

1. **History** - Automatically enabled
2. **Completion** - Automatically enabled
3. **Config** - Optional, uses defaults if not present

---

## Related Documentation

- [CLI Main Documentation](../backend/cli/README.md)
- [Phase 2 README](./AGENT_TOOLS_PHASE2_README.md)
- [Session Handover](./SESSION_HANDOVER_AGENT_TOOLS_PHASE2.md)

---

**Author**: Claude (CLI Phase 3)
**Last Updated**: 2026-01-08
