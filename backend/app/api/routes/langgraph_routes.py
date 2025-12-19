"""LangGraph API Routes

FastAPI endpoints for unified LangGraph workflow execution.
Supports enhanced workflow with streaming, HITL, and progress tracking.
"""

import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

# Import both workflows for flexibility
from app.agent.langgraph.unified_workflow import unified_workflow
from app.agent.langgraph.enhanced_workflow import enhanced_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/langgraph", tags=["langgraph"])


class WorkflowRequest(BaseModel):
    """Request to execute workflow"""
    user_request: str
    workspace_root: str
    task_type: str = "general"
    enable_debug: bool = True
    use_enhanced: bool = True  # Use enhanced workflow by default


class ApprovalRequest(BaseModel):
    """Request to approve/reject changes"""
    session_id: str
    approved: bool
    message: str = ""


@router.post("/execute")
async def execute_workflow(request: WorkflowRequest):
    """Execute LangGraph workflow with real-time streaming

    This endpoint starts the workflow and streams results including:
    - Agent thinking/reasoning
    - Code generation progress
    - Quality gate results
    - HITL checkpoints
    - Execution times per agent
    - ETA updates

    CRITICAL: This endpoint performs REAL file operations.

    Args:
        request: Workflow execution request

    Returns:
        Streaming response with workflow updates
    """
    logger.info(f"🚀 Starting workflow execution")
    logger.info(f"   Request: {request.user_request[:100]}")
    logger.info(f"   Workspace: {request.workspace_root}")
    logger.info(f"   Enhanced Mode: {request.use_enhanced}")

    async def event_stream() -> AsyncGenerator[str, None]:
        """Stream workflow events to client"""
        try:
            # Choose workflow based on request
            workflow = enhanced_workflow if request.use_enhanced else unified_workflow

            async for update in workflow.execute(
                user_request=request.user_request,
                workspace_root=request.workspace_root,
                task_type=request.task_type,
                enable_debug=request.enable_debug
            ):
                # Enrich update with metadata
                enriched_update = {
                    **update,
                    "workflow_type": "enhanced" if request.use_enhanced else "unified",
                }

                # Format as Server-Sent Events
                event_data = json.dumps(enriched_update, default=str)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            logger.error(f"❌ Error in workflow execution: {e}", exc_info=True)
            error_data = json.dumps({
                "node": "ERROR",
                "status": "error",
                "agent_title": "❌ Error",
                "agent_description": "Workflow failed",
                "updates": {"error": str(e)},
            })
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.post("/approve")
async def approve_changes(request: ApprovalRequest):
    """Process human approval decision

    Used for HITL checkpoints in the workflow.

    Args:
        request: Approval request

    Returns:
        Approval status
    """
    logger.info(f"🧑 Processing approval: {request.approved}")

    try:
        from app.hitl import get_hitl_manager

        hitl_manager = get_hitl_manager()

        # Submit the response
        from app.hitl.models import HITLResponse, HITLAction

        response = HITLResponse(
            request_id=request.session_id,
            action=HITLAction.APPROVE if request.approved else HITLAction.REJECT,
            feedback=request.message,
        )

        success = await hitl_manager.submit_response(response)

        return {
            "success": success,
            "session_id": request.session_id,
            "approved": request.approved,
            "message": request.message
        }

    except Exception as e:
        logger.error(f"❌ Error processing approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{session_id}")
async def get_workflow_status(session_id: str):
    """Get current workflow status

    Args:
        session_id: Session ID

    Returns:
        Current workflow status including progress
    """
    logger.info(f"📊 Getting status for session: {session_id}")

    # In production, query the workflow state from checkpointer
    return {
        "session_id": session_id,
        "status": "running",
        "current_node": "coder",
        "progress": 0.5,
        "agents_completed": [],
        "agents_pending": [],
        "estimated_time_remaining": None
    }


@router.get("/debug/{session_id}")
async def get_debug_logs(session_id: str):
    """Get debug logs for a session

    Args:
        session_id: Session ID

    Returns:
        Debug logs with token usage
    """
    logger.info(f"🔍 Getting debug logs for session: {session_id}")

    return {
        "session_id": session_id,
        "logs": [],
        "total_tokens": 0,
        "token_breakdown": {}
    }


@router.get("/agents")
async def get_available_agents():
    """Get list of available agents and their descriptions

    Returns:
        Agent information for UI display
    """
    from app.agent.langgraph.enhanced_workflow import AGENT_INFO

    return {
        "agents": AGENT_INFO,
        "workflow_types": {
            "enhanced": "Full workflow with Architect, parallel execution, and HITL",
            "unified": "Standard sequential workflow"
        }
    }
