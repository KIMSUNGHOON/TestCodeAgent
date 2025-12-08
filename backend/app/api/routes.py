"""API routes for the coding agent."""
import logging
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.models import (
    ChatRequest,
    ChatResponse,
    AgentStatus,
    ModelsResponse,
    ModelInfo,
    ErrorResponse,
    ChatMessage
)
from app.agent.agent_manager import agent_manager
from app.agent.workflow_manager import workflow_manager
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message.

    Args:
        request: Chat request with message and session info

    Returns:
        Chat response with agent's message
    """
    try:
        # Get or create agent for session
        agent = agent_manager.get_or_create_agent(request.session_id)

        # Process message (non-streaming)
        if not request.stream:
            response = await agent.process_message(
                user_message=request.message,
                task_type=request.task_type,
                system_prompt=request.system_prompt
            )

            return ChatResponse(
                response=response,
                session_id=request.session_id,
                task_type=request.task_type
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Use /chat/stream endpoint for streaming responses"
            )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream a chat response.

    Args:
        request: Chat request with message and session info

    Returns:
        Streaming response with agent's message chunks
    """
    try:
        # Get or create agent for session
        agent = agent_manager.get_or_create_agent(request.session_id)

        # Create streaming response
        async def generate():
            try:
                async for chunk in agent.stream_message(
                    user_message=request.message,
                    task_type=request.task_type,
                    system_prompt=request.system_prompt
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Error streaming response: {e}")
                yield f"\n\nError: {str(e)}"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"Error in chat stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/status/{session_id}", response_model=AgentStatus)
async def get_agent_status(session_id: str):
    """Get agent status for a session.

    Args:
        session_id: Session identifier

    Returns:
        Agent status with conversation history
    """
    try:
        agent = agent_manager.get_or_create_agent(session_id)
        history = agent.get_history()

        return AgentStatus(
            session_id=session_id,
            message_count=len(history),
            history=[ChatMessage(**msg) for msg in history]
        )

    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agent/session/{session_id}")
async def delete_session(session_id: str):
    """Delete an agent session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    try:
        agent_manager.delete_agent(session_id)
        return {"message": f"Session {session_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/clear/{session_id}")
async def clear_history(session_id: str):
    """Clear conversation history for a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    try:
        agent = agent_manager.get_or_create_agent(session_id)
        agent.clear_history()
        return {"message": f"History cleared for session {session_id}"}

    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/sessions")
async def list_sessions():
    """List all active sessions.

    Returns:
        List of active session IDs
    """
    try:
        sessions = agent_manager.get_active_sessions()
        return {"sessions": sessions, "count": len(sessions)}

    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """List available models.

    Returns:
        List of available models with their info
    """
    models = [
        ModelInfo(
            name=settings.reasoning_model,
            endpoint=settings.vllm_reasoning_endpoint,
            type="reasoning"
        ),
        ModelInfo(
            name=settings.coding_model,
            endpoint=settings.vllm_coding_endpoint,
            type="coding"
        )
    ]

    return ModelsResponse(models=models)


# ==================== Workflow Endpoints ====================


@router.post("/workflow/execute")
async def execute_workflow(request: ChatRequest):
    """Execute coding workflow: Planning -> Coding -> Review.

    This endpoint uses multi-agent workflow to automatically:
    1. Analyze requirements and create a plan (DeepSeek-R1)
    2. Generate code based on the plan (Qwen3-Coder)
    3. Review and improve the code (Qwen3-Coder)

    Args:
        request: Chat request with coding task

    Returns:
        Streaming response with workflow progress
    """
    try:
        # Get or create workflow for session
        workflow = workflow_manager.get_or_create_workflow(request.session_id)

        # Create streaming response
        async def generate():
            try:
                async for update in workflow.execute_stream(
                    user_request=request.message
                ):
                    # Send update as JSON
                    yield json.dumps(update) + "\n"
            except Exception as e:
                logger.error(f"Error in workflow execution: {e}")
                yield json.dumps({
                    "agent": "Workflow",
                    "status": "error",
                    "content": f"Error: {str(e)}"
                }) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson"
        )

    except Exception as e:
        logger.error(f"Error in workflow endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow/sessions")
async def list_workflow_sessions():
    """List all active workflow sessions.

    Returns:
        List of active workflow session IDs
    """
    try:
        sessions = workflow_manager.get_active_sessions()
        return {"sessions": sessions, "count": len(sessions)}

    except Exception as e:
        logger.error(f"Error listing workflow sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workflow/session/{session_id}")
async def delete_workflow_session(session_id: str):
    """Delete a workflow session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    try:
        workflow_manager.delete_workflow(session_id)
        return {"message": f"Workflow session {session_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting workflow session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
