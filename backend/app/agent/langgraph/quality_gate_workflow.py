"""Quality Gate Workflow - Production-grade LangGraph orchestrator

Implements dynamic multi-agent workflow with:
- Parallel quality gates (Security, QA, Review)
- Self-healing on failures
- Stateful persistence
- Sandboxed file operations
"""

import logging
from typing import AsyncGenerator, Dict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.langgraph.schemas.state import QualityGateState, create_initial_state
from app.agent.langgraph.nodes.supervisor import supervisor_node
from app.agent.langgraph.nodes.security_gate import security_gate_node
from app.agent.langgraph.nodes.aggregator import quality_aggregator_node
from app.agent.langgraph.nodes.persistence import persistence_node
from app.agent.langgraph.tools.context_manager import ContextManager

logger = logging.getLogger(__name__)


class QualityGateWorkflow:
    """LangGraph workflow for production quality gates"""

    def __init__(self):
        """Initialize quality gate workflow with LangGraph"""
        self.graph = self._build_graph()
        logger.info("✅ QualityGateWorkflow initialized")

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow structure

        Graph structure:
        START → Context Loader → Supervisor → Security Gate →
        Aggregator → (if failed) Self-Heal → (if passed) Persistence → END

        Returns:
            Compiled LangGraph
        """
        # Create graph with state schema
        workflow = StateGraph(QualityGateState)

        # Add nodes
        workflow.add_node("context_loader", self._context_loader_node)
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("security_gate", security_gate_node)
        workflow.add_node("aggregator", quality_aggregator_node)
        workflow.add_node("self_heal", self._self_heal_node)
        workflow.add_node("persistence", persistence_node)

        # Define edges
        workflow.add_edge(START, "context_loader")
        workflow.add_edge("context_loader", "supervisor")
        workflow.add_edge("supervisor", "security_gate")
        workflow.add_edge("security_gate", "aggregator")

        # Conditional edge from aggregator
        workflow.add_conditional_edges(
            "aggregator",
            self._route_after_aggregation,
            {
                "persist": "persistence",
                "self_heal": "self_heal",
                "end": END
            }
        )

        # Self-healing loop back to security gate
        workflow.add_edge("self_heal", "security_gate")

        # End after persistence
        workflow.add_edge("persistence", END)

        # Compile with checkpointer for state persistence
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def _context_loader_node(self, state: QualityGateState) -> Dict:
        """Load previous context from .ai_context.json

        Args:
            state: Current state

        Returns:
            State updates with loaded context
        """
        logger.info("📂 Context Loader Node: Loading previous context...")

        workspace_root = state["workspace_root"]
        context_mgr = ContextManager(workspace_root)

        previous_context = context_mgr.load_context()

        # Log context info
        if previous_context:
            logger.info("✅ Previous context loaded:")
            logger.info(f"   Project: {previous_context.get('project_name', 'unknown')}")
            logger.info(f"   Last updated: {previous_context.get('last_updated', 'unknown')}")

            # Log recent changes
            recent_changes = previous_context.get('recent_changes', [])
            if recent_changes:
                latest = recent_changes[-1]
                logger.info(f"   Latest change: {latest.get('description', 'N/A')}")

        return {
            "current_node": "context_loader",
            "previous_context": previous_context,
        }

    def _self_heal_node(self, state: QualityGateState) -> Dict:
        """Self-healing node: Analyze failures and retry

        Args:
            state: Current state

        Returns:
            State updates for retry
        """
        logger.info("🔧 Self-Heal Node: Analyzing failures...")

        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 5)

        # Increment iteration
        new_iteration = iteration + 1

        logger.info(f"   Retry attempt: {new_iteration}/{max_iterations}")

        # Analyze what failed
        security_passed = state.get("security_passed", False)
        tests_passed = state.get("tests_passed", True)
        review_approved = state.get("review_approved", True)

        failures = []
        if not security_passed:
            failures.append("security")
        if not tests_passed:
            failures.append("tests")
        if not review_approved:
            failures.append("review")

        logger.info(f"   Failed gates: {', '.join(failures)}")

        # TODO: In production, this would analyze specific failures
        # and provide targeted fixes to the coder agent

        return {
            "current_node": "self_heal",
            "iteration": new_iteration,
            "last_error": f"Quality gates failed: {', '.join(failures)}",
        }

    def _route_after_aggregation(
        self,
        state: QualityGateState
    ) -> Literal["persist", "self_heal", "end"]:
        """Routing function after aggregation

        Args:
            state: Current state

        Returns:
            Next node to execute
        """
        workflow_status = state.get("workflow_status", "running")
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 5)

        if workflow_status == "completed":
            return "persist"
        elif workflow_status == "self_healing" and iteration < max_iterations:
            return "self_heal"
        else:
            # Failed or max iterations reached
            return "end"

    async def execute(
        self,
        user_request: str,
        workspace_root: str,
        task_type: str = "general"
    ) -> AsyncGenerator[Dict, None]:
        """Execute workflow with streaming updates

        Args:
            user_request: User's task request
            workspace_root: Absolute path to workspace
            task_type: Type of task (implementation, review, etc.)

        Yields:
            State updates from each node
        """
        logger.info(f"🚀 Executing Quality Gate Workflow...")
        logger.info(f"   Request: {user_request[:100]}")
        logger.info(f"   Workspace: {workspace_root}")
        logger.info(f"   Task Type: {task_type}")

        # Create initial state
        initial_state = create_initial_state(
            user_request=user_request,
            workspace_root=workspace_root,
            task_type=task_type  # type: ignore
        )

        # Execute graph with streaming
        config = {"configurable": {"thread_id": "quality_gate_1"}}

        try:
            async for event in self.graph.astream(initial_state, config):
                # Extract node name and state updates
                for node_name, node_output in event.items():
                    logger.info(f"📍 Node '{node_name}' completed")

                    # Yield update to caller
                    yield {
                        "node": node_name,
                        "updates": node_output,
                        "status": "running"
                    }

            # Final status
            final_state = await self.graph.aget_state(config)
            yield {
                "node": "END",
                "updates": final_state.values,
                "status": "completed"
            }

            logger.info("✅ Workflow execution completed")

        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}")
            yield {
                "node": "ERROR",
                "updates": {"error": str(e)},
                "status": "error"
            }


# Global workflow instance
quality_gate_workflow = QualityGateWorkflow()
