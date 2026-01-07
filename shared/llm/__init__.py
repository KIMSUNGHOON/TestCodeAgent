"""LLM Provider Package

Provides a unified interface for different LLM models.

Usage:
    from shared.llm import LLMProviderFactory, TaskType

    # Create a provider
    provider = LLMProviderFactory.create(
        model_type="deepseek",
        endpoint="http://localhost:8001/v1",
        model="deepseek-ai/DeepSeek-R1"
    )

    # Generate response
    response = await provider.generate(
        prompt="Create a calculator app",
        task_type=TaskType.CODING
    )
"""

from .base import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    TaskType,
    LLMProviderFactory,
)

# Import adapters to register them
from .adapters import (
    GenericAdapter,
    DeepSeekAdapter,
    QwenAdapter,
)

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "LLMConfig",
    "LLMResponse",
    "TaskType",
    "LLMProviderFactory",
    # Adapters
    "GenericAdapter",
    "DeepSeekAdapter",
    "QwenAdapter",
]


def get_provider_for_settings():
    """Create LLM provider based on application settings

    Returns:
        BaseLLMProvider instance configured from settings
    """
    from app.core.config import settings

    return LLMProviderFactory.create(
        model_type=settings.model_type,
        endpoint=settings.get_coding_endpoint,
        model=settings.get_coding_model,
    )
