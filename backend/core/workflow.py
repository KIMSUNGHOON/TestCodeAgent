"""Dynamic Workflow Builder for Supervisor-Led Orchestration

This module constructs LangGraph StateGraph dynamically based on
Supervisor's analysis of task complexity and requirements.

Supports four workflow strategies:
1. linear: Simple sequential execution
2. parallel_gates: Parallel quality gates
3. adaptive_loop: Dynamic refinement with RCA
4. staged_approval: Human approval gates
"""

import logging
from typing import Dict, List, Literal, TYPE_CHECKING
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Note: Node imports are lazy-loaded in _get_nodes() to avoid circular dependencies
if TYPE_CHECKING:
    from app.agent.langgraph.schemas.state import QualityGateState

logger = logging.getLogger(__name__)

WorkflowStrategy = Literal["linear", "parallel_gates", "adaptive_loop", "staged_approval"]


class DynamicWorkflowBuilder:
    """Builds LangGraph workflows dynamically based on Supervisor's strategy

    This is NOT a fixed pipeline - it constructs the appropriate DAG
    based on task complexity and requirements.
    """

    def __init__(self):
        self.memory = MemorySaver()
        self._nodes = None  # Lazy-loaded
        logger.info("🏗️ Dynamic Workflow Builder initialized")

    def _get_nodes(self):
        """Lazy-load node functions to avoid circular imports"""
        if self._nodes is None:
            from app.agent.langgraph.nodes.coder import coder_node
            from app.agent.langgraph.nodes.reviewer import reviewer_node
            from app.agent.langgraph.nodes.refiner import refiner_node
            from app.agent.langgraph.nodes.rca_analyzer import rca_analyzer_node
            from app.agent.langgraph.nodes.security_gate import security_gate_node
            from app.agent.langgraph.nodes.qa_gate import qa_gate_node
            from app.agent.langgraph.nodes.aggregator import aggregator_node
            from app.agent.langgraph.nodes.persistence import persistence_node

            self._nodes = {
                "coder": coder_node,
                "reviewer": reviewer_node,
                "refiner": refiner_node,
                "rca_analyzer": rca_analyzer_node,
                "security_gate": security_gate_node,
                "qa_gate": qa_gate_node,
                "aggregator": aggregator_node,
                "persistence": persistence_node,
            }
        return self._nodes

    def build_workflow(
        self,
        strategy: WorkflowStrategy,
        required_agents: List[str],
        enable_parallel: bool = True,
        requires_approval: bool = False
    ) -> StateGraph:
        """Build workflow graph based on strategy

        Args:
            strategy: Workflow strategy to use
            required_agents: List of required agent capabilities
            enable_parallel: Whether to run gates in parallel
            requires_approval: Whether to include human approval

        Returns:
            Compiled LangGraph StateGraph ready for execution
        """
        logger.info(f"🎯 Building workflow with strategy: {strategy}")
        logger.info(f"   Required agents: {required_agents}")
        logger.info(f"   Parallel execution: {enable_parallel}")
        logger.info(f"   Human approval: {requires_approval}")

        # Select strategy builder
        if strategy == "linear":
            return self._build_linear_workflow(required_agents)
        elif strategy == "parallel_gates":
            return self._build_parallel_gates_workflow(required_agents, enable_parallel)
        elif strategy == "adaptive_loop":
            return self._build_adaptive_loop_workflow(required_agents, enable_parallel)
        elif strategy == "staged_approval":
            return self._build_staged_approval_workflow(required_agents, enable_parallel)
        else:
            raise ValueError(f"Unknown workflow strategy: {strategy}")

    def _build_linear_workflow(self, required_agents: List[str]) -> StateGraph:
        """Build simple linear workflow

        Flow: Coder → Reviewer → Done
        Use case: Simple tasks, quick iterations
        """
        logger.info("📏 Building LINEAR workflow")

        # Lazy-load QualityGateState
        from app.agent.langgraph.schemas.state import QualityGateState

        nodes = self._get_nodes()
        workflow = StateGraph(QualityGateState)

        # Add nodes based on required agents
        workflow.add_node("coder", nodes["coder"])

        if "review" in required_agents:
            workflow.add_node("reviewer", nodes["reviewer"])
            workflow.add_edge("coder", "reviewer")
            workflow.add_edge("reviewer", END)
        else:
            workflow.add_edge("coder", END)

        # Set entry point
        workflow.set_entry_point("coder")

        compiled = workflow.compile(checkpointer=self.memory)
        logger.info("✅ LINEAR workflow compiled")
        return compiled

    def _build_parallel_gates_workflow(
        self,
        required_agents: List[str],
        enable_parallel: bool
    ) -> StateGraph:
        """Build parallel quality gates workflow

        Flow: Coder → [Security || Testing || Review] → Aggregator → Done
        Use case: Moderate complexity, multiple quality checks
        """
        logger.info("🔀 Building PARALLEL GATES workflow")

        # Lazy-load QualityGateState
        from app.agent.langgraph.schemas.state import QualityGateState

        nodes = self._get_nodes()
        workflow = StateGraph(QualityGateState)

        # Core nodes
        workflow.add_node("coder", nodes["coder"])
        workflow.add_node("aggregator", nodes["aggregator"])

        # Quality gate nodes (conditional)
        gates_added = []

        if "security" in required_agents:
            workflow.add_node("security_gate", nodes["security_gate"])
            gates_added.append("security_gate")

        if "testing" in required_agents:
            workflow.add_node("qa_gate", nodes["qa_gate"])
            gates_added.append("qa_gate")

        if "review" in required_agents:
            workflow.add_node("reviewer", nodes["reviewer"])
            gates_added.append("reviewer")

        # Connect coder to all gates
        for gate in gates_added:
            workflow.add_edge("coder", gate)

        # Connect all gates to aggregator
        for gate in gates_added:
            workflow.add_edge(gate, "aggregator")

        # Aggregator decides next step
        workflow.add_conditional_edges(
            "aggregator",
            lambda state: "end" if state.get("review_approved", False) else "refine",
            {
                "end": END,
                "refine": "refiner" if "refinement" in required_agents else END
            }
        )

        # Add refiner if needed
        if "refinement" in required_agents:
            workflow.add_node("refiner", nodes["refiner"])
            workflow.add_edge("refiner", "coder")  # Loop back

        workflow.set_entry_point("coder")

        compiled = workflow.compile(checkpointer=self.memory)
        logger.info("✅ PARALLEL GATES workflow compiled")
        return compiled

    def _build_adaptive_loop_workflow(
        self,
        required_agents: List[str],
        enable_parallel: bool
    ) -> StateGraph:
        """Build adaptive refinement loop workflow with RCA

        Flow: Coder → Review → [RCA → Refiner → loop] OR [Done]
        Use case: Complex tasks requiring iterative refinement

        CRITICAL: Includes RCA analyzer to prevent infinite loops
        """
        logger.info("🔄 Building ADAPTIVE LOOP workflow")

        # Lazy-load QualityGateState
        from app.agent.langgraph.schemas.state import QualityGateState

        nodes = self._get_nodes()
        workflow = StateGraph(QualityGateState)

        # Core nodes
        workflow.add_node("coder", nodes["coder"])
        workflow.add_node("reviewer", nodes["reviewer"])
        workflow.add_node("rca_analyzer", nodes["rca_analyzer"])  # CRITICAL: RCA before refining
        workflow.add_node("refiner", nodes["refiner"])
        workflow.add_node("aggregator", nodes["aggregator"])

        # Optional quality gates
        if "security" in required_agents:
            workflow.add_node("security_gate", nodes["security_gate"])
            workflow.add_edge("coder", "security_gate")
            workflow.add_edge("security_gate", "reviewer")
        else:
            workflow.add_edge("coder", "reviewer")

        if "testing" in required_agents:
            workflow.add_node("qa_gate", nodes["qa_gate"])
            workflow.add_edge("reviewer", "qa_gate")
            workflow.add_edge("qa_gate", "aggregator")
        else:
            workflow.add_edge("reviewer", "aggregator")

        # Aggregator decides: approve OR refine
        workflow.add_conditional_edges(
            "aggregator",
            self._should_refine,
            {
                "approve": END,
                "refine": "rca_analyzer",  # CRITICAL: RCA first, not refiner
                "max_iterations": END
            }
        )

        # RCA → Refiner → Coder (loop)
        workflow.add_edge("rca_analyzer", "refiner")
        workflow.add_edge("refiner", "coder")

        workflow.set_entry_point("coder")

        compiled = workflow.compile(checkpointer=self.memory)
        logger.info("✅ ADAPTIVE LOOP workflow compiled")
        return compiled

    def _build_staged_approval_workflow(
        self,
        required_agents: List[str],
        enable_parallel: bool
    ) -> StateGraph:
        """Build workflow with human approval gates

        Flow: [All Gates] → Human Approval → Persistence → Done
        Use case: Critical/production changes requiring human oversight
        """
        logger.info("👤 Building STAGED APPROVAL workflow")

        # Lazy-load QualityGateState
        from app.agent.langgraph.schemas.state import QualityGateState

        nodes = self._get_nodes()
        workflow = StateGraph(QualityGateState)

        # All standard nodes
        workflow.add_node("coder", nodes["coder"])
        workflow.add_node("security_gate", nodes["security_gate"])
        workflow.add_node("qa_gate", nodes["qa_gate"])
        workflow.add_node("reviewer", nodes["reviewer"])
        workflow.add_node("rca_analyzer", nodes["rca_analyzer"])
        workflow.add_node("refiner", nodes["refiner"])
        workflow.add_node("aggregator", nodes["aggregator"])

        # Human approval node (placeholder - needs UI integration)
        workflow.add_node("human_approval", self._human_approval_node)
        workflow.add_node("persistence", nodes["persistence"])

        # Connect coder to parallel gates
        workflow.add_edge("coder", "security_gate")
        workflow.add_edge("coder", "qa_gate")
        workflow.add_edge("coder", "reviewer")

        # All gates to aggregator
        workflow.add_edge("security_gate", "aggregator")
        workflow.add_edge("qa_gate", "aggregator")
        workflow.add_edge("reviewer", "aggregator")

        # Aggregator decision with RCA
        workflow.add_conditional_edges(
            "aggregator",
            self._should_refine,
            {
                "approve": "human_approval",  # Requires human approval
                "refine": "rca_analyzer",
                "max_iterations": "human_approval"  # Escalate to human
            }
        )

        workflow.add_edge("rca_analyzer", "refiner")
        workflow.add_edge("refiner", "coder")

        # Human approval decision
        workflow.add_conditional_edges(
            "human_approval",
            lambda state: "approved" if state.get("approval_status") == "approved" else "rejected",
            {
                "approved": "persistence",
                "rejected": "rca_analyzer"  # Back to refinement
            }
        )

        workflow.add_edge("persistence", END)

        workflow.set_entry_point("coder")

        compiled = workflow.compile(checkpointer=self.memory)
        logger.info("✅ STAGED APPROVAL workflow compiled")
        return compiled

    # ==================== Decision Functions ====================

    def _should_refine(self, state: "QualityGateState") -> str:
        """Decide if refinement is needed

        Returns:
            - "approve": All gates passed
            - "refine": Issues found, refinement needed
            - "max_iterations": Hit iteration limit
        """
        review_approved = state.get("review_approved", False)
        refinement_iteration = state.get("refinement_iteration", 0)
        max_iterations = state.get("max_iterations", 5)

        # Check iteration limit first
        if refinement_iteration >= max_iterations:
            logger.warning(f"⚠️ Max iterations ({max_iterations}) reached")
            return "max_iterations"

        # Check if approved
        if review_approved:
            logger.info("✅ All gates passed - approving")
            return "approve"

        # Need refinement
        logger.info(f"🔄 Refinement needed (iteration {refinement_iteration}/{max_iterations})")
        return "refine"

    def _human_approval_node(self, state: "QualityGateState") -> Dict:
        """Human approval node

        In production, this would trigger UI notification and wait for
        human decision. For now, it's a placeholder.
        """
        logger.info("👤 Human Approval Required")
        logger.info("   (This would trigger UI notification in production)")

        # Placeholder: Auto-approve for testing
        # In production, this would wait for user input
        return {
            "current_node": "human_approval",
            "workflow_status": "awaiting_approval",
            "approval_status": "pending",
            "approval_message": "Awaiting human review of changes"
        }


def create_workflow_from_supervisor_analysis(analysis: Dict) -> StateGraph:
    """Create workflow from Supervisor's analysis

    This is the main entry point called by the Supervisor Agent.

    Args:
        analysis: Supervisor's analysis containing:
            - workflow_strategy: Strategy to use
            - required_agents: List of needed capabilities
            - requires_human_approval: Whether approval needed

    Returns:
        Compiled LangGraph ready for execution
    """
    builder = DynamicWorkflowBuilder()

    strategy = analysis.get("workflow_strategy", "linear")
    required_agents = analysis.get("required_agents", [])
    requires_approval = analysis.get("requires_human_approval", False)

    # Override strategy if approval required
    if requires_approval:
        strategy = "staged_approval"

    workflow = builder.build_workflow(
        strategy=strategy,
        required_agents=required_agents,
        enable_parallel=True,
        requires_approval=requires_approval
    )

    logger.info(f"🎉 Workflow created successfully with strategy: {strategy}")
    return workflow
