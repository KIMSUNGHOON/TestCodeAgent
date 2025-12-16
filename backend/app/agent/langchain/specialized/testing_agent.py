"""LangChain Testing Agent - Specialized in test generation and execution."""
import logging
from typing import Dict, Any

from app.agent.langchain.specialized.base_langchain_agent import (
    BaseLangChainAgent,
    LangChainAgentCapabilities,
)

logger = logging.getLogger(__name__)


class LangChainTestingAgent(BaseLangChainAgent):
    """
    LangChain agent specialized in generating and running tests.

    Capabilities:
    - Read source code
    - Generate unit tests
    - Execute test suites
    - Lint and validate code

    Uses LangGraph for ReAct-style tool usage.
    """

    def __init__(self, session_id: str):
        """Initialize LangChain Testing Agent.

        Args:
            session_id: Session identifier
        """
        capabilities = LangChainAgentCapabilities(
            can_use_tools=True,
            allowed_tools=[
                "read_file",
                "write_file",
                "run_tests",
                "execute_python",
                "lint_code"
            ],
            can_spawn_agents=False,
            max_iterations=5,
            model_type="coding"  # Use coding model for test generation
        )

        super().__init__(
            agent_type="testing",
            capabilities=capabilities,
            session_id=session_id
        )

    def get_system_prompt(self) -> str:
        """Return the system prompt for testing agent."""
        # Qwen3 style: XML tags, THOUGHTS/PLAN/ACTION markers
        return """Generate and execute tests for Python code.

<tools>
read_file: Read source code (path, max_size_mb)
write_file: Write test files (path, content, create_dirs)
run_tests: Execute pytest (test_path, timeout, verbose)
execute_python: Run Python code (code, timeout)
lint_code: Check with flake8 (file_path)
</tools>

<guidelines>
- pytest conventions with arrange-act-assert pattern
- Test names: test_<function>_<scenario>_<expected>
- Cover: happy path, edge cases (empty, None), errors, boundaries
- Use fixtures and parametrize
- Mock external dependencies
- Target >80% coverage
</guidelines>

<response_format>
THOUGHTS: [analysis of what needs testing]

PLAN:
1. [step]
2. [step]

ACTION: [tool_name]
PARAMS: {"param": "value"}

---

After completion:

TESTS_CREATED:
- [file]: [description]

TEST_RESULTS:
- passed: [count]
- failed: [count]

COVERAGE: [percentage]

ISSUES_FOUND:
- [issue]
</response_format>"""


class LangChainTestingAgentFactory:
    """Factory for creating LangChain Testing Agents."""

    @staticmethod
    def create(session_id: str) -> LangChainTestingAgent:
        """Create a new LangChain Testing Agent.

        Args:
            session_id: Session identifier

        Returns:
            New LangChainTestingAgent instance
        """
        return LangChainTestingAgent(session_id=session_id)
