"""Human Approval Node for human-in-the-loop workflow

Enhanced HITL integration with 5 checkpoint types:
- approval: Simple approve/reject
- review: Review with feedback
- edit: Direct content editing
- choice: Select from options
- confirm: Confirmation for dangerous actions
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agent.langgraph.schemas.state import QualityGateState, DebugLog
from app.hitl import HITLManager, get_hitl_manager
from app.hitl.models import (
    HITLRequest,
    HITLResponse,
    HITLCheckpointType,
    HITLContent,
    HITLAction,
    HITLStatus,
    ChoiceOption,
    HITLTemplates,
)

logger = logging.getLogger(__name__)


async def human_approval_node(state: QualityGateState) -> Dict:
    """Human Approval node: Wait for human to approve/reject

    This node:
    1. Creates an HITL request based on context
    2. Sends request via HITL Manager (broadcasts to WebSocket)
    3. Waits for user response
    4. Returns appropriate state updates

    CRITICAL: This node implements human-in-the-loop pattern.
    Workflow execution pauses here until user provides input.

    Args:
        state: Current workflow state

    Returns:
        State updates with approval status
    """
    logger.info("HITL: Human approval checkpoint reached")

    workflow_id = state.get("workflow_id", "default")
    stage_id = state.get("current_node", "human_approval")

    # Get HITL Manager
    hitl_manager = get_hitl_manager()

    # Determine what type of approval is needed based on context
    checkpoint_type, hitl_request = _create_hitl_request_from_state(state, workflow_id, stage_id)

    # Add debug log
    debug_logs = []
    if state.get("enable_debug"):
        debug_logs.append(DebugLog(
            timestamp=datetime.utcnow().isoformat(),
            node="human_approval",
            agent="HITLNode",
            event_type="thinking",
            content=f"Requesting human input: {checkpoint_type.value}",
            metadata={
                "checkpoint_type": checkpoint_type.value,
                "request_id": hitl_request.request_id,
            },
            token_usage=None
        ))

    # Check if we already have a response (resume from pause)
    existing_status = state.get("approval_status", "pending")
    if existing_status in ["approved", "rejected", "modified"]:
        logger.info(f"HITL: Existing response found: {existing_status}")
        return _process_existing_response(state, debug_logs)

    try:
        # Request human input (this will broadcast to WebSocket and wait)
        logger.info(f"HITL: Requesting input for request {hitl_request.request_id}")

        # For SSE-based workflow, we return immediately with "awaiting_approval" status
        # The API layer will handle the waiting
        return {
            "workflow_status": "awaiting_approval",
            "hitl_request": hitl_request.model_dump(),
            "hitl_checkpoint_type": checkpoint_type.value,
            "debug_logs": debug_logs,
        }

    except Exception as e:
        logger.error(f"HITL: Error creating request: {e}")
        debug_logs.append(DebugLog(
            timestamp=datetime.utcnow().isoformat(),
            node="human_approval",
            agent="HITLNode",
            event_type="error",
            content=f"Failed to create HITL request: {str(e)}",
            metadata={"error": str(e)},
            token_usage=None
        ))
        return {
            "workflow_status": "failed",
            "last_error": f"HITL request failed: {str(e)}",
            "debug_logs": debug_logs,
        }


def _create_hitl_request_from_state(
    state: QualityGateState,
    workflow_id: str,
    stage_id: str
) -> tuple[HITLCheckpointType, HITLRequest]:
    """Create appropriate HITL request based on workflow state"""

    # Check if we have code to review
    coder_output = state.get("coder_output")
    if coder_output and coder_output.get("artifacts"):
        artifacts = coder_output["artifacts"]
        if artifacts:
            # Code review request
            return (
                HITLCheckpointType.REVIEW,
                HITLRequest(
                    workflow_id=workflow_id,
                    stage_id=stage_id,
                    agent_id="coder",
                    checkpoint_type=HITLCheckpointType.REVIEW,
                    title="Code Review Required",
                    description="Review the generated code before applying.",
                    content=HITLContent(
                        code=artifacts[0].get("content", "") if isinstance(artifacts[0], dict) else "",
                        language=artifacts[0].get("language", "python") if isinstance(artifacts[0], dict) else "python",
                        filename=artifacts[0].get("filename", "generated.py") if isinstance(artifacts[0], dict) else "generated.py",
                        details={"artifacts": artifacts},
                        summary=f"Generated {len(artifacts)} file(s)"
                    ),
                    priority="high"
                )
            )

    # Check for pending diffs
    pending_diffs = state.get("pending_diffs", [])
    if pending_diffs:
        return (
            HITLCheckpointType.EDIT,
            HITLRequest(
                workflow_id=workflow_id,
                stage_id=stage_id,
                agent_id="refiner",
                checkpoint_type=HITLCheckpointType.EDIT,
                title="Review Code Changes",
                description="Review and optionally edit the proposed code changes.",
                content=HITLContent(
                    details={"diffs": pending_diffs},
                    summary=f"{len(pending_diffs)} file(s) to review"
                ),
                priority="high"
            )
        )

    # Check for final artifacts (final approval)
    final_artifacts = state.get("final_artifacts", [])
    if final_artifacts:
        return (
            HITLCheckpointType.APPROVAL,
            HITLRequest(
                workflow_id=workflow_id,
                stage_id=stage_id,
                agent_id="aggregator",
                checkpoint_type=HITLCheckpointType.APPROVAL,
                title="Final Approval",
                description="Review and approve the final results.",
                content=HITLContent(
                    details={"artifacts": final_artifacts},
                    summary=f"{len(final_artifacts)} artifact(s) ready"
                ),
                priority="high"
            )
        )

    # Default: simple approval
    return (
        HITLCheckpointType.APPROVAL,
        HITLRequest(
            workflow_id=workflow_id,
            stage_id=stage_id,
            agent_id="workflow",
            checkpoint_type=HITLCheckpointType.APPROVAL,
            title="Approval Required",
            description="Please review and approve to continue.",
            content=HITLContent(
                summary="Workflow requires your approval to continue"
            ),
            priority="normal"
        )
    )


def _process_existing_response(state: QualityGateState, debug_logs: List[DebugLog]) -> Dict:
    """Process an existing HITL response stored in state"""
    status = state.get("approval_status")
    message = state.get("approval_message", "")

    if status == "approved":
        logger.info("HITL: Changes approved")
        return {
            "approval_status": "approved",
            "workflow_status": "completed",
            "debug_logs": debug_logs,
        }
    elif status == "rejected":
        logger.info("HITL: Changes rejected")
        return {
            "approval_status": "rejected",
            "workflow_status": "self_healing" if message else "failed",
            "approval_message": message,
            "debug_logs": debug_logs,
        }
    elif status == "modified":
        logger.info("HITL: Content modified by user")
        return {
            "approval_status": "modified",
            "workflow_status": "completed",
            "debug_logs": debug_logs,
        }
    else:
        return {
            "workflow_status": "awaiting_approval",
            "debug_logs": debug_logs,
        }


async def process_hitl_response(
    state: QualityGateState,
    response: HITLResponse
) -> Dict:
    """Process user's HITL response and update workflow state

    This function is called by the API endpoint when user submits response.

    Args:
        state: Current workflow state
        response: User's response

    Returns:
        State updates to resume workflow
    """
    logger.info(f"HITL: Processing response: {response.action.value}")

    debug_logs = []
    if state.get("enable_debug"):
        debug_logs.append(DebugLog(
            timestamp=datetime.utcnow().isoformat(),
            node="human_approval",
            agent="HITLNode",
            event_type="result",
            content=f"User response: {response.action.value}",
            metadata={
                "action": response.action.value,
                "feedback": response.feedback,
                "has_modified_content": response.modified_content is not None,
            },
            token_usage=None
        ))

    if response.action == HITLAction.APPROVE:
        return {
            "approval_status": "approved",
            "approval_message": response.feedback,
            "workflow_status": "completed",
            "debug_logs": debug_logs,
        }

    elif response.action == HITLAction.CONFIRM:
        return {
            "approval_status": "approved",
            "approval_message": response.feedback,
            "workflow_status": "running",  # Continue execution
            "debug_logs": debug_logs,
        }

    elif response.action == HITLAction.REJECT:
        return {
            "approval_status": "rejected",
            "approval_message": response.feedback,
            "workflow_status": "failed",
            "last_failure_reason": response.feedback or "Rejected by user",
            "debug_logs": debug_logs,
        }

    elif response.action == HITLAction.RETRY:
        return {
            "approval_status": "rejected",
            "approval_message": response.retry_instructions or response.feedback,
            "workflow_status": "self_healing",  # Trigger retry
            "last_failure_reason": response.retry_instructions or "Retry requested",
            "debug_logs": debug_logs,
        }

    elif response.action == HITLAction.EDIT:
        # User edited the content directly
        return {
            "approval_status": "modified",
            "approval_message": response.feedback,
            "user_modified_content": response.modified_content,
            "workflow_status": "completed",
            "debug_logs": debug_logs,
        }

    elif response.action == HITLAction.SELECT:
        return {
            "approval_status": "selected",
            "selected_option": response.selected_option,
            "approval_message": response.feedback,
            "workflow_status": "running",  # Continue with selection
            "debug_logs": debug_logs,
        }

    elif response.action == HITLAction.CANCEL:
        return {
            "approval_status": "cancelled",
            "approval_message": response.feedback or "Cancelled by user",
            "workflow_status": "failed",
            "debug_logs": debug_logs,
        }

    else:
        logger.warning(f"HITL: Unknown action: {response.action}")
        return {
            "approval_status": "pending",
            "workflow_status": "awaiting_approval",
            "debug_logs": debug_logs,
        }


def create_workflow_plan_approval(
    workflow_id: str,
    plan: Dict[str, Any]
) -> HITLRequest:
    """Create HITL request for workflow plan approval

    Args:
        workflow_id: Workflow ID
        plan: Workflow plan to review

    Returns:
        HITLRequest for plan approval
    """
    stages = plan.get("stages", [])
    agents = set()
    for stage in stages:
        agents.update(stage.get("agents", []))

    return HITLRequest(
        workflow_id=workflow_id,
        stage_id="workflow_plan",
        agent_id="supervisor",
        checkpoint_type=HITLCheckpointType.APPROVAL,
        title="Workflow Plan Review",
        description="Review the proposed workflow before execution begins.",
        content=HITLContent(
            workflow_plan=plan,
            summary=f"{len(stages)} stages, {len(agents)} agents"
        ),
        priority="high"
    )


def create_implementation_choice(
    workflow_id: str,
    stage_id: str,
    question: str,
    options: List[Dict[str, Any]]
) -> HITLRequest:
    """Create HITL request for implementation choice

    Args:
        workflow_id: Workflow ID
        stage_id: Current stage ID
        question: Question to ask user
        options: List of option dicts with id, title, description, etc.

    Returns:
        HITLRequest for choice
    """
    choice_options = [
        ChoiceOption(
            option_id=opt.get("id", str(i)),
            title=opt.get("title", f"Option {i+1}"),
            description=opt.get("description", ""),
            preview=opt.get("preview"),
            pros=opt.get("pros", []),
            cons=opt.get("cons", []),
            recommended=opt.get("recommended", False),
        )
        for i, opt in enumerate(options)
    ]

    return HITLRequest(
        workflow_id=workflow_id,
        stage_id=stage_id,
        agent_id="supervisor",
        checkpoint_type=HITLCheckpointType.CHOICE,
        title="Decision Required",
        description=question,
        content=HITLContent(
            options=choice_options,
            summary=f"Choose from {len(options)} options"
        ),
        priority="high"
    )


def create_confirmation_request(
    workflow_id: str,
    stage_id: str,
    action: str,
    risks: List[str]
) -> HITLRequest:
    """Create HITL request for dangerous action confirmation

    Args:
        workflow_id: Workflow ID
        stage_id: Current stage ID
        action: Description of the action
        risks: List of potential risks

    Returns:
        HITLRequest for confirmation
    """
    return HITLRequest(
        workflow_id=workflow_id,
        stage_id=stage_id,
        agent_id="executor",
        checkpoint_type=HITLCheckpointType.CONFIRM,
        title="Confirmation Required",
        description=f"The following action requires your confirmation: {action}",
        content=HITLContent(
            action_description=action,
            risks=risks,
            summary="This action may have significant effects"
        ),
        priority="critical"
    )


# Legacy compatibility functions
def process_approval(state: QualityGateState, approved: bool, message: str = "") -> Dict:
    """Legacy function for backward compatibility

    Use process_hitl_response instead for new code.
    """
    response = HITLResponse(
        request_id="legacy",
        action=HITLAction.APPROVE if approved else HITLAction.REJECT,
        feedback=message
    )
    # Note: This is synchronous for backward compatibility
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't await, return sync result
            return {
                "approval_status": "approved" if approved else "rejected",
                "approval_message": message,
                "workflow_status": "completed" if approved else "self_healing",
            }
        else:
            return loop.run_until_complete(process_hitl_response(state, response))
    except RuntimeError:
        return {
            "approval_status": "approved" if approved else "rejected",
            "approval_message": message,
            "workflow_status": "completed" if approved else "self_healing",
        }


def create_approval_summary(state: QualityGateState) -> Dict:
    """Create a summary of changes for approval UI

    Args:
        state: Current workflow state

    Returns:
        Dict with summary information for frontend
    """
    pending_diffs = state.get("pending_diffs", [])
    coder_output = state.get("coder_output", {})
    artifacts = coder_output.get("artifacts", []) if coder_output else []

    return {
        "total_files": len(pending_diffs) + len(artifacts),
        "pending_diffs": len(pending_diffs),
        "generated_files": len(artifacts),
        "status": state.get("workflow_status", "running"),
        "checkpoint_type": state.get("hitl_checkpoint_type", "approval"),
    }
