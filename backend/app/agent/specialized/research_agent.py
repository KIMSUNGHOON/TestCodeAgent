"""
Research Agent - Specialized in code exploration and analysis
"""

from typing import Dict, Any
from .base_specialized_agent import BaseSpecializedAgent, AgentCapabilities


class ResearchAgent(BaseSpecializedAgent):
    """
    Agent specialized in exploring codebases and gathering context.

    Capabilities:
    - Read files and search for patterns
    - Analyze project structure
    - Gather requirements and context
    - Identify similar implementations
    """

    def __init__(self, session_id: str):
        capabilities = AgentCapabilities(
            can_use_tools=True,
            allowed_tools=[
                "read_file",
                "search_files",
                "list_directory",
                "git_status",
                "git_log"
            ],
            can_spawn_agents=False,
            max_iterations=3
        )

        super().__init__(
            agent_type="research",
            model_name="deepseek-r1",  # Use reasoning model
            capabilities=capabilities,
            session_id=session_id
        )

    def get_system_prompt(self) -> str:
        # DeepSeek R1 style: Minimal prompt, user role focus, <think> tags for reasoning
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

    async def process(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research task and gather context.

        Args:
            task: Research task description
            context: Additional context

        Returns:
            Research results with findings
        """
        results = {
            "task": task,
            "findings": [],
            "relevant_files": [],
            "recommendations": [],
            "context": {}
        }

        # Example workflow (in production, this would use LLM to decide):

        # 1. If search pattern provided, search for files
        if "search_pattern" in context:
            search_result = await self.use_tool(
                "search_files",
                {"pattern": context["search_pattern"]}
            )
            if search_result.success:
                results["relevant_files"] = search_result.output
                results["findings"].append(
                    f"Found {len(search_result.output)} files matching pattern"
                )

        # 2. If directory provided, list contents
        if "directory" in context:
            dir_result = await self.use_tool(
                "list_directory",
                {"path": context["directory"]}
            )
            if dir_result.success:
                results["context"]["directory_contents"] = dir_result.output
                results["findings"].append(
                    f"Listed {len(dir_result.output)} items in directory"
                )

        # 3. If file path provided, read it
        if "file_path" in context:
            file_result = await self.use_tool(
                "read_file",
                {"path": context["file_path"]}
            )
            if file_result.success:
                results["context"]["file_content"] = file_result.output
                results["findings"].append(f"Read file: {context['file_path']}")

        # 4. Get git status
        git_status = await self.use_tool("git_status", {})
        if git_status.success:
            results["context"]["git_status"] = git_status.output

        return results
