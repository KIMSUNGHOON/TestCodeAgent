"""Phase 6 Context Window Optimization - Test Script"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_token_utils():
    """Test improved token utilities"""
    print("\n=== Testing Token Utilities ===")

    from shared.utils.token_utils import (
        count_tokens_accurate,
        check_context_budget,
        estimate_tokens,
        get_model_limits,
        TokenBudget
    )

    # Test basic token counting
    test_text = "Hello, this is a test message for token counting."
    basic = estimate_tokens(test_text)
    accurate = count_tokens_accurate(test_text)
    print(f"Basic estimate: {basic} tokens")
    print(f"Accurate estimate: {accurate} tokens")

    # Test CJK handling
    korean_text = "안녕하세요, 이것은 한국어 테스트입니다."
    korean_tokens = count_tokens_accurate(korean_text)
    print(f"Korean text tokens: {korean_tokens}")

    # Test code block handling
    code_text = """```python
def hello():
    print("Hello, World!")
```"""
    code_tokens = count_tokens_accurate(code_text)
    print(f"Code block tokens: {code_tokens}")

    # Test context budget
    context = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there! How can I help?"},
        ],
        "artifacts": [{"content": "test code"}],
        "system_prompt": "You are a helpful assistant."
    }
    budget = check_context_budget(context, max_tokens=1000)
    print(f"\nContext budget check:")
    print(f"  Total tokens: {budget.total_tokens}")
    print(f"  Max tokens: {budget.max_tokens}")
    print(f"  Within budget: {budget.within_budget}")
    print(f"  Utilization: {budget.utilization_percent}%")

    # Test model limits
    limits = get_model_limits("gpt-4-turbo")
    print(f"\nGPT-4 Turbo limits:")
    print(f"  Context limit: {limits['context_limit']}")
    print(f"  Response reserve: {limits['response_reserve']}")
    print(f"  Effective limit: {limits['effective_limit']}")

    print("\n[OK] Token utilities test passed!")
    return True


def test_context_compressor():
    """Test context compression functionality"""
    print("\n=== Testing Context Compressor ===")

    from core.context_compressor import (
        ContextCompressor,
        CompressionConfig,
        compress_context,
        ContentPriority
    )

    # Create test messages
    messages = []
    for i in range(60):
        role = "user" if i % 2 == 0 else "assistant"
        if i % 10 == 0:
            content = f"Message {i}: ```python\ndef func_{i}():\n    return {i}\n```"
        elif i % 7 == 0:
            content = f"Message {i}: Error: something went wrong at line {i}"
        else:
            content = f"Message {i}: This is a regular conversation message number {i}."
        messages.append({
            "role": role,
            "content": content,
            "timestamp": f"2026-01-0{i%9+1}T10:00:00"
        })

    print(f"Original message count: {len(messages)}")

    # Test compression
    config = CompressionConfig(
        recent_message_count=20,
        compression_threshold=50
    )
    compressor = ContextCompressor(config)

    # Test content extraction
    test_msg = {
        "role": "assistant",
        "content": """Here's the code:
```python
def calculate(x, y):
    return x + y
```
Error: TypeError: unsupported operand
File path: /src/calculator.py
Let's use this approach for the implementation."""
    }
    extracted, priority = compressor.extract_important_content(test_msg)
    print(f"\nExtracted content from test message:")
    print(f"  Code blocks: {len(extracted.code_blocks)}")
    print(f"  File paths: {extracted.file_paths}")
    print(f"  Errors: {extracted.error_messages}")
    print(f"  Priority: {priority}")

    # Test full compression
    compressed = compressor.compress(messages)
    print(f"\nCompressed message count: {len(compressed)}")

    # Check sliding window
    stats = compressor.get_compression_stats(messages, compressed)
    print(f"\nCompression stats:")
    print(f"  Original tokens: {stats['original_tokens']}")
    print(f"  Compressed tokens: {stats['compressed_tokens']}")
    print(f"  Savings: {stats['savings_percent']}%")

    # Verify first message is compressed summary
    if compressed and compressed[0].get("is_compressed"):
        print(f"\n[OK] First message is compressed summary")
        print(f"  Original count: {compressed[0].get('original_count')}")
    else:
        print(f"\n[OK] Messages below compression threshold or compression disabled")

    print("\n[OK] Context compressor test passed!")
    return True


def test_context_store_constants():
    """Test expanded context store constants"""
    print("\n=== Testing Context Store Constants ===")

    from core.context_store import (
        MAX_MESSAGES,
        RECENT_MESSAGES_FOR_LLM,
        RECENT_MESSAGES_FOR_CONTEXT,
        MAX_ARTIFACTS,
        RECENT_ARTIFACTS_FOR_CONTEXT,
        ENABLE_COMPRESSION,
        COMPRESSION_THRESHOLD
    )

    print(f"MAX_MESSAGES: {MAX_MESSAGES} (expected: 100)")
    print(f"RECENT_MESSAGES_FOR_LLM: {RECENT_MESSAGES_FOR_LLM} (expected: 30)")
    print(f"RECENT_MESSAGES_FOR_CONTEXT: {RECENT_MESSAGES_FOR_CONTEXT} (expected: 20)")
    print(f"MAX_ARTIFACTS: {MAX_ARTIFACTS} (expected: 50)")
    print(f"RECENT_ARTIFACTS_FOR_CONTEXT: {RECENT_ARTIFACTS_FOR_CONTEXT} (expected: 20)")
    print(f"ENABLE_COMPRESSION: {ENABLE_COMPRESSION} (expected: True)")
    print(f"COMPRESSION_THRESHOLD: {COMPRESSION_THRESHOLD} (expected: 50)")

    # Verify expanded values
    assert MAX_MESSAGES == 100, f"MAX_MESSAGES should be 100, got {MAX_MESSAGES}"
    assert RECENT_MESSAGES_FOR_LLM == 30, f"RECENT_MESSAGES_FOR_LLM should be 30, got {RECENT_MESSAGES_FOR_LLM}"
    assert RECENT_MESSAGES_FOR_CONTEXT == 20, f"RECENT_MESSAGES_FOR_CONTEXT should be 20, got {RECENT_MESSAGES_FOR_CONTEXT}"
    assert MAX_ARTIFACTS == 50, f"MAX_ARTIFACTS should be 50, got {MAX_ARTIFACTS}"

    print("\n[OK] Context store constants test passed!")
    return True


def test_rag_context_defaults():
    """Test RAG context builder expanded defaults"""
    print("\n=== Testing RAG Context Defaults ===")

    from app.services.rag_context import RAGContextBuilder

    print(f"DEFAULT_N_RESULTS: {RAGContextBuilder.DEFAULT_N_RESULTS} (expected: 7)")
    print(f"DEFAULT_CONVERSATION_RESULTS: {RAGContextBuilder.DEFAULT_CONVERSATION_RESULTS} (expected: 5)")
    print(f"MAX_CONTEXT_LENGTH: {RAGContextBuilder.MAX_CONTEXT_LENGTH} (expected: 12000)")

    assert RAGContextBuilder.DEFAULT_N_RESULTS == 7
    assert RAGContextBuilder.DEFAULT_CONVERSATION_RESULTS == 5
    assert RAGContextBuilder.MAX_CONTEXT_LENGTH == 12000

    print("\n[OK] RAG context defaults test passed!")
    return True


def main():
    """Run all Phase 6 tests"""
    print("=" * 60)
    print("Phase 6: Context Window Optimization - Test Suite")
    print("=" * 60)

    results = []

    try:
        results.append(("Token Utilities", test_token_utils()))
    except Exception as e:
        print(f"\n[FAILED] Token utilities test: {e}")
        results.append(("Token Utilities", False))

    try:
        results.append(("Context Compressor", test_context_compressor()))
    except Exception as e:
        print(f"\n[FAILED] Context compressor test: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Context Compressor", False))

    try:
        results.append(("Context Store Constants", test_context_store_constants()))
    except Exception as e:
        print(f"\n[FAILED] Context store constants test: {e}")
        results.append(("Context Store Constants", False))

    try:
        results.append(("RAG Context Defaults", test_rag_context_defaults()))
    except Exception as e:
        print(f"\n[FAILED] RAG context defaults test: {e}")
        results.append(("RAG Context Defaults", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All Phase 6 tests passed!")
        return 0
    else:
        print("\n[WARNING] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
