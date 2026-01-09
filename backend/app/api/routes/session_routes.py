"""Session API Routes for Remote Client

FastAPI endpoints for remote client session management.
Provides RESTful session-based API for remote CLI access.
"""

import logging
import uuid
import os
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["sessions"])  # No prefix - will be added at /api level


# ============================================================================
# Request/Response Models
# ============================================================================

class SessionCreateRequest(BaseModel):
    """Request to create a new session"""
    workspace: Optional[str] = None  # Optional workspace override


class SessionCreateResponse(BaseModel):
    """Response from session creation"""
    session_id: str
    workspace: str
    message: str


class SessionExecuteRequest(BaseModel):
    """Request to execute code in a session"""
    user_request: str
    max_iterations: int = 15  # Maximum tool call iterations


# ============================================================================
# Session Store (uses SessionManager for consistency with local CLI)
# ============================================================================

class SessionStore:
    """Simple session storage using SessionManager"""

    def __init__(self):
        self.sessions = {}  # session_id -> SessionManager

    def create_session(self, workspace: Optional[str] = None) -> dict:
        """Create a new session

        Args:
            workspace: Optional custom workspace path

        Returns:
            Session info dictionary
        """
        from cli.session_manager import SessionManager

        session_id = f"session-{uuid.uuid4().hex[:12]}"

        # Generate workspace path: $DEFAULT_WORKSPACE/session_id
        if workspace:
            workspace_path = os.path.abspath(workspace)
        else:
            base_workspace = os.getenv("DEFAULT_WORKSPACE", os.getcwd())
            workspace_path = os.path.join(base_workspace, session_id)

        # Create SessionManager (same as local CLI)
        session_mgr = SessionManager(
            workspace=workspace_path,
            session_id=session_id,
            model=os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-R1"),
            auto_save=False  # Don't auto-save for remote sessions
        )

        session_info = {
            "session_id": session_id,
            "workspace": workspace_path,
            "created_at": None,
            "status": "active"
        }

        self.sessions[session_id] = session_mgr
        logger.info(f"✅ Created session {session_id}")
        logger.info(f"   Workspace: {workspace_path}")

        return session_info

    def get_session(self, session_id: str):
        """Get SessionManager by ID

        Args:
            session_id: Session identifier

        Returns:
            SessionManager or None if not found
        """
        return self.sessions.get(session_id)


# Global session store
session_store = SessionStore()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new coding session

    Creates an isolated workspace for the session and returns session ID.

    Args:
        request: Session creation request with optional workspace

    Returns:
        Session information including ID and workspace path
    """
    try:
        session_info = session_store.create_session(request.workspace)

        return SessionCreateResponse(
            session_id=session_info["session_id"],
            workspace=session_info["workspace"],
            message="Session created successfully"
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information

    Args:
        session_id: Session identifier

    Returns:
        Session information
    """
    session_mgr = session_store.get_session(session_id)

    if not session_mgr:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {
        "session_id": session_mgr.session_id,
        "workspace": str(session_mgr.workspace),
        "model": session_mgr.model,
        "status": "active"
    }


@router.post("/sessions/{session_id}/execute")
async def execute_in_session(session_id: str, request: SessionExecuteRequest):
    """Execute a request in the session with Server-Sent Events (SSE) streaming

    This endpoint streams workflow execution updates in real-time using SSE.
    Uses the same Tool Use workflow as local CLI for consistency.

    Args:
        session_id: Session identifier
        request: Execution request with user's coding task

    Returns:
        StreamingResponse with SSE events
    """
    # Get session manager
    session_mgr = session_store.get_session(session_id)
    if not session_mgr:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    logger.info(f"🚀 Executing request in session {session_id}")
    logger.info(f"   Request: {request.user_request[:100]}")
    logger.info(f"   Workspace: {session_mgr.workspace}")

    async def event_stream() -> AsyncGenerator[str, None]:
        """Generate SSE events from workflow execution

        SSE Format:
            event: <event_type>
            data: <json_data>
        """
        try:
            # Use Tool Use workflow (same as local CLI)
            async for update in session_mgr.execute_tool_use_workflow(
                user_request=request.user_request,
                max_iterations=request.max_iterations
            ):
                # update format from supervisor.execute_with_tools():
                # {"type": "reasoning"|"tool_call_start"|"tool_call_result"|"final_response", ...}

                update_type = update.get("type", "update")

                # Map to SSE event types
                event_type = "update"
                if update_type == "reasoning":
                    event_type = "reasoning"
                elif update_type == "tool_call_start":
                    event_type = "tool_start"
                elif update_type == "tool_call_result":
                    event_type = "tool_result"
                elif update_type == "final_response":
                    event_type = "response"
                elif update_type == "error":
                    event_type = "error"

                # Send as SSE
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(update)}\n\n"

            # Send completion event
            completion_data = {
                "type": "complete",
                "session_id": session_id,
                "status": "completed"
            }
            yield f"event: complete\n"
            yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=True)
            error_data = {
                "type": "error",
                "error": str(e),
                "session_id": session_id
            }
            yield f"event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session

    Args:
        session_id: Session identifier

    Returns:
        Confirmation message
    """
    session_mgr = session_store.get_session(session_id)

    if not session_mgr:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Remove from store
    del session_store.sessions[session_id]

    logger.info(f"🗑️  Deleted session {session_id}")

    return {
        "message": f"Session {session_id} deleted",
        "session_id": session_id
    }
