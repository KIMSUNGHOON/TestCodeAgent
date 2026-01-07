"""Core orchestration components for AI Code Assistance Application

This package contains the Supervisor-led dynamic workflow system:
- supervisor: The Strategist (analyzes, decides, orchestrates)
- workflow: Dynamic DAG builder
- agent_registry: Available agents and their capabilities
"""

from core.supervisor import SupervisorAgent, TaskComplexity, AgentCapability
from core.workflow import DynamicWorkflowBuilder, create_workflow_from_supervisor_analysis
from core.agent_registry import AgentRegistry, AgentInfo, get_registry, reset_registry

__version__ = "1.0.0"

__all__ = [
    # Supervisor
    "SupervisorAgent",
    "TaskComplexity",
    "AgentCapability",
    # Workflow
    "DynamicWorkflowBuilder",
    "create_workflow_from_supervisor_analysis",
    # Agent Registry
    "AgentRegistry",
    "AgentInfo",
    "get_registry",
    "reset_registry",
]
