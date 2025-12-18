"""LangGraph API Routes

FastAPI endpoints for unified LangGraph workflow execution.
"""

import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.agent.langgraph.unified_workflow import unified_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/langgraph", tags=["langgraph"])


class WorkflowRequest(BaseModel):
    """Request to execute workflow"""
    user_request: str
    workspace_root: str
    task_type: str = "general"
    enable_debug: bool = True


class ApprovalRequest(BaseModel):
    """Request to approve/reject changes"""
    session_id: str
    approved: bool
    message: str = ""


@router.post("/execute")
async def execute_workflow(request: WorkflowRequest):
    """Execute unified LangGraph workflow

    This endpoint starts the workflow and streams results in real-time.

    CRITICAL: This endpoint performs REAL file operations.

    Args:
        request: Workflow execution request

    Returns:
        Streaming response with workflow updates
    """
    logger.info(f"🚀 Starting workflow execution")
    logger.info(f"   Request: {request.user_request[:100]}")
    logger.info(f"   Workspace: {request.workspace_root}")

    async def event_stream() -> AsyncGenerator[str, None]:
        """Stream workflow events to client"""
        try:
            async for update in unified_workflow.execute(
                user_request=request.user_request,
                workspace_root=request.workspace_root,
                task_type=request.task_type,
                enable_debug=request.enable_debug
            ):
                # Format as Server-Sent Events
                event_data = json.dumps(update)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            logger.error(f"❌ Error in workflow execution: {e}")
            error_data = json.dumps({
                "node": "ERROR",
                "updates": {"error": str(e)},
                "status": "error"
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

    Args:
        request: Approval request

    Returns:
        Approval status
    """
    logger.info(f"🧑 Processing approval: {request.approved}")

    try:
        # In production, this would update the workflow state
        # and resume execution
        # For now, just return success
        return {
            "success": True,
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
        Current workflow status
    """
    logger.info(f"📊 Getting status for session: {session_id}")

    # In production, query the workflow state from checkpointer
    # For now, return placeholder
    return {
        "session_id": session_id,
        "status": "running",
        "current_node": "coder",
        "progress": 0.5
    }


@router.get("/debug/{session_id}")
async def get_debug_logs(session_id: str):
    """Get debug logs for a session

    Args:
        session_id: Session ID

    Returns:
        Debug logs
    """
    logger.info(f"🔍 Getting debug logs for session: {session_id}")

    # In production, retrieve logs from state
    # For now, return empty list
    return {
        "session_id": session_id,
        "logs": [],
        "total_tokens": 0
    }
