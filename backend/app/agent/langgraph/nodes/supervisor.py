"""Supervisor Node for task analysis and routing

Analyzes user request and determines optimal workflow path.
"""

import logging
from typing import Dict
from app.agent.langgraph.schemas.state import QualityGateState, TaskType

logger = logging.getLogger(__name__)


def supervisor_node(state: QualityGateState) -> Dict:
    """Supervisor node: Analyze task and route to appropriate path

    Determines:
    1. Task type (implementation, review, testing, security_audit)
    2. Whether to use parallel execution
    3. Maximum iterations for self-healing

    Args:
        state: Current workflow state

    Returns:
        State updates
    """
    logger.info("🎯 Supervisor Node: Analyzing task...")

    user_request = state["user_request"].lower()

    # Task type detection (check testing first, as "add" can match both testing and implementation)
    task_type: TaskType = "general"

    if any(keyword in user_request for keyword in ["unit test", "integration test", "test"]):
        task_type = "testing"
    elif any(keyword in user_request for keyword in ["security", "vulnerability", "owasp"]):
        task_type = "security_audit"
    elif any(keyword in user_request for keyword in ["review", "check", "analyze code"]):
        task_type = "review"
    elif any(keyword in user_request for keyword in ["implement", "create", "add", "build"]):
        task_type = "implementation"

    # Determine execution mode
    # Use parallel for implementation (need all gates), sequential for review
    execution_mode = "parallel" if task_type == "implementation" else "sequential"
    parallel_execution = (execution_mode == "parallel")

    # Determine max iterations based on task complexity
    max_iterations = 3 if task_type == "implementation" else 1

    logger.info(f"✅ Task Analysis Complete:")
    logger.info(f"   Task Type: {task_type}")
    logger.info(f"   Execution Mode: {execution_mode}")
    logger.info(f"   Max Iterations: {max_iterations}")
    logger.info(f"   Parallel Gates: {parallel_execution}")

    return {
        "current_node": "supervisor",
        "task_type": task_type,
        "execution_mode": execution_mode,
        "parallel_execution": parallel_execution,
        "max_iterations": max_iterations,
    }
