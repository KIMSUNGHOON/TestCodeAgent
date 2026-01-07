"""Persistence Node for state save to .ai_context.json

Saves workflow execution results and updates recommended next tasks.
"""

import logging
from typing import Dict
from datetime import datetime
from app.agent.langgraph.schemas.state import QualityGateState
from app.agent.langgraph.tools.context_manager import ContextManager

logger = logging.getLogger(__name__)


def persistence_node(state: QualityGateState) -> Dict:
    """Save workflow state to .ai_context.json

    Persists:
    1. Workflow execution results
    2. Generated artifacts
    3. Quality gate outcomes
    4. Recommended next tasks

    Args:
        state: Current workflow state

    Returns:
        State updates with persistence status
    """
    logger.info("💾 Persistence Node: Saving state to .ai_context.json...")

    workspace_root = state["workspace_root"]
    context_mgr = ContextManager(workspace_root)

    # Calculate duration
    started_at = datetime.fromisoformat(state["started_at"])
    completed_at = datetime.utcnow()
    duration_ms = (completed_at - started_at).total_seconds() * 1000

    # Extract artifacts
    final_artifacts = state.get("final_artifacts", [])
    artifact_files = [a["filename"] for a in final_artifacts]

    # Save workflow execution
    workflow_status = state.get("workflow_status", "unknown")
    success = context_mgr.add_workflow_execution(
        workflow_type=state.get("task_type", "general"),
        status=workflow_status,
        duration_ms=duration_ms,
        artifacts=artifact_files,
        notes=f"User request: {state['user_request'][:100]}"
    )

    if not success:
        logger.error("❌ Failed to save workflow execution")
        return {
            "current_node": "persistence",
            "completed_at": completed_at.isoformat(),
            "total_duration_ms": duration_ms,
        }

    # Update recommended next tasks based on results
    next_tasks = []

    # If security issues found, recommend security review
    security_findings = state.get("security_findings", [])
    critical_security = [f for f in security_findings if f["severity"] == "critical"]
    if critical_security:
        next_tasks.append({
            "priority": "critical",
            "task": "Fix critical security vulnerabilities",
            "rationale": f"{len(critical_security)} critical security issues found",
            "estimated_effort": "1-2 hours"
        })

    # If tests failed, recommend test fixes
    test_results = state.get("qa_test_results", [])
    failed_tests = [t for t in test_results if not t["passed"]]
    if failed_tests:
        next_tasks.append({
            "priority": "high",
            "task": "Fix failing unit tests",
            "rationale": f"{len(failed_tests)} tests failing",
            "estimated_effort": "30-60 minutes"
        })

    # If completed successfully, recommend next feature
    if workflow_status == "completed":
        next_tasks.append({
            "priority": "medium",
            "task": "Add integration tests",
            "rationale": "Successful implementation completed, add integration coverage",
            "estimated_effort": "2-3 hours"
        })

    if next_tasks:
        context_mgr.update_next_tasks(next_tasks)

    logger.info(f"✅ Workflow state persisted successfully")
    logger.info(f"   Duration: {duration_ms:.2f}ms")
    logger.info(f"   Artifacts: {len(artifact_files)}")
    logger.info(f"   Next tasks: {len(next_tasks)}")

    return {
        "current_node": "persistence",
        "completed_at": completed_at.isoformat(),
        "total_duration_ms": duration_ms,
    }
