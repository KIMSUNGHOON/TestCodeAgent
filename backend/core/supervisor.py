"""Supervisor Agent - The Strategist

This is the orchestrator that analyzes user requests and dynamically
constructs workflows based on task complexity and requirements.

Uses DeepSeek-R1 for reasoning and planning.
"""

import logging
from typing import Dict, List, Optional, Literal
from datetime import datetime

# Import DeepSeek-R1 prompts
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.prompts.deepseek_r1 import DEEPSEEK_R1_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class TaskComplexity:
    """Task complexity levels"""
    SIMPLE = "simple"  # Single agent, no loops
    MODERATE = "moderate"  # Multiple agents, basic loop
    COMPLEX = "complex"  # All gates, refinement loops
    CRITICAL = "critical"  # All gates, security, human approval


class AgentCapability:
    """Agent capabilities"""
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    SECURITY = "security"
    TESTING = "testing"
    REFINEMENT = "refinement"
    RCA = "root_cause_analysis"


class SupervisorAgent:
    """The Strategist - Analyzes requests and orchestrates workflows

    This agent uses DeepSeek-R1 reasoning to:
    1. Understand user intent
    2. Assess task complexity
    3. Determine required agents
    4. Build dynamic workflow DAG
    5. Monitor execution and adjust as needed
    """

    def __init__(self):
        """Initialize Supervisor Agent"""
        self.system_prompt = DEEPSEEK_R1_SYSTEM_PROMPT
        logger.info("✅ Supervisor Agent initialized")

    def analyze_request(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        """Analyze user request and determine workflow

        Uses DeepSeek-R1 reasoning to understand intent.

        Args:
            user_request: User's input
            context: Optional context from previous interactions

        Returns:
            Analysis results with workflow plan
        """
        logger.info("🎯 Supervisor: Analyzing user request...")
        logger.info(f"   Request: {user_request[:100]}...")

        # In production, this would call DeepSeek-R1 API with <think> blocks
        # For now, we use rule-based analysis

        analysis = {
            "user_request": user_request,
            "timestamp": datetime.utcnow().isoformat(),
            "complexity": self._assess_complexity(user_request),
            "task_type": self._determine_task_type(user_request),
            "required_agents": self._determine_required_agents(user_request),
            "workflow_strategy": self._build_workflow_strategy(user_request),
            "max_iterations": self._determine_max_iterations(user_request),
            "requires_human_approval": self._requires_human_approval(user_request),
            "reasoning": self._generate_reasoning(user_request),
        }

        logger.info(f"✅ Analysis Complete:")
        logger.info(f"   Complexity: {analysis['complexity']}")
        logger.info(f"   Task Type: {analysis['task_type']}")
        logger.info(f"   Required Agents: {len(analysis['required_agents'])}")
        logger.info(f"   Strategy: {analysis['workflow_strategy']}")

        return analysis

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

        In production, this would use DeepSeek-R1 <think> blocks
        """
        complexity = self._assess_complexity(request)
        task_type = self._determine_task_type(request)
        agents = self._determine_required_agents(request)

        reasoning = f"""<think>
1. Request Analysis:
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
   - Enable refinement loops if needed
</think>

Strategy: {self._build_workflow_strategy(request)} approach with {len(agents)} agents.
"""
        return reasoning


# Global supervisor instance
supervisor = SupervisorAgent()
