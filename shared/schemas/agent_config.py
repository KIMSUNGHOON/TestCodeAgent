"""Shared agent configuration schemas"""

from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for AI model"""

    model_name: str
    api_endpoint: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    stream: bool = True

    class Config:
        frozen = True


class DeepSeekR1Config(ModelConfig):
    """DeepSeek-R1 specific configuration"""

    model_name: str = "deepseek-reasoner"
    thinking_budget: int = Field(default=32000, description="Tokens for <think> blocks")
    temperature: float = 0.7


class QwenCoderConfig(ModelConfig):
    """Qwen2.5-Coder specific configuration"""

    model_name: str = "qwen2.5-coder-32b-instruct"
    temperature: float = 0.2  # Lower for deterministic code
    auto_execute_tools: bool = True


class AgentRole(BaseModel):
    """Agent role definition"""

    name: str
    model_configuration: ModelConfig  # Renamed to avoid Pydantic reserved field
    system_prompt: str
    capabilities: list[str]


class WorkflowConfig(BaseModel):
    """LangGraph workflow configuration"""

    reasoning_agent: AgentRole
    implementation_agent: AgentRole
    max_iterations: int = 7
    enable_debug: bool = True
    workspace_root: str = "/tmp/workspace"


class DebugConfig(BaseModel):
    """Debug panel configuration"""

    enabled: bool = True
    show_thinking: bool = True  # Show DeepSeek <think> blocks
    show_tool_calls: bool = True  # Show Qwen tool executions
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
