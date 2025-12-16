"""Dynamic workflow-based coding agent using LangGraph with SupervisorAgent."""
import logging
import re
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, AsyncGenerator, Optional, TypedDict, Annotated, Literal
from operator import add
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from app.agent.base.interface import BaseWorkflow, BaseWorkflowManager

logger = logging.getLogger(__name__)


# Task types that can be identified
TaskType = Literal[
    "code_generation",    # Create new code from scratch
    "bug_fix",            # Fix existing code
    "refactoring",        # Improve code structure
    "test_generation",    # Write tests
    "code_review",        # Review existing code
    "documentation",      # Write docs
    "general"             # Default fallback
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
            ("ReviewAgent", "decision"),  # conditional
            ("FixCodeAgent", "ReviewAgent"),  # loop back
        ],
        "has_review_loop": True
    },
    "bug_fix": {
        "name": "Bug Fix Workflow",
        "nodes": ["AnalysisAgent", "DebugAgent", "FixCodeAgent", "TestAgent"],
        "flow": [
            ("START", "AnalysisAgent"),
            ("AnalysisAgent", "DebugAgent"),
            ("DebugAgent", "FixCodeAgent"),
            ("FixCodeAgent", "TestAgent"),
            ("TestAgent", "decision"),  # conditional
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
            ("ReviewAgent", "decision"),
            ("FixCodeAgent", "ReviewAgent"),
        ],
        "has_review_loop": True
    },
    "test_generation": {
        "name": "Test Generation Workflow",
        "nodes": ["AnalysisAgent", "TestGenAgent", "ValidationAgent"],
        "flow": [
            ("START", "AnalysisAgent"),
            ("AnalysisAgent", "TestGenAgent"),
            ("TestGenAgent", "ValidationAgent"),
            ("ValidationAgent", "decision"),
        ],
        "has_review_loop": True
    },
    "code_review": {
        "name": "Code Review Workflow",
        "nodes": ["ReviewAgent", "SuggestionAgent"],
        "flow": [
            ("START", "ReviewAgent"),
            ("ReviewAgent", "SuggestionAgent"),
        ],
        "has_review_loop": False
    },
    "documentation": {
        "name": "Documentation Workflow",
        "nodes": ["AnalysisAgent", "DocGenAgent", "ReviewAgent"],
        "flow": [
            ("START", "AnalysisAgent"),
            ("AnalysisAgent", "DocGenAgent"),
            ("DocGenAgent", "ReviewAgent"),
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
            ("ReviewAgent", "decision"),
            ("FixCodeAgent", "ReviewAgent"),
        ],
        "has_review_loop": True
    }
}


# State definition for LangGraph
class WorkflowState(TypedDict):
    """State maintained throughout the workflow."""
    user_request: str
    task_type: TaskType
    task_analysis: str
    plan_text: str
    checklist: List[Dict[str, Any]]
    code_text: str
    artifacts: Annotated[List[Dict[str, Any]], add]
    review_result: Dict[str, Any]
    review_iteration: int
    max_iterations: int
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
    """Parse review text into structured format with line-specific issues.

    Expected format:
    ANALYSIS: [summary]
    ISSUES:
    - File: [filename]
    - Line: [line number]
    - Severity: [critical/warning/info]
    - Issue: [problem]
    - Fix: [suggestion]
    SUGGESTIONS:
    - File: [filename]
    - Line: [line]
    - Suggestion: [improvement]
    STATUS: APPROVED or NEEDS_REVISION
    """
    issues = []
    suggestions = []
    approved = False
    analysis = ""

    # Parse ANALYSIS
    analysis_match = re.search(r'ANALYSIS:\s*(.+?)(?=\n\n|ISSUES:|$)', text, re.IGNORECASE | re.DOTALL)
    if analysis_match:
        analysis = analysis_match.group(1).strip()

    # Parse STATUS field explicitly - this takes precedence
    status_match = re.search(r'STATUS:\s*(APPROVED|NEEDS_REVISION)', text, re.IGNORECASE)
    if status_match:
        approved = status_match.group(1).upper() == "APPROVED"
    else:
        # Fallback: if no explicit status, check for approval keywords
        if re.search(r'\b(?:lgtm|looks good|no issues found)\b', text, re.IGNORECASE):
            approved = True

    # Parse ISSUES section with structured format
    issues_section = re.search(r'ISSUES:\s*(.*?)(?=SUGGESTIONS:|STATUS:|```|$)', text, re.IGNORECASE | re.DOTALL)
    if issues_section:
        issues_text = issues_section.group(1).strip()

        # Try to parse structured issues (File/Line/Severity/Issue/Fix format)
        issue_blocks = re.split(r'\n\s*\n|\n(?=-\s*File:)', issues_text)
        for block in issue_blocks:
            if not block.strip():
                continue

            issue_obj = {}
            # Parse each field
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

            # If we got at least an issue description, add it
            if issue_obj.get("issue"):
                issues.append(issue_obj)
            elif block.strip() and not any(k in block.lower() for k in ['file:', 'line:', 'severity:']):
                # Fallback: simple text issue (old format compatibility)
                simple_match = re.search(r'[-*]\s*(?:Issue:\s*)?(.+)', block, re.IGNORECASE)
                if simple_match:
                    issues.append({"issue": simple_match.group(1).strip(), "severity": "warning"})

    # Parse SUGGESTIONS section with structured format
    suggestions_section = re.search(r'SUGGESTIONS:\s*(.*?)(?=STATUS:|ISSUES:|```|$)', text, re.IGNORECASE | re.DOTALL)
    if suggestions_section:
        suggestions_text = suggestions_section.group(1).strip()

        # Try to parse structured suggestions
        suggestion_blocks = re.split(r'\n\s*\n|\n(?=-\s*File:)', suggestions_text)
        for block in suggestion_blocks:
            if not block.strip():
                continue

            suggestion_obj = {}
            file_match = re.search(r'-?\s*File:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
            line_match = re.search(r'-?\s*Line:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
            suggestion_match = re.search(r'-?\s*Suggestion:\s*(.+?)(?:\n\n|$)', block, re.IGNORECASE | re.DOTALL)

            if file_match:
                suggestion_obj["file"] = file_match.group(1).strip()
            if line_match:
                suggestion_obj["line"] = line_match.group(1).strip()
            if suggestion_match:
                suggestion_obj["suggestion"] = suggestion_match.group(1).strip()

            if suggestion_obj.get("suggestion"):
                suggestions.append(suggestion_obj)
            elif block.strip() and not any(k in block.lower() for k in ['file:', 'line:']):
                # Fallback: simple text suggestion
                simple_match = re.search(r'[-*]\s*(?:Suggest(?:ion)?:\s*)?(.+)', block, re.IGNORECASE)
                if simple_match:
                    suggestions.append({"suggestion": simple_match.group(1).strip()})

    # If issues exist but STATUS says APPROVED, check severity
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


def parse_task_type(text: str) -> TaskType:
    """Parse task type from supervisor analysis."""
    text_lower = text.lower()

    if any(kw in text_lower for kw in ["code_generation", "create", "implement", "build", "make"]):
        return "code_generation"
    elif any(kw in text_lower for kw in ["bug_fix", "fix", "debug", "error", "issue"]):
        return "bug_fix"
    elif any(kw in text_lower for kw in ["refactor", "improve", "optimize", "clean"]):
        return "refactoring"
    elif any(kw in text_lower for kw in ["test", "unit test", "testing"]):
        return "test_generation"
    elif any(kw in text_lower for kw in ["review", "check", "analyze code"]):
        return "code_review"
    elif any(kw in text_lower for kw in ["document", "doc", "readme", "comment"]):
        return "documentation"
    else:
        return "general"


class DynamicLangGraphWorkflow(BaseWorkflow):
    """Dynamic multi-agent workflow that creates workflow based on task analysis."""

    def __init__(self):
        """Initialize the dynamic workflow."""
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

        # Supervisor prompt for task analysis
        self.supervisor_prompt = """You are a Supervisor Agent that analyzes user requests and determines the best workflow.

<task>
Analyze the user's request and determine:
1. TASK_TYPE: One of [code_generation, bug_fix, refactoring, test_generation, code_review, documentation, general]
2. COMPLEXITY: [simple, medium, complex]
3. REQUIREMENTS: List key requirements
4. RECOMMENDED_AGENTS: Which agents should be used
</task>

<response_format>
TASK_TYPE: [type]
COMPLEXITY: [level]
REQUIREMENTS:
- [requirement 1]
- [requirement 2]
RECOMMENDED_AGENTS: [agent1, agent2, ...]
ANALYSIS: [brief analysis of the task]
</response_format>

Be precise and concise. Focus on understanding what the user wants to achieve."""

        # Agent-specific prompts
        self.prompts = {
            "PlanningAgent": """Analyze request and create implementation checklist.

<think>
Break down the request into atomic, sequential steps.
Consider dependencies between tasks.
Order by implementation sequence.
</think>

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
- One code block per file
- Include filename after language
- Write complete, runnable code
</rules>""",

            "ReviewAgent": """Review code and provide detailed, line-specific feedback.

<response_format>
ANALYSIS: [brief overall review summary]

ISSUES:
For each issue, specify:
- File: [filename]
- Line: [line number or range, e.g., "15" or "15-20"]
- Severity: [critical/warning/info]
- Issue: [detailed description of the problem]
- Fix: [suggested fix]

Example:
- File: calculator.py
- Line: 25
- Severity: critical
- Issue: Division by zero not handled
- Fix: Add check for zero divisor before division

SUGGESTIONS:
- File: [filename]
- Line: [line number]
- Suggestion: [improvement recommendation]

STATUS: [APPROVED or NEEDS_REVISION]

If NEEDS_REVISION, provide corrected code:
```language filename.ext
// corrected complete code with fixes applied
```
</response_format>

<rules>
- Be specific about line numbers
- Critical issues = bugs, errors, security problems (MUST fix)
- Warnings = code smells, potential issues (SHOULD fix)
- Info = style, best practices (COULD improve)
- Only set STATUS: APPROVED if no critical/warning issues exist
</rules>""",

            "FixCodeAgent": """Fix the code based on review feedback.

<review_issues>
{issues}
</review_issues>

<review_suggestions>
{suggestions}
</review_suggestions>

<response_format>
FIXES_APPLIED: [list what you fixed]

```language filename.ext
// corrected complete code
```
</response_format>""",

            "AnalysisAgent": """Analyze the code/problem and provide insights.

<response_format>
ANALYSIS:
- [finding 1]
- [finding 2]

ROOT_CAUSE: [if applicable]
RECOMMENDATION: [suggested approach]
</response_format>""",

            "DebugAgent": """Debug the code and identify issues.

<response_format>
BUGS_FOUND:
- [bug 1]: [description]
- [bug 2]: [description]

DEBUG_STEPS:
1. [step]
2. [step]
</response_format>""",

            "RefactorAgent": """Refactor the code for better quality.

<response_format>
REFACTORING_PLAN:
- [change 1]
- [change 2]

```language filename.ext
// refactored code
```
</response_format>""",

            "TestGenAgent": """Generate tests for the code.

<response_format>
TEST_STRATEGY: [approach]

```language test_filename.ext
// test code
```
</response_format>""",

            "ValidationAgent": """Validate the tests and coverage.

<response_format>
VALIDATION_RESULT:
- Coverage: [percentage]
- Edge cases: [covered/missing]

STATUS: [PASS or NEEDS_MORE_TESTS]
</response_format>""",

            "DocGenAgent": """Generate documentation for the code.

<response_format>
```markdown README.md
// documentation
```
</response_format>""",

            "SuggestionAgent": """Provide improvement suggestions.

<response_format>
SUGGESTIONS:
1. [suggestion with explanation]
2. [suggestion with explanation]

PRIORITY: [high/medium/low for each]
</response_format>"""
        }

        logger.info("DynamicLangGraphWorkflow initialized")

    async def _analyze_task(self, user_request: str) -> tuple[TaskType, str, Dict[str, Any]]:
        """Use Supervisor to analyze the task and determine workflow type."""
        messages = [
            SystemMessage(content=self.supervisor_prompt),
            HumanMessage(content=user_request)
        ]

        response = await self.reasoning_llm.ainvoke(messages)
        analysis_text = response.content

        # Parse task type from response
        task_type = parse_task_type(analysis_text)

        # Get workflow template
        template = WORKFLOW_TEMPLATES[task_type]

        return task_type, analysis_text, template

    async def execute(
        self,
        user_request: str,
        context: Optional[Any] = None
    ) -> str:
        """Execute the dynamic workflow."""
        logger.info(f"Executing dynamic workflow for: {user_request[:100]}...")

        # First, analyze the task
        task_type, analysis, template = await self._analyze_task(user_request)
        logger.info(f"Task type determined: {task_type}, using workflow: {template['name']}")

        # For now, use the streaming version's logic
        # This is a simplified non-streaming version
        return f"Task analyzed as: {task_type}\nWorkflow: {template['name']}"

    async def execute_stream(
        self,
        user_request: str,
        context: Optional[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the dynamic workflow with streaming updates."""
        logger.info(f"Streaming dynamic workflow for: {user_request[:100]}...")
        workflow_id = str(uuid.uuid4())[:8]
        max_iterations = settings.max_review_iterations

        try:
            # ========================================
            # Phase 1: Supervisor analyzes the task
            # ========================================
            yield {
                "agent": "SupervisorAgent",
                "type": "agent_spawn",
                "status": "running",
                "message": "Spawning SupervisorAgent for task analysis",
                "agent_spawn": {
                    "agent_id": f"supervisor-{uuid.uuid4().hex[:6]}",
                    "agent_type": "SupervisorAgent",
                    "parent_agent": None,
                    "spawn_reason": "Analyze user request and determine optimal workflow",
                    "timestamp": datetime.now().isoformat()
                }
            }

            yield {
                "agent": "SupervisorAgent",
                "type": "thinking",
                "status": "running",
                "message": "Analyzing task to determine optimal workflow..."
            }

            # Analyze the task
            messages = [
                SystemMessage(content=self.supervisor_prompt),
                HumanMessage(content=user_request)
            ]

            start_time = time.time()
            analysis_text = ""
            async for chunk in self.reasoning_llm.astream(messages):
                if chunk.content:
                    analysis_text += chunk.content
            analysis_latency_ms = int((time.time() - start_time) * 1000)

            # Parse task type
            task_type = parse_task_type(analysis_text)
            template = WORKFLOW_TEMPLATES[task_type]

            yield {
                "agent": "SupervisorAgent",
                "type": "completed",
                "status": "completed",
                "message": f"Task identified as: {task_type}",
                "task_analysis": {
                    "task_type": task_type,
                    "workflow_name": template["name"],
                    "agents": template["nodes"],
                    "has_review_loop": template["has_review_loop"]
                },
                "prompt_info": {
                    "system_prompt": self.supervisor_prompt,
                    "user_prompt": user_request,
                    "output": analysis_text,
                    "model": settings.reasoning_model,
                    "latency_ms": analysis_latency_ms
                }
            }

            # ========================================
            # Phase 2: Create dynamic workflow
            # ========================================
            # Build workflow edges with conditions
            edges = []
            for i, (from_node, to_node) in enumerate(template["flow"]):
                edge = {"from": from_node, "to": to_node}
                if to_node == "decision":
                    edge["to"] = "Decision"
                    edge["condition"] = "review result"
                edges.append(edge)

            # Add decision edges if has review loop
            if template["has_review_loop"]:
                edges.append({"from": "Decision", "to": "FixCodeAgent", "condition": "not approved"})
                edges.append({"from": "Decision", "to": "END", "condition": "approved"})

            yield {
                "agent": "Orchestrator",
                "type": "workflow_created",
                "status": "running",
                "message": f"Created {template['name']} (max {max_iterations} iterations)",
                "workflow_info": {
                    "workflow_id": workflow_id,
                    "workflow_type": template["name"],
                    "task_type": task_type,
                    "nodes": template["nodes"],
                    "edges": edges,
                    "current_node": template["nodes"][0] if template["nodes"] else "END",
                    "max_iterations": max_iterations,
                    "dynamically_created": True
                }
            }

            # ========================================
            # Phase 3: Execute the workflow
            # ========================================
            # For code_generation, bug_fix, refactoring, general - use standard flow
            if task_type in ["code_generation", "general", "bug_fix", "refactoring"]:
                # Execute standard Planning -> Coding -> Review loop
                async for update in self._execute_coding_workflow(
                    user_request, task_type, template, workflow_id, max_iterations
                ):
                    yield update
            elif task_type == "test_generation":
                async for update in self._execute_test_workflow(
                    user_request, template, workflow_id, max_iterations
                ):
                    yield update
            elif task_type == "code_review":
                async for update in self._execute_review_only_workflow(
                    user_request, template, workflow_id
                ):
                    yield update
            elif task_type == "documentation":
                async for update in self._execute_doc_workflow(
                    user_request, template, workflow_id
                ):
                    yield update
            else:
                # Fallback to general coding workflow
                async for update in self._execute_coding_workflow(
                    user_request, task_type, template, workflow_id, max_iterations
                ):
                    yield update

        except Exception as e:
            logger.error(f"Error in dynamic workflow: {e}")
            yield {
                "agent": "Workflow",
                "type": "error",
                "status": "error",
                "message": str(e)
            }
            raise

    async def _execute_coding_workflow(
        self,
        user_request: str,
        task_type: TaskType,
        template: Dict[str, Any],
        workflow_id: str,
        max_iterations: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the standard coding workflow (Planning -> Coding -> Review -> Fix loop)."""

        # Step 1: Planning
        planning_agent = template["nodes"][0]  # Usually PlanningAgent or AnalysisAgent
        yield {
            "agent": planning_agent,
            "type": "agent_spawn",
            "status": "running",
            "message": f"Spawning {planning_agent}",
            "agent_spawn": {
                "agent_id": f"{planning_agent.lower()}-{uuid.uuid4().hex[:6]}",
                "agent_type": planning_agent,
                "parent_agent": "Orchestrator",
                "spawn_reason": "Create implementation plan",
                "timestamp": datetime.now().isoformat()
            }
        }

        yield {
            "agent": planning_agent,
            "type": "thinking",
            "status": "running",
            "message": "Creating implementation plan..."
        }

        planning_prompt = self.prompts.get(planning_agent, self.prompts["PlanningAgent"])
        messages = [
            SystemMessage(content=planning_prompt),
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
            "agent": planning_agent,
            "type": "completed",
            "status": "completed",
            "items": checklist,
            "prompt_info": {
                "system_prompt": planning_prompt,
                "user_prompt": user_request,
                "output": plan_text,
                "model": settings.reasoning_model,
                "latency_ms": latency_ms
            }
        }

        # Step 2: Coding
        coding_agent = "CodingAgent" if "CodingAgent" in template["nodes"] else "RefactorAgent"
        yield {
            "agent": coding_agent,
            "type": "agent_spawn",
            "status": "running",
            "message": f"Spawning {coding_agent}",
            "agent_spawn": {
                "agent_id": f"{coding_agent.lower()}-{uuid.uuid4().hex[:6]}",
                "agent_type": coding_agent,
                "parent_agent": "Orchestrator",
                "spawn_reason": f"Implement {len(checklist)} tasks",
                "timestamp": datetime.now().isoformat()
            }
        }

        all_artifacts = []
        code_text = ""
        existing_code = ""
        coding_prompt = self.prompts.get(coding_agent, self.prompts["CodingAgent"])

        for idx, task_item in enumerate(checklist):
            task_num = idx + 1
            task_description = task_item["task"]

            yield {
                "agent": coding_agent,
                "type": "thinking",
                "status": "running",
                "message": f"Task {task_num}/{len(checklist)}: {task_description}",
                "checklist": checklist
            }

            context_parts = [f"Original request: {user_request}"]
            context_parts.append(f"\nFull plan:\n{plan_text}")
            if existing_code:
                context_parts.append(f"\nCode so far:\n{existing_code}")
            context_parts.append(f"\nCurrent task ({task_num}/{len(checklist)}): {task_description}")

            user_prompt = "\n".join(context_parts)
            messages = [
                SystemMessage(content=coding_prompt),
                HumanMessage(content=user_prompt)
            ]

            start_time = time.time()
            task_code = ""
            async for chunk in self.coding_llm.astream(messages):
                if chunk.content:
                    task_code += chunk.content
            task_latency_ms = int((time.time() - start_time) * 1000)

            code_text += task_code + "\n"
            task_artifacts = parse_code_blocks(task_code)
            all_artifacts.extend(task_artifacts)

            for artifact in task_artifacts:
                existing_code += f"\n\n```{artifact['language']} {artifact['filename']}\n{artifact['content']}\n```"
                yield {
                    "agent": coding_agent,
                    "type": "artifact",
                    "status": "running",
                    "message": f"Created {artifact['filename']}",
                    "artifact": artifact
                }

            checklist[idx]["completed"] = True
            checklist[idx]["artifacts"] = [a["filename"] for a in task_artifacts]

            yield {
                "agent": coding_agent,
                "type": "task_completed",
                "status": "running",
                "message": f"Task {task_num}/{len(checklist)} completed",
                "task_result": {"task_num": task_num, "task": task_description, "artifacts": task_artifacts},
                "checklist": checklist,
                "prompt_info": {
                    "system_prompt": coding_prompt,
                    "user_prompt": user_prompt,
                    "output": task_code,
                    "model": settings.coding_model,
                    "latency_ms": task_latency_ms
                }
            }

        yield {
            "agent": coding_agent,
            "type": "completed",
            "status": "completed",
            "artifacts": all_artifacts,
            "checklist": checklist
        }

        # Step 3: Review Loop (if has_review_loop)
        if template["has_review_loop"]:
            review_iteration = 0
            approved = False
            review_prompt = self.prompts["ReviewAgent"]
            fix_prompt_template = self.prompts["FixCodeAgent"]

            while not approved and review_iteration < max_iterations:
                review_iteration += 1

                # Review
                yield {
                    "agent": "ReviewAgent",
                    "type": "agent_spawn",
                    "status": "running",
                    "message": f"Spawning ReviewAgent (iteration {review_iteration}/{max_iterations})",
                    "agent_spawn": {
                        "agent_id": f"review-{uuid.uuid4().hex[:6]}",
                        "agent_type": "ReviewAgent",
                        "parent_agent": "Orchestrator",
                        "spawn_reason": f"Review iteration {review_iteration}",
                        "timestamp": datetime.now().isoformat()
                    },
                    "iteration_info": {"current": review_iteration, "max": max_iterations}
                }

                yield {
                    "agent": "ReviewAgent",
                    "type": "thinking",
                    "status": "running",
                    "message": f"Reviewing code (iteration {review_iteration}/{max_iterations})..."
                }

                review_user_prompt = f"Review this code:\n\n{code_text}"
                messages = [
                    SystemMessage(content=review_prompt),
                    HumanMessage(content=review_user_prompt)
                ]

                start_time = time.time()
                review_text = ""
                async for chunk in self.coding_llm.astream(messages):
                    if chunk.content:
                        review_text += chunk.content
                review_latency_ms = int((time.time() - start_time) * 1000)

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
                        "system_prompt": review_prompt,
                        "user_prompt": review_user_prompt,
                        "output": review_text,
                        "model": settings.coding_model,
                        "latency_ms": review_latency_ms
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
                        "type": "agent_spawn",
                        "status": "running",
                        "message": f"Spawning FixCodeAgent",
                        "agent_spawn": {
                            "agent_id": f"fix-{uuid.uuid4().hex[:6]}",
                            "agent_type": "FixCodeAgent",
                            "parent_agent": "Orchestrator",
                            "spawn_reason": f"Fix {len(review_result['issues'])} issues",
                            "timestamp": datetime.now().isoformat()
                        }
                    }

                    yield {
                        "agent": "FixCodeAgent",
                        "type": "thinking",
                        "status": "running",
                        "message": f"Fixing {len(review_result['issues'])} issues..."
                    }

                    # Format issues for FixCodeAgent (handle both old and new format)
                    def format_issue(issue):
                        if isinstance(issue, dict):
                            parts = []
                            if issue.get("file"):
                                parts.append(f"File: {issue['file']}")
                            if issue.get("line"):
                                parts.append(f"Line: {issue['line']}")
                            if issue.get("severity"):
                                parts.append(f"Severity: {issue['severity']}")
                            if issue.get("issue"):
                                parts.append(f"Issue: {issue['issue']}")
                            if issue.get("fix"):
                                parts.append(f"Suggested Fix: {issue['fix']}")
                            return "\n  ".join(parts)
                        return str(issue)

                    def format_suggestion(suggestion):
                        if isinstance(suggestion, dict):
                            parts = []
                            if suggestion.get("file"):
                                parts.append(f"File: {suggestion['file']}")
                            if suggestion.get("line"):
                                parts.append(f"Line: {suggestion['line']}")
                            if suggestion.get("suggestion"):
                                parts.append(f"Suggestion: {suggestion['suggestion']}")
                            return "\n  ".join(parts)
                        return str(suggestion)

                    issues_text = "\n".join(f"- {format_issue(i)}" for i in review_result["issues"]) or "None"
                    suggestions_text = "\n".join(f"- {format_suggestion(s)}" for s in review_result["suggestions"]) or "None"

                    fix_prompt = fix_prompt_template.format(
                        issues=issues_text,
                        suggestions=suggestions_text
                    )

                    fix_user_prompt = f"Code to fix:\n\n{code_text}"
                    messages = [
                        SystemMessage(content=fix_prompt),
                        HumanMessage(content=fix_user_prompt)
                    ]

                    start_time = time.time()
                    fixed_code = ""
                    async for chunk in self.coding_llm.astream(messages):
                        if chunk.content:
                            fixed_code += chunk.content
                    fix_latency_ms = int((time.time() - start_time) * 1000)

                    code_text = fixed_code
                    fixed_artifacts = parse_code_blocks(fixed_code)
                    all_artifacts = fixed_artifacts

                    for artifact in fixed_artifacts:
                        yield {
                            "agent": "FixCodeAgent",
                            "type": "artifact",
                            "status": "running",
                            "message": f"Fixed: {artifact['filename']}",
                            "artifact": artifact
                        }

                    yield {
                        "agent": "FixCodeAgent",
                        "type": "completed",
                        "status": "completed",
                        "artifacts": fixed_artifacts,
                        "prompt_info": {
                            "system_prompt": fix_prompt,
                            "user_prompt": fix_user_prompt,
                            "output": fixed_code,
                            "model": settings.coding_model,
                            "latency_ms": fix_latency_ms
                        }
                    }

            # Final result summary
            final_status = "approved" if approved else "max_iterations_reached"
            final_message = (
                f"Code review passed. Generated {len(all_artifacts)} file(s)."
                if approved else
                f"Review loop ended after {review_iteration} iterations. Generated {len(all_artifacts)} file(s)."
            )

            # Orchestrator completion
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
            # No review loop - just finish
            final_message = f"Completed. Generated {len(all_artifacts)} file(s)."

            yield {
                "agent": "Orchestrator",
                "type": "completed",
                "status": "completed",
                "message": final_message,
                "final_result": {
                    "success": True,
                    "message": final_message,
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

    async def _execute_test_workflow(
        self,
        user_request: str,
        template: Dict[str, Any],
        workflow_id: str,
        max_iterations: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute test generation workflow."""
        # Simplified - use coding workflow structure
        async for update in self._execute_coding_workflow(
            user_request, "test_generation", template, workflow_id, max_iterations
        ):
            yield update

    async def _execute_review_only_workflow(
        self,
        user_request: str,
        template: Dict[str, Any],
        workflow_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute review-only workflow (no code generation)."""
        # Review agent
        yield {
            "agent": "ReviewAgent",
            "type": "agent_spawn",
            "status": "running",
            "message": "Spawning ReviewAgent",
            "agent_spawn": {
                "agent_id": f"review-{uuid.uuid4().hex[:6]}",
                "agent_type": "ReviewAgent",
                "parent_agent": "Orchestrator",
                "spawn_reason": "Review provided code",
                "timestamp": datetime.now().isoformat()
            }
        }

        yield {
            "agent": "ReviewAgent",
            "type": "thinking",
            "status": "running",
            "message": "Reviewing code..."
        }

        messages = [
            SystemMessage(content=self.prompts["ReviewAgent"]),
            HumanMessage(content=user_request)
        ]

        start_time = time.time()
        review_text = ""
        async for chunk in self.coding_llm.astream(messages):
            if chunk.content:
                review_text += chunk.content
        latency_ms = int((time.time() - start_time) * 1000)

        review_result = parse_review(review_text)

        yield {
            "agent": "ReviewAgent",
            "type": "completed",
            "status": "completed",
            "issues": review_result["issues"],
            "suggestions": review_result["suggestions"],
            "approved": review_result["approved"],
            "prompt_info": {
                "system_prompt": self.prompts["ReviewAgent"],
                "user_prompt": user_request,
                "output": review_text,
                "model": settings.coding_model,
                "latency_ms": latency_ms
            }
        }

        yield {
            "agent": "Workflow",
            "type": "completed",
            "status": "finished",
            "summary": {
                "tasks_completed": 1,
                "total_tasks": 1,
                "artifacts_count": 0,
                "review_approved": review_result["approved"]
            },
            "workflow_info": {
                "workflow_id": workflow_id,
                "workflow_type": template["name"],
                "task_type": "code_review",
                "current_node": "END",
                "dynamically_created": True
            }
        }

    async def _execute_doc_workflow(
        self,
        user_request: str,
        template: Dict[str, Any],
        workflow_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute documentation workflow."""
        # Analysis
        yield {
            "agent": "AnalysisAgent",
            "type": "agent_spawn",
            "status": "running",
            "message": "Spawning AnalysisAgent",
            "agent_spawn": {
                "agent_id": f"analysis-{uuid.uuid4().hex[:6]}",
                "agent_type": "AnalysisAgent",
                "parent_agent": "Orchestrator",
                "spawn_reason": "Analyze code for documentation",
                "timestamp": datetime.now().isoformat()
            }
        }

        messages = [
            SystemMessage(content=self.prompts["AnalysisAgent"]),
            HumanMessage(content=user_request)
        ]

        analysis_text = ""
        async for chunk in self.reasoning_llm.astream(messages):
            if chunk.content:
                analysis_text += chunk.content

        yield {
            "agent": "AnalysisAgent",
            "type": "completed",
            "status": "completed",
            "content": analysis_text
        }

        # DocGen
        yield {
            "agent": "DocGenAgent",
            "type": "agent_spawn",
            "status": "running",
            "message": "Spawning DocGenAgent",
            "agent_spawn": {
                "agent_id": f"docgen-{uuid.uuid4().hex[:6]}",
                "agent_type": "DocGenAgent",
                "parent_agent": "Orchestrator",
                "spawn_reason": "Generate documentation",
                "timestamp": datetime.now().isoformat()
            }
        }

        messages = [
            SystemMessage(content=self.prompts["DocGenAgent"]),
            HumanMessage(content=f"{user_request}\n\nAnalysis:\n{analysis_text}")
        ]

        doc_text = ""
        async for chunk in self.coding_llm.astream(messages):
            if chunk.content:
                doc_text += chunk.content

        artifacts = parse_code_blocks(doc_text)

        for artifact in artifacts:
            yield {
                "agent": "DocGenAgent",
                "type": "artifact",
                "status": "running",
                "artifact": artifact
            }

        yield {
            "agent": "DocGenAgent",
            "type": "completed",
            "status": "completed",
            "artifacts": artifacts
        }

        yield {
            "agent": "Workflow",
            "type": "completed",
            "status": "finished",
            "summary": {
                "tasks_completed": 1,
                "total_tasks": 1,
                "artifacts_count": len(artifacts),
                "review_approved": True
            },
            "workflow_info": {
                "workflow_id": workflow_id,
                "workflow_type": template["name"],
                "task_type": "documentation",
                "current_node": "END",
                "dynamically_created": True
            }
        }


class LangGraphWorkflowManager(BaseWorkflowManager):
    """Manager for dynamic LangGraph workflow sessions."""

    def __init__(self):
        """Initialize workflow manager."""
        self.workflows: Dict[str, DynamicLangGraphWorkflow] = {}
        logger.info("LangGraphWorkflowManager initialized with dynamic workflow support")

    def get_or_create_workflow(self, session_id: str) -> DynamicLangGraphWorkflow:
        """Get existing workflow or create new one for session."""
        if session_id not in self.workflows:
            self.workflows[session_id] = DynamicLangGraphWorkflow()
            logger.info(f"Created new dynamic workflow for session {session_id}")
        return self.workflows[session_id]

    def delete_workflow(self, session_id: str) -> None:
        """Delete workflow for session."""
        if session_id in self.workflows:
            del self.workflows[session_id]
            logger.info(f"Deleted workflow for session {session_id}")

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.workflows.keys())


# Global workflow manager instance
workflow_manager = LangGraphWorkflowManager()

# Backward compatibility alias
LangGraphWorkflow = DynamicLangGraphWorkflow
