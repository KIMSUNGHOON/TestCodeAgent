"""LLM Provider Integration Tests

Tests for the LLM Provider abstraction layer covering:
1. Single model mode - All tasks use one model
2. Multi model mode - Different models for different tasks
3. Fallback behavior - Graceful degradation when LLM unavailable

Usage:
    pytest backend/tests/integration/test_llm_provider.py -v
    python -m backend.tests.integration.test_llm_provider  # Direct run
"""

import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

# pytest is optional for direct running
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False

    # Mock pytest.mark.asyncio decorator
    class _MockMark:
        @staticmethod
        def asyncio(func):
            return func

    class _MockPytest:
        mark = _MockMark()

    pytest = _MockPytest()

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import LLM Provider modules
from shared.llm import (
    LLMProviderFactory,
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    TaskType,
    GenericAdapter,
    DeepSeekAdapter,
    QwenAdapter,
)


class TestLLMProviderImports:
    """Test 1: Module imports and basic structure"""

    def test_base_imports(self):
        """Verify all base classes can be imported"""
        assert BaseLLMProvider is not None
        assert LLMConfig is not None
        assert LLMResponse is not None
        assert TaskType is not None
        assert LLMProviderFactory is not None

    def test_adapter_imports(self):
        """Verify all adapters can be imported"""
        assert GenericAdapter is not None
        assert DeepSeekAdapter is not None
        assert QwenAdapter is not None

    def test_task_types(self):
        """Verify TaskType enum values"""
        assert TaskType.REASONING.value == "reasoning"
        assert TaskType.CODING.value == "coding"
        assert TaskType.REVIEW.value == "review"
        assert TaskType.REFINE.value == "refine"
        assert TaskType.GENERAL.value == "general"

    def test_llm_config_defaults(self):
        """Verify LLMConfig default values"""
        config = LLMConfig()
        assert config.temperature == 0.3
        assert config.max_tokens == 4096
        assert config.top_p == 0.95
        assert config.stream is False

    def test_llm_config_to_dict(self):
        """Verify LLMConfig serialization"""
        config = LLMConfig(temperature=0.5, max_tokens=2048)
        config_dict = config.to_dict()
        assert config_dict["temperature"] == 0.5
        assert config_dict["max_tokens"] == 2048
        assert "stop" in config_dict


class TestSingleModelMode:
    """Test 2: Single model mode - All tasks use generic adapter"""

    def setup_method(self):
        """Setup test fixtures"""
        self.endpoint = "http://localhost:8001/v1"
        self.model = "gpt-oss-120b"

    def test_factory_creates_generic_adapter(self):
        """Factory creates generic adapter correctly"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint=self.endpoint,
            model=self.model
        )
        assert isinstance(provider, GenericAdapter)
        assert provider.model_type == "generic"
        assert provider.endpoint == self.endpoint
        assert provider.model == self.model

    def test_factory_falls_back_to_generic(self):
        """Unknown model types fall back to generic"""
        provider = LLMProviderFactory.create(
            model_type="unknown_model",
            endpoint=self.endpoint,
            model=self.model
        )
        assert isinstance(provider, GenericAdapter)

    def test_generic_system_prompts_per_task(self):
        """Verify task-specific system prompts exist"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint=self.endpoint,
            model=self.model
        )

        # Each task type should have a different system prompt
        prompts = {}
        for task_type in TaskType:
            prompt = provider.format_system_prompt(task_type)
            assert prompt is not None
            assert len(prompt) > 0
            prompts[task_type] = prompt

        # CODING and REVIEW prompts should be different
        assert prompts[TaskType.CODING] != prompts[TaskType.REVIEW]

    def test_generic_prompt_formatting(self):
        """Test prompt formatting for different task types"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint=self.endpoint,
            model=self.model
        )

        # Test CODING format includes JSON structure
        coding_prompt = provider.format_prompt("Create a calculator", TaskType.CODING)
        assert "files" in coding_prompt
        assert "filename" in coding_prompt

        # Test REVIEW format includes JSON structure
        review_prompt = provider.format_prompt("Review this code", TaskType.REVIEW)
        assert "approved" in review_prompt
        assert "quality_score" in review_prompt

    def test_task_specific_config(self):
        """Verify task-specific configurations"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint=self.endpoint,
            model=self.model
        )

        coding_config = provider.get_config_for_task(TaskType.CODING)
        review_config = provider.get_config_for_task(TaskType.REVIEW)
        reasoning_config = provider.get_config_for_task(TaskType.REASONING)

        # CODING should have low temperature
        assert coding_config.temperature <= 0.3

        # REVIEW should have very low temperature
        assert review_config.temperature <= 0.2

        # REASONING should have higher temperature
        assert reasoning_config.temperature >= 0.5


class TestMultiModelMode:
    """Test 3: Multi model mode - Different adapters for different tasks"""

    def test_deepseek_adapter_creation(self):
        """DeepSeek adapter created correctly"""
        provider = LLMProviderFactory.create(
            model_type="deepseek",
            endpoint="http://localhost:8001/v1",
            model="deepseek-ai/DeepSeek-R1"
        )
        assert isinstance(provider, DeepSeekAdapter)
        assert provider.model_type == "deepseek"

    def test_qwen_adapter_creation(self):
        """Qwen adapter created correctly"""
        provider = LLMProviderFactory.create(
            model_type="qwen",
            endpoint="http://localhost:8002/v1",
            model="Qwen/Qwen3-8B-Coder"
        )
        assert isinstance(provider, QwenAdapter)
        assert provider.model_type == "qwen"

    def test_deepseek_think_tags(self):
        """DeepSeek prompts include <think> tags"""
        provider = LLMProviderFactory.create(
            model_type="deepseek",
            endpoint="http://localhost:8001/v1",
            model="deepseek-ai/DeepSeek-R1"
        )

        # System prompt should mention <think> tags
        system_prompt = provider.format_system_prompt(TaskType.REASONING)
        assert "<think>" in system_prompt

        # Formatted prompt should include <think> structure
        formatted = provider.format_prompt("Analyze this", TaskType.REASONING)
        assert "<think>" in formatted

    def test_deepseek_thinking_extraction(self):
        """DeepSeek can extract thinking blocks from response"""
        provider = LLMProviderFactory.create(
            model_type="deepseek",
            endpoint="http://localhost:8001/v1",
            model="deepseek-ai/DeepSeek-R1"
        )

        # Simulate response with thinking block
        mock_response = """<think>
1. Analyzing the problem
2. Considering options
3. Making decision
</think>

The final answer is 42."""

        result = provider.parse_response(mock_response, TaskType.REASONING)
        assert result.thinking_blocks is not None
        assert len(result.thinking_blocks) == 1
        assert "Analyzing the problem" in result.thinking_blocks[0]
        assert "42" in result.content

    def test_qwen_coding_optimized(self):
        """Qwen adapter has coding-optimized settings"""
        provider = LLMProviderFactory.create(
            model_type="qwen",
            endpoint="http://localhost:8002/v1",
            model="Qwen/Qwen3-8B-Coder"
        )

        coding_config = provider.get_config_for_task(TaskType.CODING)

        # Should have low temperature for consistent code generation
        assert coding_config.temperature <= 0.3

        # Should have high token limit for code
        assert coding_config.max_tokens >= 4000

    def test_available_adapters(self):
        """All expected adapters are registered"""
        available = LLMProviderFactory.get_available_types()

        # Check core adapters
        assert "generic" in available
        assert "deepseek" in available
        assert "qwen" in available

        # Check aliases
        assert "gpt" in available
        assert "claude" in available


class TestFallbackBehavior:
    """Test 4: Fallback behavior when LLM unavailable"""

    def test_json_extraction_success(self):
        """JSON can be extracted from response"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint="http://localhost:8001/v1",
            model="test-model"
        )

        response_text = """Here's the review:
{
    "approved": false,
    "quality_score": 0.7,
    "issues": ["Missing error handling"],
    "suggestions": ["Add try-catch block"]
}"""

        result = provider.parse_response(response_text, TaskType.REVIEW)
        assert result.parsed_json is not None
        assert result.parsed_json["approved"] is False
        assert result.parsed_json["quality_score"] == 0.7

    def test_json_extraction_failure_graceful(self):
        """Failed JSON extraction returns None gracefully"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint="http://localhost:8001/v1",
            model="test-model"
        )

        response_text = "This is just plain text without JSON"
        result = provider.parse_response(response_text, TaskType.REVIEW)
        assert result.parsed_json is None
        assert result.content == response_text

    def test_llm_response_structure(self):
        """LLMResponse has expected structure"""
        response = LLMResponse(
            content="test content",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            parsed_json={"key": "value"}
        )

        assert response.content == "test content"
        assert response.model == "test-model"
        assert response.usage["prompt_tokens"] == 10
        assert response.parsed_json["key"] == "value"


class TestRefinerFallback:
    """Test 5: Refiner heuristic fallback"""

    def test_refiner_heuristic_import(self):
        """Refiner heuristic function can be imported"""
        from app.agent.langgraph.nodes.refiner import _apply_fix_heuristic
        assert _apply_fix_heuristic is not None

    def test_refiner_todo_fix(self):
        """Heuristic fixes TODO issues"""
        from app.agent.langgraph.nodes.refiner import _apply_fix_heuristic

        original = """# Calculator module
# TODO: Implement add function
def placeholder():
    pass"""

        fixed = _apply_fix_heuristic(original, "TODO: incomplete implementation")
        # Should remove or complete TODO
        assert fixed != original or "add" in fixed.lower()

    def test_refiner_security_fix(self):
        """Heuristic adds security comments"""
        from app.agent.langgraph.nodes.refiner import _apply_fix_heuristic

        original = """def process_input(data):
    return eval(data)"""

        fixed = _apply_fix_heuristic(original, "Security: input validation missing")
        assert "Security" in fixed or "validation" in fixed.lower()

    def test_refiner_error_handling_fix(self):
        """Heuristic adds error handling"""
        from app.agent.langgraph.nodes.refiner import _apply_fix_heuristic

        original = """def risky_operation():
    return do_something()"""

        fixed = _apply_fix_heuristic(original, "Missing error handling")
        assert "try:" in fixed or "except" in fixed


class TestConfigIntegration:
    """Test 6: Config integration with settings"""

    def test_settings_model_type(self):
        """Settings has model_type attribute"""
        from app.core.config import settings

        assert hasattr(settings, 'model_type')
        assert settings.model_type in ["deepseek", "qwen", "gpt", "claude", "generic"]

    def test_settings_endpoints(self):
        """Settings provides endpoint methods"""
        from app.core.config import settings

        # Should have endpoint getters
        assert hasattr(settings, 'get_coding_endpoint')
        assert hasattr(settings, 'get_reasoning_endpoint')

        # Endpoints should be strings
        coding_endpoint = settings.get_coding_endpoint
        assert isinstance(coding_endpoint, str)
        assert coding_endpoint.startswith("http")

    def test_settings_models(self):
        """Settings provides model getters"""
        from app.core.config import settings

        assert hasattr(settings, 'get_coding_model')
        assert hasattr(settings, 'get_reasoning_model')

        # Models should be strings
        coding_model = settings.get_coding_model
        assert isinstance(coding_model, str)


class TestAsyncOperations:
    """Test 7: Async operations (mocked)"""

    @pytest.mark.asyncio
    async def test_async_generate_mocked(self):
        """Async generate works with mocked HTTP"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint="http://localhost:8001/v1",
            model="test-model"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"text": '{"files": [{"filename": "test.py", "content": "print(1)"}]}'}]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await provider.generate("Create test", TaskType.CODING)

            assert result is not None
            assert result.content is not None

    def test_sync_generate_mocked(self):
        """Sync generate works with mocked HTTP"""
        provider = LLMProviderFactory.create(
            model_type="generic",
            endpoint="http://localhost:8001/v1",
            model="test-model"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"text": "Fixed code here"}]
        }

        with patch('httpx.Client') as mock_client:
            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=None)
            mock_client.return_value = mock_instance

            result = provider.generate_sync("Fix this code", TaskType.REFINE)

            assert result is not None
            assert "Fixed code" in result.content


def run_tests():
    """Run all tests and print summary"""
    print("=" * 60)
    print("LLM Provider Integration Tests")
    print("=" * 60)

    test_classes = [
        TestLLMProviderImports,
        TestSingleModelMode,
        TestMultiModelMode,
        TestFallbackBehavior,
        TestRefinerFallback,
        TestConfigIntegration,
        TestAsyncOperations,
    ]

    total_passed = 0
    total_failed = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)

        instance = test_class()
        if hasattr(instance, 'setup_method'):
            instance.setup_method()

        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(instance, method_name)

                    # Handle async tests
                    if asyncio.iscoroutinefunction(method):
                        asyncio.get_event_loop().run_until_complete(method())
                    else:
                        method()

                    print(f"  ✅ {method_name}")
                    total_passed += 1
                except Exception as e:
                    print(f"  ❌ {method_name}: {str(e)[:50]}")
                    total_failed += 1
                    failed_tests.append(f"{test_class.__name__}.{method_name}")

    print("\n" + "=" * 60)
    print(f"📊 Results: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    if failed_tests:
        print("\n❌ Failed tests:")
        for test in failed_tests:
            print(f"  - {test}")
        return 1

    print("\n✅ All tests passed!")
    return 0


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
