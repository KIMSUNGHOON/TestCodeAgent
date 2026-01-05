"""LLM Provider Interface - Abstract Base for Model Adapters

This module defines the abstract interface for LLM providers,
enabling seamless switching between different models (DeepSeek, Qwen, GPT, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, AsyncGenerator, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that can be performed by LLM"""
    REASONING = "reasoning"
    CODING = "coding"
    REVIEW = "review"
    REFINE = "refine"
    GENERAL = "general"


@dataclass
class LLMConfig:
    """Configuration for LLM requests"""
    temperature: float = 0.3
    max_tokens: int = 4096
    top_p: float = 0.95
    stop_sequences: List[str] = field(default_factory=lambda: ["</s>"])
    stream: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stop": self.stop_sequences,
            "stream": self.stream,
        }


@dataclass
class LLMResponse:
    """Standardized response from LLM"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict] = None

    # Parsed structured data (if applicable)
    parsed_json: Optional[Dict] = None
    thinking_blocks: Optional[List[str]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers

    All model-specific adapters should inherit from this class
    and implement the abstract methods.
    """

    def __init__(self, endpoint: str, model: str, config: Optional[LLMConfig] = None):
        self.endpoint = endpoint
        self.model = model
        self.config = config or LLMConfig()
        self._client = None

    @property
    @abstractmethod
    def model_type(self) -> str:
        """Return the model type identifier (e.g., 'deepseek', 'qwen', 'gpt')"""
        pass

    @abstractmethod
    def format_prompt(self, prompt: str, task_type: TaskType) -> str:
        """Format prompt according to model's requirements

        Args:
            prompt: The raw prompt text
            task_type: Type of task being performed

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    def format_system_prompt(self, task_type: TaskType) -> str:
        """Get the appropriate system prompt for the task type

        Args:
            task_type: Type of task being performed

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    def parse_response(self, response: str, task_type: TaskType) -> LLMResponse:
        """Parse the raw LLM response into a standardized format

        Args:
            response: Raw response text from LLM
            task_type: Type of task that was performed

        Returns:
            Standardized LLMResponse object
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate a response from the LLM

        Args:
            prompt: The prompt to send to the LLM
            task_type: Type of task being performed
            config_override: Optional config to override defaults

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM

        Args:
            prompt: The prompt to send to the LLM
            task_type: Type of task being performed
            config_override: Optional config to override defaults

        Yields:
            Response chunks as strings
        """
        pass

    def get_config_for_task(self, task_type: TaskType) -> LLMConfig:
        """Get optimal configuration for a specific task type

        Args:
            task_type: Type of task

        Returns:
            LLMConfig optimized for the task
        """
        # Default configurations by task type
        task_configs = {
            TaskType.REASONING: LLMConfig(temperature=0.7, max_tokens=8000),
            TaskType.CODING: LLMConfig(temperature=0.2, max_tokens=4096),
            TaskType.REVIEW: LLMConfig(temperature=0.1, max_tokens=2048),
            TaskType.REFINE: LLMConfig(temperature=0.3, max_tokens=4096),
            TaskType.GENERAL: self.config,
        }
        return task_configs.get(task_type, self.config)

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from response text

        Args:
            text: Response text that may contain JSON

        Returns:
            Parsed JSON dict or None
        """
        import json
        try:
            # Find JSON boundaries
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from response")
        return None


class LLMProviderFactory:
    """Factory for creating LLM provider instances"""

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, model_type: str, provider_class: type):
        """Register a provider class for a model type"""
        cls._providers[model_type] = provider_class

    @classmethod
    def create(
        cls,
        model_type: str,
        endpoint: str,
        model: str,
        config: Optional[LLMConfig] = None
    ) -> BaseLLMProvider:
        """Create a provider instance for the given model type

        Args:
            model_type: Type of model (deepseek, qwen, gpt, generic)
            endpoint: API endpoint URL
            model: Model name/identifier
            config: Optional configuration

        Returns:
            LLM provider instance

        Raises:
            ValueError: If model_type is not registered
        """
        if model_type not in cls._providers:
            # Fallback to generic if specific adapter not found
            if "generic" in cls._providers:
                logger.warning(f"No adapter for '{model_type}', using generic")
                model_type = "generic"
            else:
                raise ValueError(f"Unknown model type: {model_type}")

        return cls._providers[model_type](endpoint, model, config)

    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of registered model types"""
        return list(cls._providers.keys())
