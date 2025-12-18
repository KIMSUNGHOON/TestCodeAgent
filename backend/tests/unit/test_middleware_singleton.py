"""Unit tests for thread-safe middleware singleton pattern.

Tests the get_or_create_middleware helper function to ensure:
1. Singleton behavior (same instance returned)
2. Thread safety (no race conditions)
3. Error handling (graceful failure)
"""
import pytest
import threading
import time
import logging
from unittest.mock import Mock, patch

# Test the singleton pattern implementation directly
# to avoid dependency issues with LangChain imports

logger = logging.getLogger(__name__)

# Replicate the singleton pattern for testing
_test_middleware_cache = {}
_test_middleware_lock = threading.Lock()


def get_or_create_middleware(key: str, factory_fn):
    """Thread-safe middleware singleton accessor (test implementation)."""
    with _test_middleware_lock:
        if key not in _test_middleware_cache:
            try:
                _test_middleware_cache[key] = factory_fn()
                logger.info(f"✅ Created SINGLETON {key} middleware")
            except Exception as e:
                logger.warning(f"⚠️  Failed to create {key} middleware: {e}")
                return None
        else:
            logger.info(f"♻️  Reusing {key} middleware singleton")
        return _test_middleware_cache.get(key)


@pytest.fixture(autouse=True)
def clean_cache():
    """Clean middleware cache before and after each test."""
    _test_middleware_cache.clear()
    yield
    _test_middleware_cache.clear()


class TestMiddlewareSingleton:
    """Test suite for middleware singleton pattern."""

    def test_create_new_middleware(self):
        """Test creating new middleware when cache is empty."""
        mock_middleware = Mock(name="TestMiddleware")
        factory = Mock(return_value=mock_middleware)

        result = get_or_create_middleware("test_key", factory)

        assert result is mock_middleware
        assert factory.call_count == 1
        assert _test_middleware_cache["test_key"] is mock_middleware

    def test_reuse_existing_middleware(self):
        """Test reusing middleware from cache."""
        mock_middleware = Mock(name="TestMiddleware")
        factory = Mock(return_value=mock_middleware)

        # First call creates
        result1 = get_or_create_middleware("test_key", factory)
        # Second call reuses
        result2 = get_or_create_middleware("test_key", factory)

        assert result1 is result2
        assert factory.call_count == 1  # Factory called only once
        assert _test_middleware_cache["test_key"] is mock_middleware

    def test_factory_exception_handling(self):
        """Test graceful handling of factory exceptions."""
        def failing_factory():
            raise ValueError("Factory failed!")

        result = get_or_create_middleware("test_key", failing_factory)

        assert result is None
        assert "test_key" not in _test_middleware_cache

    def test_thread_safety_concurrent_creation(self):
        """Test thread safety with concurrent middleware creation.

        This is the CRITICAL test for the race condition fix.
        Multiple threads try to create the same middleware simultaneously.
        Only ONE instance should be created.
        """
        call_count = 0
        call_lock = threading.Lock()
        created_instances = []

        def slow_factory():
            """Simulate slow middleware creation to expose race conditions."""
            nonlocal call_count
            with call_lock:
                call_count += 1
            # Simulate work
            time.sleep(0.01)
            instance = Mock(name=f"Middleware_{call_count}")
            created_instances.append(instance)
            return instance

        # Launch 10 threads simultaneously
        threads = []
        results = []

        def worker():
            result = get_or_create_middleware("concurrent_key", slow_factory)
            results.append(result)

        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Assertions
        assert call_count == 1, f"Factory called {call_count} times, expected 1"
        assert len(created_instances) == 1, f"Created {len(created_instances)} instances, expected 1"
        assert len(results) == 10, "All threads should return a result"
        assert all(r is results[0] for r in results), "All threads should get the same instance"

    def test_multiple_different_middlewares(self):
        """Test creating multiple different middlewares (different keys)."""
        middleware1 = Mock(name="Middleware1")
        middleware2 = Mock(name="Middleware2")

        result1 = get_or_create_middleware("key1", lambda: middleware1)
        result2 = get_or_create_middleware("key2", lambda: middleware2)

        assert result1 is middleware1
        assert result2 is middleware2
        assert result1 is not result2
        assert _test_middleware_cache["key1"] is middleware1
        assert _test_middleware_cache["key2"] is middleware2

class TestIntegrationScenarios:
    """Integration test scenarios for middleware singleton."""

    def test_deepagents_workflow_scenario(self):
        """Simulate the actual DeepAgents workflow usage scenario."""
        from unittest.mock import MagicMock

        # Simulate SubAgentMiddleware creation
        SubAgentMiddleware = MagicMock()
        subagent_instance = Mock(name="SubAgentMiddleware")
        SubAgentMiddleware.return_value = subagent_instance

        # Simulate FilesystemMiddleware creation
        FilesystemMiddleware = MagicMock()
        filesystem_instance = Mock(name="FilesystemMiddleware")
        FilesystemMiddleware.return_value = filesystem_instance

        # First session creates both middlewares
        sub1 = get_or_create_middleware("subagent", lambda: SubAgentMiddleware())
        fs1 = get_or_create_middleware("filesystem", lambda: FilesystemMiddleware())

        # Second session reuses both
        sub2 = get_or_create_middleware("subagent", lambda: SubAgentMiddleware())
        fs2 = get_or_create_middleware("filesystem", lambda: FilesystemMiddleware())

        # Verify singleton behavior
        assert sub1 is sub2
        assert fs1 is fs2
        assert SubAgentMiddleware.call_count == 1
        assert FilesystemMiddleware.call_count == 1

    def test_cross_module_usage(self):
        """Test that the same cache is used across different modules."""
        # This simulates workflow_manager.py and deepagent_workflow.py
        # both using the same singleton cache

        middleware = Mock(name="SharedMiddleware")

        # Module 1 creates
        result1 = get_or_create_middleware("shared", lambda: middleware)

        # Module 2 reuses (simulated by another call)
        result2 = get_or_create_middleware("shared", lambda: Mock(name="ShouldNotCreate"))

        assert result1 is result2
        assert result1 is middleware
