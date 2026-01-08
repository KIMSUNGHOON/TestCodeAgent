"""Plan Mode Schemas - Phase 5

Defines data structures for the Plan Mode with Approval Workflow.
Plans are created before code generation and require user approval.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class PlanAction(str, Enum):
    """Types of actions a plan step can perform"""
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    RUN_TESTS = "run_tests"
    RUN_LINT = "run_lint"
    INSTALL_DEPS = "install_deps"
    EXECUTE_CODE = "execute_code"
    REVIEW_CODE = "review_code"
    REFACTOR = "refactor"
    CUSTOM = "custom"


class StepStatus(str, Enum):
    """Status of a plan step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanApprovalStatus(str, Enum):
    """Status of plan approval"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class PlanComplexity(str, Enum):
    """Estimated complexity of a step"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PlanStep:
    """A single step in the execution plan

    Attributes:
        step: Step number (1-indexed)
        action: Type of action to perform
        target: Target file or component
        description: Human-readable description
        requires_approval: If True, pause for user approval before this step
        estimated_complexity: Estimated difficulty level
        dependencies: List of step numbers that must complete first
        status: Current execution status
        output: Result of step execution (if completed)
        error: Error message (if failed)
    """
    step: int
    action: str
    target: str
    description: str
    requires_approval: bool = False
    estimated_complexity: str = "low"
    dependencies: List[int] = field(default_factory=list)
    status: str = "pending"
    output: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "step": self.step,
            "action": self.action,
            "target": self.target,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "estimated_complexity": self.estimated_complexity,
            "dependencies": self.dependencies,
            "status": self.status,
            "output": self.output,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        """Create from dictionary"""
        return cls(
            step=data.get("step", 0),
            action=data.get("action", "custom"),
            target=data.get("target", ""),
            description=data.get("description", ""),
            requires_approval=data.get("requires_approval", False),
            estimated_complexity=data.get("estimated_complexity", "low"),
            dependencies=data.get("dependencies", []),
            status=data.get("status", "pending"),
            output=data.get("output"),
            error=data.get("error"),
        )


@dataclass
class ExecutionPlan:
    """Complete execution plan for a user request

    The plan contains all steps needed to fulfill the user's request,
    organized in execution order with dependencies.

    Attributes:
        plan_id: Unique identifier for this plan
        session_id: Session this plan belongs to
        created_at: ISO timestamp of creation
        user_request: Original user request
        steps: List of plan steps
        estimated_files: List of files that will be affected
        risks: List of potential risks or warnings
        total_steps: Total number of steps
        approval_status: Current approval status
        approved_at: ISO timestamp of approval (if approved)
        approved_by: User who approved (if applicable)
        rejection_reason: Reason for rejection (if rejected)
        modifications: List of modifications made by user
        execution_started_at: When execution started
        execution_completed_at: When execution completed
        current_step: Currently executing step number
    """
    plan_id: str
    session_id: str
    created_at: str
    user_request: str
    steps: List[PlanStep]
    estimated_files: List[str]
    risks: List[str]
    total_steps: int
    approval_status: str = "pending"
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    modifications: List[Dict[str, Any]] = field(default_factory=list)
    execution_started_at: Optional[str] = None
    execution_completed_at: Optional[str] = None
    current_step: int = 0

    @classmethod
    def create(
        cls,
        session_id: str,
        user_request: str,
        steps: List[PlanStep],
        estimated_files: List[str],
        risks: List[str]
    ) -> "ExecutionPlan":
        """Create a new execution plan"""
        return cls(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            created_at=datetime.utcnow().isoformat(),
            user_request=user_request,
            steps=steps,
            estimated_files=estimated_files,
            risks=risks,
            total_steps=len(steps),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "user_request": self.user_request,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_files": self.estimated_files,
            "risks": self.risks,
            "total_steps": self.total_steps,
            "approval_status": self.approval_status,
            "approved_at": self.approved_at,
            "approved_by": self.approved_by,
            "rejection_reason": self.rejection_reason,
            "modifications": self.modifications,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "current_step": self.current_step,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        """Create from dictionary"""
        steps = [PlanStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            plan_id=data.get("plan_id", ""),
            session_id=data.get("session_id", ""),
            created_at=data.get("created_at", ""),
            user_request=data.get("user_request", ""),
            steps=steps,
            estimated_files=data.get("estimated_files", []),
            risks=data.get("risks", []),
            total_steps=data.get("total_steps", len(steps)),
            approval_status=data.get("approval_status", "pending"),
            approved_at=data.get("approved_at"),
            approved_by=data.get("approved_by"),
            rejection_reason=data.get("rejection_reason"),
            modifications=data.get("modifications", []),
            execution_started_at=data.get("execution_started_at"),
            execution_completed_at=data.get("execution_completed_at"),
            current_step=data.get("current_step", 0),
        )

    def approve(self, approved_by: str = "user") -> None:
        """Mark plan as approved"""
        self.approval_status = PlanApprovalStatus.APPROVED.value
        self.approved_at = datetime.utcnow().isoformat()
        self.approved_by = approved_by

    def reject(self, reason: str) -> None:
        """Mark plan as rejected"""
        self.approval_status = PlanApprovalStatus.REJECTED.value
        self.rejection_reason = reason

    def modify(self, new_steps: List[PlanStep], modification_note: str = "") -> None:
        """Update plan with modified steps"""
        self.steps = new_steps
        self.total_steps = len(new_steps)
        self.approval_status = PlanApprovalStatus.MODIFIED.value
        self.modifications.append({
            "timestamp": datetime.utcnow().isoformat(),
            "note": modification_note,
            "step_count": len(new_steps),
        })

    def start_execution(self) -> None:
        """Mark execution as started"""
        self.execution_started_at = datetime.utcnow().isoformat()
        if self.steps:
            self.steps[0].status = StepStatus.IN_PROGRESS.value
            self.current_step = 1

    def complete_step(self, step_num: int, output: str = "") -> None:
        """Mark a step as completed"""
        for step in self.steps:
            if step.step == step_num:
                step.status = StepStatus.COMPLETED.value
                step.output = output
                break

        # Move to next step
        if step_num < self.total_steps:
            self.current_step = step_num + 1
            for step in self.steps:
                if step.step == step_num + 1:
                    step.status = StepStatus.IN_PROGRESS.value
                    break
        else:
            # All steps completed
            self.execution_completed_at = datetime.utcnow().isoformat()

    def fail_step(self, step_num: int, error: str) -> None:
        """Mark a step as failed"""
        for step in self.steps:
            if step.step == step_num:
                step.status = StepStatus.FAILED.value
                step.error = error
                break

    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next pending step"""
        for step in self.steps:
            if step.status == StepStatus.PENDING.value:
                # Check dependencies
                deps_met = all(
                    any(s.step == dep and s.status == StepStatus.COMPLETED.value
                        for s in self.steps)
                    for dep in step.dependencies
                )
                if deps_met or not step.dependencies:
                    return step
        return None

    def get_progress(self) -> Dict[str, Any]:
        """Get execution progress summary"""
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED.value)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED.value)
        in_progress = sum(1 for s in self.steps if s.status == StepStatus.IN_PROGRESS.value)

        return {
            "total_steps": self.total_steps,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": self.total_steps - completed - failed - in_progress,
            "progress_percent": (completed / self.total_steps * 100) if self.total_steps > 0 else 0,
            "current_step": self.current_step,
        }


@dataclass
class PlanGenerationRequest:
    """Request to generate a new plan"""
    user_request: str
    session_id: str
    workspace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class PlanApprovalRequest:
    """Request to approve/reject/modify a plan"""
    plan_id: str
    action: str  # approve, reject, modify
    reason: Optional[str] = None  # For rejection
    modified_steps: Optional[List[Dict[str, Any]]] = None  # For modification
