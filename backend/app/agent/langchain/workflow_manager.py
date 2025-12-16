"""Workflow-based coding agent using LangGraph."""
import logging
import re
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator, Optional, TypedDict, Annotated
from operator import add
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from app.core.config import settings
from app.agent.base.interface import BaseWorkflow, BaseWorkflowManager

logger = logging.getLogger(__name__)


# State definition for LangGraph
class WorkflowState(TypedDict):
    """State maintained throughout the workflow."""
    user_request: str
    plan_text: str
    checklist: List[Dict[str, Any]]
    code_text: str
    artifacts: Annotated[List[Dict[str, Any]], add]
    review_result: Dict[str, Any]
    current_task_idx: int
    status: str
    error: Optional[str]


def parse_checklist(text: str) -> List[Dict[str, Any]]:
    """Parse text into checklist items."""
    items = []
    pattern = r'(?:^|\n)\s*(?:(\d+)[.\)]\s*|[-*]\s*)(.+?)(?=\n|$)'
    matches = re.findall(pattern, text)

    for i, (num, task) in enumerate(matches, 1):
        task = task.strip()
        if task:
            items.append({
                "id": int(num) if num else i,
                "task": task,
                "completed": False,
                "artifacts": []
            })

    return items


def parse_code_blocks(text: str) -> List[Dict[str, Any]]:
    """Extract code blocks from text."""
    artifacts = []
    pattern = r'```(\w+)?(?:\s+(\S+))?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)

    extensions = {
        "python": "py", "javascript": "js", "typescript": "ts",
        "java": "java", "go": "go", "rust": "rs", "cpp": "cpp",
        "c": "c", "html": "html", "css": "css", "json": "json",
        "yaml": "yaml", "sql": "sql", "bash": "sh", "shell": "sh"
    }

    for lang, filename, content in matches:
        lang = lang or "text"
        if not filename:
            ext = extensions.get(lang.lower(), "txt")
            filename = f"code.{ext}"
        artifacts.append({
            "type": "artifact",
            "language": lang,
            "filename": filename,
            "content": content.strip()
        })

    return artifacts


def parse_review(text: str) -> Dict[str, Any]:
    """Parse review text into structured format."""
    issues = []
    suggestions = []
    approved = False

    if re.search(r'(?:approved|lgtm|looks good|no issues)', text, re.IGNORECASE):
        approved = True

    issue_pattern = r'(?:^|\n)\s*[-*]?\s*(?:issue|bug|error|problem|warning)[:.]?\s*(.+?)(?=\n|$)'
    for match in re.finditer(issue_pattern, text, re.IGNORECASE):
        issues.append(match.group(1).strip())

    suggestion_pattern = r'(?:^|\n)\s*[-*]?\s*(?:suggest|recommend|consider|improvement)[:.]?\s*(.+?)(?=\n|$)'
    for match in re.finditer(suggestion_pattern, text, re.IGNORECASE):
        suggestions.append(match.group(1).strip())

    return {
        "issues": issues,
        "suggestions": suggestions,
        "approved": approved,
        "corrected_artifacts": parse_code_blocks(text)
    }


class LangGraphWorkflow(BaseWorkflow):
    """Multi-agent coding workflow using LangGraph: Planning -> Coding -> Review."""

    def __init__(self):
        """Initialize the LangGraph workflow."""
        # Initialize LLM clients
        self.reasoning_llm = ChatOpenAI(
            base_url=settings.vllm_reasoning_endpoint,
            model=settings.reasoning_model,
            temperature=0.7,
            max_tokens=2048,
            api_key="not-needed",
        )

        self.coding_llm = ChatOpenAI(
            base_url=settings.vllm_coding_endpoint,
            model=settings.coding_model,
            temperature=0.7,
            max_tokens=2048,
            api_key="not-needed",
        )

        # System prompts for each agent
        # DeepSeek R1 style for planning (reasoning model)
        self.planning_prompt = """Analyze request and create implementation checklist.

<think>
Break down the request into atomic, sequential steps.
Consider dependencies between tasks.
Order by implementation sequence.
</think>

<output_format>
1. [Task description]
2. [Task description]
3. [Task description]
</output_format>

Rules:
- One task per line
- Clear, actionable steps
- No explanations, only the numbered list"""

        # Qwen3 style for coding (coding model)
        self.coding_prompt = """Implement the specified task.

<response_format>
THOUGHTS: [brief analysis]

```language filename.ext
// complete code
```
</response_format>

<rules>
- Focus ONLY on current task
- One code block per file
- Include filename after language
- Write complete, runnable code
- Full file content for updates
- No explanations outside code blocks
</rules>"""

        # Qwen3 style for review (coding model)
        self.review_prompt = """Review code and provide structured feedback.

<response_format>
ANALYSIS: [brief review summary]

ISSUES:
- Issue: [problem description]

SUGGESTIONS:
- Suggest: [improvement]

STATUS: [APPROVED or NEEDS_REVISION]

If changes needed:
```language filename.ext
// corrected code
```
</response_format>

<criteria>
- Code correctness
- Best practices
- Security concerns
- Performance issues
</criteria>

Only list actual issues found. Be concise."""

        # Build the workflow graph
        self.graph = self._build_graph()

        logger.info("LangGraphWorkflow initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph = StateGraph(WorkflowState)

        # Add nodes
        graph.add_node("planning", self._planning_node)
        graph.add_node("coding", self._coding_node)
        graph.add_node("review", self._review_node)

        # Add edges
        graph.add_edge(START, "planning")
        graph.add_edge("planning", "coding")
        graph.add_edge("coding", "review")
        graph.add_edge("review", END)

        return graph.compile()

    async def _planning_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Planning agent node."""
        messages = [
            SystemMessage(content=self.planning_prompt),
            HumanMessage(content=state["user_request"])
        ]

        response = await self.reasoning_llm.ainvoke(messages)
        plan_text = response.content
        checklist = parse_checklist(plan_text)

        return {
            "plan_text": plan_text,
            "checklist": checklist,
            "status": "planning_complete"
        }

    async def _coding_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Coding agent node - implements all tasks."""
        all_artifacts = []
        code_text = ""
        checklist = state["checklist"]
        existing_code = ""

        for idx, task_item in enumerate(checklist):
            task_description = task_item["task"]

            # Build context message
            context_parts = [f"Original request: {state['user_request']}"]
            context_parts.append(f"\nFull plan:\n{state['plan_text']}")

            if existing_code:
                context_parts.append(f"\nCode implemented so far:\n{existing_code}")

            context_parts.append(f"\nCurrent task ({idx + 1}/{len(checklist)}): {task_description}")
            context_parts.append("\nPlease implement this specific task now.")

            messages = [
                SystemMessage(content=self.coding_prompt),
                HumanMessage(content="\n".join(context_parts))
            ]

            response = await self.coding_llm.ainvoke(messages)
            task_code = response.content
            code_text += task_code + "\n"

            # Extract artifacts from this task
            task_artifacts = parse_code_blocks(task_code)
            all_artifacts.extend(task_artifacts)

            # Update context with generated code
            for artifact in task_artifacts:
                existing_code += f"\n\n```{artifact['language']} {artifact['filename']}\n{artifact['content']}\n```"

            # Mark task as completed
            checklist[idx]["completed"] = True
            checklist[idx]["artifacts"] = [a["filename"] for a in task_artifacts]

        return {
            "code_text": code_text,
            "artifacts": all_artifacts,
            "checklist": checklist,
            "status": "coding_complete"
        }

    async def _review_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Review agent node."""
        messages = [
            SystemMessage(content=self.review_prompt),
            HumanMessage(content=f"Please review this code:\n\n{state['code_text']}")
        ]

        response = await self.coding_llm.ainvoke(messages)
        review_result = parse_review(response.content)

        return {
            "review_result": review_result,
            "status": "review_complete"
        }

    async def execute(
        self,
        user_request: str,
        context: Optional[Any] = None
    ) -> str:
        """Execute the coding workflow.

        Args:
            user_request: User's coding request
            context: Optional run context

        Returns:
            Final result from the workflow
        """
        logger.info(f"Executing LangGraph workflow for request: {user_request[:100]}...")

        initial_state = WorkflowState(
            user_request=user_request,
            plan_text="",
            checklist=[],
            code_text="",
            artifacts=[],
            review_result={},
            current_task_idx=0,
            status="started",
            error=None
        )

        result = await self.graph.ainvoke(initial_state)
        return result.get("code_text", "")

    async def execute_stream(
        self,
        user_request: str,
        context: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the workflow with streaming updates.

        Args:
            user_request: User's coding request
            context: Optional run context

        Yields:
            Updates with workflow progress
        """
        logger.info(f"Streaming LangGraph workflow for request: {user_request[:100]}...")
        workflow_id = str(uuid.uuid4())[:8]

        try:
            # Emit workflow creation event
            yield {
                "agent": "Orchestrator",
                "type": "workflow_created",
                "status": "running",
                "message": "LangGraph workflow initialized",
                "workflow_info": {
                    "workflow_id": workflow_id,
                    "workflow_type": "LangGraph Multi-Agent",
                    "nodes": ["PlanningAgent", "CodingAgent", "ReviewAgent"],
                    "edges": [
                        {"from": "START", "to": "PlanningAgent"},
                        {"from": "PlanningAgent", "to": "CodingAgent"},
                        {"from": "CodingAgent", "to": "ReviewAgent"},
                        {"from": "ReviewAgent", "to": "END"}
                    ],
                    "current_node": "PlanningAgent"
                }
            }

            # Step 1: Planning - emit agent spawn
            planning_agent_id = f"planning-{uuid.uuid4().hex[:6]}"
            yield {
                "agent": "PlanningAgent",
                "type": "agent_spawn",
                "status": "running",
                "message": "Spawning PlanningAgent for task analysis",
                "agent_spawn": {
                    "agent_id": planning_agent_id,
                    "agent_type": "PlanningAgent",
                    "parent_agent": "Orchestrator",
                    "spawn_reason": "Analyze user request and create implementation checklist",
                    "timestamp": datetime.now().isoformat()
                }
            }

            yield {
                "agent": "PlanningAgent",
                "type": "thinking",
                "status": "running",
                "message": "Analyzing requirements..."
            }

            messages = [
                SystemMessage(content=self.planning_prompt),
                HumanMessage(content=user_request)
            ]

            start_time = time.time()
            plan_text = ""
            async for chunk in self.reasoning_llm.astream(messages):
                if chunk.content:
                    plan_text += chunk.content
            latency_ms = int((time.time() - start_time) * 1000)

            checklist = parse_checklist(plan_text)

            yield {
                "agent": "PlanningAgent",
                "type": "completed",
                "status": "completed",
                "items": checklist,
                "prompt_info": {
                    "system_prompt": self.planning_prompt,
                    "user_prompt": user_request,
                    "output": plan_text,
                    "model": settings.reasoning_model,
                    "latency_ms": latency_ms
                }
            }

            # Step 2: Coding - emit agent spawn
            coding_agent_id = f"coding-{uuid.uuid4().hex[:6]}"
            yield {
                "agent": "CodingAgent",
                "type": "agent_spawn",
                "status": "running",
                "message": "Spawning CodingAgent for implementation",
                "agent_spawn": {
                    "agent_id": coding_agent_id,
                    "agent_type": "CodingAgent",
                    "parent_agent": "Orchestrator",
                    "spawn_reason": f"Implement {len(checklist)} tasks from planning phase",
                    "timestamp": datetime.now().isoformat()
                }
            }

            all_artifacts = []
            code_text = ""
            existing_code = ""

            for idx, task_item in enumerate(checklist):
                task_num = idx + 1
                task_description = task_item["task"]

                yield {
                    "agent": "CodingAgent",
                    "type": "thinking",
                    "status": "running",
                    "message": f"Task {task_num}/{len(checklist)}: {task_description}",
                    "checklist": checklist
                }

                # Build context
                context_parts = [f"Original request: {user_request}"]
                context_parts.append(f"\nFull plan:\n{plan_text}")

                if existing_code:
                    context_parts.append(f"\nCode implemented so far:\n{existing_code}")

                context_parts.append(f"\nCurrent task ({task_num}/{len(checklist)}): {task_description}")
                context_parts.append("\nPlease implement this specific task now.")

                user_prompt_content = "\n".join(context_parts)
                messages = [
                    SystemMessage(content=self.coding_prompt),
                    HumanMessage(content=user_prompt_content)
                ]

                start_time = time.time()
                task_code = ""
                async for chunk in self.coding_llm.astream(messages):
                    if chunk.content:
                        task_code += chunk.content
                task_latency_ms = int((time.time() - start_time) * 1000)

                code_text += task_code + "\n"

                # Extract artifacts
                task_artifacts = parse_code_blocks(task_code)
                all_artifacts.extend(task_artifacts)

                for artifact in task_artifacts:
                    existing_code += f"\n\n```{artifact['language']} {artifact['filename']}\n{artifact['content']}\n```"

                    yield {
                        "agent": "CodingAgent",
                        "type": "artifact",
                        "status": "running",
                        "message": f"Task {task_num}: Created {artifact['filename']}",
                        "artifact": artifact,
                        "checklist": checklist
                    }

                # Mark task completed
                checklist[idx]["completed"] = True
                checklist[idx]["artifacts"] = [a["filename"] for a in task_artifacts]

                yield {
                    "agent": "CodingAgent",
                    "type": "task_completed",
                    "status": "running",
                    "message": f"Task {task_num}/{len(checklist)}: {task_description}",
                    "task_result": {
                        "task_num": task_num,
                        "task": task_description,
                        "artifacts": task_artifacts
                    },
                    "checklist": checklist,
                    "prompt_info": {
                        "system_prompt": self.coding_prompt,
                        "user_prompt": user_prompt_content,
                        "output": task_code,
                        "model": settings.coding_model,
                        "latency_ms": task_latency_ms
                    }
                }

            yield {
                "agent": "CodingAgent",
                "type": "completed",
                "status": "completed",
                "artifacts": all_artifacts,
                "checklist": checklist
            }

            # Step 3: Review - emit agent spawn
            review_agent_id = f"review-{uuid.uuid4().hex[:6]}"
            yield {
                "agent": "ReviewAgent",
                "type": "agent_spawn",
                "status": "running",
                "message": "Spawning ReviewAgent for code review",
                "agent_spawn": {
                    "agent_id": review_agent_id,
                    "agent_type": "ReviewAgent",
                    "parent_agent": "Orchestrator",
                    "spawn_reason": f"Review {len(all_artifacts)} artifacts for quality and correctness",
                    "timestamp": datetime.now().isoformat()
                }
            }

            yield {
                "agent": "ReviewAgent",
                "type": "thinking",
                "status": "running",
                "message": "Reviewing code..."
            }

            review_user_prompt = f"Please review this code:\n\n{code_text}"
            messages = [
                SystemMessage(content=self.review_prompt),
                HumanMessage(content=review_user_prompt)
            ]

            start_time = time.time()
            review_text = ""
            async for chunk in self.coding_llm.astream(messages):
                if chunk.content:
                    review_text += chunk.content
            review_latency_ms = int((time.time() - start_time) * 1000)

            review_result = parse_review(review_text)

            yield {
                "agent": "ReviewAgent",
                "type": "completed",
                "status": "completed",
                "issues": review_result["issues"],
                "suggestions": review_result["suggestions"],
                "approved": review_result["approved"],
                "corrected_artifacts": review_result["corrected_artifacts"],
                "prompt_info": {
                    "system_prompt": self.review_prompt,
                    "user_prompt": review_user_prompt,
                    "output": review_text,
                    "model": settings.coding_model,
                    "latency_ms": review_latency_ms
                }
            }

            # Final summary
            yield {
                "agent": "Workflow",
                "type": "completed",
                "status": "finished",
                "summary": {
                    "tasks_completed": sum(1 for item in checklist if item["completed"]),
                    "total_tasks": len(checklist),
                    "artifacts_count": len(all_artifacts),
                    "review_approved": review_result["approved"]
                },
                "workflow_info": {
                    "workflow_id": workflow_id,
                    "workflow_type": "LangGraph Multi-Agent",
                    "nodes": ["PlanningAgent", "CodingAgent", "ReviewAgent"],
                    "edges": [
                        {"from": "START", "to": "PlanningAgent"},
                        {"from": "PlanningAgent", "to": "CodingAgent"},
                        {"from": "CodingAgent", "to": "ReviewAgent"},
                        {"from": "ReviewAgent", "to": "END"}
                    ],
                    "current_node": "END"
                }
            }

        except Exception as e:
            logger.error(f"Error in LangGraph workflow: {e}")
            yield {
                "agent": "Workflow",
                "type": "error",
                "status": "error",
                "message": str(e)
            }
            raise


class LangGraphWorkflowManager(BaseWorkflowManager):
    """Manager for LangGraph workflow sessions."""

    def __init__(self):
        """Initialize workflow manager."""
        self.workflows: Dict[str, LangGraphWorkflow] = {}
        logger.info("LangGraphWorkflowManager initialized")

    def get_or_create_workflow(self, session_id: str) -> LangGraphWorkflow:
        """Get existing workflow or create new one for session.

        Args:
            session_id: Session identifier

        Returns:
            LangGraphWorkflow instance
        """
        if session_id not in self.workflows:
            self.workflows[session_id] = LangGraphWorkflow()
            logger.info(f"Created new LangGraph workflow for session {session_id}")
        return self.workflows[session_id]

    def delete_workflow(self, session_id: str) -> None:
        """Delete workflow for session.

        Args:
            session_id: Session identifier
        """
        if session_id in self.workflows:
            del self.workflows[session_id]
            logger.info(f"Deleted workflow for session {session_id}")

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs.

        Returns:
            List of session IDs
        """
        return list(self.workflows.keys())


# Global workflow manager instance
workflow_manager = LangGraphWorkflowManager()
