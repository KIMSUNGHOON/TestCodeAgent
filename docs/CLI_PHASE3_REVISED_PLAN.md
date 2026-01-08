# CLI Phase 3: Revised Implementation Plan

**Based on**: CLI Tools Analysis Report v1.0
**Date**: 2026-01-08
**Estimated Duration**: 2-3 days (15-20 hours)
**Priority**: Essential enhancements for production readiness

---

## Overview

Phase 3 focuses on **essential enhancements** that significantly improve user experience with minimal complexity. Based on the tools analysis, we will:

1. **Add prompt_toolkit** for command history and autocomplete
2. **Implement settings system** for configuration management
3. **Add critical slash commands** (/diff, /tree, /export)
4. Keep current **argparse + Rich** stack (no migration needed)

---

## Phase 3 Goals

### Primary Objectives

✅ **User Experience**:
- Command history navigation (↑↓ arrows)
- Autocomplete for slash commands (Tab key)
- Persistent user preferences

✅ **Productivity**:
- File diff visualization
- Workspace tree view
- Session export to Markdown

✅ **Configuration**:
- Settings file (.testcodeagent/settings.json)
- Model selection
- Theme preferences

### Non-Goals (Deferred to Phase 4+)

❌ **Not in Phase 3**:
- Typer migration (current argparse works fine)
- Textual full TUI (too complex for current needs)
- Interactive file browser (low priority)
- Plugin system (future enhancement)

---

## Implementation Tasks

### Task Group 1: Enhanced Input with prompt_toolkit

**Priority**: 🔥 P0 (Critical)
**Estimated Time**: 5 hours
**Dependencies**: `prompt-toolkit >= 3.0.0`

#### T3.1.1: Install and Configure prompt_toolkit

**File**: `backend/requirements.txt`

```diff
# CLI dependencies
rich>=13.0.0
- click>=8.0.0  # Remove (not used)
+ prompt-toolkit>=3.0.0  # Add for enhanced input
```

**Validation**:
```bash
pip install prompt-toolkit
python -c "from prompt_toolkit import PromptSession; print('OK')"
```

#### T3.1.2: Create Input Handler Module

**File**: `backend/cli/utils/input.py` (NEW)

```python
"""Enhanced input handling with prompt_toolkit"""

from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory


class EnhancedInput:
    """Prompt toolkit-based input handler"""

    def __init__(self, history_file: Path, slash_commands: list):
        """Initialize enhanced input with history and autocomplete

        Args:
            history_file: Path to history file
            slash_commands: List of slash commands for autocomplete
        """
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Create completer for slash commands
        self.completer = WordCompleter(
            slash_commands,
            ignore_case=True,
            sentence=True
        )

        # Create prompt session
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer
        )

    def prompt(self, message: str = "You: ") -> str:
        """Get user input with history and autocomplete

        Args:
            message: Prompt message

        Returns:
            User input string
        """
        return self.session.prompt(message)
```

**Tests**:
```python
# backend/cli/test_input.py
def test_enhanced_input():
    inp = EnhancedInput(
        Path('.testcodeagent/history.txt'),
        ['/help', '/status', '/exit']
    )
    # Manual test: type /h and press Tab
    # Manual test: press ↑ for history
```

#### T3.1.3: Integrate into TerminalUI

**File**: `backend/cli/terminal_ui.py`

```python
from cli.utils.input import EnhancedInput

class TerminalUI:
    def __init__(self, session_mgr: SessionManager):
        self.session_mgr = session_mgr
        self.console = Console()

        # Initialize enhanced input
        history_file = session_mgr.workspace / '.testcodeagent' / 'history.txt'
        slash_commands = [
            '/help', '/status', '/history', '/context',
            '/files', '/preview', '/sessions', '/clear', '/exit',
            '/diff', '/tree', '/export', '/search'  # Include new commands
        ]

        self.input_handler = EnhancedInput(history_file, slash_commands)

    def start_interactive(self):
        """Start interactive REPL mode"""
        self._show_welcome()

        while True:
            try:
                # Use enhanced input instead of Rich Prompt
                user_input = self.input_handler.prompt("\n[You] ")

                # Rest of the code stays the same...
```

**Acceptance Criteria**:
- ✅ Press ↑ to see previous commands
- ✅ Press ↓ to navigate forward in history
- ✅ Type `/h` and press Tab → autocomplete to `/help`
- ✅ History persists across sessions

---

### Task Group 2: Settings System

**Priority**: 🔥 P0 (Critical)
**Estimated Time**: 4 hours

#### T3.2.1: Create Config Module

**File**: `backend/cli/config.py` (NEW)

```python
"""CLI configuration management"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class CLIConfig:
    """Manage CLI settings"""

    DEFAULT_SETTINGS = {
        "model": "deepseek-r1:14b",
        "auto_save_session": True,
        "syntax_theme": "monokai",
        "display_thinking": False,
        "max_history_items": 100,
        "default_workspace": ".",
        "color_scheme": "default"
    }

    def __init__(self, workspace: Path):
        """Initialize config for workspace

        Args:
            workspace: Workspace directory
        """
        self.workspace = workspace
        self.config_dir = workspace / ".testcodeagent"
        self.config_file = self.config_dir / "settings.json"
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create with defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                    # Merge with defaults (user settings override)
                    return {**self.DEFAULT_SETTINGS, **user_settings}
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in {self.config_file}, using defaults")
                return self.DEFAULT_SETTINGS.copy()
        else:
            # Create default settings file
            self.save_settings()
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """Save current settings to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value
        """
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set setting value and save

        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value
        self.save_settings()

    def reset(self):
        """Reset to default settings"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.save_settings()
```

#### T3.2.2: Add `/config` Slash Command

**File**: `backend/cli/terminal_ui.py`

```python
def _cmd_config(self, args: list):
    """Manage settings

    Usage:
        /config               # Show all settings
        /config <key>         # Show specific setting
        /config <key> <value> # Set setting value
        /config reset         # Reset to defaults
    """
    config = self.session_mgr.config

    if not args:
        # Show all settings
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="dim")
        table.add_column("Value")
        table.add_column("Default", style="dim")

        for key, default_value in CLIConfig.DEFAULT_SETTINGS.items():
            current_value = config.get(key)
            is_default = current_value == default_value

            table.add_row(
                key,
                str(current_value),
                str(default_value) + (" ✓" if is_default else "")
            )

        self.console.print(Panel(table, title="Settings", border_style="cyan"))

    elif args[0] == "reset":
        # Reset to defaults
        config.reset()
        self.console.print("[green]✓[/green] Settings reset to defaults")

    elif len(args) == 1:
        # Show specific setting
        key = args[0]
        value = config.get(key)
        if value is not None:
            self.console.print(f"{key} = {value}")
        else:
            self.console.print(f"[yellow]Unknown setting:[/yellow] {key}")

    elif len(args) >= 2:
        # Set setting value
        key = args[0]
        value = " ".join(args[1:])

        # Type conversion for known settings
        if key in ["auto_save_session", "display_thinking"]:
            value = value.lower() in ['true', '1', 'yes']
        elif key == "max_history_items":
            value = int(value)

        config.set(key, value)
        self.console.print(f"[green]✓[/green] {key} = {value}")
```

#### T3.2.3: Integrate Config into SessionManager

**File**: `backend/cli/session_manager.py`

```python
from cli.config import CLIConfig

class SessionManager:
    def __init__(
        self,
        workspace: str = ".",
        session_id: Optional[str] = None,
        model: Optional[str] = None,  # Now optional
        auto_save: Optional[bool] = None  # Now optional
    ):
        self.workspace = Path(workspace).resolve()

        # Load config
        self.config = CLIConfig(self.workspace)

        # Use config values if not explicitly provided
        self.model = model or self.config.get("model")
        self.auto_save = auto_save if auto_save is not None else self.config.get("auto_save_session")

        # ... rest of initialization
```

**Acceptance Criteria**:
- ✅ Settings file created on first run
- ✅ `/config` shows all settings
- ✅ `/config model` shows model setting
- ✅ `/config model qwen2.5-coder:32b` updates setting
- ✅ Settings persist across sessions

---

### Task Group 3: Essential Slash Commands

**Priority**: P1 (High)
**Estimated Time**: 8 hours

#### T3.3.1: Implement `/diff` Command

**File**: `backend/cli/terminal_ui.py`

```python
import difflib
from rich.syntax import Syntax

def _cmd_diff(self, args: list):
    """Show diff for modified file

    Usage:
        /diff <file_path>     # Show changes from backup
        /diff <file1> <file2> # Compare two files
    """
    if not args:
        self.console.print("[yellow]Usage:[/yellow]")
        self.console.print("  /diff <file_path>       # Show changes")
        self.console.print("  /diff <file1> <file2>   # Compare files")
        return

    workspace = self.session_mgr.workspace

    if len(args) == 1:
        # Show diff from backup
        file_path = args[0]
        full_path = workspace / file_path
        backup_path = full_path.with_suffix(full_path.suffix + '.bak')

        if not full_path.exists():
            self.console.print(f"[red]File not found:[/red] {file_path}")
            return

        if not backup_path.exists():
            self.console.print(f"[yellow]No backup found for:[/yellow] {file_path}")
            self.console.print("[dim]Tip: Backups are created when files are modified[/dim]")
            return

        old_label = f"{file_path} (backup)"
        new_label = f"{file_path} (current)"

        with open(backup_path, 'r', encoding='utf-8') as f:
            old_lines = f.readlines()
        with open(full_path, 'r', encoding='utf-8') as f:
            new_lines = f.readlines()

    else:
        # Compare two files
        file1_path = workspace / args[0]
        file2_path = workspace / args[1]

        if not file1_path.exists():
            self.console.print(f"[red]File not found:[/red] {args[0]}")
            return
        if not file2_path.exists():
            self.console.print(f"[red]File not found:[/red] {args[1]}")
            return

        old_label = args[0]
        new_label = args[1]

        with open(file1_path, 'r', encoding='utf-8') as f:
            old_lines = f.readlines()
        with open(file2_path, 'r', encoding='utf-8') as f:
            new_lines = f.readlines()

    # Generate unified diff
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=old_label,
        tofile=new_label,
        lineterm=''
    )

    diff_text = '\n'.join(diff)

    if diff_text:
        self.console.print(f"\n[bold cyan]Diff:[/bold cyan] {old_label} → {new_label}\n")
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
        self.console.print(syntax)
    else:
        self.console.print("[green]No differences found[/green]")
```

#### T3.3.2: Implement `/tree` Command

**File**: `backend/cli/terminal_ui.py`

```python
from rich.tree import Tree

def _cmd_tree(self, args: list):
    """Show file tree of workspace

    Usage:
        /tree           # Show tree (depth 3)
        /tree 5         # Show tree (depth 5)
        /tree <path>    # Show tree of specific directory
    """
    workspace = self.session_mgr.workspace
    max_depth = 3
    target_path = workspace

    # Parse arguments
    if args:
        if args[0].isdigit():
            max_depth = int(args[0])
        else:
            target_path = workspace / args[0]
            if not target_path.exists():
                self.console.print(f"[red]Directory not found:[/red] {args[0]}")
                return
            if len(args) > 1 and args[1].isdigit():
                max_depth = int(args[1])

    # Create root tree
    tree = Tree(
        f"📁 [bold cyan]{target_path.name or target_path}[/bold cyan]",
        guide_style="dim"
    )

    def add_directory(parent: Tree, path: Path, depth: int = 0):
        """Recursively add directories and files to tree"""
        if depth >= max_depth:
            return

        try:
            # Get sorted items (directories first, then files)
            items = sorted(
                path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )

            for item in items:
                # Skip hidden files and common ignore patterns
                if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules']:
                    continue

                if item.is_dir():
                    # Add directory
                    branch = parent.add(f"📁 [bold cyan]{item.name}[/bold cyan]")
                    add_directory(branch, item, depth + 1)
                else:
                    # Add file with size
                    try:
                        size = item.stat().st_size
                        if size < 1024:
                            size_str = f"{size}B"
                        elif size < 1024 * 1024:
                            size_str = f"{size/1024:.1f}KB"
                        else:
                            size_str = f"{size/(1024*1024):.1f}MB"

                        # File icon based on extension
                        ext = item.suffix.lower()
                        icons = {
                            '.py': '🐍', '.js': '📜', '.ts': '📘',
                            '.md': '📝', '.json': '📋', '.yaml': '⚙️',
                            '.txt': '📄', '.log': '📊'
                        }
                        icon = icons.get(ext, '📄')

                        parent.add(f"{icon} {item.name} [dim]({size_str})[/dim]")
                    except OSError:
                        parent.add(f"📄 {item.name}")

        except PermissionError:
            parent.add("[red]Permission denied[/red]")

    # Build and display tree
    add_directory(tree, target_path)
    self.console.print(tree)
```

#### T3.3.3: Implement `/export` Command

**File**: `backend/cli/terminal_ui.py`

```python
def _cmd_export(self, args: list):
    """Export session to Markdown file

    Usage:
        /export                    # Export to session-{id}.md
        /export <filename>         # Export to specific file
    """
    # Determine output filename
    if args:
        output_file = self.session_mgr.workspace / args[0]
        if not output_file.suffix:
            output_file = output_file.with_suffix('.md')
    else:
        output_file = self.session_mgr.workspace / f"{self.session_mgr.session_id}.md"

    # Get session summary
    summary = self.session_mgr.get_history_summary()
    history = self.session_mgr.conversation_history

    # Build Markdown content
    md_lines = [
        f"# Session Export: {self.session_mgr.session_id}",
        "",
        "## Session Information",
        "",
        f"- **Created**: {summary.get('created_at', 'Unknown')}",
        f"- **Updated**: {summary.get('updated_at', 'N/A')}",
        f"- **Workspace**: `{summary.get('workspace')}`",
        f"- **Model**: {summary.get('model')}",
        f"- **Total Messages**: {summary.get('total_messages')}",
        "",
        "---",
        "",
        "## Conversation",
        ""
    ]

    for i, msg in enumerate(history, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        role_name = "👤 **User**" if role == "user" else "🤖 **AI Assistant**"

        md_lines.extend([
            f"### Message {i}: {role_name}",
            f"*{timestamp}*",
            "",
            content,
            "",
            "---",
            ""
        ])

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    self.console.print(f"[green]✓ Session exported to:[/green] {output_file}")
    self.console.print(f"[dim]File size: {output_file.stat().st_size} bytes[/dim]")
```

**Acceptance Criteria**:
- ✅ `/diff file.py` shows changes from backup
- ✅ `/diff file1.py file2.py` compares two files
- ✅ `/tree` shows workspace file tree
- ✅ `/tree 5` shows tree with depth 5
- ✅ `/export` creates Markdown file with conversation

---

### Task Group 4: Testing and Documentation

**Priority**: P1 (High)
**Estimated Time**: 3 hours

#### T3.4.1: Update Tests

**File**: `backend/cli/test_phase3.py` (NEW)

```python
"""Tests for Phase 3 features"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.config import CLIConfig
from cli.utils.input import EnhancedInput


def test_config():
    """Test config system"""
    print("Testing CLIConfig...")

    config = CLIConfig(Path('.'))

    # Test get
    assert config.get('model') == 'deepseek-r1:14b'
    print("✓ Default model setting")

    # Test set
    config.set('model', 'qwen2.5-coder:32b')
    assert config.get('model') == 'qwen2.5-coder:32b'
    print("✓ Setting update")

    # Test reset
    config.reset()
    assert config.get('model') == 'deepseek-r1:14b'
    print("✓ Reset to defaults")

    print()


def test_enhanced_input():
    """Test enhanced input (manual)"""
    print("Testing EnhancedInput (manual)...")
    print("  1. Type /h and press Tab → should autocomplete")
    print("  2. Press ↑ → should show previous command")
    print("  3. Start typing → should show suggestion")
    print()


if __name__ == '__main__':
    test_config()
    test_enhanced_input()
    print("✅ Phase 3 tests completed!")
```

#### T3.4.2: Update Documentation

**File**: `docs/CLI_README.md` (UPDATE)

Add sections for new features:

```markdown
## New in Phase 3

### Command History and Autocomplete

Press ↑/↓ to navigate command history.
Press Tab to autocomplete slash commands.

### Configuration

Manage settings with `/config`:

```bash
/config                    # Show all settings
/config model              # Show model setting
/config model qwen2.5      # Change model
/config reset              # Reset to defaults
```

Settings file: `.testcodeagent/settings.json`

### File Management

```bash
/diff calculator.py        # Show changes from backup
/tree                      # Show file tree
/tree 5                    # Show tree (depth 5)
/export                    # Export session to Markdown
```
```

**File**: `debug/Requirement.md` (UPDATE)

Add Issue 53 for Phase 3 completion.

---

## Success Criteria

### Functional Requirements

- ✅ Command history works (↑↓ arrows)
- ✅ Autocomplete works (Tab key)
- ✅ Settings persist across sessions
- ✅ `/config` manages all settings
- ✅ `/diff` shows file differences
- ✅ `/tree` displays workspace structure
- ✅ `/export` creates Markdown export

### Non-Functional Requirements

- ✅ No breaking changes to Phase 1/2 features
- ✅ All existing tests still pass
- ✅ Code follows existing patterns
- ✅ Documentation updated
- ✅ Performance not degraded

---

## Timeline

### Day 1 (6-8 hours)
- ✅ Install prompt_toolkit
- ✅ Create EnhancedInput module
- ✅ Integrate into TerminalUI
- ✅ Create CLIConfig module
- ✅ Test history and autocomplete

### Day 2 (6-8 hours)
- ✅ Add `/config` command
- ✅ Implement `/diff` command
- ✅ Implement `/tree` command
- ✅ Implement `/export` command
- ✅ Integration testing

### Day 3 (3-4 hours)
- ✅ Write tests
- ✅ Update documentation
- ✅ Final testing
- ✅ Git commit & push

**Total**: 15-20 hours over 3 days

---

## Risk Mitigation

### Risk 1: prompt_toolkit Compatibility Issues

**Probability**: Low
**Impact**: Medium

**Mitigation**:
- Test on Python 3.9, 3.10, 3.11
- Fallback to basic input if import fails
- Document version requirements

### Risk 2: Settings File Corruption

**Probability**: Low
**Impact**: Low

**Mitigation**:
- Validate JSON on load
- Fallback to defaults on error
- Create backup on save

### Risk 3: Performance Degradation

**Probability**: Very Low
**Impact**: Low

**Mitigation**:
- prompt_toolkit is fast
- Config loads once per session
- No impact on streaming workflow

---

## Dependencies

### Python Packages

```txt
# Existing (keep)
rich >= 13.0.0

# New (add)
prompt-toolkit >= 3.0.0
```

### System Requirements

- Python >= 3.9
- Terminal with arrow key support
- UTF-8 encoding

---

## Rollout Plan

### Phase 3.1: Input Enhancement (Week 1, Days 1-2)
- Install prompt_toolkit
- Implement EnhancedInput
- Test history and autocomplete

### Phase 3.2: Configuration (Week 1, Days 2-3)
- Implement CLIConfig
- Add `/config` command
- Test settings persistence

### Phase 3.3: Advanced Commands (Week 1, Days 3-5)
- Implement `/diff`
- Implement `/tree`
- Implement `/export`

### Phase 3.4: Polish and Deploy (Week 1, Day 5)
- Write tests
- Update docs
- Git commit
- Announce to users

---

## Post-Phase 3 Considerations

### Future Enhancements (Phase 4+)

**Potential Additions**:
- `/search` command (file content search)
- Session tagging and filtering
- File path autocomplete
- Multi-line input for long prompts
- Textual TUI for advanced users

**Migration Opportunities**:
- Consider Typer if argument parsing becomes complex
- Consider Textual if interactive widgets are needed

---

**Plan Version**: 1.0 (Revised)
**Last Updated**: 2026-01-08
**Status**: Ready for Implementation
