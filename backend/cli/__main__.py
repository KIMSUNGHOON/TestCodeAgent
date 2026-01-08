"""TestCodeAgent CLI - Command Line Interface

Interactive CLI for TestCodeAgent that provides:
- Interactive REPL mode for conversational coding
- One-shot mode for single commands
- Session management and persistence
- Rich terminal UI with streaming progress

Usage:
    # Interactive mode
    python -m cli

    # One-shot mode
    python -m cli "Create a Python calculator"

    # With options
    python -m cli --workspace ./my-project --model deepseek-r1:14b

    # Resume session
    python -m cli --session-id session-20260108-123456
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add backend to path if running as module
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cli.terminal_ui import TerminalUI
from cli.session_manager import SessionManager


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="TestCodeAgent - Interactive AI coding assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  testcodeagent                           # Start interactive mode
  testcodeagent "Create a Python calculator"  # One-shot mode
  testcodeagent -w ./myproject            # Specify workspace
  testcodeagent -s session-123            # Resume session
  testcodeagent -m qwen2.5-coder:32b      # Use different model

Slash Commands (in interactive mode):
  /help       - Show available commands
  /status     - Show current session status
  /history    - Show conversation history
  /context    - Show current context information
  /files      - Show generated files
  /clear      - Clear terminal screen
  /exit       - Exit CLI (also Ctrl+D)
        """
    )

    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional prompt for one-shot mode. If not provided, starts interactive mode."
    )

    parser.add_argument(
        "-w", "--workspace",
        default=".",
        help="Workspace directory (default: current directory)"
    )

    parser.add_argument(
        "-s", "--session-id",
        help="Session ID to resume (default: create new session)"
    )

    parser.add_argument(
        "-m", "--model",
        default="deepseek-r1:14b",
        help="LLM model to use (default: deepseek-r1:14b)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="TestCodeAgent CLI v1.0.0"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save session history"
    )

    return parser.parse_args()


def main():
    """Main CLI entry point"""
    args = parse_args()

    # Setup logging if debug mode
    if args.debug:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    try:
        # Initialize session manager
        session_mgr = SessionManager(
            workspace=args.workspace,
            session_id=args.session_id,
            model=args.model,
            auto_save=not args.no_save
        )

        # Initialize terminal UI
        ui = TerminalUI(session_mgr)

        # Check if one-shot mode or interactive mode
        if args.prompt:
            # One-shot mode
            prompt_text = " ".join(args.prompt)
            ui.execute_one_shot(prompt_text)
        else:
            # Interactive REPL mode
            ui.start_interactive()

    except KeyboardInterrupt:
        print("\n\nExiting TestCodeAgent CLI...")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
