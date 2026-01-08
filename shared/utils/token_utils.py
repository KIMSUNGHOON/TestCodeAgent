"""Token estimation utilities (Phase 6 Enhanced).

Provides functions to estimate token counts for LLM API calls,
with improved accuracy and context budget management.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported model types with their token limits."""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"
    GPT_35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    GEMINI_PRO = "gemini-pro"
    LLAMA_70B = "llama-70b"
    DEFAULT = "default"


# Model-specific context window sizes
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-3.5-turbo": 16384,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "gemini-pro": 32000,
    "llama-70b": 4096,
    "default": 8000,
}

# Reserved tokens for response generation
MODEL_RESPONSE_RESERVE: Dict[str, int] = {
    "gpt-4": 2048,
    "gpt-4-turbo": 4096,
    "gpt-4o": 4096,
    "gpt-3.5-turbo": 2048,
    "claude-3-opus": 4096,
    "claude-3-sonnet": 4096,
    "claude-3-haiku": 2048,
    "gemini-pro": 2048,
    "llama-70b": 1024,
    "default": 2000,
}


@dataclass
class TokenBudget:
    """Token budget information for context management."""
    total_tokens: int
    max_tokens: int
    available_tokens: int
    within_budget: bool
    overflow: int
    utilization_percent: float
    warnings: List[str]


def estimate_tokens(text: str) -> int:
    """Estimate token count from text (legacy function).

    Rough estimation: ~4 chars per token for English, ~1.5 chars for Korean/CJK.
    Uses a weighted average assuming mixed content.

    Args:
        text: Input text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Count CJK characters (Korean, Chinese, Japanese)
    cjk_count = sum(
        1 for c in text
        if '\u4e00' <= c <= '\u9fff'  # Chinese
        or '\uac00' <= c <= '\ud7af'  # Korean
        or '\u3040' <= c <= '\u30ff'  # Japanese
    )
    ascii_count = len(text) - cjk_count

    # CJK: ~1.5 chars/token, ASCII: ~4 chars/token
    estimated = (cjk_count / 1.5) + (ascii_count / 4)
    return int(estimated)


def count_tokens_accurate(text: str, model: str = "default") -> int:
    """More accurate token counting using word-based estimation.

    This function provides better accuracy than simple character counting
    by considering:
    - Word boundaries and punctuation
    - CJK character handling
    - Code-specific tokenization patterns
    - Special characters and whitespace

    Args:
        text: Input text to count tokens for
        model: Model name for model-specific adjustments

    Returns:
        Estimated token count (more accurate than estimate_tokens)
    """
    if not text:
        return 0

    total_tokens = 0

    # Split into segments for different handling
    # 1. Count CJK characters (each CJK char is typically 1-2 tokens)
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\uac00-\ud7af\u3040-\u30ff]+')
    cjk_matches = cjk_pattern.findall(text)
    for match in cjk_matches:
        # CJK characters: approximately 1.2 tokens per character
        total_tokens += int(len(match) * 1.2)

    # Remove CJK for ASCII processing
    ascii_text = cjk_pattern.sub(' ', text)

    # 2. Handle code blocks specially (code is tokenized differently)
    code_pattern = re.compile(r'```[\s\S]*?```|`[^`]+`')
    code_matches = code_pattern.findall(ascii_text)
    for match in code_matches:
        # Code: approximately 1 token per 3.5 characters
        total_tokens += int(len(match) / 3.5)

    # Remove code for word processing
    text_without_code = code_pattern.sub(' ', ascii_text)

    # 3. Count words and punctuation
    # Split on whitespace and punctuation
    word_pattern = re.compile(r'\b\w+\b')
    words = word_pattern.findall(text_without_code)

    # Count special tokens (punctuation, operators)
    special_pattern = re.compile(r'[^\w\s]')
    specials = special_pattern.findall(text_without_code)

    # Words: ~1.3 tokens per word (subword tokenization)
    total_tokens += int(len(words) * 1.3)

    # Special characters: ~0.5 tokens each (often merged)
    total_tokens += int(len(specials) * 0.5)

    # 4. Add whitespace tokens (newlines, etc.)
    newline_count = text.count('\n')
    total_tokens += newline_count

    # Model-specific adjustments
    if 'claude' in model.lower():
        # Claude tends to tokenize slightly differently
        total_tokens = int(total_tokens * 1.05)
    elif 'gpt' in model.lower():
        # GPT uses BPE, similar to our estimation
        pass

    return max(1, total_tokens)


def count_messages_tokens(messages: List[Dict[str, Any]], model: str = "default") -> int:
    """Count tokens for a list of chat messages.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name for token counting

    Returns:
        Total token count including message overhead
    """
    if not messages:
        return 0

    total = 0
    # Each message has overhead for role and formatting
    message_overhead = 4  # Approximate tokens per message structure

    for msg in messages:
        total += message_overhead
        content = msg.get('content', '')
        if isinstance(content, str):
            total += count_tokens_accurate(content, model)
        elif isinstance(content, list):
            # Handle multi-part content (images, etc.)
            for part in content:
                if isinstance(part, dict) and 'text' in part:
                    total += count_tokens_accurate(part['text'], model)

        # Role token
        role = msg.get('role', '')
        total += count_tokens_accurate(role, model)

    # Conversation overhead
    total += 3  # Every conversation has some fixed overhead

    return total


def check_context_budget(
    context: Dict[str, Any],
    max_tokens: Optional[int] = None,
    model: str = "default"
) -> TokenBudget:
    """Check context against token budget.

    Analyzes the context dictionary and returns detailed budget information
    including warnings for potential issues.

    Args:
        context: Context dictionary with messages, artifacts, etc.
        max_tokens: Maximum allowed tokens (uses model default if not specified)
        model: Model name for limit lookup

    Returns:
        TokenBudget dataclass with detailed budget information
    """
    # Get model-specific limits
    if max_tokens is None:
        context_limit = MODEL_CONTEXT_LIMITS.get(model, MODEL_CONTEXT_LIMITS["default"])
        response_reserve = MODEL_RESPONSE_RESERVE.get(model, MODEL_RESPONSE_RESERVE["default"])
        max_tokens = context_limit - response_reserve

    warnings: List[str] = []
    total_tokens = 0

    # Count message tokens
    messages = context.get('messages', []) or context.get('conversation_history', [])
    if messages:
        messages_tokens = count_messages_tokens(messages, model)
        total_tokens += messages_tokens

        if len(messages) > 50:
            warnings.append(f"Large message count: {len(messages)} messages")

    # Count artifact tokens
    artifacts = context.get('artifacts', [])
    if artifacts:
        for artifact in artifacts:
            content = artifact.get('content', '') if isinstance(artifact, dict) else str(artifact)
            total_tokens += count_tokens_accurate(content, model)

        if len(artifacts) > 20:
            warnings.append(f"Large artifact count: {len(artifacts)} artifacts")

    # Count system prompt tokens
    system_prompt = context.get('system_prompt', '') or context.get('system', '')
    if system_prompt:
        total_tokens += count_tokens_accurate(system_prompt, model)

    # Count other context fields
    for key in ['user_request', 'task_description', 'additional_context']:
        value = context.get(key, '')
        if value:
            total_tokens += count_tokens_accurate(str(value), model)

    # Calculate budget metrics
    within_budget = total_tokens <= max_tokens
    overflow = max(0, total_tokens - max_tokens)
    available = max(0, max_tokens - total_tokens)
    utilization = (total_tokens / max_tokens * 100) if max_tokens > 0 else 0

    # Generate warnings
    if utilization > 90:
        warnings.append(f"High token utilization: {utilization:.1f}%")
    elif utilization > 75:
        warnings.append(f"Moderate token utilization: {utilization:.1f}%")

    if overflow > 0:
        warnings.append(f"Context overflow by {overflow} tokens")

    return TokenBudget(
        total_tokens=total_tokens,
        max_tokens=max_tokens,
        available_tokens=available,
        within_budget=within_budget,
        overflow=overflow,
        utilization_percent=round(utilization, 2),
        warnings=warnings
    )


def truncate_to_budget(
    text: str,
    max_tokens: int,
    model: str = "default",
    preserve_end: bool = False
) -> str:
    """Truncate text to fit within token budget.

    Args:
        text: Text to truncate
        max_tokens: Maximum allowed tokens
        model: Model name for token counting
        preserve_end: If True, preserve end of text instead of beginning

    Returns:
        Truncated text within budget
    """
    if not text:
        return ""

    current_tokens = count_tokens_accurate(text, model)
    if current_tokens <= max_tokens:
        return text

    # Binary search for optimal truncation point
    if preserve_end:
        # Start from end
        lines = text.split('\n')
        result_lines = []
        total = 0

        for line in reversed(lines):
            line_tokens = count_tokens_accurate(line + '\n', model)
            if total + line_tokens <= max_tokens:
                result_lines.insert(0, line)
                total += line_tokens
            else:
                break

        return '\n'.join(result_lines)
    else:
        # Start from beginning
        lines = text.split('\n')
        result_lines = []
        total = 0

        for line in lines:
            line_tokens = count_tokens_accurate(line + '\n', model)
            if total + line_tokens <= max_tokens:
                result_lines.append(line)
                total += line_tokens
            else:
                break

        return '\n'.join(result_lines)


def create_token_usage(prompt_text: str, completion_text: str) -> Dict[str, int]:
    """Create token_usage dict from prompt and completion texts.

    Args:
        prompt_text: The input/prompt text
        completion_text: The output/completion text

    Returns:
        Dict with prompt_tokens, completion_tokens, total_tokens
    """
    prompt_tokens = count_tokens_accurate(prompt_text)
    completion_tokens = count_tokens_accurate(completion_text)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens
    }


def get_model_limits(model: str = "default") -> Dict[str, int]:
    """Get token limits for a specific model.

    Args:
        model: Model name

    Returns:
        Dict with context_limit, response_reserve, and effective_limit
    """
    context_limit = MODEL_CONTEXT_LIMITS.get(model, MODEL_CONTEXT_LIMITS["default"])
    response_reserve = MODEL_RESPONSE_RESERVE.get(model, MODEL_RESPONSE_RESERVE["default"])

    return {
        "context_limit": context_limit,
        "response_reserve": response_reserve,
        "effective_limit": context_limit - response_reserve
    }


def estimate_compression_savings(
    messages: List[Dict[str, Any]],
    compression_ratio: float = 0.3,
    model: str = "default"
) -> Dict[str, int]:
    """Estimate potential token savings from compression.

    Args:
        messages: List of messages to potentially compress
        compression_ratio: Expected compression ratio (0.3 = 70% reduction)
        model: Model name for token counting

    Returns:
        Dict with current_tokens, compressed_tokens, and savings
    """
    current_tokens = count_messages_tokens(messages, model)
    compressed_tokens = int(current_tokens * compression_ratio)
    savings = current_tokens - compressed_tokens

    return {
        "current_tokens": current_tokens,
        "compressed_tokens": compressed_tokens,
        "savings": savings,
        "savings_percent": round((savings / current_tokens * 100) if current_tokens > 0 else 0, 2)
    }
