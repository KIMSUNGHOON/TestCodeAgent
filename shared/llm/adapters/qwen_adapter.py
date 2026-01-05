"""Qwen-Coder LLM Adapter

Specialized adapter for Qwen2.5-Coder optimized for code generation tasks.
"""

import logging
import httpx
from typing import Optional, AsyncGenerator

from shared.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    TaskType,
    LLMProviderFactory,
)

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
        config_override: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate response from Qwen-Coder"""
        config = config_override or self.get_config_for_task(task_type)
        formatted_prompt = self.format_prompt(prompt, task_type)
        system_prompt = self.format_system_prompt(task_type)

        full_prompt = f"{system_prompt}\n\n{formatted_prompt}"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.endpoint}/completions",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        **config.to_dict(),
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["text"]

                    llm_response = self.parse_response(content, task_type)
                    llm_response.usage = result.get("usage")
                    llm_response.raw_response = result
                    return llm_response
                else:
                    logger.error(f"Qwen request failed: {response.status_code}")
                    raise Exception(f"Qwen request failed: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Qwen request timed out")
            raise

    def generate_sync(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Synchronous generation for Qwen-Coder"""
        config = config_override or self.get_config_for_task(task_type)
        formatted_prompt = self.format_prompt(prompt, task_type)
        system_prompt = self.format_system_prompt(task_type)

        full_prompt = f"{system_prompt}\n\n{formatted_prompt}"

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.endpoint}/completions",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        **config.to_dict(),
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["text"]

                    llm_response = self.parse_response(content, task_type)
                    llm_response.usage = result.get("usage")
                    llm_response.raw_response = result
                    return llm_response
                else:
                    logger.error(f"Qwen request failed: {response.status_code}")
                    raise Exception(f"Qwen request failed: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Qwen request timed out")
            raise

    async def stream(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Qwen-Coder"""
        config = config_override or self.get_config_for_task(task_type)
        config.stream = True

        formatted_prompt = self.format_prompt(prompt, task_type)
        system_prompt = self.format_system_prompt(task_type)
        full_prompt = f"{system_prompt}\n\n{formatted_prompt}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.endpoint}/completions",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    **config.to_dict(),
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
                                    text = chunk["choices"][0].get("text", "")
                                    if text:
                                        yield text
                            except json.JSONDecodeError:
                                continue


# Register adapter
LLMProviderFactory.register("qwen", QwenAdapter)
