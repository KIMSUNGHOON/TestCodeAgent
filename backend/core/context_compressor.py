"""Context Compressor - Smart Context Management (Phase 6).

This module provides intelligent context compression to manage
large conversation histories efficiently while preserving important
information like code, errors, and decision points.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# Import token utilities (will be available in shared.utils)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from shared.utils.token_utils import (
        count_tokens_accurate,
        count_messages_tokens,
        check_context_budget,
        TokenBudget
    )
except ImportError:
    # Fallback for testing
    def count_tokens_accurate(text: str, model: str = "default") -> int:
        return len(text) // 4

    def count_messages_tokens(messages: List[Dict], model: str = "default") -> int:
        return sum(count_tokens_accurate(m.get('content', '')) for m in messages)

logger = logging.getLogger(__name__)


class ContentPriority(Enum):
    """Content priority levels for compression decisions."""
    CRITICAL = 1    # Never compress: errors, security issues
    HIGH = 2        # Preserve fully: code blocks, file paths
    MEDIUM = 3      # Preserve summary: decisions, explanations
    LOW = 4         # Can be compressed: casual conversation


@dataclass
class ExtractedContent:
    """Container for extracted important content from messages."""
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    file_paths: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)

    def to_summary(self) -> str:
        """Convert extracted content to a summary string."""
        parts = []

        if self.file_paths:
            parts.append(f"Files referenced: {', '.join(self.file_paths[:10])}")

        if self.error_messages:
            parts.append(f"Errors encountered: {len(self.error_messages)} issues")
            for error in self.error_messages[:3]:
                parts.append(f"  - {error[:200]}")

        if self.code_blocks:
            parts.append(f"Code blocks: {len(self.code_blocks)} snippets")
            for block in self.code_blocks[:2]:
                lang = block.get('language', 'text')
                preview = block.get('content', '')[:100]
                parts.append(f"  - [{lang}] {preview}...")

        if self.decisions:
            parts.append("Key decisions:")
            for decision in self.decisions[:5]:
                parts.append(f"  - {decision}")

        if self.commands:
            parts.append(f"Commands executed: {', '.join(self.commands[:5])}")

        if self.key_points:
            parts.append("Key points:")
            for point in self.key_points[:5]:
                parts.append(f"  - {point}")

        return "\n".join(parts) if parts else "No significant content extracted"


@dataclass
class CompressionConfig:
    """Configuration for context compression."""
    # Sliding window settings
    recent_message_count: int = 20          # Keep last N messages uncompressed
    summary_max_tokens: int = 1000          # Max tokens for compressed summary

    # Content extraction settings
    max_code_blocks: int = 10               # Max code blocks to preserve
    max_file_paths: int = 20                # Max file paths to preserve
    max_errors: int = 10                    # Max error messages to preserve

    # Compression thresholds
    compression_threshold: int = 50         # Start compression after N messages
    message_content_limit: int = 2000       # Max chars per message in compressed history

    # Model settings
    model: str = "default"                  # Model for token counting


class ContextCompressor:
    """Smart context compression engine.

    Compresses conversation history while preserving important information
    like code blocks, error messages, file references, and key decisions.
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        """Initialize the compressor.

        Args:
            config: Compression configuration
        """
        self.config = config or CompressionConfig()
        logger.info("ContextCompressor initialized")

    def compress(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Compress a list of messages to fit within token budget.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum allowed tokens (uses config if not specified)

        Returns:
            Compressed list of messages
        """
        if not messages:
            return []

        # If below threshold, no compression needed
        if len(messages) <= self.config.compression_threshold:
            return messages

        logger.info(f"Compressing {len(messages)} messages")

        # Create sliding window
        return self.create_sliding_window(
            messages,
            recent_count=self.config.recent_message_count,
            max_summary_tokens=max_tokens or self.config.summary_max_tokens
        )

    def extract_important_content(
        self,
        message: Dict[str, Any]
    ) -> Tuple[ExtractedContent, ContentPriority]:
        """Extract important content from a message.

        Identifies and extracts:
        - Code blocks (high priority)
        - File paths (high priority)
        - Error messages (critical priority)
        - Commands (medium priority)
        - Decision statements (medium priority)

        Args:
            message: Message dict with 'role' and 'content'

        Returns:
            Tuple of (ExtractedContent, ContentPriority)
        """
        content = message.get('content', '')
        if not content:
            return ExtractedContent(), ContentPriority.LOW

        extracted = ExtractedContent()
        priority = ContentPriority.LOW

        # 1. Extract code blocks (```...```)
        code_pattern = re.compile(r'```(\w*)\n?([\s\S]*?)```', re.MULTILINE)
        for match in code_pattern.finditer(content):
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            if code:
                extracted.code_blocks.append({
                    'language': language,
                    'content': code
                })
                priority = ContentPriority.HIGH

        # 2. Extract file paths
        file_patterns = [
            r'(?:^|\s)([A-Za-z]:[\\\/][\w\\\/\-\.]+)',  # Windows paths
            r'(?:^|\s)((?:/[\w\-\.]+)+)',               # Unix paths
            r'(?:^|\s)([\w\-]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md|txt|html|css|go|rs|java|c|cpp|h))',  # File extensions
        ]
        for pattern in file_patterns:
            for match in re.finditer(pattern, content):
                path = match.group(1).strip()
                if path and path not in extracted.file_paths:
                    extracted.file_paths.append(path)
                    if priority.value > ContentPriority.HIGH.value:
                        priority = ContentPriority.HIGH

        # 3. Extract error messages
        error_patterns = [
            r'(?i)(error|exception|failed|failure|traceback|warning)[:.\s]+([^\n]+)',
            r'(?i)(TypeError|ValueError|KeyError|AttributeError|ImportError|SyntaxError)[:.\s]*([^\n]*)',
            r'(?i)(?:^|\n)(FAILED|ERROR)[:\s]+([^\n]+)',
        ]
        for pattern in error_patterns:
            for match in re.finditer(pattern, content):
                error_type = match.group(1)
                error_msg = match.group(2).strip() if len(match.groups()) > 1 else ""
                full_error = f"{error_type}: {error_msg}" if error_msg else error_type
                if full_error not in extracted.error_messages:
                    extracted.error_messages.append(full_error)
                    priority = ContentPriority.CRITICAL

        # 4. Extract commands
        command_patterns = [
            r'(?:^|\n)\$\s*([^\n]+)',           # $ command
            r'(?:^|\n)>\s*([^\n]+)',            # > command
            r'`([^`]+)`',                        # Inline code
        ]
        for pattern in command_patterns:
            for match in re.finditer(pattern, content):
                cmd = match.group(1).strip()
                if cmd and len(cmd) < 200 and cmd not in extracted.commands:
                    extracted.commands.append(cmd)
                    if priority.value > ContentPriority.MEDIUM.value:
                        priority = ContentPriority.MEDIUM

        # 5. Extract decision statements
        decision_patterns = [
            r'(?i)(?:^|\n)(?:let\'s|we should|i will|decided to|choosing|using|implementing)([^\n.]+)',
            r'(?i)(?:^|\n)(?:approach|solution|plan|strategy)[:.\s]+([^\n]+)',
        ]
        for pattern in decision_patterns:
            for match in re.finditer(pattern, content):
                decision = match.group(1).strip() if match.groups() else match.group(0).strip()
                if decision and len(decision) > 10 and decision not in extracted.decisions:
                    extracted.decisions.append(decision[:200])
                    if priority.value > ContentPriority.MEDIUM.value:
                        priority = ContentPriority.MEDIUM

        # 6. Extract key points (sentences with important keywords)
        key_patterns = [
            r'(?i)(?:^|\n)(?:important|note|remember|key|summary)[:.\s]+([^\n]+)',
            r'(?i)(?:^|\n)(?:created|modified|deleted|updated)(?:\s+file)?[:.\s]+([^\n]+)',
        ]
        for pattern in key_patterns:
            for match in re.finditer(pattern, content):
                point = match.group(1).strip() if match.groups() else match.group(0).strip()
                if point and point not in extracted.key_points:
                    extracted.key_points.append(point[:200])

        return extracted, priority

    def summarize_messages(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000
    ) -> str:
        """Summarize multiple messages into a compact representation.

        Args:
            messages: List of messages to summarize
            max_tokens: Maximum tokens for the summary

        Returns:
            Summary string
        """
        if not messages:
            return ""

        # Extract important content from all messages
        all_extracted = ExtractedContent()
        priorities = []

        for msg in messages:
            extracted, priority = self.extract_important_content(msg)
            priorities.append(priority)

            # Merge extracted content
            all_extracted.code_blocks.extend(extracted.code_blocks[:self.config.max_code_blocks])
            all_extracted.file_paths.extend(extracted.file_paths[:self.config.max_file_paths])
            all_extracted.error_messages.extend(extracted.error_messages[:self.config.max_errors])
            all_extracted.decisions.extend(extracted.decisions)
            all_extracted.commands.extend(extracted.commands)
            all_extracted.key_points.extend(extracted.key_points)

        # Deduplicate
        all_extracted.file_paths = list(dict.fromkeys(all_extracted.file_paths))[:self.config.max_file_paths]
        all_extracted.error_messages = list(dict.fromkeys(all_extracted.error_messages))[:self.config.max_errors]
        all_extracted.decisions = list(dict.fromkeys(all_extracted.decisions))[:10]
        all_extracted.commands = list(dict.fromkeys(all_extracted.commands))[:10]
        all_extracted.key_points = list(dict.fromkeys(all_extracted.key_points))[:10]

        # Create summary
        summary_parts = [
            f"[Conversation Summary: {len(messages)} messages]",
            f"Time range: {messages[0].get('timestamp', 'unknown')} to {messages[-1].get('timestamp', 'unknown')}",
            "",
            all_extracted.to_summary()
        ]

        # Add brief message overview
        summary_parts.append("\nMessage Overview:")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:100]
            if len(msg.get('content', '')) > 100:
                content += "..."
            summary_parts.append(f"  {i+1}. [{role}] {content}")

            # Limit overview length
            if i >= 9:
                remaining = len(messages) - 10
                if remaining > 0:
                    summary_parts.append(f"  ... and {remaining} more messages")
                break

        summary = "\n".join(summary_parts)

        # Truncate if exceeds token limit
        current_tokens = count_tokens_accurate(summary, self.config.model)
        if current_tokens > max_tokens:
            # Progressively truncate less important parts
            # Remove message overview first
            summary_parts = summary_parts[:4]  # Keep header and extracted content
            summary = "\n".join(summary_parts)

        return summary

    def create_sliding_window(
        self,
        messages: List[Dict[str, Any]],
        recent_count: int = 20,
        max_summary_tokens: int = 1000
    ) -> List[Dict[str, Any]]:
        """Create a sliding window with recent messages and compressed history.

        Args:
            messages: Full message list
            recent_count: Number of recent messages to keep uncompressed
            max_summary_tokens: Max tokens for the history summary

        Returns:
            List with summary message + recent messages
        """
        if len(messages) <= recent_count:
            return messages

        # Split into history and recent
        history_messages = messages[:-recent_count]
        recent_messages = messages[-recent_count:]

        # Compress history into a summary
        summary = self.summarize_messages(history_messages, max_summary_tokens)

        # Create summary message
        summary_message = {
            "role": "system",
            "content": f"[COMPRESSED HISTORY]\n{summary}\n[END COMPRESSED HISTORY]",
            "timestamp": datetime.now().isoformat(),
            "is_compressed": True,
            "original_count": len(history_messages)
        }

        # Return summary + recent messages
        result = [summary_message] + recent_messages

        logger.info(
            f"Created sliding window: {len(history_messages)} messages compressed, "
            f"{len(recent_messages)} recent messages preserved"
        )

        return result

    def get_compression_stats(
        self,
        original_messages: List[Dict[str, Any]],
        compressed_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get statistics about compression results.

        Args:
            original_messages: Original message list
            compressed_messages: Compressed message list

        Returns:
            Dict with compression statistics
        """
        original_tokens = count_messages_tokens(original_messages, self.config.model)
        compressed_tokens = count_messages_tokens(compressed_messages, self.config.model)
        savings = original_tokens - compressed_tokens

        return {
            "original_messages": len(original_messages),
            "compressed_messages": len(compressed_messages),
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "tokens_saved": savings,
            "compression_ratio": round(compressed_tokens / original_tokens, 3) if original_tokens > 0 else 1.0,
            "savings_percent": round((savings / original_tokens * 100), 2) if original_tokens > 0 else 0
        }


# Default compressor instance
_default_compressor: Optional[ContextCompressor] = None


def get_compressor(config: Optional[CompressionConfig] = None) -> ContextCompressor:
    """Get or create default compressor instance.

    Args:
        config: Optional configuration (uses default if not provided)

    Returns:
        ContextCompressor instance
    """
    global _default_compressor

    if config is not None:
        return ContextCompressor(config)

    if _default_compressor is None:
        _default_compressor = ContextCompressor()

    return _default_compressor


def compress_context(
    messages: List[Dict[str, Any]],
    max_tokens: Optional[int] = None,
    recent_count: int = 20
) -> List[Dict[str, Any]]:
    """Convenience function to compress context.

    Args:
        messages: Messages to compress
        max_tokens: Maximum tokens for result
        recent_count: Recent messages to preserve

    Returns:
        Compressed message list
    """
    compressor = get_compressor()
    compressor.config.recent_message_count = recent_count
    return compressor.compress(messages, max_tokens)
