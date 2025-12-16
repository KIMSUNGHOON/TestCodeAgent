"""
Testing Agent - Specialized in test generation and execution
"""

from typing import Dict, Any
from .base_specialized_agent import BaseSpecializedAgent, AgentCapabilities


class TestingAgent(BaseSpecializedAgent):
    """
    Agent specialized in creating and running tests.

    Capabilities:
    - Generate unit tests
    - Run test suites
    - Analyze test coverage
    - Write test fixtures
    """

    def __init__(self, session_id: str):
        capabilities = AgentCapabilities(
            can_use_tools=True,
            allowed_tools=[
                "read_file",
                "write_file",
                "run_tests",
                "execute_python",
                "lint_code"
            ],
            can_spawn_agents=False,
            max_iterations=5
        )

        super().__init__(
            agent_type="testing",
            model_name="qwen3-coder",  # Use coding model
            capabilities=capabilities,
            session_id=session_id
        )

    def get_system_prompt(self) -> str:
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

    async def process(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate and run tests.

        Args:
            task: Testing task description
            context: Code to test and requirements

        Returns:
            Test results
        """
        results = {
            "task": task,
            "test_file": None,
            "test_results": None,
            "coverage": 0,
            "issues": []
        }

        # Example workflow:

        # 1. If source file provided, read it
        if "source_file" in context:
            source_result = await self.use_tool(
                "read_file",
                {"path": context["source_file"]}
            )
            if source_result.success:
                results["source_code"] = source_result.output

        # 2. If test file path provided, run tests
        if "test_path" in context:
            test_result = await self.use_tool(
                "run_tests",
                {"test_path": context["test_path"]}
            )
            if test_result.success:
                results["test_results"] = test_result.output
                results["passed"] = test_result.output.get("passed", False)
            else:
                results["issues"].append(test_result.error)

        # 3. If test code provided, write and run it
        if "test_code" in context and "test_file_path" in context:
            write_result = await self.use_tool(
                "write_file",
                {
                    "path": context["test_file_path"],
                    "content": context["test_code"]
                }
            )
            if write_result.success:
                results["test_file"] = context["test_file_path"]

                # Run the tests
                run_result = await self.use_tool(
                    "run_tests",
                    {"test_path": context["test_file_path"]}
                )
                results["test_results"] = run_result.output

        return results
