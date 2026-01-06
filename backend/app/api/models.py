"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Role of the message sender (user/assistant/system)")
    content: str = Field(..., description="Content of the message")


class ArtifactContext(BaseModel):
    """Artifact context for continuing work."""
    filename: str = Field(..., description="Artifact filename")
    language: str = Field(..., description="Programming language")
    content: str = Field(..., description="Artifact content")


class ConversationContext(BaseModel):
    """Context from previous conversation turns."""
    messages: List[ChatMessage] = Field(default_factory=list, description="Previous messages")
    artifacts: List[ArtifactContext] = Field(default_factory=list, description="Generated artifacts")
    last_task_type: Optional[str] = Field(None, description="Last detected task type")
    review_status: Optional[str] = Field(None, description="Last review status")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    session_id: str = Field(default="default", description="Session identifier")
    task_type: str = Field(default="coding", description="Task type (reasoning/coding)")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt")
    stream: bool = Field(default=False, description="Whether to stream the response")
    context: Optional[ConversationContext] = Field(None, description="Previous conversation context")
    workspace: Optional[str] = Field(None, description="Workspace directory for file operations")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session identifier")
    task_type: str = Field(..., description="Task type used")


class AgentStatus(BaseModel):
    """Agent status model."""
    session_id: str = Field(..., description="Session identifier")
    message_count: int = Field(..., description="Number of messages in history")
    history: List[ChatMessage] = Field(..., description="Conversation history")


class ModelInfo(BaseModel):
    """Model information."""
    name: str = Field(..., description="Model name")
    endpoint: str = Field(..., description="Model endpoint")
    type: str = Field(..., description="Model type (reasoning/coding)")


class ModelsResponse(BaseModel):
    """Models list response."""
    models: List[ModelInfo] = Field(..., description="Available models")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class ArtifactInfo(BaseModel):
    """Artifact information model."""
    filename: str = Field(..., description="Artifact filename")
    language: str = Field(default="text", description="Programming language")
    content: Optional[str] = Field(None, description="Artifact content (may be omitted for large files)")
    saved_path: Optional[str] = Field(None, description="Path where artifact was saved")
    size: Optional[int] = Field(None, description="File size in bytes")


class AnalysisSummary(BaseModel):
    """Supervisor analysis summary."""
    complexity: Optional[str] = Field(None, description="Task complexity: simple, moderate, complex, critical")
    task_type: Optional[str] = Field(None, description="Task type: implementation, review, testing, etc.")
    required_agents: List[str] = Field(default_factory=list, description="Required agent capabilities")
    confidence: Optional[float] = Field(None, description="Analysis confidence score (0-1)")
    workflow_strategy: Optional[str] = Field(None, description="Workflow strategy: linear, parallel_gates, etc.")


class UnifiedChatResponse(BaseModel):
    """Unified chat response model.

    This is the standard response format for all chat endpoints.
    It provides structured information about the response type,
    generated artifacts, and suggested next actions.
    """
    response_type: str = Field(
        ...,
        description="Response type: quick_qa, planning, code_generation, code_review, debugging"
    )
    content: str = Field(..., description="User-friendly response content")
    artifacts: List[ArtifactInfo] = Field(
        default_factory=list,
        description="Generated artifacts (code files, etc.)"
    )
    plan_file: Optional[str] = Field(
        None,
        description="Path to saved plan file (for planning responses)"
    )
    analysis: Optional[AnalysisSummary] = Field(
        None,
        description="Supervisor analysis summary"
    )
    next_actions: List[str] = Field(
        default_factory=list,
        description="Suggested next actions for the user"
    )
    session_id: str = Field(..., description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata (tokens used, latency, etc.)"
    )
    success: bool = Field(default=True, description="Whether the request was successful")
    error: Optional[str] = Field(None, description="Error message if request failed")


class StreamUpdate(BaseModel):
    """Streaming update model for real-time progress."""
    agent: str = Field(..., description="Agent name producing the update")
    update_type: str = Field(
        ...,
        description="Update type: thinking, artifact, progress, completed, error"
    )
    status: str = Field(..., description="Status: running, completed, error")
    message: str = Field(..., description="Human-readable status message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional update data")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
