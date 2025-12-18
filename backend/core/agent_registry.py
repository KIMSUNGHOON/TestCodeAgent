"""Agent Registry - Catalog of Available Agents and Capabilities

This module maintains the mapping between agent capabilities and
their actual implementations. The Supervisor uses this registry to
determine which agents to include in the dynamic workflow.
"""

import logging
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Information about an available agent"""

    name: str
    capability: str
    description: str
    node_function: Callable
    model: str  # "deepseek-r1" or "qwen-coder"
    required_for: List[str]  # Task types that require this agent
    optional_for: List[str]  # Task types where this is optional
    dependencies: List[str]  # Other capabilities this depends on


class AgentRegistry:
    """Registry of all available agents and their capabilities

    The Supervisor queries this registry to determine which agents
    are available and what they can do.
    """

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._capability_map: Dict[str, List[str]] = {}
        self._initialized = False
        logger.info("🗂️ Agent Registry created (lazy initialization)")

    def _ensure_initialized(self):
        """Ensure registry is initialized (lazy loading)"""
        if not self._initialized:
            self._initialize_registry()
            self._initialized = True
            logger.info(f"📚 Agent Registry initialized with {len(self._agents)} agents")

    def _initialize_registry(self):
        """Initialize registry with all available agents"""

        # Import all node functions (lazy)
        from app.agent.langgraph.nodes.coder import coder_node
        from app.agent.langgraph.nodes.reviewer import reviewer_node
        from app.agent.langgraph.nodes.refiner import refiner_node
        from app.agent.langgraph.nodes.rca_analyzer import rca_analyzer_node
        from app.agent.langgraph.nodes.security_gate import security_gate_node
        from app.agent.langgraph.nodes.qa_gate import qa_gate_node
        from app.agent.langgraph.nodes.aggregator import aggregator_node
        from app.agent.langgraph.nodes.persistence import persistence_node

        # Register all agents
        agents = [
            AgentInfo(
                name="coder",
                capability="implementation",
                description="Implements code using Qwen2.5-Coder",
                node_function=coder_node,
                model="qwen-coder",
                required_for=["implementation", "general"],
                optional_for=["review", "testing"],
                dependencies=[]
            ),
            AgentInfo(
                name="reviewer",
                capability="review",
                description="Reviews code quality and provides feedback",
                node_function=reviewer_node,
                model="qwen-coder",
                required_for=["review", "implementation"],
                optional_for=["testing", "security_audit"],
                dependencies=["implementation"]
            ),
            AgentInfo(
                name="refiner",
                capability="refinement",
                description="Refines code based on review feedback",
                node_function=refiner_node,
                model="qwen-coder",
                required_for=["implementation"],
                optional_for=["review"],
                dependencies=["implementation", "review"]
            ),
            AgentInfo(
                name="rca_analyzer",
                capability="root_cause_analysis",
                description="Analyzes why refinement is failing using DeepSeek-R1",
                node_function=rca_analyzer_node,
                model="deepseek-r1",
                required_for=[],
                optional_for=["implementation", "review"],
                dependencies=["review"]
            ),
            AgentInfo(
                name="security_gate",
                capability="security",
                description="Performs security analysis and vulnerability detection",
                node_function=security_gate_node,
                model="qwen-coder",
                required_for=["security_audit"],
                optional_for=["implementation"],
                dependencies=["implementation"]
            ),
            AgentInfo(
                name="qa_gate",
                capability="testing",
                description="Runs tests and validates code quality",
                node_function=qa_gate_node,
                model="qwen-coder",
                required_for=["testing"],
                optional_for=["implementation", "review"],
                dependencies=["implementation"]
            ),
            AgentInfo(
                name="aggregator",
                capability="aggregation",
                description="Aggregates quality gate results and makes decisions",
                node_function=aggregator_node,
                model="qwen-coder",
                required_for=["review", "testing", "security_audit"],
                optional_for=["implementation"],
                dependencies=["review"]
            ),
            AgentInfo(
                name="persistence",
                capability="persistence",
                description="Persists final artifacts and metadata",
                node_function=persistence_node,
                model="qwen-coder",
                required_for=[],
                optional_for=["implementation", "review"],
                dependencies=[]
            ),
        ]

        for agent in agents:
            self.register_agent(agent)

    def register_agent(self, agent: AgentInfo):
        """Register an agent in the registry"""
        self._agents[agent.name] = agent

        # Update capability map
        if agent.capability not in self._capability_map:
            self._capability_map[agent.capability] = []
        self._capability_map[agent.capability].append(agent.name)

        logger.debug(f"   Registered: {agent.name} ({agent.capability})")

    def get_agent(self, name: str) -> Optional[AgentInfo]:
        """Get agent by name"""
        self._ensure_initialized()
        return self._agents.get(name)

    def get_agents_by_capability(self, capability: str) -> List[AgentInfo]:
        """Get all agents that provide a specific capability"""
        self._ensure_initialized()
        agent_names = self._capability_map.get(capability, [])
        return [self._agents[name] for name in agent_names]

    def get_required_agents(self, task_type: str) -> List[str]:
        """Get list of required agent capabilities for a task type

        Args:
            task_type: Type of task (implementation, review, testing, etc.)

        Returns:
            List of required capability names
        """
        self._ensure_initialized()
        required = []
        for agent in self._agents.values():
            if task_type in agent.required_for:
                required.append(agent.capability)

        logger.info(f"📋 Required agents for '{task_type}': {required}")
        return required

    def get_optional_agents(self, task_type: str) -> List[str]:
        """Get list of optional agent capabilities for a task type"""
        self._ensure_initialized()
        optional = []
        for agent in self._agents.values():
            if task_type in agent.optional_for:
                optional.append(agent.capability)

        logger.debug(f"   Optional agents for '{task_type}': {optional}")
        return optional

    def resolve_dependencies(self, capabilities: List[str]) -> List[str]:
        """Resolve agent dependencies

        Given a list of capabilities, returns complete list including
        all dependencies in correct execution order.

        Args:
            capabilities: List of requested capabilities

        Returns:
            Ordered list of capabilities including dependencies
        """
        self._ensure_initialized()
        resolved = []
        visited = set()

        def _resolve(capability: str):
            if capability in visited:
                return
            visited.add(capability)

            # Get agents for this capability
            agents = self.get_agents_by_capability(capability)
            if not agents:
                logger.warning(f"⚠️ No agent found for capability: {capability}")
                return

            # Resolve dependencies first
            agent = agents[0]  # Use first agent
            for dep in agent.dependencies:
                _resolve(dep)

            # Add this capability
            if capability not in resolved:
                resolved.append(capability)

        for cap in capabilities:
            _resolve(cap)

        logger.info(f"🔗 Resolved dependencies: {capabilities} → {resolved}")
        return resolved

    def get_model_for_capability(self, capability: str) -> Optional[str]:
        """Get which model handles a specific capability

        Returns:
            "deepseek-r1" or "qwen-coder"
        """
        self._ensure_initialized()
        agents = self.get_agents_by_capability(capability)
        if agents:
            return agents[0].model
        return None

    def validate_workflow(self, capabilities: List[str]) -> bool:
        """Validate that a workflow configuration is valid

        Checks:
        1. All capabilities are available
        2. All dependencies are satisfied
        3. No circular dependencies

        Returns:
            True if valid, False otherwise
        """
        self._ensure_initialized()
        # Check all capabilities exist
        for cap in capabilities:
            if cap not in self._capability_map:
                logger.error(f"❌ Invalid capability: {cap}")
                return False

        # Check dependencies are satisfied
        resolved = self.resolve_dependencies(capabilities)
        for cap in capabilities:
            agents = self.get_agents_by_capability(cap)
            if not agents:
                continue

            agent = agents[0]
            for dep in agent.dependencies:
                if dep not in resolved:
                    logger.error(f"❌ Missing dependency: {cap} requires {dep}")
                    return False

        logger.info("✅ Workflow configuration is valid")
        return True

    def get_all_capabilities(self) -> List[str]:
        """Get list of all available capabilities"""
        self._ensure_initialized()
        return list(self._capability_map.keys())

    def get_statistics(self) -> Dict:
        """Get registry statistics"""
        self._ensure_initialized()
        deepseek_agents = [a for a in self._agents.values() if a.model == "deepseek-r1"]
        qwen_agents = [a for a in self._agents.values() if a.model == "qwen-coder"]

        return {
            "total_agents": len(self._agents),
            "total_capabilities": len(self._capability_map),
            "deepseek_agents": len(deepseek_agents),
            "qwen_agents": len(qwen_agents),
            "agents": list(self._agents.keys()),
            "capabilities": list(self._capability_map.keys()),
        }

    def print_registry(self):
        """Print registry contents for debugging"""
        self._ensure_initialized()
        stats = self.get_statistics()

        print("\n" + "=" * 60)
        print("📚 AGENT REGISTRY")
        print("=" * 60)
        print(f"Total Agents: {stats['total_agents']}")
        print(f"Total Capabilities: {stats['total_capabilities']}")
        print(f"DeepSeek-R1 Agents: {stats['deepseek_agents']}")
        print(f"Qwen-Coder Agents: {stats['qwen_agents']}")
        print("\n" + "-" * 60)
        print("AGENTS:")
        print("-" * 60)

        for name, agent in self._agents.items():
            print(f"\n{name.upper()}")
            print(f"  Capability: {agent.capability}")
            print(f"  Model: {agent.model}")
            print(f"  Description: {agent.description}")
            print(f"  Required for: {', '.join(agent.required_for) or 'None'}")
            print(f"  Optional for: {', '.join(agent.optional_for) or 'None'}")
            print(f"  Dependencies: {', '.join(agent.dependencies) or 'None'}")

        print("\n" + "=" * 60 + "\n")


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get global agent registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


def reset_registry():
    """Reset global registry (for testing)"""
    global _global_registry
    _global_registry = None
