"""Qwen-Coder LLM Adapter

Specialized adapter for Qwen2.5-Coder optimized for code generation tasks.
"""

import logging
import httpx
import asyncio
import time
from typing import Optional, AsyncGenerator

from shared.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    TaskType,
    LLMProviderFactory,
)


def _calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
    """Calculate exponential backoff delay with jitter.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds with jitter
    """
    import random
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter (0.5x to 1.5x)
    jitter = delay * (0.5 + random.random())
    return jitter

logger = logging.getLogger(__name__)


# Qwen-Coder specific system prompts
QWEN_SYSTEM_PROMPTS = {
    TaskType.CODING: """You are Qwen2.5-Coder, a professional software engineer.

ROLE: Expert Code Generator
EXPERTISE: Python, TypeScript, React, FastAPI, System Design

CRITICAL RULES:
1. Generate ONLY executable code - no explanations unless asked
2. ALWAYS include proper error handling
3. ALWAYS add type hints and docstrings
4. Follow PEP 8 for Python, ESLint for TypeScript
5. Create complete, production-ready implementations

SECURITY RULES (MUST FOLLOW):
1. NEVER use eval() or exec() - use ast.literal_eval() for safe parsing
2. NEVER use subprocess with shell=True - use subprocess.run([cmd, arg1, arg2])
3. NEVER use os.system() - use subprocess module instead
4. NEVER hardcode passwords, API keys, or secrets - use environment variables
5. ALWAYS sanitize user inputs before using in file paths or SQL
6. Use parameterized queries for SQL, never string concatenation

OUTPUT: Return code in the specified format without additional commentary.""",

    TaskType.REVIEW: """You are Qwen2.5-Coder performing code review.

Focus on:
1. Correctness - Does the code work?
2. Security - Any vulnerabilities?
3. Performance - Any bottlenecks?
4. Style - Does it follow conventions?
5. Maintainability - Is it readable?

Be specific and actionable in feedback.""",

    TaskType.REFINE: """You are Qwen2.5-Coder fixing code issues.

Rules:
1. Make minimal, targeted changes
2. Preserve existing functionality
3. Fix ALL reported issues
4. Add missing error handling
5. Improve code quality

Return the complete fixed code.""",

    TaskType.GENERAL: """You are Qwen2.5-Coder, an expert programming assistant.

Provide clear, accurate, and complete code solutions.
Focus on practical, working implementations.""",
}


class QwenAdapter(BaseLLMProvider):
    """Adapter for Qwen2.5-Coder model

    Optimized for:
    - Code generation
    - Code review
    - Refactoring
    - Low temperature for consistency
    """

    @property
    def model_type(self) -> str:
        return "qwen"

    def format_system_prompt(self, task_type: TaskType) -> str:
        """Get Qwen-Coder system prompt"""
        return QWEN_SYSTEM_PROMPTS.get(task_type, QWEN_SYSTEM_PROMPTS[TaskType.GENERAL])

    def format_prompt(self, prompt: str, task_type: TaskType) -> str:
        """Format prompt for Qwen-Coder"""
        if task_type == TaskType.CODING:
            return f"""{prompt}

Generate complete, working code. Include all necessary files.
Respond in JSON format:
{{
    "files": [
        {{
            "filename": "example.py",
            "content": "# Complete implementation here",
            "language": "python",
            "description": "Brief description"
        }}
    ]
}}

Code:"""

        elif task_type == TaskType.REVIEW:
            return f"""{prompt}

Provide review in JSON format:
{{
    "approved": true/false,
    "quality_score": 0.0-1.0,
    "issues": ["specific issue 1", "specific issue 2"],
    "suggestions": ["improvement 1", "improvement 2"],
    "critique": "Overall assessment"
}}

Review:"""

        elif task_type == TaskType.REFINE:
            return f"""{prompt}

Apply fixes and return the corrected code.
Maintain the same structure and format as the original.

Fixed code:"""

        else:
            return prompt

    def parse_response(self, response: str, task_type: TaskType) -> LLMResponse:
        """Parse Qwen-Coder response"""
        parsed_json = None

        if task_type in (TaskType.CODING, TaskType.REVIEW):
            parsed_json = self._extract_json(response)

        return LLMResponse(
            content=response,
            model=self.model,
            parsed_json=parsed_json,
        )

    def get_config_for_task(self, task_type: TaskType) -> LLMConfig:
        """Qwen-Coder optimized configurations"""
        configs = {
            TaskType.CODING: LLMConfig(
                temperature=0.2,  # Low for consistent code generation
                max_tokens=8000,
                top_p=0.95,
                stop_sequences=["</s>", "```\n\n", "Human:", "User:"],
            ),
            TaskType.REVIEW: LLMConfig(
                temperature=0.1,  # Very low for consistent reviews
                max_tokens=2048,
                stop_sequences=["</s>", "Human:"],
            ),
            TaskType.REFINE: LLMConfig(
                temperature=0.2,
                max_tokens=4096,
                stop_sequences=["</s>"],
            ),
            TaskType.GENERAL: LLMConfig(
                temperature=0.3,
                max_tokens=4096,
                stop_sequences=["</s>"],
            ),
        }
        return configs.get(task_type, self.config)

    async def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None,
        max_retries: int = 3
    ) -> LLMResponse:
        """Generate response from Qwen-Coder with retry and exponential backoff"""
        config = config_override or self.get_config_for_task(task_type)
        formatted_prompt = self.format_prompt(prompt, task_type)
        system_prompt = self.format_system_prompt(task_type)

        # Log prompt size for debugging
        prompt_tokens_estimate = len(f"{system_prompt}\n\n{formatted_prompt}") // 4
        logger.debug(f"Qwen request: ~{prompt_tokens_estimate} tokens, task={task_type.value}")

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    # Use chat completions format for instruction-tuned models
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": formatted_prompt}
                    ]

                    response = await client.post(
                        f"{self.endpoint}/chat/completions",
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": config.temperature,
                            "max_tokens": config.max_tokens,
                            "top_p": config.top_p,
                            "stop": config.stop_sequences if config.stop_sequences else None,
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # Chat completions returns message.content, not text
                        content = result["choices"][0].get("message", {}).get("content", "")

                        # Retry on empty response with backoff
                        if not content or not content.strip():
                            finish_reason = result.get("choices", [{}])[0].get("finish_reason", "unknown")
                            usage = result.get("usage", {})
                            logger.warning(
                                f"Empty response from Qwen: "
                                f"finish_reason={finish_reason}, "
                                f"prompt_tokens={usage.get('prompt_tokens', 'N/A')}, "
                                f"completion_tokens={usage.get('completion_tokens', 'N/A')}"
                            )

                            if attempt < max_retries:
                                backoff = _calculate_backoff(attempt)
                                logger.warning(f"Retrying in {backoff:.1f}s ({attempt + 1}/{max_retries})...")
                                await asyncio.sleep(backoff)
                                continue
                            else:
                                logger.error("Empty response from Qwen after all retries")
                                return LLMResponse(
                                    content="[LLM returned empty response - please retry]",
                                    model=self.model,
                                    finish_reason=finish_reason,
                                )

                        llm_response = self.parse_response(content, task_type)
                        llm_response.usage = result.get("usage")
                        llm_response.raw_response = result
                        return llm_response
                    else:
                        # Retry on server errors (5xx) with backoff
                        if response.status_code >= 500 and attempt < max_retries:
                            backoff = _calculate_backoff(attempt)
                            logger.warning(f"Qwen server error {response.status_code}, retrying in {backoff:.1f}s...")
                            await asyncio.sleep(backoff)
                            continue
                        logger.error(f"Qwen request failed: {response.status_code}")
                        raise Exception(f"Qwen request failed: {response.status_code}")

            except httpx.TimeoutException:
                if attempt < max_retries:
                    backoff = _calculate_backoff(attempt)
                    logger.warning(f"Qwen request timed out, retrying in {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    continue
                logger.error("Qwen request timed out after all retries")
                raise

        # Should not reach here, but return empty response as fallback
        return LLMResponse(content="", model=self.model)

    def generate_sync(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None,
        max_retries: int = 3
    ) -> LLMResponse:
        """Synchronous generation for Qwen-Coder with retry and exponential backoff"""
        config = config_override or self.get_config_for_task(task_type)
        formatted_prompt = self.format_prompt(prompt, task_type)
        system_prompt = self.format_system_prompt(task_type)

        # Log prompt size for debugging
        prompt_tokens_estimate = len(f"{system_prompt}\n\n{formatted_prompt}") // 4
        logger.debug(f"Qwen sync request: ~{prompt_tokens_estimate} tokens, task={task_type.value}")

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=120.0) as client:
                    # Use chat completions format for instruction-tuned models
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": formatted_prompt}
                    ]

                    response = client.post(
                        f"{self.endpoint}/chat/completions",
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": config.temperature,
                            "max_tokens": config.max_tokens,
                            "top_p": config.top_p,
                            "stop": config.stop_sequences if config.stop_sequences else None,
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # Chat completions returns message.content, not text
                        content = result["choices"][0].get("message", {}).get("content", "")

                        # Retry on empty response with backoff
                        if not content or not content.strip():
                            finish_reason = result.get("choices", [{}])[0].get("finish_reason", "unknown")
                            usage = result.get("usage", {})
                            logger.warning(
                                f"Empty response from Qwen (sync): "
                                f"finish_reason={finish_reason}, "
                                f"prompt_tokens={usage.get('prompt_tokens', 'N/A')}, "
                                f"completion_tokens={usage.get('completion_tokens', 'N/A')}"
                            )

                            if attempt < max_retries:
                                backoff = _calculate_backoff(attempt)
                                logger.warning(f"Retrying in {backoff:.1f}s ({attempt + 1}/{max_retries})...")
                                time.sleep(backoff)
                                continue
                            else:
                                logger.error("Empty response from Qwen (sync) after all retries")
                                return LLMResponse(
                                    content="[LLM returned empty response - please retry]",
                                    model=self.model,
                                    finish_reason=finish_reason,
                                )

                        llm_response = self.parse_response(content, task_type)
                        llm_response.usage = result.get("usage")
                        llm_response.raw_response = result
                        return llm_response
                    else:
                        # Retry on server errors (5xx) with backoff
                        if response.status_code >= 500 and attempt < max_retries:
                            backoff = _calculate_backoff(attempt)
                            logger.warning(f"Qwen server error {response.status_code}, retrying in {backoff:.1f}s...")
                            time.sleep(backoff)
                            continue
                        logger.error(f"Qwen request failed: {response.status_code}")
                        raise Exception(f"Qwen request failed: {response.status_code}")

            except httpx.TimeoutException:
                if attempt < max_retries:
                    backoff = _calculate_backoff(attempt)
                    logger.warning(f"Qwen request timed out, retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                    continue
                logger.error("Qwen request timed out after all retries")
                raise

        # Should not reach here, but return empty response as fallback
        return LLMResponse(content="", model=self.model)

    async def stream(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Qwen-Coder using chat completions format"""
        config = config_override or self.get_config_for_task(task_type)

        formatted_prompt = self.format_prompt(prompt, task_type)
        system_prompt = self.format_system_prompt(task_type)

        # Use chat completions format
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_prompt}
        ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.endpoint}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "top_p": config.top_p,
                    "stop": config.stop_sequences if config.stop_sequences else None,
                    "stream": True,
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data and data != "[DONE]":
                            import json
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and chunk["choices"]:
                                    # Chat completions streaming returns delta.content
                                    delta = chunk["choices"][0].get("delta", {})
                                    text = delta.get("content", "")
                                    if text:
                                        yield text
                            except json.JSONDecodeError:
                                continue


# Register adapter
LLMProviderFactory.register("qwen", QwenAdapter)
