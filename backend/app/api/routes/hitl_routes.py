"""HITL API Routes

REST API endpoints for Human-in-the-Loop functionality.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.hitl import HITLManager, HITLRequest, HITLResponse, HITLStatus, get_hitl_manager
from app.hitl.models import HITLAction, HITLEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl", tags=["HITL"])


# ==================== Request/Response Models ====================

class HITLResponseInput(BaseModel):
    """Input model for submitting HITL response"""
    action: HITLAction
    feedback: Optional[str] = None
    modified_content: Optional[str] = None
    selected_option: Optional[str] = None
    retry_instructions: Optional[str] = None


class HITLRequestSummary(BaseModel):
    """Summary of a HITL request for listing"""
    request_id: str
    workflow_id: str
    stage_id: str
    checkpoint_type: str
    title: str
    status: str
    priority: str
    created_at: str


# ==================== WebSocket Connection Manager ====================

class HITLWebSocketManager:
    """Manages WebSocket connections for HITL events"""

    def __init__(self):
        # Connected clients by workflow_id
        self._connections: dict[str, set[WebSocket]] = {}
        # All connections
        self._all_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, workflow_id: Optional[str] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self._all_connections.add(websocket)

        if workflow_id:
            if workflow_id not in self._connections:
                self._connections[workflow_id] = set()
            self._connections[workflow_id].add(websocket)

        logger.info(f"[HITL WS] Client connected (workflow={workflow_id})")

    def disconnect(self, websocket: WebSocket, workflow_id: Optional[str] = None):
        """Handle WebSocket disconnection"""
        self._all_connections.discard(websocket)

        if workflow_id and workflow_id in self._connections:
            self._connections[workflow_id].discard(websocket)
            if not self._connections[workflow_id]:
                del self._connections[workflow_id]

        logger.info(f"[HITL WS] Client disconnected (workflow={workflow_id})")

    async def broadcast_to_workflow(self, workflow_id: str, event: HITLEvent):
        """Broadcast event to all clients subscribed to a workflow"""
        connections = self._connections.get(workflow_id, set())

        # Also send to global listeners
        all_connections = connections | self._all_connections

        disconnected = set()
        for websocket in all_connections:
            try:
                await websocket.send_json(event.model_dump())
            except Exception as e:
                logger.warning(f"[HITL WS] Failed to send to client: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, workflow_id)

    async def broadcast_event(self, event: HITLEvent):
        """Broadcast event to relevant clients"""
        await self.broadcast_to_workflow(event.workflow_id, event)


# Global WebSocket manager
ws_manager = HITLWebSocketManager()


# ==================== REST Endpoints ====================

@router.get("/pending", response_model=List[HITLRequestSummary])
async def list_pending_requests(workflow_id: Optional[str] = None):
    """List all pending HITL requests

    Args:
        workflow_id: Optional filter by workflow ID

    Returns:
        List of pending request summaries
    """
    manager = get_hitl_manager()
    requests = manager.get_pending_requests(workflow_id)

    return [
        HITLRequestSummary(
            request_id=req.request_id,
            workflow_id=req.workflow_id,
            stage_id=req.stage_id,
            checkpoint_type=req.checkpoint_type.value,
            title=req.title,
            status=req.status.value,
            priority=req.priority,
            created_at=req.created_at.isoformat()
        )
        for req in requests
    ]


@router.get("/request/{request_id}")
async def get_request(request_id: str):
    """Get details of a specific HITL request

    Args:
        request_id: The request ID

    Returns:
        Full request details
    """
    manager = get_hitl_manager()
    request = manager.get_request(request_id)

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return request.model_dump()


@router.post("/respond/{request_id}")
async def submit_response(request_id: str, response_input: HITLResponseInput):
    """Submit response to a HITL request

    Args:
        request_id: The request ID
        response_input: User's response

    Returns:
        Confirmation of response submission
    """
    manager = get_hitl_manager()

    # Check request exists
    request = manager.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Create response object
    response = HITLResponse(
        request_id=request_id,
        action=response_input.action,
        feedback=response_input.feedback,
        modified_content=response_input.modified_content,
        selected_option=response_input.selected_option,
        retry_instructions=response_input.retry_instructions
    )

    # Submit response
    success = await manager.submit_response(response)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit response")

    return {
        "success": True,
        "request_id": request_id,
        "action": response.action.value,
        "message": "Response submitted successfully"
    }


@router.post("/cancel/{request_id}")
async def cancel_request(request_id: str, reason: Optional[str] = "Cancelled by user"):
    """Cancel a pending HITL request

    Args:
        request_id: The request ID
        reason: Cancellation reason

    Returns:
        Confirmation of cancellation
    """
    manager = get_hitl_manager()

    success = await manager.cancel_request(request_id, reason)

    if not success:
        raise HTTPException(status_code=404, detail="Request not found")

    return {
        "success": True,
        "request_id": request_id,
        "message": "Request cancelled"
    }


@router.post("/cancel/workflow/{workflow_id}")
async def cancel_workflow_requests(workflow_id: str, reason: Optional[str] = "Workflow cancelled"):
    """Cancel all pending requests for a workflow

    Args:
        workflow_id: The workflow ID
        reason: Cancellation reason

    Returns:
        Confirmation of cancellation
    """
    manager = get_hitl_manager()
    await manager.cancel_workflow_requests(workflow_id, reason)

    return {
        "success": True,
        "workflow_id": workflow_id,
        "message": "All workflow requests cancelled"
    }


# ==================== WebSocket Endpoint ====================

@router.websocket("/ws/{workflow_id}")
async def hitl_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time HITL events

    Clients connect to receive HITL events for a specific workflow.
    Events include: hitl.request, hitl.response, hitl.timeout, hitl.cancelled
    """
    await ws_manager.connect(websocket, workflow_id)

    # Set broadcast callback on HITL manager
    manager = get_hitl_manager()
    manager.set_broadcast_callback(ws_manager.broadcast_event)

    try:
        # Send any pending requests for this workflow
        pending = manager.get_pending_requests(workflow_id)
        for request in pending:
            await websocket.send_json({
                "event_type": "hitl.pending",
                "workflow_id": workflow_id,
                "request_id": request.request_id,
                "data": request.model_dump()
            })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle client messages (e.g., submit response via WebSocket)
                if data.get("action") == "respond":
                    response = HITLResponse(
                        request_id=data.get("request_id"),
                        action=HITLAction(data.get("response_action")),
                        feedback=data.get("feedback"),
                        modified_content=data.get("modified_content"),
                        selected_option=data.get("selected_option")
                    )
                    await manager.submit_response(response)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[HITL WS] Error handling message: {e}")

    finally:
        ws_manager.disconnect(websocket, workflow_id)


@router.websocket("/ws")
async def hitl_websocket_global(websocket: WebSocket):
    """Global WebSocket endpoint for all HITL events

    Clients connect to receive HITL events for all workflows.
    """
    await ws_manager.connect(websocket)

    # Set broadcast callback on HITL manager
    manager = get_hitl_manager()
    manager.set_broadcast_callback(ws_manager.broadcast_event)

    try:
        # Send all pending requests
        pending = manager.get_pending_requests()
        for request in pending:
            await websocket.send_json({
                "event_type": "hitl.pending",
                "workflow_id": request.workflow_id,
                "request_id": request.request_id,
                "data": request.model_dump()
            })

        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_json()

                # Handle responses
                if data.get("action") == "respond":
                    response = HITLResponse(
                        request_id=data.get("request_id"),
                        action=HITLAction(data.get("response_action")),
                        feedback=data.get("feedback"),
                        modified_content=data.get("modified_content"),
                        selected_option=data.get("selected_option")
                    )
                    await manager.submit_response(response)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[HITL WS] Error handling message: {e}")

    finally:
        ws_manager.disconnect(websocket)
