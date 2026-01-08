"""Plan Mode API Routes (Phase 5)

REST API endpoints for Plan Mode with Approval Workflow.
Enables generating, reviewing, approving, and executing structured plans.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.agent.handlers.planning import PlanningHandler
from app.agent.langgraph.schemas.plan import (
    ExecutionPlan,
    PlanStep,
    PlanApprovalStatus,
    StepStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plan", tags=["Plan Mode"])


# ==================== In-Memory Plan Storage ====================
# In production, this should be replaced with database storage

class PlanStore:
    """Simple in-memory store for execution plans"""

    def __init__(self):
        self._plans: Dict[str, ExecutionPlan] = {}

    def save(self, plan: ExecutionPlan) -> None:
        """Save a plan to the store"""
        self._plans[plan.plan_id] = plan

    def get(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Retrieve a plan by ID"""
        return self._plans.get(plan_id)

    def get_by_session(self, session_id: str) -> List[ExecutionPlan]:
        """Get all plans for a session"""
        return [p for p in self._plans.values() if p.session_id == session_id]

    def delete(self, plan_id: str) -> bool:
        """Delete a plan"""
        if plan_id in self._plans:
            del self._plans[plan_id]
            return True
        return False

    def list_all(self) -> List[ExecutionPlan]:
        """List all plans"""
        return list(self._plans.values())


# Global plan store
plan_store = PlanStore()


# ==================== Request/Response Models ====================

class PlanGenerateRequest(BaseModel):
    """Request to generate a new plan"""
    message: str
    session_id: str
    workspace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PlanStepInput(BaseModel):
    """Input model for a plan step"""
    step: int
    action: str
    target: str
    description: str
    requires_approval: bool = False
    estimated_complexity: str = "low"
    dependencies: List[int] = []


class PlanModifyRequest(BaseModel):
    """Request to modify a plan"""
    steps: List[PlanStepInput]
    modification_note: Optional[str] = ""


class PlanRejectRequest(BaseModel):
    """Request to reject a plan"""
    reason: str


class PlanSummary(BaseModel):
    """Summary of a plan for listing"""
    plan_id: str
    session_id: str
    user_request: str
    total_steps: int
    approval_status: str
    created_at: str
    progress_percent: float = 0.0


# ==================== REST Endpoints ====================

@router.post("/generate", response_model=Dict[str, Any])
async def generate_plan(request: PlanGenerateRequest):
    """Generate a new execution plan

    Creates a structured plan based on the user's request.
    The plan must be approved before execution.

    Args:
        request: Plan generation request

    Returns:
        Generated execution plan
    """
    try:
        logger.info(f"Generating plan for session {request.session_id}: {request.message[:50]}...")

        # Create planning handler
        handler = PlanningHandler()

        # Build analysis context (simplified for plan generation)
        analysis = {
            "complexity": "moderate",
            "task_type": "implementation",
            "response_type": "planning",
        }

        # Add context if provided
        context = request.context if request.context else {}
        if request.workspace:
            context["workspace"] = request.workspace

        # Generate structured plan
        plan = await handler.generate_structured_plan(
            user_message=request.message,
            session_id=request.session_id,
            analysis=analysis,
            context=context
        )

        # Save to store
        plan_store.save(plan)

        logger.info(f"Plan generated: {plan.plan_id} with {plan.total_steps} steps")

        return {
            "success": True,
            "plan": plan.to_dict(),
            "message": f"Plan generated with {plan.total_steps} steps"
        }

    except Exception as e:
        logger.error(f"Failed to generate plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}", response_model=Dict[str, Any])
async def get_plan(plan_id: str):
    """Get details of a specific plan

    Args:
        plan_id: The plan ID

    Returns:
        Full plan details including steps and progress
    """
    plan = plan_store.get(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "success": True,
        "plan": plan.to_dict(),
        "progress": plan.get_progress()
    }


@router.get("/session/{session_id}", response_model=List[PlanSummary])
async def list_session_plans(session_id: str):
    """List all plans for a session

    Args:
        session_id: The session ID

    Returns:
        List of plan summaries
    """
    plans = plan_store.get_by_session(session_id)

    return [
        PlanSummary(
            plan_id=p.plan_id,
            session_id=p.session_id,
            user_request=p.user_request[:100],
            total_steps=p.total_steps,
            approval_status=p.approval_status,
            created_at=p.created_at,
            progress_percent=p.get_progress()["progress_percent"]
        )
        for p in plans
    ]


@router.post("/{plan_id}/approve", response_model=Dict[str, Any])
async def approve_plan(plan_id: str):
    """Approve a plan for execution

    Changes the plan status to approved, allowing execution to begin.

    Args:
        plan_id: The plan ID

    Returns:
        Confirmation of approval
    """
    plan = plan_store.get(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.approval_status != PlanApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Plan cannot be approved (current status: {plan.approval_status})"
        )

    plan.approve()
    plan_store.save(plan)

    logger.info(f"Plan approved: {plan_id}")

    return {
        "success": True,
        "plan_id": plan_id,
        "status": plan.approval_status,
        "message": "Plan approved successfully"
    }


@router.post("/{plan_id}/modify", response_model=Dict[str, Any])
async def modify_plan(plan_id: str, request: PlanModifyRequest):
    """Modify a plan's steps

    Allows the user to adjust steps before approval.

    Args:
        plan_id: The plan ID
        request: Modified steps

    Returns:
        Updated plan
    """
    plan = plan_store.get(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Convert input to PlanStep objects
    new_steps = [
        PlanStep(
            step=s.step,
            action=s.action,
            target=s.target,
            description=s.description,
            requires_approval=s.requires_approval,
            estimated_complexity=s.estimated_complexity,
            dependencies=s.dependencies
        )
        for s in request.steps
    ]

    plan.modify(new_steps, request.modification_note or "")
    plan_store.save(plan)

    logger.info(f"Plan modified: {plan_id}, {len(new_steps)} steps")

    return {
        "success": True,
        "plan": plan.to_dict(),
        "message": "Plan modified successfully"
    }


@router.post("/{plan_id}/reject", response_model=Dict[str, Any])
async def reject_plan(plan_id: str, request: PlanRejectRequest):
    """Reject a plan

    Marks the plan as rejected and records the reason.

    Args:
        plan_id: The plan ID
        request: Rejection reason

    Returns:
        Confirmation of rejection
    """
    plan = plan_store.get(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.reject(request.reason)
    plan_store.save(plan)

    logger.info(f"Plan rejected: {plan_id}, reason: {request.reason}")

    return {
        "success": True,
        "plan_id": plan_id,
        "status": plan.approval_status,
        "message": "Plan rejected"
    }


@router.post("/{plan_id}/execute", response_model=Dict[str, Any])
async def start_execution(plan_id: str, background_tasks: BackgroundTasks):
    """Start executing an approved plan

    Begins step-by-step execution of the plan.
    Use GET /plan/{plan_id}/status to monitor progress.

    Args:
        plan_id: The plan ID

    Returns:
        Execution start confirmation
    """
    plan = plan_store.get(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.approval_status != PlanApprovalStatus.APPROVED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Plan must be approved before execution (current: {plan.approval_status})"
        )

    if plan.execution_started_at:
        raise HTTPException(status_code=400, detail="Plan execution already started")

    plan.start_execution()
    plan_store.save(plan)

    logger.info(f"Plan execution started: {plan_id}")

    return {
        "success": True,
        "plan_id": plan_id,
        "message": "Execution started",
        "progress": plan.get_progress()
    }


@router.get("/{plan_id}/execute/stream")
async def execute_stream(plan_id: str):
    """Stream plan execution progress

    Returns a Server-Sent Events stream with execution updates.

    Args:
        plan_id: The plan ID

    Returns:
        SSE stream with execution progress
    """
    plan = plan_store.get(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    async def generate_events():
        """Generate SSE events for execution progress"""
        # This is a placeholder - actual execution would be handled
        # by the plan_executor node
        yield f"data: {json.dumps({'type': 'start', 'plan_id': plan_id})}\n\n"

        for step in plan.steps:
            yield f"data: {json.dumps({'type': 'step_start', 'step': step.step, 'description': step.description})}\n\n"

            # Simulate execution (actual implementation would execute the step)
            plan.complete_step(step.step, f"Step {step.step} completed")
            plan_store.save(plan)

            yield f"data: {json.dumps({'type': 'step_complete', 'step': step.step, 'progress': plan.get_progress()})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'plan_id': plan_id, 'progress': plan.get_progress()})}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/{plan_id}/status", response_model=Dict[str, Any])
async def get_execution_status(plan_id: str):
    """Get current execution status of a plan

    Args:
        plan_id: The plan ID

    Returns:
        Current execution status and progress
    """
    plan = plan_store.get(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    progress = plan.get_progress()

    return {
        "success": True,
        "plan_id": plan_id,
        "approval_status": plan.approval_status,
        "execution_started_at": plan.execution_started_at,
        "execution_completed_at": plan.execution_completed_at,
        "current_step": plan.current_step,
        "progress": progress,
        "steps": [s.to_dict() for s in plan.steps]
    }


@router.delete("/{plan_id}", response_model=Dict[str, Any])
async def delete_plan(plan_id: str):
    """Delete a plan

    Args:
        plan_id: The plan ID

    Returns:
        Confirmation of deletion
    """
    success = plan_store.delete(plan_id)

    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    logger.info(f"Plan deleted: {plan_id}")

    return {
        "success": True,
        "plan_id": plan_id,
        "message": "Plan deleted"
    }


@router.get("/", response_model=List[PlanSummary])
async def list_all_plans():
    """List all plans

    Returns:
        List of all plan summaries
    """
    plans = plan_store.list_all()

    return [
        PlanSummary(
            plan_id=p.plan_id,
            session_id=p.session_id,
            user_request=p.user_request[:100],
            total_steps=p.total_steps,
            approval_status=p.approval_status,
            created_at=p.created_at,
            progress_percent=p.get_progress()["progress_percent"]
        )
        for p in plans
    ]
