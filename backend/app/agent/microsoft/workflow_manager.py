"""Dynamic workflow-based coding agent using Microsoft Agent Framework.

Mirrors the LangChain implementation with:
- SupervisorAgent for task analysis
- Dynamic workflow creation based on task type
- Review loop with FixCodeAgent
- Configurable max iterations
"""
import logging
import re
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator, Optional, Literal
from dataclasses import dataclass, field
from agent_framework import (
    WorkflowBuilder,
    ChatAgent,
    AgentRunContext,
    ChatMessage,
    BaseChatClient,
    ChatResponseUpdate,
    TextContent,
)
from app.services.vllm_client import vllm_router
from app.agent.base.interface import BaseWorkflow, BaseWorkflowManager
from app.core.config import settings

logger = logging.getLogger(__name__)

# Task types that can be identified
TaskType = Literal[
    "code_generation", "bug_fix", "refactoring",
    "test_generation", "code_review", "documentation", "general"
]

# Workflow templates for each task type
WORKFLOW_TEMPLATES: Dict[TaskType, Dict[str, Any]] = {
    "code_generation": {
        "name": "Code Generation Workflow",
        "nodes": ["PlanningAgent", "CodingAgent", "ReviewAgent", "FixCodeAgent"],
        "flow": [
            ("START", "PlanningAgent"),
            ("PlanningAgent", "CodingAgent"),
            ("CodingAgent", "ReviewAgent"),
            ("ReviewAgent", "Decision"),
            ("Decision", "FixCodeAgent", "needs_fix"),
            ("Decision", "END", "approved"),
            ("FixCodeAgent", "ReviewAgent")
        ],
        "has_review_loop": True
    },
    "bug_fix": {
        "name": "Bug Fix Workflow",
        "nodes": ["AnalysisAgent", "DebugAgent", "CodingAgent", "ReviewAgent", "FixCodeAgent"],
        "flow": [
            ("START", "AnalysisAgent"),
            ("AnalysisAgent", "DebugAgent"),
            ("DebugAgent", "CodingAgent"),
            ("CodingAgent", "ReviewAgent"),
            ("ReviewAgent", "Decision"),
            ("Decision", "FixCodeAgent", "needs_fix"),
            ("Decision", "END", "approved"),
            ("FixCodeAgent", "ReviewAgent")
        ],
        "has_review_loop": True
    },
    "refactoring": {
        "name": "Refactoring Workflow",
        "nodes": ["AnalysisAgent", "RefactorAgent", "ReviewAgent", "FixCodeAgent"],
        "flow": [
            ("START", "AnalysisAgent"),
            ("AnalysisAgent", "RefactorAgent"),
            ("RefactorAgent", "ReviewAgent"),
            ("ReviewAgent", "Decision"),
            ("Decision", "FixCodeAgent", "needs_fix"),
            ("Decision", "END", "approved"),
            ("FixCodeAgent", "ReviewAgent")
        ],
        "has_review_loop": True
    },
    "test_generation": {
        "name": "Test Generation Workflow",
        "nodes": ["AnalysisAgent", "TestGenAgent", "ReviewAgent"],
        "flow": [
            ("START", "AnalysisAgent"),
            ("AnalysisAgent", "TestGenAgent"),
            ("TestGenAgent", "ReviewAgent"),
            ("ReviewAgent", "END")
        ],
        "has_review_loop": False
    },
    "code_review": {
        "name": "Code Review Workflow",
        "nodes": ["ReviewAgent"],
        "flow": [
            ("START", "ReviewAgent"),
            ("ReviewAgent", "END")
        ],
        "has_review_loop": False
    },
    "documentation": {
        "name": "Documentation Workflow",
        "nodes": ["AnalysisAgent", "DocGenAgent"],
        "flow": [
            ("START", "AnalysisAgent"),
            ("AnalysisAgent", "DocGenAgent"),
            ("DocGenAgent", "END")
        ],
        "has_review_loop": False
    },
    "general": {
        "name": "General Coding Workflow",
        "nodes": ["PlanningAgent", "CodingAgent", "ReviewAgent", "FixCodeAgent"],
        "flow": [
            ("START", "PlanningAgent"),
            ("PlanningAgent", "CodingAgent"),
            ("CodingAgent", "ReviewAgent"),
            ("ReviewAgent", "Decision"),
            ("Decision", "FixCodeAgent", "needs_fix"),
            ("Decision", "END", "approved"),
            ("FixCodeAgent", "ReviewAgent")
        ],
        "has_review_loop": True
    }
}


class CodeBlockParser:
    """Parser for detecting and extracting code blocks from streaming text."""

    def __init__(self):
        self.buffer = ""
        self.in_code_block = False
        self.current_language = ""
        self.current_filename = ""
        self.used_filenames = set()  # Track used filenames for uniqueness
        self.file_counter = {}  # Track counter per extension

    def add_chunk(self, chunk: str) -> List[Dict[str, Any]]:
        self.buffer += chunk
        artifacts = []

        while True:
            if not self.in_code_block:
                match = re.search(r'```(\w+)?(?:\s+(\S+))?\n', self.buffer)
                if match:
                    self.in_code_block = True
                    self.current_language = match.group(1) or "text"
                    self.current_filename = match.group(2) or ""  # Will generate later
                    self.buffer = self.buffer[match.end():]
                else:
                    break
            else:
                end_match = re.search(r'\n```(?:\s|$)', self.buffer)
                if end_match:
                    code_content = self.buffer[:end_match.start()].strip()

                    # Generate unique filename if not provided
                    filename = self.current_filename
                    if not filename:
                        # Try to extract from first comment line
                        first_line = code_content.split('\n')[0] if code_content else ""
                        comment_match = re.match(r'^(?:#|//|/\*)\s*(?:file(?:name)?:\s*)?(\S+\.\w+)', first_line, re.IGNORECASE)
                        if comment_match:
                            filename = comment_match.group(1)
                        else:
                            # Generate unique name
                            ext = self._get_extension(self.current_language)
                            base_name = f"code_{self.current_language.lower()}" if self.current_language != "text" else "code"
                            if ext not in self.file_counter:
                                self.file_counter[ext] = 0
                            self.file_counter[ext] += 1
                            if self.file_counter[ext] == 1:
                                filename = f"{base_name}.{ext}"
                            else:
                                filename = f"{base_name}_{self.file_counter[ext]}.{ext}"

                    # Ensure uniqueness
                    original_filename = filename
                    counter = 1
                    while filename in self.used_filenames:
                        name, ext = original_filename.rsplit('.', 1) if '.' in original_filename else (original_filename, 'txt')
                        filename = f"{name}_{counter}.{ext}"
                        counter += 1
                    self.used_filenames.add(filename)

                    artifacts.append({
                        "type": "artifact",
                        "language": self.current_language,
                        "filename": filename,
                        "content": code_content
                    })
                    self.buffer = self.buffer[end_match.end():]
                    self.in_code_block = False
                    self.current_language = ""
                    self.current_filename = ""
                else:
                    break

        return artifacts

    def _get_extension(self, language: str) -> str:
        extensions = {
            "python": "py", "javascript": "js", "typescript": "ts",
            "java": "java", "go": "go", "rust": "rs", "cpp": "cpp",
            "c": "c", "html": "html", "css": "css", "json": "json",
            "yaml": "yaml", "sql": "sql", "bash": "sh", "shell": "sh"
        }
        return extensions.get(language.lower(), "txt")


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
    """Extract code blocks from text with unique filename generation."""
    artifacts = []
    pattern = r'```(\w+)?(?:\s+(\S+))?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)

    extensions = {
        "python": "py", "javascript": "js", "typescript": "ts",
        "java": "java", "go": "go", "rust": "rs", "cpp": "cpp",
        "c": "c", "html": "html", "css": "css", "json": "json",
        "yaml": "yaml", "sql": "sql", "bash": "sh", "shell": "sh"
    }

    # Track used filenames to generate unique names
    used_filenames = set()
    file_counter = {}  # Track counter per extension

    for lang, filename, content in matches:
        lang = lang or "text"
        content = content.strip()

        # Try to extract filename from first comment line if not provided
        if not filename and content:
            first_line = content.split('\n')[0] if content else ""
            # Match patterns like: # filename.py, // filename.js, /* filename.css */
            comment_match = re.match(r'^(?:#|//|/\*)\s*(?:file(?:name)?:\s*)?(\S+\.\w+)', first_line, re.IGNORECASE)
            if comment_match:
                filename = comment_match.group(1)

        # Generate unique filename if still not provided
        if not filename:
            ext = extensions.get(lang.lower(), "txt")
            base_name = f"code_{lang.lower()}" if lang != "text" else "code"

            # Initialize counter for this extension
            if ext not in file_counter:
                file_counter[ext] = 0
            file_counter[ext] += 1

            # Generate unique name
            if file_counter[ext] == 1:
                filename = f"{base_name}.{ext}"
            else:
                filename = f"{base_name}_{file_counter[ext]}.{ext}"

        # Ensure filename is unique even if explicitly provided
        original_filename = filename
        counter = 1
        while filename in used_filenames:
            name, ext = original_filename.rsplit('.', 1) if '.' in original_filename else (original_filename, 'txt')
            filename = f"{name}_{counter}.{ext}"
            counter += 1

        used_filenames.add(filename)

        artifacts.append({
            "type": "artifact",
            "language": lang,
            "filename": filename,
            "content": content
        })

    return artifacts


def parse_review(text: str) -> Dict[str, Any]:
    """Parse review text into structured format with line-specific issues."""
    issues = []
    suggestions = []
    approved = False
    analysis = ""

    # Parse ANALYSIS
    analysis_match = re.search(r'ANALYSIS:\s*(.+?)(?=\n\n|ISSUES:|$)', text, re.IGNORECASE | re.DOTALL)
    if analysis_match:
        analysis = analysis_match.group(1).strip()

    # Parse STATUS
    status_match = re.search(r'STATUS:\s*(APPROVED|NEEDS_REVISION)', text, re.IGNORECASE)
    if status_match:
        approved = status_match.group(1).upper() == "APPROVED"
    elif re.search(r'\b(?:lgtm|looks good|no issues found)\b', text, re.IGNORECASE):
        approved = True

    # Parse ISSUES section
    issues_section = re.search(r'ISSUES:\s*(.*?)(?=SUGGESTIONS:|STATUS:|```|$)', text, re.IGNORECASE | re.DOTALL)
    if issues_section:
        issues_text = issues_section.group(1).strip()
        issue_blocks = re.split(r'\n\s*\n|\n(?=-\s*File:)', issues_text)
        for block in issue_blocks:
            if not block.strip():
                continue

            issue_obj = {}
            file_match = re.search(r'-?\s*File:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
            line_match = re.search(r'-?\s*Line:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
            severity_match = re.search(r'-?\s*Severity:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
            issue_match = re.search(r'-?\s*Issue:\s*(.+?)(?:\n-|$)', block, re.IGNORECASE | re.DOTALL)
            fix_match = re.search(r'-?\s*Fix:\s*(.+?)(?:\n\n|$)', block, re.IGNORECASE | re.DOTALL)

            if file_match:
                issue_obj["file"] = file_match.group(1).strip()
            if line_match:
                issue_obj["line"] = line_match.group(1).strip()
            if severity_match:
                issue_obj["severity"] = severity_match.group(1).strip().lower()
            if issue_match:
                issue_obj["issue"] = issue_match.group(1).strip()
            if fix_match:
                issue_obj["fix"] = fix_match.group(1).strip()

            if issue_obj.get("issue"):
                issues.append(issue_obj)
            elif block.strip():
                simple_match = re.search(r'[-*]\s*(?:Issue:\s*)?(.+)', block, re.IGNORECASE)
                if simple_match:
                    issues.append({"issue": simple_match.group(1).strip(), "severity": "warning"})

    # Parse SUGGESTIONS section
    suggestions_section = re.search(r'SUGGESTIONS:\s*(.*?)(?=STATUS:|ISSUES:|```|$)', text, re.IGNORECASE | re.DOTALL)
    if suggestions_section:
        suggestions_text = suggestions_section.group(1).strip()
        for match in re.finditer(r'[-*]\s*(?:Suggest(?:ion)?:\s*)?(.+?)(?=\n[-*]|\n\n|$)', suggestions_text, re.IGNORECASE):
            suggestions.append({"suggestion": match.group(1).strip()})

    # Check severity for approval override
    if issues and approved:
        for issue in issues:
            severity = issue.get("severity", "warning") if isinstance(issue, dict) else "warning"
            if severity in ["critical", "error"]:
                approved = False
                break

    return {
        "analysis": analysis,
        "issues": issues,
        "suggestions": suggestions,
        "approved": approved,
        "corrected_artifacts": parse_code_blocks(text)
    }


@dataclass
class Response:
    """Complete response wrapper."""
    messages: List[ChatMessage] = field(default_factory=list)
    conversation_id: Optional[str] = None
    response_id: Optional[str] = None
    object: str = "response"
    created_at: Optional[datetime] = None
    status: str = "completed"
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None

    def __post_init__(self):
        if self.response_id is None:
            self.response_id = f"resp_{uuid.uuid4().hex[:24]}"
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def text(self) -> str:
        return self.messages[0].text if self.messages else ""


class VLLMChatClient(BaseChatClient):
    """Custom chat client for vLLM."""

    def __init__(self, model_type: str):
        self.vllm_client = vllm_router.get_client(model_type)
        self.model_type = model_type

    async def _inner_get_response(self, messages: List[ChatMessage], **kwargs) -> Response:
        vllm_messages = [
            {"role": msg.role if isinstance(msg.role, str) else msg.role.value, "content": msg.text}
            for msg in messages
        ]

        vllm_response = await self.vllm_client.chat_completion(
            messages=vllm_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=False
        )

        response_message = ChatMessage(role="assistant", text=vllm_response.choices[0].message.content)
        return Response(messages=[response_message], model=self.model_type)

    async def _inner_get_streaming_response(self, messages: List[ChatMessage], **kwargs) -> AsyncGenerator[ChatResponseUpdate, None]:
        vllm_messages = [
            {"role": msg.role if isinstance(msg.role, str) else msg.role.value, "content": msg.text}
            for msg in messages
        ]

        async for chunk in self.vllm_client.stream_chat_completion(
            messages=vllm_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096)
        ):
            yield ChatResponseUpdate(contents=[TextContent(text=chunk)], role="assistant", author_name=self.model_type)


class DynamicCodingWorkflow(BaseWorkflow):
    """Dynamic multi-agent coding workflow with SupervisorAgent."""

    def __init__(self):
        """Initialize the dynamic workflow."""
        self.reasoning_client = VLLMChatClient("reasoning")
        self.coding_client = VLLMChatClient("coding")

        # Agent prompts
        self.prompts = {
            "SupervisorAgent": """You are a Supervisor Agent that analyzes user requests and determines the best workflow.

<task>
Analyze the user's request and determine:
1. TASK_TYPE: One of [code_generation, bug_fix, refactoring, test_generation, code_review, documentation, general]
2. COMPLEXITY: [simple, medium, complex]
3. REQUIREMENTS: List key requirements
4. RECOMMENDED_AGENTS: Which agents should be used
</task>

<output_format>
TASK_TYPE: [type]
COMPLEXITY: [level]
REQUIREMENTS:
- [requirement 1]
- [requirement 2]
RECOMMENDED_AGENTS: [agent1], [agent2], ...
</output_format>

Be concise. Focus on accurate classification.""",

            "PlanningAgent": """Analyze request and create implementation checklist.

<output_format>
1. [Task description]
2. [Task description]
</output_format>

Rules:
- One task per line
- Clear, actionable steps
- No explanations, only the numbered list""",

            "CodingAgent": """Implement the specified task.

<response_format>
THOUGHTS: [brief analysis]

```language filename.ext
// complete code
```
</response_format>

<rules>
- Focus ONLY on current task
- Include filename after language
- Write complete, runnable code
</rules>""",

            "ReviewAgent": """Review code and provide detailed, line-specific feedback.

<response_format>
ANALYSIS: [brief overall review summary]

ISSUES:
- File: [filename]
- Line: [line number]
- Severity: [critical/warning/info]
- Issue: [problem description]
- Fix: [suggested fix]

SUGGESTIONS:
- Suggestion: [improvement]

STATUS: [APPROVED or NEEDS_REVISION]

If NEEDS_REVISION, provide corrected code:
```language filename.ext
// corrected complete code
```
</response_format>""",

            "FixCodeAgent": """Fix the code based on review feedback.

<review_issues>
{issues}
</review_issues>

<rules>
- Address ALL issues listed above
- Provide complete corrected code
- Use same filename format
</rules>

```language filename.ext
// corrected code
```"""
        }

        logger.info("DynamicCodingWorkflow (Microsoft) initialized")

    def _analyze_task(self, supervisor_response: str) -> TaskType:
        """Analyze supervisor response to determine task type."""
        text_lower = supervisor_response.lower()

        # Look for explicit TASK_TYPE
        task_match = re.search(r'task_type:\s*(\w+)', text_lower)
        if task_match:
            task_type = task_match.group(1).replace(' ', '_')
            if task_type in WORKFLOW_TEMPLATES:
                return task_type

        # Fallback detection
        if any(kw in text_lower for kw in ["bug_fix", "fix", "debug", "error"]):
            return "bug_fix"
        elif any(kw in text_lower for kw in ["refactor", "restructure", "clean"]):
            return "refactoring"
        elif any(kw in text_lower for kw in ["test", "testing", "unit test"]):
            return "test_generation"
        elif any(kw in text_lower for kw in ["review", "check", "audit"]):
            return "code_review"
        elif any(kw in text_lower for kw in ["document", "documentation", "docstring"]):
            return "documentation"
        elif any(kw in text_lower for kw in ["create", "implement", "build", "make"]):
            return "code_generation"

        return "general"

    async def execute(self, user_request: str, context: Optional[AgentRunContext] = None) -> str:
        """Execute the dynamic workflow."""
        logger.info(f"Executing dynamic workflow for: {user_request[:100]}...")
        result = ""
        async for update in self.execute_stream(user_request, context):
            if update.get("type") == "completed" and update.get("agent") == "Orchestrator":
                result = str(update.get("final_result", {}))
        return result

    async def execute_stream(self, user_request: str, context: Optional[AgentRunContext] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the workflow with streaming updates."""
        logger.info(f"Streaming dynamic workflow for: {user_request[:100]}...")

        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        max_iterations = settings.max_review_iterations

        def extract_text(update: ChatResponseUpdate) -> str:
            return "".join(c.text for c in update.contents if isinstance(c, TextContent) and c.text)

        try:
            # Phase 1: Supervisor Agent analyzes task
            yield {
                "agent": "SupervisorAgent",
                "type": "agent_spawn",
                "status": "running",
                "message": "Analyzing task...",
                "agent_spawn": {
                    "agent_id": f"supervisor-{uuid.uuid4().hex[:6]}",
                    "agent_type": "SupervisorAgent",
                    "parent_agent": "Orchestrator",
                    "spawn_reason": "Analyze task and determine workflow",
                    "timestamp": datetime.now().isoformat()
                }
            }

            supervisor_agent = ChatAgent(
                name="SupervisorAgent",
                description="Analyzes tasks and determines workflow",
                chat_client=self.reasoning_client,
                system_message=self.prompts["SupervisorAgent"]
            )

            supervisor_msg = ChatMessage(role="user", text=f"Analyze this request:\n\n{user_request}")
            supervisor_text = ""
            start_time = time.time()
            async for update in supervisor_agent.run_stream(supervisor_msg):
                supervisor_text += extract_text(update)
            supervisor_latency = int((time.time() - start_time) * 1000)

            task_type = self._analyze_task(supervisor_text)
            template = WORKFLOW_TEMPLATES[task_type]

            yield {
                "agent": "SupervisorAgent",
                "type": "completed",
                "status": "completed",
                "message": f"Task type: {task_type}",
                "task_analysis": {
                    "task_type": task_type,
                    "workflow_name": template["name"],
                    "agents": template["nodes"],
                    "has_review_loop": template["has_review_loop"]
                },
                "prompt_info": {
                    "system_prompt": self.prompts["SupervisorAgent"],
                    "user_prompt": f"Analyze this request:\n\n{user_request}",
                    "output": supervisor_text,
                    "model": settings.reasoning_model,
                    "latency_ms": supervisor_latency
                }
            }

            # Phase 2: Create workflow
            yield {
                "agent": "Orchestrator",
                "type": "workflow_created",
                "status": "running",
                "message": f"Created {template['name']}",
                "workflow_info": {
                    "workflow_id": workflow_id,
                    "workflow_type": template["name"],
                    "task_type": task_type,
                    "nodes": template["nodes"],
                    "edges": [{"from": f[0], "to": f[1], "condition": f[2] if len(f) > 2 else None} for f in template["flow"]],
                    "max_iterations": max_iterations if template["has_review_loop"] else 0,
                    "dynamically_created": True
                }
            }

            # Phase 3: Execute workflow based on task type
            if task_type in ["code_generation", "bug_fix", "refactoring", "general"]:
                async for update in self._execute_coding_workflow(user_request, task_type, template, workflow_id, max_iterations):
                    yield update
            elif task_type == "test_generation":
                async for update in self._execute_test_workflow(user_request, task_type, template, workflow_id):
                    yield update
            elif task_type == "code_review":
                async for update in self._execute_review_only_workflow(user_request, task_type, template, workflow_id):
                    yield update
            else:
                async for update in self._execute_coding_workflow(user_request, task_type, template, workflow_id, max_iterations):
                    yield update

        except Exception as e:
            logger.error(f"Error in dynamic workflow: {e}")
            yield {"agent": "Workflow", "type": "error", "status": "error", "message": str(e)}
            raise

    async def _execute_coding_workflow(
        self,
        user_request: str,
        task_type: TaskType,
        template: Dict[str, Any],
        workflow_id: str,
        max_iterations: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the main coding workflow with review loop."""

        def extract_text(update: ChatResponseUpdate) -> str:
            return "".join(c.text for c in update.contents if isinstance(c, TextContent) and c.text)

        # Step 1: Planning
        planning_agent = ChatAgent(
            name="PlanningAgent",
            description="Creates implementation plan",
            chat_client=self.reasoning_client,
            system_message=self.prompts["PlanningAgent"]
        )

        yield {"agent": "PlanningAgent", "type": "thinking", "status": "running", "message": "Creating plan..."}

        plan_msg = ChatMessage(role="user", text=user_request)
        plan_text = ""
        start_time = time.time()
        async for update in planning_agent.run_stream(plan_msg):
            plan_text += extract_text(update)
        plan_latency = int((time.time() - start_time) * 1000)

        checklist = parse_checklist(plan_text)
        yield {
            "agent": "PlanningAgent",
            "type": "completed",
            "status": "completed",
            "items": checklist,
            "prompt_info": {
                "system_prompt": self.prompts["PlanningAgent"],
                "user_prompt": user_request,
                "output": plan_text,
                "model": settings.reasoning_model,
                "latency_ms": plan_latency
            }
        }

        # Step 2: Coding
        coding_agent = ChatAgent(
            name="CodingAgent",
            description="Implements code",
            chat_client=self.coding_client,
            system_message=self.prompts["CodingAgent"]
        )

        all_artifacts = []
        code_text = ""
        existing_code = ""

        for idx, task_item in enumerate(checklist):
            task_num = idx + 1
            task_desc = task_item["task"]

            yield {
                "agent": "CodingAgent",
                "type": "thinking",
                "status": "running",
                "message": f"Task {task_num}/{len(checklist)}: {task_desc}",
                "checklist": checklist
            }

            user_prompt = f"Request: {user_request}\n\nPlan:\n{plan_text}"
            if existing_code:
                user_prompt += f"\n\nExisting code:\n{existing_code}"
            user_prompt += f"\n\nCurrent task ({task_num}/{len(checklist)}): {task_desc}"

            coding_msg = ChatMessage(role="user", text=user_prompt)
            task_code = ""
            start_time = time.time()
            async for update in coding_agent.run_stream(coding_msg):
                task_code += extract_text(update)
            task_latency = int((time.time() - start_time) * 1000)

            code_text += task_code + "\n"
            task_artifacts = parse_code_blocks(task_code)
            all_artifacts.extend(task_artifacts)

            for artifact in task_artifacts:
                existing_code += f"\n\n```{artifact['language']} {artifact['filename']}\n{artifact['content']}\n```"
                yield {
                    "agent": "CodingAgent",
                    "type": "artifact",
                    "status": "running",
                    "message": f"Created {artifact['filename']}",
                    "artifact": artifact
                }

            checklist[idx]["completed"] = True
            checklist[idx]["artifacts"] = [a["filename"] for a in task_artifacts]

            yield {
                "agent": "CodingAgent",
                "type": "task_completed",
                "status": "running",
                "message": f"Task {task_num}/{len(checklist)} completed",
                "task_result": {"task_num": task_num, "task": task_desc, "artifacts": task_artifacts},
                "checklist": checklist,
                "prompt_info": {
                    "system_prompt": self.prompts["CodingAgent"],
                    "user_prompt": user_prompt,
                    "output": task_code,
                    "model": settings.coding_model,
                    "latency_ms": task_latency
                }
            }

        yield {"agent": "CodingAgent", "type": "completed", "status": "completed", "artifacts": all_artifacts, "checklist": checklist}

        # Step 3: Review Loop
        if template["has_review_loop"]:
            review_iteration = 0
            approved = False

            while not approved and review_iteration < max_iterations:
                review_iteration += 1

                # Review
                yield {
                    "agent": "ReviewAgent",
                    "type": "thinking",
                    "status": "running",
                    "message": f"Reviewing (iteration {review_iteration}/{max_iterations})...",
                    "iteration_info": {"current": review_iteration, "max": max_iterations}
                }

                review_agent = ChatAgent(
                    name="ReviewAgent",
                    description="Reviews code",
                    chat_client=self.coding_client,
                    system_message=self.prompts["ReviewAgent"]
                )

                review_msg = ChatMessage(role="user", text=f"Review this code:\n\n{code_text}")
                review_text = ""
                start_time = time.time()
                async for update in review_agent.run_stream(review_msg):
                    review_text += extract_text(update)
                review_latency = int((time.time() - start_time) * 1000)

                review_result = parse_review(review_text)
                approved = review_result["approved"]

                yield {
                    "agent": "ReviewAgent",
                    "type": "completed",
                    "status": "completed",
                    "analysis": review_result.get("analysis", ""),
                    "issues": review_result["issues"],
                    "suggestions": review_result["suggestions"],
                    "approved": approved,
                    "corrected_artifacts": review_result["corrected_artifacts"],
                    "prompt_info": {
                        "system_prompt": self.prompts["ReviewAgent"],
                        "user_prompt": f"Review this code:\n\n{code_text}",
                        "output": review_text,
                        "model": settings.coding_model,
                        "latency_ms": review_latency
                    },
                    "iteration_info": {"current": review_iteration, "max": max_iterations}
                }

                # Decision
                yield {
                    "agent": "Orchestrator",
                    "type": "decision",
                    "status": "running",
                    "message": f"Decision: {'APPROVED' if approved else 'NEEDS_REVISION'}",
                    "decision": {
                        "approved": approved,
                        "iteration": review_iteration,
                        "max_iterations": max_iterations,
                        "action": "end" if approved else ("fix_code" if review_iteration < max_iterations else "end_max_iterations")
                    }
                }

                # Fix if needed
                if not approved and review_iteration < max_iterations:
                    yield {
                        "agent": "FixCodeAgent",
                        "type": "thinking",
                        "status": "running",
                        "message": f"Fixing {len(review_result['issues'])} issues..."
                    }

                    # Format issues
                    def format_issue(issue):
                        if isinstance(issue, dict):
                            parts = []
                            if issue.get("file"):
                                parts.append(f"File: {issue['file']}")
                            if issue.get("line"):
                                parts.append(f"Line: {issue['line']}")
                            if issue.get("issue"):
                                parts.append(f"Issue: {issue['issue']}")
                            if issue.get("fix"):
                                parts.append(f"Fix: {issue['fix']}")
                            return "\n  ".join(parts)
                        return str(issue)

                    issues_text = "\n".join(f"- {format_issue(i)}" for i in review_result["issues"]) or "None"
                    fix_prompt = self.prompts["FixCodeAgent"].format(issues=issues_text)

                    fix_agent = ChatAgent(
                        name="FixCodeAgent",
                        description="Fixes code issues",
                        chat_client=self.coding_client,
                        system_message=fix_prompt
                    )

                    fix_msg = ChatMessage(role="user", text=f"Fix this code:\n\n{code_text}")
                    fixed_code = ""
                    start_time = time.time()
                    async for update in fix_agent.run_stream(fix_msg):
                        fixed_code += extract_text(update)
                    fix_latency = int((time.time() - start_time) * 1000)

                    code_text = fixed_code
                    fixed_artifacts = parse_code_blocks(fixed_code)
                    all_artifacts = fixed_artifacts

                    for artifact in fixed_artifacts:
                        yield {
                            "agent": "FixCodeAgent",
                            "type": "artifact",
                            "status": "running",
                            "message": f"Fixed {artifact['filename']}",
                            "artifact": artifact
                        }

                    yield {
                        "agent": "FixCodeAgent",
                        "type": "completed",
                        "status": "completed",
                        "artifacts": fixed_artifacts,
                        "prompt_info": {
                            "system_prompt": fix_prompt,
                            "user_prompt": f"Fix this code:\n\n{code_text}",
                            "output": fixed_code,
                            "model": settings.coding_model,
                            "latency_ms": fix_latency
                        }
                    }

            # Final result
            final_status = "approved" if approved else "max_iterations_reached"
            final_message = (
                f"Code review passed. Generated {len(all_artifacts)} file(s)."
                if approved else
                f"Review loop ended after {review_iteration} iterations. Generated {len(all_artifacts)} file(s)."
            )

            yield {
                "agent": "Orchestrator",
                "type": "completed",
                "status": "completed",
                "message": final_message,
                "final_result": {
                    "success": approved,
                    "message": final_message,
                    "tasks_completed": sum(1 for item in checklist if item["completed"]),
                    "total_tasks": len(checklist),
                    "artifacts": [{"filename": a["filename"], "language": a["language"]} for a in all_artifacts],
                    "review_status": "approved" if approved else "needs_revision",
                    "review_iterations": review_iteration
                },
                "artifacts": all_artifacts,
                "workflow_info": {
                    "workflow_id": workflow_id,
                    "workflow_type": template["name"],
                    "task_type": task_type,
                    "nodes": template["nodes"],
                    "current_node": "END",
                    "final_status": final_status,
                    "dynamically_created": True
                }
            }
        else:
            # No review loop
            yield {
                "agent": "Orchestrator",
                "type": "completed",
                "status": "completed",
                "message": f"Completed. Generated {len(all_artifacts)} file(s).",
                "final_result": {
                    "success": True,
                    "message": f"Completed. Generated {len(all_artifacts)} file(s).",
                    "tasks_completed": len(checklist),
                    "total_tasks": len(checklist),
                    "artifacts": [{"filename": a["filename"], "language": a["language"]} for a in all_artifacts],
                    "review_status": "skipped",
                    "review_iterations": 0
                },
                "artifacts": all_artifacts,
                "workflow_info": {
                    "workflow_id": workflow_id,
                    "workflow_type": template["name"],
                    "task_type": task_type,
                    "nodes": template["nodes"],
                    "current_node": "END",
                    "dynamically_created": True
                }
            }

    async def _execute_test_workflow(self, user_request: str, task_type: TaskType, template: Dict, workflow_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute test generation workflow."""
        # Simplified - uses same pattern but with test-focused prompts
        async for update in self._execute_coding_workflow(user_request, task_type, template, workflow_id, 0):
            yield update

    async def _execute_review_only_workflow(self, user_request: str, task_type: TaskType, template: Dict, workflow_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute review-only workflow."""
        def extract_text(update: ChatResponseUpdate) -> str:
            return "".join(c.text for c in update.contents if isinstance(c, TextContent) and c.text)

        yield {"agent": "ReviewAgent", "type": "thinking", "status": "running", "message": "Reviewing code..."}

        review_agent = ChatAgent(
            name="ReviewAgent",
            description="Reviews code",
            chat_client=self.coding_client,
            system_message=self.prompts["ReviewAgent"]
        )

        review_msg = ChatMessage(role="user", text=f"Review this code:\n\n{user_request}")
        review_text = ""
        start_time = time.time()
        async for update in review_agent.run_stream(review_msg):
            review_text += extract_text(update)
        review_latency = int((time.time() - start_time) * 1000)

        review_result = parse_review(review_text)

        yield {
            "agent": "ReviewAgent",
            "type": "completed",
            "status": "completed",
            "analysis": review_result.get("analysis", ""),
            "issues": review_result["issues"],
            "suggestions": review_result["suggestions"],
            "approved": review_result["approved"],
            "corrected_artifacts": review_result["corrected_artifacts"],
            "prompt_info": {
                "system_prompt": self.prompts["ReviewAgent"],
                "user_prompt": f"Review this code:\n\n{user_request}",
                "output": review_text,
                "model": settings.coding_model,
                "latency_ms": review_latency
            }
        }

        yield {
            "agent": "Orchestrator",
            "type": "completed",
            "status": "completed",
            "message": "Review completed.",
            "final_result": {
                "success": True,
                "message": "Review completed.",
                "tasks_completed": 1,
                "total_tasks": 1,
                "artifacts": [],
                "review_status": "approved" if review_result["approved"] else "needs_revision",
                "review_iterations": 1
            },
            "workflow_info": {
                "workflow_id": workflow_id,
                "workflow_type": template["name"],
                "task_type": task_type,
                "nodes": template["nodes"],
                "current_node": "END",
                "dynamically_created": True
            }
        }


class WorkflowManager(BaseWorkflowManager):
    """Manager for dynamic workflow sessions."""

    def __init__(self):
        self.workflows: Dict[str, DynamicCodingWorkflow] = {}
        logger.info("WorkflowManager (Microsoft) initialized with dynamic workflow support")

    def get_or_create_workflow(self, session_id: str) -> DynamicCodingWorkflow:
        if session_id not in self.workflows:
            self.workflows[session_id] = DynamicCodingWorkflow()
            logger.info(f"Created new dynamic workflow for session {session_id}")
        return self.workflows[session_id]

    def delete_workflow(self, session_id: str) -> None:
        if session_id in self.workflows:
            del self.workflows[session_id]
            logger.info(f"Deleted workflow for session {session_id}")

    def get_active_sessions(self) -> List[str]:
        return list(self.workflows.keys())


# Global workflow manager instance
workflow_manager = WorkflowManager()

# Backward compatibility
CodingWorkflow = DynamicCodingWorkflow
