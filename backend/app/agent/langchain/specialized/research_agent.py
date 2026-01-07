"""LangChain Research Agent - Specialized in code exploration and analysis."""
import logging
from typing import Dict, Any

from app.agent.langchain.specialized.base_langchain_agent import (
    BaseLangChainAgent,
    LangChainAgentCapabilities,
)

logger = logging.getLogger(__name__)


class LangChainResearchAgent(BaseLangChainAgent):
    """
    LangChain agent specialized in exploring codebases and gathering context.

    Capabilities:
    - Read files and search for patterns
    - Analyze project structure
    - Gather requirements and context
    - Identify similar implementations

    Uses LangGraph for ReAct-style tool usage.
    """

    def __init__(self, session_id: str):
        """Initialize LangChain Research Agent.

        Args:
            session_id: Session identifier
        """
        capabilities = LangChainAgentCapabilities(
            can_use_tools=True,
            allowed_tools=[
                "read_file",
                "search_files",
                "list_directory",
                "git_status",
                "git_log"
            ],
            can_spawn_agents=False,
            max_iterations=5,
            model_type="reasoning"  # Use reasoning model for analysis
        )

        super().__init__(
            agent_type="research",
            capabilities=capabilities,
            session_id=session_id
        )

    def get_system_prompt(self) -> str:
        """Return the system prompt for research agent."""
        # DeepSeek R1 style: Minimal prompt, <think> tags for reasoning
        return """Research codebase and gather context.

<tools>
read_file: Read file contents (path, max_size_mb)
search_files: Glob pattern search (pattern, path, max_results)
list_directory: List directory contents (path, recursive, max_depth)
git_status: Repository status
git_log: Commit history (max_count)
</tools>

<workflow>
1. Understand project structure first
2. Find README and documentation
3. Search for relevant patterns
4. Analyze code with file paths and line numbers
</workflow>

<think>
Use this tag to reason through each step before acting.
Plan your exploration strategy, then execute tools, then synthesize findings.
</think>

<output_format>
FILES_FOUND:
- [path]: [description]

KEY_FINDINGS:
- [finding]

RECOMMENDATIONS:
- [recommendation]
</output_format>"""


class LangChainResearchAgentFactory:
    """Factory for creating LangChain Research Agents."""

    @staticmethod
    def create(session_id: str) -> LangChainResearchAgent:
        """Create a new LangChain Research Agent.

        Args:
            session_id: Session identifier

        Returns:
            New LangChainResearchAgent instance
        """
        return LangChainResearchAgent(session_id=session_id)
