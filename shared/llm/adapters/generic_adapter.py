"""Generic LLM Adapter - For GPT, Claude, Llama, Mistral, and other models

This adapter provides a model-agnostic implementation that works with
most OpenAI-compatible API endpoints.
"""

import logging
import httpx
from typing import Optional, AsyncGenerator, Dict, List

from shared.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    TaskType,
    LLMProviderFactory,
)

logger = logging.getLogger(__name__)


# Task-specific system prompts for generic models
GENERIC_SYSTEM_PROMPTS = {
    TaskType.REASONING: """You are an expert AI assistant specialized in analysis and planning.

For complex problems:
1. Think through the problem step by step
2. Consider multiple approaches
3. Identify potential issues
4. Provide a structured analysis

Be thorough but concise in your reasoning.""",

    TaskType.CODING: """You are an expert software engineer.

Guidelines:
- Generate production-ready, executable code
- Include proper error handling
- Follow language best practices
- Add type hints where applicable
- Write clear, self-documenting code

Output format: Provide code in properly formatted code blocks.""",

    TaskType.REVIEW: """You are a senior code reviewer.

Review criteria:
1. Correctness - Does it work as intended?
2. Security - Are there vulnerabilities?
3. Performance - Any obvious inefficiencies?
4. Maintainability - Is it clean and readable?
5. Best practices - Does it follow conventions?

Provide specific, actionable feedback.""",

    TaskType.REFINE: """You are a code improvement specialist.

Your task:
1. Analyze the reported issues carefully
2. Make targeted, minimal fixes
3. Preserve existing functionality
4. Improve code quality
5. Add missing error handling

Focus on quality improvements without over-engineering.""",

    TaskType.GENERAL: """You are a helpful AI assistant specialized in software engineering.

Provide clear, accurate, and actionable responses.
When dealing with code, ensure it is correct and follows best practices.""",
}


class GenericAdapter(BaseLLMProvider):
    """Generic adapter for OpenAI-compatible LLM APIs

    Works with: GPT-4, GPT-3.5, Claude, Llama, Mistral, and similar models.
    """

    @property
    def model_type(self) -> str:
        return "generic"

    def format_system_prompt(self, task_type: TaskType) -> str:
        """Get system prompt for task type"""
        return GENERIC_SYSTEM_PROMPTS.get(task_type, GENERIC_SYSTEM_PROMPTS[TaskType.GENERAL])

    def format_prompt(self, prompt: str, task_type: TaskType) -> str:
        """Format prompt with step-by-step instruction for reasoning"""
        if task_type == TaskType.REASONING:
            return f"""Think through this step by step:

{prompt}

Provide your analysis:"""
        elif task_type == TaskType.CODING:
            return f"""{prompt}

Generate the code now. Respond in JSON format:
{{
    "files": [
        {{
            "filename": "path/to/file.py",
            "content": "complete code here",
            "language": "python",
            "description": "brief description"
        }}
    ]
}}"""
        elif task_type == TaskType.REVIEW:
            return f"""{prompt}

Provide your review in JSON format:
{{
    "approved": true/false,
    "quality_score": 0.0 to 1.0,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "critique": "overall assessment"
}}"""
        else:
            return prompt

    def parse_response(self, response: str, task_type: TaskType) -> LLMResponse:
        """Parse response based on task type"""
        parsed_json = None
        thinking_blocks = None

        # Try to extract JSON for structured tasks
        if task_type in (TaskType.CODING, TaskType.REVIEW, TaskType.REFINE):
            parsed_json = self._extract_json(response)

        return LLMResponse(
            content=response,
            model=self.model,
            parsed_json=parsed_json,
            thinking_blocks=thinking_blocks,
        )

    async def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate response using the LLM API"""
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
                    return self.parse_response(content, task_type)
                else:
                    logger.error(f"LLM request failed: {response.status_code}")
                    raise Exception(f"LLM request failed: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("LLM request timed out")
            raise
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def generate_sync(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Synchronous version of generate"""
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
                    return self.parse_response(content, task_type)
                else:
                    logger.error(f"LLM request failed: {response.status_code}")
                    raise Exception(f"LLM request failed: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("LLM request timed out")
            raise

    async def stream(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        config_override: Optional[LLMConfig] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from the LLM"""
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
LLMProviderFactory.register("generic", GenericAdapter)
LLMProviderFactory.register("gpt", GenericAdapter)
LLMProviderFactory.register("claude", GenericAdapter)
LLMProviderFactory.register("llama", GenericAdapter)
LLMProviderFactory.register("mistral", GenericAdapter)
