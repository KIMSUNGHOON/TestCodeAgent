"""Language detection utilities.

Provides functions to detect the language of text and ensure
response language matches user's input language.
"""

from typing import Literal

Language = Literal["korean", "english"]


def detect_language(text: str) -> Language:
    """Detect if text is primarily Korean or English.

    Uses character analysis to determine the dominant language.
    Korean (Hangul) characters: U+AC00 to U+D7AF

    Args:
        text: Input text to analyze

    Returns:
        "korean" if text contains significant Korean characters, else "english"
    """
    if not text:
        return "english"

    # Count Korean characters (Hangul syllables)
    korean_count = sum(1 for c in text if '\uac00' <= c <= '\ud7af')

    # Count alphabetic characters (for comparison)
    alpha_count = sum(1 for c in text if c.isalpha())

    if alpha_count == 0:
        return "english"

    # If more than 20% of alphabetic characters are Korean, it's Korean
    korean_ratio = korean_count / alpha_count
    return "korean" if korean_ratio > 0.2 else "english"


def get_language_instruction(language: Language) -> str:
    """Get explicit language instruction for prompts.

    Args:
        language: Detected language ("korean" or "english")

    Returns:
        Language instruction string to prepend to prompts
    """
    if language == "korean":
        return """[LANGUAGE INSTRUCTION]
You MUST respond in Korean (한국어).
Do NOT switch to English during your response.
All explanations, comments, and descriptions must be in Korean.
Code comments can be in English for technical accuracy.
[/LANGUAGE INSTRUCTION]

"""
    else:
        return """[LANGUAGE INSTRUCTION]
You MUST respond in English.
Do NOT switch to Korean or other languages during your response.
All explanations, comments, and descriptions must be in English.
[/LANGUAGE INSTRUCTION]

"""


def apply_language_context(prompt: str, user_message: str) -> str:
    """Apply language context to a prompt based on user's message language.

    Args:
        prompt: Original system prompt
        user_message: User's input message (to detect language from)

    Returns:
        Prompt with language instruction prepended
    """
    language = detect_language(user_message)
    instruction = get_language_instruction(language)
    return instruction + prompt
