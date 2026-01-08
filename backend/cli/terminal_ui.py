"""Terminal UI for TestCodeAgent CLI

Rich-based terminal interface providing:
- Interactive REPL mode
- Streaming progress indicators
- Markdown rendering for AI responses
- Syntax highlighting for code
- Slash command handling
"""

import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.text import Text

from cli.session_manager import SessionManager


class TerminalUI:
    """Rich-based terminal user interface"""

    def __init__(self, session_mgr: SessionManager):
        """Initialize terminal UI

        Args:
            session_mgr: SessionManager instance
        """
        self.session_mgr = session_mgr
        self.console = Console()

    def start_interactive(self):
        """Start interactive REPL mode"""
        self._show_welcome()

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Execute workflow
                asyncio.run(self._execute_workflow(user_input))

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit or Ctrl+D to quit[/yellow]")
                continue
            except EOFError:
                self._handle_exit()
                break

    def execute_one_shot(self, prompt: str):
        """Execute single prompt and exit

        Args:
            prompt: User prompt
        """
        self.console.print(Panel(
            f"[cyan]Executing:[/cyan] {prompt}",
            title="TestCodeAgent - One-shot Mode",
            border_style="cyan"
        ))

        asyncio.run(self._execute_workflow(prompt))

    async def _execute_workflow(self, user_request: str):
        """Execute workflow with streaming progress

        Args:
            user_request: User's request
        """
        current_agent = None
        current_content = ""
        artifacts = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=self.console,
            transient=True
        ) as progress:
            # Create progress task
            task = progress.add_task("[cyan]Processing...", total=None)

            try:
                async for update in self.session_mgr.execute_streaming_workflow(user_request):
                    update_type = update.get("type")

                    if update_type == "agent_start":
                        current_agent = update.get("agent")
                        progress.update(task, description=f"[cyan]{current_agent} working...")

                    elif update_type == "agent_stream":
                        # Accumulate streaming content
                        chunk = update.get("content", "")
                        current_content += chunk

                    elif update_type == "agent_end":
                        # Display accumulated content
                        if current_content:
                            self._display_agent_response(current_agent, current_content)
                            current_content = ""

                    elif update_type == "artifact":
                        # Store artifact for later display
                        artifacts.append(update)

                    elif update_type == "final_response":
                        # Display final response
                        final_content = update.get("content", "")
                        if final_content and final_content != current_content:
                            self.console.print("\n[bold green]Final Response:[/bold green]")
                            self.console.print(Markdown(final_content))

                    elif update_type == "error":
                        error_msg = update.get("message", "Unknown error")
                        self.console.print(f"\n[bold red]❌ Error:[/bold red] {error_msg}")

            except Exception as e:
                self.console.print(f"\n[bold red]❌ Execution Error:[/bold red] {str(e)}")
                return

        # Display artifacts if any
        if artifacts:
            self._display_artifacts(artifacts)

    def _display_agent_response(self, agent: str, content: str):
        """Display agent response with formatting

        Args:
            agent: Agent name
            content: Response content
        """
        if not content.strip():
            return

        self.console.print(f"\n[bold magenta]{agent}:[/bold magenta]")

        # Try to render as markdown
        try:
            self.console.print(Markdown(content))
        except Exception:
            # Fallback to plain text
            self.console.print(content)

    def _display_artifacts(self, artifacts: list):
        """Display file artifacts

        Args:
            artifacts: List of artifact updates
        """
        if not artifacts:
            return

        self.console.print("\n[bold green]📁 Files:[/bold green]")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Action", style="dim", width=12)
        table.add_column("File Path")
        table.add_column("Lines", justify="right")

        for artifact in artifacts:
            action = artifact.get("action", "unknown")
            file_path = artifact.get("file_path", "")
            lines = artifact.get("lines", 0)

            # Color code by action
            if action == "created":
                action_str = "[green]CREATED[/green]"
            elif action == "modified":
                action_str = "[yellow]MODIFIED[/yellow]"
            elif action == "deleted":
                action_str = "[red]DELETED[/red]"
            else:
                action_str = action

            table.add_row(action_str, file_path, str(lines) if lines else "-")

        self.console.print(table)

    def _handle_command(self, command: str):
        """Handle slash commands

        Args:
            command: Command string (starting with /)
        """
        cmd_parts = command[1:].split()
        if not cmd_parts:
            return

        cmd_name = cmd_parts[0].lower()
        cmd_args = cmd_parts[1:]

        if cmd_name == "help":
            self._cmd_help()
        elif cmd_name == "status":
            self._cmd_status()
        elif cmd_name == "history":
            self._cmd_history()
        elif cmd_name == "context":
            self._cmd_context()
        elif cmd_name == "files":
            self._cmd_files()
        elif cmd_name == "clear":
            self._cmd_clear()
        elif cmd_name in ["exit", "quit"]:
            self._handle_exit()
            raise EOFError()
        elif cmd_name == "sessions":
            self._cmd_sessions()
        else:
            self.console.print(f"[red]Unknown command: {cmd_name}[/red]")
            self.console.print("Type [cyan]/help[/cyan] for available commands")

    def _cmd_help(self):
        """Show help message"""
        help_text = """
# Available Commands

## Session Management
- `/status` - Show current session status
- `/sessions` - List all saved sessions
- `/history` - Show conversation history
- `/context` - Show extracted context information

## Workspace
- `/files` - Show generated/modified files
- `/clear` - Clear terminal screen

## Utility
- `/help` - Show this help message
- `/exit` or `/quit` - Exit CLI (also Ctrl+D)

## Tips
- Press Ctrl+C to cancel current input
- Press Ctrl+D to exit
- Use arrow keys to navigate command history
        """
        self.console.print(Markdown(help_text))

    def _cmd_status(self):
        """Show session status"""
        summary = self.session_mgr.get_history_summary()

        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        table.add_row("Session ID", summary.get("session_id", "Unknown"))
        table.add_row("Workspace", summary.get("workspace", "Unknown"))
        table.add_row("Model", summary.get("model", "Unknown"))
        table.add_row("Total Messages", str(summary.get("total_messages", 0)))
        table.add_row("User Messages", str(summary.get("user_messages", 0)))
        table.add_row("AI Messages", str(summary.get("assistant_messages", 0)))
        table.add_row("Created", summary.get("created_at", "Unknown"))
        table.add_row("Updated", summary.get("updated_at", "N/A"))

        self.console.print(Panel(table, title="Session Status", border_style="cyan"))

    def _cmd_history(self):
        """Show conversation history"""
        history = self.session_mgr.conversation_history

        if not history:
            self.console.print("[yellow]No conversation history yet[/yellow]")
            return

        self.console.print(f"\n[bold cyan]Conversation History[/bold cyan] ({len(history)} messages)\n")

        for i, msg in enumerate(history, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            role_color = "cyan" if role == "user" else "magenta"
            role_name = "You" if role == "user" else "AI"

            self.console.print(f"[bold {role_color}][{i}] {role_name}[/bold {role_color}] ({timestamp})")

            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."

            self.console.print(f"  {content}\n")

    def _cmd_context(self):
        """Show context information"""
        context = self.session_mgr.get_context_info()

        self.console.print("\n[bold cyan]Context Information[/bold cyan]\n")

        # Files mentioned
        files = context.get("files_mentioned", [])
        if files:
            self.console.print("[bold green]Files Mentioned:[/bold green]")
            for file in files[:10]:
                self.console.print(f"  • {file}")
            if len(files) > 10:
                self.console.print(f"  ... and {len(files) - 10} more")
            self.console.print()

        # Errors encountered
        errors = context.get("errors_encountered", [])
        if errors:
            self.console.print("[bold red]Errors Encountered:[/bold red]")
            for error in errors[:5]:
                self.console.print(f"  • {error}")
            if len(errors) > 5:
                self.console.print(f"  ... and {len(errors) - 5} more")
            self.console.print()

        # Decisions made
        decisions = context.get("decisions_made", [])
        if decisions:
            self.console.print("[bold yellow]Key Decisions:[/bold yellow]")
            for decision in decisions[:5]:
                self.console.print(f"  • {decision}")
            if len(decisions) > 5:
                self.console.print(f"  ... and {len(decisions) - 5} more")
            self.console.print()

        if not files and not errors and not decisions:
            self.console.print("[yellow]No context information extracted yet[/yellow]")

    def _cmd_files(self):
        """Show generated/modified files"""
        workspace = self.session_mgr.workspace

        # List files in workspace (simple implementation)
        # In production, this should track actual modified files
        self.console.print(f"\n[bold cyan]Workspace:[/bold cyan] {workspace}\n")
        self.console.print("[yellow]Note: File tracking will be implemented with artifact system[/yellow]")

    def _cmd_clear(self):
        """Clear terminal screen"""
        self.console.clear()

    def _cmd_sessions(self):
        """List all sessions"""
        sessions = self.session_mgr.list_sessions()

        if not sessions:
            self.console.print("[yellow]No saved sessions found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Session ID", style="dim")
        table.add_column("Created")
        table.add_column("Updated")
        table.add_column("Messages", justify="right")
        table.add_column("Workspace")

        for session in sessions[:10]:  # Show latest 10
            table.add_row(
                session.get("session_id", ""),
                session.get("created_at", "")[:19],  # Truncate ISO timestamp
                session.get("updated_at", "")[:19],
                str(session.get("message_count", 0)),
                str(Path(session.get("workspace", "")).name)
            )

        self.console.print(Panel(table, title="Recent Sessions", border_style="cyan"))

        if len(sessions) > 10:
            self.console.print(f"\n[dim]Showing 10 of {len(sessions)} sessions[/dim]")

    def _handle_exit(self):
        """Handle exit"""
        self.console.print("\n[cyan]Saving session...[/cyan]")
        self.session_mgr.save_session()
        self.console.print("[green]✓[/green] Session saved")
        self.console.print("\n[bold cyan]Thank you for using TestCodeAgent![/bold cyan]")

    def _show_welcome(self):
        """Show welcome message"""
        welcome_text = f"""
[bold cyan]TestCodeAgent CLI[/bold cyan] - Interactive AI Coding Assistant

[dim]Session ID:[/dim] {self.session_mgr.session_id}
[dim]Workspace:[/dim] {self.session_mgr.workspace}
[dim]Model:[/dim] {self.session_mgr.model}

Type your request or use slash commands (type [cyan]/help[/cyan] for available commands)
Press [cyan]Ctrl+D[/cyan] to exit
        """

        self.console.print(Panel(
            welcome_text.strip(),
            border_style="cyan",
            padding=(1, 2)
        ))
