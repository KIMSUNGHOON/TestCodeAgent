"""Supervisor Agent - The Strategist

This is the orchestrator that analyzes user requests and dynamically
constructs workflows based on task complexity and requirements.

Supports two modes:
1. Traditional: Analyze request → Build fixed workflow (backward compatible)
2. Tool Use: LLM freely decides which agents to call iteratively (new, flexible)

Uses DeepSeek-R1 or GPT-OSS for reasoning and planning via vLLM API.
"""

import asyncio
import logging
import re
import json
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field

# Import vLLM client for DeepSeek-R1
import sys
from pathlib import Path

# Add project root to path for shared module access
PROJECT_ROOT = Path(__file__).parent.parent.parent  # backend/core -> backend -> project_root
sys.path.insert(0, str(PROJECT_ROOT))

# Add backend to path for app module access
BACKEND_ROOT = Path(__file__).parent.parent  # backend/core -> backend
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.vllm_client import vllm_router
from app.core.config import settings

# Import model-specific prompts
from shared.prompts.deepseek_r1 import (
    DEEPSEEK_R1_SYSTEM_PROMPT,
    DEEPSEEK_R1_CONFIG,
)
from shared.prompts.gpt_oss import (
    GPT_OSS_SYSTEM_PROMPT,
    GPT_OSS_SUPERVISOR_PROMPT,
    GPT_OSS_PLANNING_PROMPT,
    GPT_OSS_QA_PROMPT,
    GPT_OSS_CONFIG,
)

# Import agent tools for Tool Use pattern
from core.agent_tools import get_agent_tools

logger = logging.getLogger(__name__)


class TaskComplexity:
    """Task complexity levels"""
    SIMPLE = "simple"  # Single agent, no loops
    MODERATE = "moderate"  # Multiple agents, basic loop
    COMPLEX = "complex"  # All gates, refinement loops
    CRITICAL = "critical"  # All gates, security, human approval


class ResponseType:
    """Response type - determines workflow routing"""
    QUICK_QA = "quick_qa"  # Simple Q&A - supervisor responds directly
    PLANNING = "planning"  # Planning/design - supervisor with detailed analysis
    CODE_GENERATION = "code_generation"  # Full pipeline - all agents
    CODE_REVIEW = "code_review"  # Review existing code
    DEBUGGING = "debugging"  # Debug/fix issues


class AgentCapability:
    """Agent capabilities"""
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    SECURITY = "security"
    TESTING = "testing"
    REFINEMENT = "refinement"
    RCA = "root_cause_analysis"


@dataclass
class ThinkingBlock:
    """Parsed thinking block from DeepSeek-R1"""
    content: str
    step_number: int = 0
    is_complete: bool = False


@dataclass
class SupervisorAnalysis:
    """Result of supervisor analysis"""
    user_request: str
    timestamp: str
    complexity: str
    task_type: str
    required_agents: List[str]
    workflow_strategy: str
    max_iterations: int
    requires_human_approval: bool
    reasoning: str
    thinking_blocks: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    api_used: bool = False  # True if DeepSeek-R1 API was used


# Supervisor Analysis Prompt for DeepSeek-R1
SUPERVISOR_ANALYSIS_PROMPT = """Analyze the following user request and determine the optimal workflow strategy.

USER REQUEST:
{user_request}

CONTEXT (if available):
{context}

ANALYSIS REQUIREMENTS:
1. Assess task complexity (simple, moderate, complex, critical)
2. Determine primary task type (implementation, review, testing, security_audit, general)
3. Identify required agent capabilities
4. Select optimal workflow strategy
5. Estimate maximum iterations needed
6. Determine if human approval is required

AVAILABLE STRATEGIES:
- linear: Simple sequential execution (for simple tasks)
- parallel_gates: Parallel quality gates (for moderate tasks)
- adaptive_loop: Dynamic refinement with RCA (for complex tasks)
- staged_approval: Includes human approval gates (for critical tasks)

AVAILABLE AGENT CAPABILITIES:
- planning: High-level task planning
- implementation: Code generation
- review: Code review
- security: Security analysis
- testing: Test generation and execution
- refinement: Code improvement
- root_cause_analysis: Deep problem analysis

Provide your analysis in the following JSON format AFTER your thinking:

```json
{{
    "complexity": "simple|moderate|complex|critical",
    "task_type": "implementation|review|testing|security_audit|general",
    "required_agents": ["agent1", "agent2"],
    "workflow_strategy": "linear|parallel_gates|adaptive_loop|staged_approval",
    "max_iterations": 5,
    "requires_human_approval": false,
    "confidence_score": 0.85
}}
```
"""


class SupervisorAgent:
    """The Strategist - Analyzes requests and orchestrates workflows

    This agent uses LLM reasoning to:
    1. Understand user intent
    2. Assess task complexity
    3. Determine required agents
    4. Build dynamic workflow DAG
    5. Monitor execution and adjust as needed

    Supports multiple LLM backends:
    - DeepSeek-R1: Uses <think></think> tags for reasoning
    - GPT-OSS: Uses Harmony format without <think> tags
    - Qwen: Standard prompting
    """

    def __init__(self, use_api: bool = True):
        """Initialize Supervisor Agent

        Args:
            use_api: Whether to use LLM API (True) or rule-based fallback (False)
        """
        # Detect model type from settings
        self.model_type = settings.get_reasoning_model_type
        logger.info(f"🔍 Detected reasoning model type: {self.model_type}")

        # Select appropriate prompts based on model type
        if self.model_type == "gpt-oss":
            self.system_prompt = GPT_OSS_SYSTEM_PROMPT
            self.analysis_prompt = GPT_OSS_SUPERVISOR_PROMPT
            self.planning_prompt = GPT_OSS_PLANNING_PROMPT
            self.qa_prompt = GPT_OSS_QA_PROMPT
            self.config = GPT_OSS_CONFIG
            self.uses_think_tags = False
        elif self.model_type == "deepseek":
            self.system_prompt = DEEPSEEK_R1_SYSTEM_PROMPT
            self.analysis_prompt = SUPERVISOR_ANALYSIS_PROMPT
            self.planning_prompt = None  # Use default
            self.qa_prompt = None
            self.config = DEEPSEEK_R1_CONFIG
            self.uses_think_tags = True
        else:
            # Generic/Qwen - use GPT-OSS style (no think tags)
            self.system_prompt = GPT_OSS_SYSTEM_PROMPT
            self.analysis_prompt = GPT_OSS_SUPERVISOR_PROMPT
            self.planning_prompt = GPT_OSS_PLANNING_PROMPT
            self.qa_prompt = GPT_OSS_QA_PROMPT
            self.config = GPT_OSS_CONFIG
            self.uses_think_tags = False

        self.use_api = use_api
        self._thinking_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
        self._json_pattern = re.compile(r'```json\s*(.*?)\s*```', re.DOTALL)
        logger.info(f"✅ Supervisor Agent initialized (API mode: {use_api}, model: {self.model_type})")

    def _strip_think_tags(self, text: str) -> str:
        """Remove <think></think> tags from text

        For models that don't use think tags (GPT-OSS, Qwen),
        we strip any accidental <think> content from output.

        Args:
            text: Text that may contain think tags

        Returns:
            Clean text without think tags
        """
        if not text:
            return ""

        # Remove <think>...</think> blocks entirely
        clean = self._thinking_pattern.sub('', text)
        # Clean up any extra whitespace
        clean = re.sub(r'\n\s*\n\s*\n', '\n\n', clean)
        return clean.strip()

    def _format_context_harmony(self, context: Dict) -> str:
        """Format context in Harmony-style structured format (Phase 6 Enhanced)

        OpenAI Harmony format emphasizes structured, hierarchical context presentation
        for better LLM comprehension, especially for GPT-OSS models.

        Phase 6 Enhancements:
        - Expanded message content limit: 1000 → 4000 chars
        - Context compression support for long histories
        - Token budget awareness

        Args:
            context: Context dictionary with conversation_history, system_prompt, etc.

        Returns:
            Formatted context string in Harmony format
        """
        if not context:
            return "No previous context available."

        formatted_parts = []

        # Phase 6: Check if context is already compressed
        is_compressed = context.get("compressed", False)
        original_count = context.get("original_message_count", 0)

        # Add system context if available
        if context.get("system_prompt"):
            formatted_parts.append(f"### System Context\n{context['system_prompt']}\n")

        # Format conversation history (Phase 6: Expanded from 6 to 20 messages, 1000 → 4000 chars)
        if context.get("conversation_history"):
            history = context["conversation_history"]

            # Phase 6: Add compression indicator if applicable
            if is_compressed:
                formatted_parts.append(f"### Conversation History (Compressed: {original_count} → {len(history)} messages)\n")
            else:
                formatted_parts.append(f"### Conversation History ({len(history)} messages)\n")

            # Take recent messages
            for i, msg in enumerate(history, 1):
                role = "USER" if msg.get("role") == "user" else "ASSISTANT"
                content = msg.get("content", "")

                # Check for compressed history marker
                if msg.get("is_compressed"):
                    formatted_parts.append(f"**[Compressed History]**:\n{content}\n")
                    continue

                # Phase 6: Expanded content limit (1000 → 4000 chars)
                if len(content) > 4000:
                    content = content[:4000] + "...[truncated]"

                formatted_parts.append(f"**[{i}] {role}**: {content}\n")

        # Add turn count
        if context.get("turn_count"):
            formatted_parts.append(f"\n**Total Turns**: {context['turn_count']}\n")

        # Phase 6: Add artifact summary if available
        if context.get("artifacts"):
            artifacts = context["artifacts"]
            formatted_parts.append(f"\n### Referenced Artifacts ({len(artifacts)} files)\n")
            for art in artifacts[:10]:  # Limit to 10 artifacts in summary
                filename = art.get("filename", "unknown")
                language = art.get("language", "text")
                formatted_parts.append(f"- {filename} ({language})\n")

        return "\n".join(formatted_parts) if formatted_parts else "No previous context available."

    async def analyze_request_async(
        self,
        user_request: str,
        context: Optional[Dict] = None
    ) -> AsyncGenerator[Dict, None]:
        """Analyze user request asynchronously with streaming

        Uses DeepSeek-R1 reasoning with streaming <think> blocks.

        Args:
            user_request: User's input
            context: Optional context from previous interactions

        Yields:
            Analysis updates including thinking blocks
        """
        logger.info("🎯 Supervisor: Analyzing user request (async)...")
        logger.info(f"   Request: {user_request[:100]}...")

        thinking_buffer = []

        if self.use_api:
            try:
                # Get reasoning client
                client = vllm_router.get_client("reasoning")

                # Build prompt using model-appropriate template with Harmony format
                # Format conversation history in structured way
                context_formatted = self._format_context_harmony(context) if context else "No previous context available."

                prompt = self.analysis_prompt.format(
                    user_request=user_request,
                    context=context_formatted
                )

                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ]

                # Stream response
                full_response = ""
                current_thinking = ""
                in_thinking_block = False

                async for chunk in client.stream_chat_completion(
                    messages=messages,
                    temperature=self.config.get("temperature", 0.7),
                    max_tokens=self.config.get("max_tokens", 8000)
                ):
                    full_response += chunk

                    # Only process <think> tags if model uses them (DeepSeek)
                    if self.uses_think_tags:
                        # Detect thinking blocks
                        if "<think>" in chunk:
                            in_thinking_block = True
                            current_thinking = ""

                        if in_thinking_block:
                            current_thinking += chunk

                            # Yield partial thinking for streaming UI
                            yield {
                                "type": "thinking",
                                "content": current_thinking,
                                "is_complete": False
                            }

                        if "</think>" in chunk:
                            in_thinking_block = False
                            thinking_buffer.append(current_thinking)

                            # Yield complete thinking block
                            yield {
                                "type": "thinking",
                                "content": current_thinking,
                                "is_complete": True
                            }

                # Parse final analysis
                analysis = self._parse_llm_response(full_response, user_request, thinking_buffer)
                analysis["api_used"] = True

                yield {
                    "type": "analysis",
                    "content": analysis
                }

                logger.info(f"✅ API Analysis Complete (model: {self.model_type})")

            except Exception as e:
                logger.warning(f"⚠️ LLM API call failed: {e}, falling back to rule-based")
                # Fallback to rule-based
                analysis = self._rule_based_analysis(user_request)
                yield {
                    "type": "analysis",
                    "content": analysis
                }
        else:
            # Use rule-based analysis
            analysis = self._rule_based_analysis(user_request)
            yield {
                "type": "analysis",
                "content": analysis
            }

    def analyze_request(
        self,
        user_request: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """Analyze user request synchronously (for backward compatibility)

        Uses rule-based analysis by default for sync calls.

        Args:
            user_request: User's input
            context: Optional context from previous interactions

        Returns:
            Analysis results with workflow plan
        """
        logger.info("🎯 Supervisor: Analyzing user request (sync)...")
        logger.info(f"   Request: {user_request[:100]}...")

        analysis = self._rule_based_analysis(user_request)

        logger.info(f"✅ Analysis Complete:")
        logger.info(f"   Complexity: {analysis['complexity']}")
        logger.info(f"   Task Type: {analysis['task_type']}")
        logger.info(f"   Required Agents: {len(analysis['required_agents'])}")
        logger.info(f"   Strategy: {analysis['workflow_strategy']}")

        return analysis

    def _parse_llm_response(
        self,
        response: str,
        user_request: str,
        thinking_blocks: List[str]
    ) -> Dict:
        """Parse LLM response to extract analysis

        Args:
            response: Full LLM response
            user_request: Original user request
            thinking_blocks: Collected thinking blocks

        Returns:
            Parsed analysis dict
        """
        import json

        # Strip <think> tags from response if model doesn't use them
        clean_response = response
        if not self.uses_think_tags:
            clean_response = self._strip_think_tags(response)

        # Extract JSON from response
        json_match = self._json_pattern.search(clean_response)

        if json_match:
            try:
                parsed = json.loads(json_match.group(1))

                # Clean reasoning - strip think tags if present
                reasoning = "\n".join(thinking_blocks) if thinking_blocks else ""
                if not self.uses_think_tags:
                    reasoning = self._strip_think_tags(reasoning)
                    # For GPT-OSS, use analysis_summary as reasoning if available
                    if parsed.get("analysis_summary"):
                        reasoning = parsed["analysis_summary"]

                return {
                    "user_request": user_request,
                    "timestamp": datetime.utcnow().isoformat(),
                    "response_type": parsed.get("response_type", self._determine_response_type(user_request)),
                    "complexity": parsed.get("complexity", TaskComplexity.MODERATE),
                    "task_type": parsed.get("task_type", "general"),
                    "required_agents": parsed.get("required_agents", [AgentCapability.IMPLEMENTATION]),
                    "workflow_strategy": parsed.get("workflow_strategy", "parallel_gates"),
                    "max_iterations": parsed.get("max_iterations", 5),
                    "requires_human_approval": parsed.get("requires_human_approval", False),
                    "reasoning": reasoning,
                    "thinking_blocks": thinking_blocks if self.uses_think_tags else [],
                    "confidence_score": parsed.get("confidence_score", 0.8),
                    "api_used": True
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from LLM response")

        # Fallback to rule-based if parsing fails
        return self._rule_based_analysis(user_request, thinking_blocks)

    def _rule_based_analysis(
        self,
        request: str,
        thinking_blocks: Optional[List[str]] = None
    ) -> Dict:
        """Rule-based analysis fallback

        Args:
            request: User request
            thinking_blocks: Optional thinking blocks from failed API call

        Returns:
            Analysis dict
        """
        response_type = self._determine_response_type(request)
        return {
            "user_request": request,
            "timestamp": datetime.utcnow().isoformat(),
            "response_type": response_type,  # NEW: determines workflow routing
            "complexity": self._assess_complexity(request),
            "task_type": self._determine_task_type(request),
            "required_agents": self._determine_required_agents(request),
            "workflow_strategy": self._build_workflow_strategy(request),
            "max_iterations": self._determine_max_iterations(request),
            "requires_human_approval": self._requires_human_approval(request),
            "reasoning": self._generate_reasoning(request),
            "thinking_blocks": thinking_blocks or [],
            "confidence_score": 0.7,  # Lower confidence for rule-based
            "api_used": False
        }

    def _determine_response_type(self, request: str) -> str:
        """Determine how to respond to this request

        This is the KEY routing decision - determines if we need:
        - quick_qa: Simple answer, no code generation
        - planning: Detailed plan/design, no code yet
        - code_generation: Full pipeline with all agents
        - code_review: Review existing code
        - debugging: Fix/debug issues

        Args:
            request: User request

        Returns:
            Response type string
        """
        request_lower = request.lower()

        # Check each response type in priority order
        if self._is_quick_qa_request(request_lower):
            return ResponseType.QUICK_QA

        if self._is_planning_request(request_lower):
            return ResponseType.PLANNING

        if self._is_code_review_request(request_lower):
            return ResponseType.CODE_REVIEW

        if self._is_debugging_request(request_lower):
            return ResponseType.DEBUGGING

        if self._is_code_generation_request(request_lower):
            return ResponseType.CODE_GENERATION

        # Default: If unclear, use planning to clarify
        return ResponseType.PLANNING

    def _is_quick_qa_request(self, request_lower: str) -> bool:
        """Check if request is a simple Q&A question

        Simple questions that don't need code generation.

        Args:
            request_lower: Lowercase user request

        Returns:
            True if this is a Q&A request
        """
        qa_patterns = [
            # Korean
            "뭐야", "뭔가요", "무엇", "알려줘", "설명해", "어떻게 동작",
            "왜", "차이점", "비교", "장단점", "추천", "조언",
            # English
            "what is", "what are", "how does", "why", "explain",
            "difference between", "compare", "pros and cons",
            "recommend", "advice", "tell me about",
        ]
        return any(p in request_lower for p in qa_patterns) and not self._has_code_intent(request_lower)

    def _is_planning_request(self, request_lower: str) -> bool:
        """Check if request is for planning/design

        Detailed analysis or design without code generation.

        Args:
            request_lower: Lowercase user request

        Returns:
            True if this is a planning request
        """
        planning_patterns = [
            # Korean
            "계획", "설계", "아키텍처", "구조", "방법론", "전략",
            "어떻게 만들", "어떻게 구현", "방향",
            # English
            "plan", "design", "architecture", "structure", "strategy",
            "how should i", "how would you", "approach", "methodology",
        ]
        return any(p in request_lower for p in planning_patterns)

    def _is_code_review_request(self, request_lower: str) -> bool:
        """Check if request is for code review

        Review, analyze, or improve existing code.

        Args:
            request_lower: Lowercase user request

        Returns:
            True if this is a code review request
        """
        review_patterns = [
            # Korean
            "리뷰", "검토", "분석해", "확인해", "문제 있", "개선",
            # English
            "review", "check", "analyze", "look at", "improve", "refactor",
        ]
        has_review_pattern = any(p in request_lower for p in review_patterns)
        has_code_keyword = "코드" in request_lower or "code" in request_lower
        return has_review_pattern and has_code_keyword

    def _is_debugging_request(self, request_lower: str) -> bool:
        """Check if request is for debugging

        Fix errors, bugs, or issues.

        Args:
            request_lower: Lowercase user request

        Returns:
            True if this is a debugging request
        """
        debug_patterns = [
            # Korean
            "오류", "에러", "버그", "수정", "안돼", "안됨", "왜 안",
            "문제", "고쳐", "디버그",
            # English
            "error", "bug", "fix", "doesn't work", "not working", "debug",
            "issue", "problem", "broken",
        ]
        return any(p in request_lower for p in debug_patterns)

    def _is_code_generation_request(self, request_lower: str) -> bool:
        """Check if request is for code generation

        Explicit code creation requests.

        Args:
            request_lower: Lowercase user request

        Returns:
            True if this is a code generation request
        """
        code_patterns = [
            # Korean - verb stems to match various conjugations
            "만들", "만드",  # covers 만들어, 만들고, 만드는, etc.
            "구현",  # covers 구현해, 구현하고, 구현할
            "작성",  # covers 작성해, 작성하고, 작성할
            "개발",  # covers 개발해, 개발하고, 개발할
            "생성",  # covers 생성해, 생성하고, 생성할
            "추가",  # covers 추가해, 추가하고, 추가할
            "코드",
            # Intent patterns
            "싶습니다", "싶어요", "싶어", "원합니다", "원해요", "원해",
            "해줘", "해주세요", "해 줘", "해 주세요",
            # English
            "create", "implement", "write", "develop", "code",
            "generate", "build", "make",
        ]
        return any(p in request_lower for p in code_patterns)

    def _has_code_intent(self, request_lower: str) -> bool:
        """Check if request has intent to generate code

        Uses verb stems to match various Korean conjugations.
        """
        code_intent_words = [
            # Korean - verb stems
            "만들", "만드", "구현", "작성", "개발", "코드",
            "생성", "추가",
            # Intent patterns
            "싶습니다", "싶어요", "싶어", "원합니다", "원해요", "원해",
            "해줘", "해주세요",
            # English
            "create", "implement", "write", "develop", "generate code",
            "build", "make a", "code for",
        ]
        return any(w in request_lower for w in code_intent_words)

    def _assess_complexity(self, request: str) -> str:
        """Assess task complexity

        SIMPLE: Single file, clear requirements
        MODERATE: Multiple files, some ambiguity
        COMPLEX: Architecture changes, multiple components
        CRITICAL: Security-sensitive, production code
        """
        request_lower = request.lower()

        # Critical indicators
        if any(word in request_lower for word in [
            "production", "deploy", "critical", "security", "auth", "payment"
        ]):
            return TaskComplexity.CRITICAL

        # Complex indicators
        if any(word in request_lower for word in [
            "refactor", "architecture", "system", "integrate", "migrate"
        ]):
            return TaskComplexity.COMPLEX

        # Moderate indicators
        if any(word in request_lower for word in [
            "multiple", "several", "add and", "implement feature"
        ]):
            return TaskComplexity.MODERATE

        # Simple by default
        return TaskComplexity.SIMPLE

    def _determine_task_type(self, request: str) -> str:
        """Determine primary task type"""
        request_lower = request.lower()

        # Check in priority order
        if any(word in request_lower for word in ["test", "testing", "unit test"]):
            return "testing"
        elif any(word in request_lower for word in ["security", "vulnerability", "owasp"]):
            return "security_audit"
        elif any(word in request_lower for word in ["review", "check", "analyze"]):
            return "review"
        elif any(word in request_lower for word in ["implement", "create", "add", "build"]):
            return "implementation"
        else:
            return "general"

    def _determine_required_agents(self, request: str) -> List[str]:
        """Determine which agents are needed

        Returns list of agent capabilities required
        """
        request_lower = request.lower()
        required = []

        # Always need planning for complex tasks
        complexity = self._assess_complexity(request)
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]:
            required.append(AgentCapability.PLANNING)

        # Implementation agent
        if any(word in request_lower for word in [
            "implement", "create", "add", "build", "write"
        ]):
            required.append(AgentCapability.IMPLEMENTATION)

        # Review agent (almost always needed)
        if complexity != TaskComplexity.SIMPLE:
            required.append(AgentCapability.REVIEW)

        # Security agent for critical tasks
        if complexity == TaskComplexity.CRITICAL or "security" in request_lower:
            required.append(AgentCapability.SECURITY)

        # Testing agent
        if "test" in request_lower or complexity == TaskComplexity.CRITICAL:
            required.append(AgentCapability.TESTING)

        # Refinement for moderate+ complexity
        if complexity in [TaskComplexity.MODERATE, TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]:
            required.append(AgentCapability.REFINEMENT)

        # RCA for complex+ tasks
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]:
            required.append(AgentCapability.RCA)

        return required or [AgentCapability.IMPLEMENTATION]  # At least one agent

    def _build_workflow_strategy(self, request: str) -> str:
        """Build workflow execution strategy

        Returns strategy name:
        - linear: Simple sequential execution
        - parallel_gates: Parallel quality gates
        - adaptive_loop: Dynamic refinement with RCA
        - staged_approval: Includes human approval gates
        """
        complexity = self._assess_complexity(request)

        if complexity == TaskComplexity.CRITICAL:
            return "staged_approval"
        elif complexity == TaskComplexity.COMPLEX:
            return "adaptive_loop"
        elif complexity == TaskComplexity.MODERATE:
            return "parallel_gates"
        else:
            return "linear"

    def _determine_max_iterations(self, request: str) -> int:
        """Determine maximum refinement iterations"""
        complexity = self._assess_complexity(request)

        iterations_map = {
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MODERATE: 5,
            TaskComplexity.COMPLEX: 7,
            TaskComplexity.CRITICAL: 10,
        }

        return iterations_map.get(complexity, 5)

    def _requires_human_approval(self, request: str) -> bool:
        """Check if human approval is required"""
        complexity = self._assess_complexity(request)
        request_lower = request.lower()

        # Always require approval for critical tasks
        if complexity == TaskComplexity.CRITICAL:
            return True

        # Require approval for sensitive operations
        if any(word in request_lower for word in [
            "delete", "drop", "truncate", "production", "deploy"
        ]):
            return True

        return False

    def _generate_reasoning(self, request: str) -> str:
        """Generate reasoning explanation

        Model-aware: Uses <think> tags only for DeepSeek-R1
        """
        complexity = self._assess_complexity(request)
        task_type = self._determine_task_type(request)
        agents = self._determine_required_agents(request)

        # Build reasoning content
        analysis_content = f"""1. Request Analysis:
   - Input: "{request[:100]}..."
   - Detected complexity: {complexity}
   - Primary task type: {task_type}

2. Required Capabilities:
   {chr(10).join(f"   - {agent}" for agent in agents)}

3. Workflow Strategy:
   - Complexity level requires {self._build_workflow_strategy(request)} strategy
   - Max iterations: {self._determine_max_iterations(request)}
   - Human approval: {self._requires_human_approval(request)}

4. Execution Plan:
   - Start with planning/analysis
   - Route to appropriate implementation agents
   - Apply quality gates based on complexity
   - Enable refinement loops if needed"""

        # Format based on model type
        if self.uses_think_tags:
            # DeepSeek-R1: Use <think> tags
            reasoning = f"""<think>
{analysis_content}
</think>

Strategy: {self._build_workflow_strategy(request)} approach with {len(agents)} agents."""
        else:
            # GPT-OSS/Qwen: Structured format without <think> tags
            reasoning = f"""## Analysis

{analysis_content}

**Strategy:** {self._build_workflow_strategy(request)} approach with {len(agents)} agents."""

        return reasoning

    async def adjust_workflow(
        self,
        current_state: Dict,
        failure_reason: str
    ) -> Dict:
        """Dynamically adjust workflow based on execution feedback

        Uses DeepSeek-R1 RCA to analyze failures and adjust strategy.

        Args:
            current_state: Current workflow state
            failure_reason: Reason for the adjustment

        Returns:
            Adjusted workflow parameters
        """
        logger.info(f"🔄 Supervisor: Adjusting workflow due to: {failure_reason}")

        # Use RCA to determine adjustment
        rca_result = await self._perform_rca(current_state, failure_reason)

        return {
            "adjusted": True,
            "reason": failure_reason,
            "rca_analysis": rca_result,
            "new_max_iterations": current_state.get("max_iterations", 5) + 2,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _perform_rca(
        self,
        state: Dict,
        failure_reason: str
    ) -> str:
        """Perform Root Cause Analysis using DeepSeek-R1

        Args:
            state: Current workflow state
            failure_reason: Failure description

        Returns:
            RCA analysis text
        """
        if not self.use_api:
            return f"Rule-based RCA: {failure_reason}"

        try:
            client = vllm_router.get_client("reasoning")

            from shared.prompts.deepseek_r1 import DEEPSEEK_R1_RCA_PROMPT

            prompt = DEEPSEEK_R1_RCA_PROMPT.format(
                error_description=failure_reason,
                current_state=str(state.get("workflow_status", "unknown")),
                expected_behavior="Successful completion",
                logs=str(state.get("error_log", []))[-1000:]
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await client.chat_completion(
                messages=messages,
                temperature=0.5,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.warning(f"RCA API call failed: {e}")
            return f"RCA unavailable: {failure_reason}"

    # ============================================
    # NEW: Tool Use Pattern (Phase 2)
    # ============================================

    async def execute_with_tools(
        self,
        user_request: str,
        context: Optional[Dict] = None,
        max_iterations: int = 10
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute workflow using Tool Use pattern (Claude Code style)

        Instead of fixed workflow types, LLM freely decides which agents to call.
        This provides maximum flexibility for handling any type of request.

        Args:
            user_request: User's request
            context: Optional context (conversation history, etc.)
            max_iterations: Maximum tool call iterations (prevent infinite loops)

        Yields:
            Stream updates for each tool call and response
        """
        logger.info(f"🔧 Supervisor: Starting Tool Use execution")
        logger.info(f"   Request: {user_request[:100]}...")

        # Build messages
        messages = []

        # System prompt with tool instructions
        tool_system_prompt = self._build_tool_use_system_prompt()
        messages.append({"role": "system", "content": tool_system_prompt})

        # Add context if available
        if context and context.get("conversation_history"):
            formatted_context = self._format_context_harmony(context)
            messages.append({
                "role": "user",
                "content": f"## Previous Context\n{formatted_context}"
            })

        # Add user request
        messages.append({"role": "user", "content": user_request})

        # Get agent tools
        tools = get_agent_tools()

        # Iterative Tool Use Loop (like Claude Code)
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 Iteration {iteration}/{max_iterations}")

            # Yield iteration start
            yield {
                "type": "tool_iteration",
                "iteration": iteration,
                "max_iterations": max_iterations
            }

            try:
                # Call LLM with tools
                client = vllm_router.get_client("reasoning")

                response = await client.chat_completion_with_tools(
                    messages=messages,
                    tools=tools,
                    temperature=0.7,
                    max_tokens=4096
                )

                message = response.choices[0].message

                # Check if LLM wants to call tools
                if message.tool_calls:
                    logger.info(f"🔧 LLM requested {len(message.tool_calls)} tool calls")

                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": message.tool_calls
                    })

                    # Execute each tool call
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        logger.info(f"   → Calling: {tool_name}({list(tool_args.keys())})")

                        # Yield tool call start
                        yield {
                            "type": "tool_call_start",
                            "tool": tool_name,
                            "arguments": tool_args,
                            "tool_call_id": tool_call.id
                        }

                        # Execute tool
                        tool_result = await self._execute_tool(
                            tool_name=tool_name,
                            arguments=tool_args,
                            context=context
                        )

                        # Yield tool result
                        yield {
                            "type": "tool_call_result",
                            "tool": tool_name,
                            "result": tool_result,
                            "tool_call_id": tool_call.id
                        }

                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result)
                        })

                        # Check if complete_task was called
                        if tool_name == "complete_task":
                            logger.info("✅ Task completed by LLM")
                            yield {
                                "type": "final_response",
                                "content": tool_result.get("response", ""),
                                "summary": tool_result.get("summary", ""),
                                "files_created": tool_result.get("files_created", [])
                            }
                            return

                        # Check if ask_human was called
                        if tool_name == "ask_human":
                            # This will be handled by HITL system
                            # The human response will be added to messages
                            pass

                    # Continue loop - LLM will see tool results and decide next step

                else:
                    # No tool calls - LLM provided final response
                    logger.info("✅ LLM provided final response (no tool calls)")
                    yield {
                        "type": "final_response",
                        "content": message.content or "Task completed",
                        "summary": "Completed without additional tools"
                    }
                    return

            except Exception as e:
                logger.error(f"❌ Tool Use execution error: {e}")
                yield {
                    "type": "error",
                    "message": str(e),
                    "iteration": iteration
                }
                return

        # Max iterations reached
        logger.warning(f"⚠️ Max iterations ({max_iterations}) reached")
        yield {
            "type": "max_iterations_reached",
            "message": f"Reached maximum {max_iterations} iterations",
            "content": "Task may not be fully complete. Please review the results."
        }

    def _build_tool_use_system_prompt(self) -> str:
        """Build system prompt for Tool Use mode"""
        return """You are an advanced AI software engineer with access to specialized agent tools.

Your role is to:
1. Understand user requests
2. Plan the best approach
3. Call appropriate agent tools to accomplish tasks
4. Ask humans for clarification when needed
5. Complete tasks successfully

## Available Tools

You have access to these agent tools:
- **ask_human**: Ask user questions when unclear or for important decisions
- **architect_agent**: Design project structure and architecture
- **coder_agent**: Write production-ready code
- **reviewer_agent**: Review code for quality and security
- **refiner_agent**: Fix issues and improve code
- **qa_tester_agent**: Generate and run tests
- **security_auditor_agent**: Deep security analysis
- **complete_task**: Mark task as complete with final response

## Guidelines

1. **For simple questions** (like "hello", "what is X"):
   - Answer directly with complete_task()
   - No need for other agents

2. **For code generation**:
   - Start with architect_agent() to plan structure
   - Use coder_agent() to implement
   - Use reviewer_agent() to check quality
   - Fix issues with refiner_agent() if needed
   - Complete with complete_task()

3. **When uncertain**:
   - Use ask_human() to clarify
   - Better to ask than to guess wrong
   - Provide context: why you're asking, what options you see

4. **For critical operations**:
   - Use security_auditor_agent() for sensitive code
   - Use ask_human() for dangerous operations (delete, drop, production changes)
   - Always confirm with user before irreversible actions

5. **Efficiency**:
   - Don't call unnecessary agents
   - Skip review for trivial code changes
   - Use judgment - balance thoroughness vs speed

## Your Workflow is Dynamic

You decide:
- Which agents to call
- In what order
- How many iterations
- When to ask humans
- When task is complete

Think step by step and use tools wisely."""

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a tool (agent) call

        Args:
            tool_name: Name of the tool/agent to call
            arguments: Tool arguments
            context: Optional context

        Returns:
            Tool execution result
        """
        logger.info(f"🔧 Executing tool: {tool_name}")

        # Special case: ask_human (HITL)
        if tool_name == "ask_human":
            return await self._handle_ask_human(arguments, context)

        # Special case: complete_task
        if tool_name == "complete_task":
            return {
                "success": True,
                "summary": arguments.get("summary", ""),
                "response": arguments.get("response", ""),
                "files_created": arguments.get("files_created", [])
            }

        # Agent tools - delegate to actual agents
        # TODO: Implement agent execution
        # For now, return placeholder
        return {
            "success": True,
            "agent": tool_name,
            "message": f"Agent {tool_name} executed (placeholder)",
            "arguments": arguments
        }

    async def _handle_ask_human(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Handle ask_human tool call via HITL system

        Args:
            arguments: Tool arguments (question, reason, options)
            context: Context with workflow_id

        Returns:
            Human's answer
        """
        from app.hitl import get_hitl_manager
        from app.hitl.models import HITLTemplates

        question = arguments.get("question", "")
        reason = arguments.get("reason", "")
        options = arguments.get("options")

        logger.info(f"❓ Asking human: {question}")

        # Get workflow ID from context
        workflow_id = context.get("workflow_id", "default") if context else "default"
        stage_id = f"ask_human_{datetime.utcnow().timestamp()}"

        # Create HITL request
        hitl_request = HITLTemplates.ask_human(
            workflow_id=workflow_id,
            stage_id=stage_id,
            question=question,
            reason=reason,
            options=options
        )

        # Send to HITL manager and wait for response
        hitl_manager = get_hitl_manager()
        response = await hitl_manager.request_and_wait(hitl_request, timeout=300)

        # Extract answer
        if response.action == "select" and response.selected_option:
            # User selected an option
            selected_idx = int(response.selected_option.split("_")[1])
            answer = options[selected_idx] if options else response.feedback
        else:
            # User provided free-form feedback
            answer = response.feedback or "No response provided"

        logger.info(f"✅ Human answered: {answer}")

        return {
            "success": True,
            "question": question,
            "answer": answer,
            "feedback": response.feedback
        }


# Global supervisor instance (with API mode enabled by default)
supervisor = SupervisorAgent(use_api=True)
