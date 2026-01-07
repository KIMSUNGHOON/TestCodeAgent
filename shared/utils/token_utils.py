"""Token estimation utilities.

Provides functions to estimate token counts for LLM API calls.
"""

from typing import Dict


def estimate_tokens(text: str) -> int:
    """Estimate token count from text.

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


def create_token_usage(prompt_text: str, completion_text: str) -> Dict[str, int]:
    """Create token_usage dict from prompt and completion texts.

    Args:
        prompt_text: The input/prompt text
        completion_text: The output/completion text

    Returns:
        Dict with prompt_tokens, completion_tokens, total_tokens
    """
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = estimate_tokens(completion_text)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens
    }
