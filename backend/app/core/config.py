"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import List, Literal, Optional


class Settings(BaseSettings):
    """Application settings."""

    # =========================
    # LLM Model Configuration
    # =========================

    # Primary LLM endpoint (used as default for all tasks)
    llm_endpoint: str = "http://localhost:8001/v1"
    llm_model: str = "deepseek-ai/DeepSeek-R1"

    # Model type for prompt selection
    # Options: "deepseek", "qwen", "gpt", "claude", "generic"
    model_type: Literal["deepseek", "qwen", "gpt", "claude", "generic"] = "deepseek"

    # Optional: Task-specific endpoints (override llm_endpoint if set)
    vllm_reasoning_endpoint: Optional[str] = None
    vllm_coding_endpoint: Optional[str] = None

    # Optional: Task-specific models (override llm_model if set)
    reasoning_model: Optional[str] = None
    coding_model: Optional[str] = None

    @property
    def get_reasoning_endpoint(self) -> str:
        """Get endpoint for reasoning tasks."""
        return self.vllm_reasoning_endpoint or self.llm_endpoint

    @property
    def get_coding_endpoint(self) -> str:
        """Get endpoint for coding tasks."""
        return self.vllm_coding_endpoint or self.llm_endpoint

    @property
    def get_reasoning_model(self) -> str:
        """Get model for reasoning tasks."""
        return self.reasoning_model or self.llm_model

    @property
    def get_coding_model(self) -> str:
        """Get model for coding tasks."""
        return self.coding_model or self.llm_model

    # =========================
    # Agent Framework Selection
    # =========================
    # Options: "microsoft", "langchain", "deepagent"
    agent_framework: Literal["microsoft", "langchain", "deepagent"] = "microsoft"

    # Workflow Configuration
    max_review_iterations: int = 3  # Maximum code review/fix iterations

    # =========================
    # API Configuration
    # =========================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
